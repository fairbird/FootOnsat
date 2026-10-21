# -*- coding: utf-8 -*-
import json
import re
import os
import subprocess
import time
import requests
import ssl
from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure
from twisted.web.client import getPage
from Components.config import config

from .compat import *
from .setup import *
from .fetch_sources import WebClientContextFactory


## url for Standings table for sofascore
json_urls = {
	"championsleague": "https://www.sofascore.com/tournament/football/europe/uefa-champions-league/7#id:96518",
	"europaleague": "https://www.sofascore.com/tournament/football/europe/uefa-europa-league/679#id:96522",
	"ConferenceLeague": "https://www.sofascore.com/tournament/football/europe/uefa-europa-conference-league/17015#id:96529",
	"premierleague": "https://www.sofascore.com/tournament/football/england/premier-league/17#id:96668",
	"championship": "https://www.sofascore.com/tournament/football/england/championship/18#id:97037",
	"seriea": "https://www.sofascore.com/tournament/football/italy/serie-a/23#id:95836",
	"ligue1": "https://www.sofascore.com/tournament/football/france/ligue-1/34#id:96127",
	"laliga": "https://www.sofascore.com/tournament/football/spain/laliga/8#id:97268",
	"laliga2": "https://www.sofascore.com/tournament/football/spain/laliga-2/54#id:97280",
	"bundesliga": "https://www.sofascore.com/tournament/football/germany/bundesliga/35#id:97464",
	"bundesliga2": "https://www.sofascore.com/tournament/football/germany/2-bundesliga/44#id:97406",
	"liganos": "https://www.sofascore.com/tournament/football/portugal/liga-portugal-betclic/238#id:97436",
	"belgianpro": "https://www.sofascore.com/tournament/football/belgium/pro-league/38#id:96616",
	"superLig": "https://www.sofascore.com/tournament/football/turkey/trendyol-super-lig/52#id:98080",
	"eredivisie": "https://www.sofascore.com/tournament/football/netherlands/eredivisie/37#id:96143",
	"saudiarabia": "https://www.sofascore.com/tournament/football/saudi-arabia/saudi-pro-league/955#id:99275",
	"afcchampions": "https://www.sofascore.com/tournament/football/asia/afc-champions-league/463#id:99217",
	"afcchampionstwo": "https://www.sofascore.com/tournament/football/asia/afc-cup/668#id:97465",
	"basketball": "https://www.sofascore.com/tournament/basketball/international/euroleague/138#id:99582",
	"nba": "https://www.sofascore.com/tournament/basketball/usa/nba/132#id:100772",
	"hockey": "https://www.sofascore.com/tournament/ice-hockey/usa/nhl/234#id:98450",
	"nfl": "https://www.sofascore.com/tournament/american-football/usa/nfl/9464#id:94366",
}

## url for Standings table for ESPN
ESPN_SLUGS = {
	"championsleague": "uefa.champions",
	"europaleague": "uefa.europa",
	"conferenceleague": "uefa.europa.conf",
	"euroleague": "basketball/euroleague",
	"basketball": "basketball/euroleague",
	"nba": "basketball/nba",
	"premierleague": "eng.1",
	"championship": "eng.2",
	"seriea": "ita.1",
	"ligue1": "fra.1",
	"laliga": "esp.1",
	"laliga2": "esp.2",
	"bundesliga": "ger.1",
	"bundesliga2": "ger.2",
	"liganos": "por.1",
	"belgianpro": "bel.1",
	"superlig": "tur.1",
	"eredivisie": "ned.1",
	"saudiarabia": "ksa.1",
	"afcchampions": "afc.champions",
	"afcchampionstwo": "afc.cup",
}


def _make_sofa_session_py2():
	if debug_Standings or debug_MatchDetails or debug_MatchStatistics or debug_MatchMedia:
		logdata("SofaSession", "Building PY2 session with TLSAdapter...")

	session = requests.Session()

	try:
		from .fetch_sources import TLSAdapter, _load_ss_cookies
		session.mount("https://", TLSAdapter())
		if debug_Standings or debug_MatchDetails or debug_MatchStatistics or debug_MatchMedia:
			logdata("SofaSession", "Mounted https:// adapter successfully")
	except Exception as _me:
		if debug_Standings or debug_MatchDetails or debug_MatchStatistics or debug_MatchMedia:
			logdata("SofaSession", "Mount adapter FAILED: %s" % str(_me))
		_load_ss_cookies = None

	try:
		if _load_ss_cookies is not None:
			_load_ss_cookies(session)
			if debug_Standings or debug_MatchDetails or debug_MatchStatistics or debug_MatchMedia:
				logdata("SofaSession", "Loaded cookies, count=%d" % len(session.cookies))
	except Exception as _le:
		if debug_Standings or debug_MatchDetails or debug_MatchStatistics or debug_MatchMedia:
			logdata("SofaSession", "Cookie load FAILED: %s" % str(_le))

	return session


def is_standings_available(source, link):
	if link.lower() in ("basketball", "euroleague"):
		return True
	if source == "espn":
		return link.lower() in ESPN_SLUGS
	if source == "sportscore":
		return False
	if source == "flashscore":
		return link in json_urls
	return link in json_urls


def get_standings_url(source, link):
	if link.lower() in ("basketball", "euroleague"):
		return json_urls.get("basketball")
	if source == "espn":
		return link if link.lower() in ESPN_SLUGS else None
	if source == "sportscore":
		return None
	return json_urls.get(link)

FS_BASE = "https://global.flashscore.ninja/2/x/feed/"
FS_HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
	'x-fsign': 'SW9D1eZo',
	'Referer': 'https://www.flashscore.com/',
	'Accept': '*/*',
}

def _fs_request(endpoint, timeout=20):
	try:
		headers = dict(FS_HEADERS)
		# Reuse the same fsign fetcher from fetch_sources
		from .fetch_sources import _get_fs_fsign
		headers['x-fsign'] = _get_fs_fsign()
		r = requests.get(FS_BASE + endpoint, headers=headers, timeout=timeout, verify=False)
		if r.status_code == 200:
			return r.text
		return None
	except Exception:
		return None

def _fs_parse(text):
	if not text:
		return []
	blocks = []
	for chunk in text.split('~'):
		chunk = chunk.strip()
		if not chunk or '÷' not in chunk:
			continue
		fields = []
		for f in chunk.split('¬'):
			if '÷' not in f:
				continue
			k, v = f.split('÷', 1)
			fields.append((k, v))
		if fields:
			blocks.append(fields)
	return blocks


# =========================================================
# Standings
# =========================================================

class StandingsFetcherBase(object):
	def __init__(self, screen, league, url):
		self.screen = screen
		self.league = league
		self.url = url

	def fetch(self):
		raise NotImplementedError


class SofaScoreStandings(StandingsFetcherBase):
	def fetch(self):
		if debug_Standings:
			logdata("StandingsScreen", "SofaScore.fetch started | league=%s | url=%s" % (self.league, self.url))
		url_to_parse = self.url
		if not isinstance(url_to_parse, compat_str):
			url_to_parse = str(url_to_parse)
		parsed_url = compat_urlparse(url_to_parse)
		path_parts = [p for p in parsed_url.path.split('/') if p]
		tournament_id = None
		season_id = None
		try:
			if path_parts and path_parts[-1].isdigit():
				tournament_id = path_parts[-1]
			if parsed_url.fragment and parsed_url.fragment.startswith('id:'):
				season_id = parsed_url.fragment.split(':')[-1]
		except Exception as e:
			if debug_Standings:
				logdata("StandingsScreen", "ERROR during URL parsing: %s" % str(e))
		if debug_Standings:
			logdata("StandingsScreen", "Parsed tournament_id=%s season_id=%s" % (tournament_id, season_id))
		if not tournament_id or not season_id or not tournament_id.isdigit() or not season_id.isdigit():
			if debug_Standings:
				logdata("StandingsScreen", "CRITICAL ERROR: Failed to extract numeric IDs.")
			self.screen.standings_data = []
			self.screen.display_standings()
			return
		api_url = "https://www.sofascore.com/api/v1/unique-tournament/{}/season/{}/standings/total".format(tournament_id, season_id)
		if debug_Standings:
			logdata("StandingsScreen", "Using SofaScore API URL: %s" % api_url)
		if PY3:
			def _fetch_standings_py3():
				headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.sofascore.com/', 'Origin': 'https://www.sofascore.com', 'Accept': 'application/json'}
				try:
					r = requests.get(api_url, headers=headers, timeout=15, verify=False)
					return r.content if r.status_code == 200 else None
				except Exception:
					return None
			d = deferToThread(_fetch_standings_py3)
			d.addCallback(self.screen._parse_standings_data)
			d.addErrback(self.screen._standing_error_handler, api_url)
		else:
			headers2 = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
				'Referer': 'https://www.sofascore.com/',
				'Origin': 'https://www.sofascore.com',
				'Accept': 'application/json'
			}
			def _fetch_with_requests_py2():
				try:
					s = _make_sofa_session_py2()
					s.headers.update(headers2)
					s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
					r = s.get(api_url, timeout=15, verify=False)
					if r.status_code == 403:
						r = s.get(api_url, timeout=15, verify=False)
					r.raise_for_status()
					if debug_Standings:
						logdata("StandingsScreen", "PY2 fetch OK, len=%d" % len(r.content))
					return r.content
				except Exception as e:
					if debug_Standings:
						logdata("StandingsScreen", "PY2 fetch failed: %s" % str(e))
					raise Exception("SofaScore fetch failed: %s" % str(e))
			d = deferToThread(_fetch_with_requests_py2)
			d.addCallback(self.screen._parse_standings_data)
			d.addErrback(self.screen._standing_error_handler, api_url)


class ESPNStandings(StandingsFetcherBase):
	def fetch(self):
		if debug_Standings:
			logdata("StandingsScreen", "ESPN.fetch started | league=%s" % self.league)
		slug = ESPN_SLUGS.get(self.league.lower())
		if not slug:
			if debug_Standings:
				logdata("StandingsScreen", "ESPN: no mapping for league %s" % self.league)
			self.screen.standings_data = []
			self.screen.display_standings()
			return
		sport_type = "soccer"
		if slug.startswith("basketball/"):
			sport_type = "basketball"
			slug = slug.replace("basketball/", "")
		url = "https://site.api.espn.com/apis/v2/sports/{}/{}/standings".format(sport_type, slug)
		if slug == "euroleague":
			url += "?season=2026"
		if debug_Standings:
			logdata("StandingsScreen", "ESPN API URL: %s" % url)
		def _fetch():
			try:
				r = requests.get(url, timeout=15, verify=False, headers={
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
					'Accept': 'application/json',
				})
				if debug_Standings:
					logdata("StandingsScreen", "ESPN HTTP status=%d len=%d" % (r.status_code, len(r.content) if r.content else 0))
				if r.status_code == 200:
					return r.content
				return None
			except Exception as e:
				if debug_Standings:
					logdata("StandingsScreen", "ESPN fetch error: %s" % str(e)[:200])
				return None
		d = deferToThread(_fetch)
		d.addCallback(self._parse)
		d.addErrback(self._err)

	def _err(self, failure):
		if debug_Standings:
			logdata("StandingsScreen", "ESPN deferred errback: %s" % failure.getErrorMessage())
		self.screen.standings_data = []
		try:
			self.screen.display_standings()
		except Exception:
			pass

	def _parse(self, raw):
		if debug_Standings:
			logdata("StandingsScreen", "ESPN._parse started | raw_len=%d" % (len(raw) if raw else 0))
		if not raw:
			if debug_Standings:
				logdata("StandingsScreen", "ESPN._parse: no raw data")
			self.screen.standings_data = []
			try:
				self.screen.display_standings()
			except Exception:
				pass
			return
		try:
			data = json.loads(raw.decode('utf-8', 'ignore'))
		except Exception as e:
			if debug_Standings:
				logdata("StandingsScreen", "ESPN._parse JSON error: %s" % str(e))
			self.screen.standings_data = []
			try:
				self.screen.display_standings()
			except Exception:
				pass
			return
		if debug_Standings:
			logdata("StandingsScreen", "ESPN._parse TOP_KEYS: %s" % list(data.keys())[:15])
		standings = []
		children = data.get("children", []) or [data]
		if debug_Standings:
			logdata("StandingsScreen", "ESPN._parse children=%d" % len(children))
		for child in children:
			group_name = child.get("name", "")
			if group_name:
				title = "Table %s" % group_name
				if not PY3:
					title = title.encode("utf-8")
				standings.append(title)
			table = child.get("standings", {})
			entries = table.get("entries", [])
			if debug_Standings:
				logdata("StandingsScreen", "ESPN._parse child='%s' entries=%d" % (group_name, len(entries)))
			for entry in entries:
				team = entry.get("team", {})
				team_name = team.get("displayName", "Unknown")
				logo_url = ""
				logos = team.get("logos", [])
				if logos:
					logo_url = logos[0].get("href", "")
				stats = {}
				for stat in entry.get("stats", []):
					stats[stat.get("name", "")] = stat.get("displayValue", stat.get("value", ""))
				position = str(stats.get("rank", ""))
				played = str(stats.get("gamesPlayed", ""))
				wins = str(stats.get("wins", ""))
				draws = str(stats.get("ties", ""))
				losses = str(stats.get("losses", ""))
				points = str(stats.get("points", ""))
				goals_scored = str(stats.get("pointsFor", ""))
				goals_conceded = str(stats.get("pointsAgainst", ""))
				goal_diff = str(stats.get("pointDifferential", ""))
				standings.append([
					team_name, position, played, points, wins, draws, losses,
					goals_scored, goals_conceded, goal_diff, logo_url
				])
		if debug_Standings:
			logdata("StandingsScreen", "ESPN._parse total standings=%d" % len(standings))
		self.screen.standings_data = standings
		if standings:
			deferToThread(self.screen.check_and_download_logos).addCallback(lambda x: self.screen.display_standings())
		else:
			try:
				self.screen.display_standings()
			except Exception:
				pass


class SportScoreStandings(StandingsFetcherBase):
	def fetch(self):
		if debug_Standings:
			logdata("StandingsScreen", "SportScore standings not implemented")
		self.screen.standings_data = []
		try:
			self.screen.display_standings()
		except Exception:
			pass


def get_standings_fetcher(source, screen, league, url):
	if league.lower() in ("basketball", "euroleague"):
		return SofaScoreStandings(screen, league, url)
	if source == "espn":
		return ESPNStandings(screen, league, url)
	if source == "sportscore":
		return SportScoreStandings(screen, league, url)
	if source == "flashscore":
		return FlashscoreStandings(screen, league, url)
	return SofaScoreStandings(screen, league, url)


# =========================================================
# Match Details
# =========================================================

class MatchDetailsFetcherBase(object):
	def __init__(self, screen, event_id):
		self.screen = screen
		self.event_id = event_id

	def fetch(self):
		raise NotImplementedError


class SofaScoreMatchDetails(MatchDetailsFetcherBase):
	def fetch(self):
		if debug_MatchDetails:
			logdata("MatchDetails", "SofaScore.fetch started | event_id=%s" % self.event_id)
		url_incidents = "https://www.sofascore.com/api/v1/event/{}/incidents".format(self.event_id)
		url_event = "https://www.sofascore.com/api/v1/event/{}".format(self.event_id)
		if debug_MatchDetails:
			logdata("MatchDetails", "URL incidents=%s" % url_incidents)
			logdata("MatchDetails", "URL event=%s" % url_event)

		def _fetch_details():
			def _get_data(url):
				try:
					out = subprocess.check_output([
						"/usr/bin/curl_chrome150", "-s", "-L", "-k",
						"--max-time", "20",
						"-b", "/tmp/ss_cf_cookies.txt",
						"-H", "X-Requested-With: XMLHttpRequest",
						"-H", "Accept: application/json, text/plain, */*",
						"-H", "Referer: https://www.sofascore.com/",
						"-H", "Origin: https://www.sofascore.com",
						url
					], stderr=subprocess.PIPE)
					if out:
						return json.loads(out.decode('utf-8', 'ignore'))
				except Exception:
					pass
				return None
			
			r1 = _get_data(url_incidents)
			r2 = _get_data(url_event)
			
			parsed = []
			if r1: parsed.append(r1)
			if r2: parsed.append(r2)
			return parsed if parsed else None

		d = deferToThread(_fetch_details)
		d.addCallback(self.screen.process_data)


class ESPNMatchDetails(MatchDetailsFetcherBase):
	def fetch(self):
		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN.fetch started | event_id=%s" % self.event_id)
		if "|" not in self.event_id:
			if debug_MatchDetails:
				logdata("MatchDetails", "ESPN: invalid event_id format (no pipe)")
			self.screen.process_data(None)
			return
		league_slug, ev_id = self.event_id.split("|", 1)

		summary_url = "https://site.web.api.espn.com/apis/site/v2/sports/soccer/{}/summary?event={}".format(league_slug, ev_id)
		plays_url = None
		if league_slug != "all":
			plays_url = "https://sports.core.api.espn.com/v2/sports/soccer/leagues/{}/events/{}/competitions/{}/plays?limit=1000".format(league_slug, ev_id, ev_id)

		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN summary URL=%s" % summary_url)
			if plays_url:
				logdata("MatchDetails", "ESPN plays URL=%s" % plays_url)

		def _fetch_all():
			results = {"summary": None, "plays": None}
			try:
				r = requests.get(summary_url, timeout=15, verify=False, headers={
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
					'Accept': 'application/json',
				})
				if r.status_code == 200:
					results['summary'] = r.content
			except Exception as e:
				if debug_MatchDetails:
					logdata("MatchDetails", "ESPN summary fetch error: %s" % str(e)[:200])
					
			if plays_url:
				try:
					all_items = []
					page = 1
					while page <= 20:
						page_url = plays_url + "&page=" + str(page)
						r = requests.get(page_url, timeout=15, verify=False, headers={
							'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
							'Accept': 'application/json',
						})
						if r.status_code != 200:
							if debug_MatchDetails:
								logdata("MatchDetails", "ESPN plays HTTP status=%d page=%d" % (r.status_code, page))
							break
						page_data = r.json()
						page_items = page_data.get('items', []) or []
						if debug_MatchDetails:
							logdata("MatchDetails", "ESPN plays page=%d items=%d pageCount=%s" % (page, len(page_items), page_data.get('pageCount', '?')))
						if not page_items:
							break
						all_items.extend(page_items)
						page_count = page_data.get('pageCount', 1) or 1
						if page >= page_count:
							break
						page += 1
					results['plays'] = json.dumps({"items": all_items}).encode('utf-8')
				except Exception as e:
					if debug_MatchDetails:
						logdata("MatchDetails", "ESPN plays fetch error: %s" % str(e)[:200])
			return results

		d = deferToThread(_fetch_all)
		d.addCallback(self._convert)
		d.addErrback(self._err)

	def _err(self, failure):
		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_data(None)

	def _convert(self, results):
		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN._convert started")

		summary_raw = results.get('summary') if results else None
		plays_raw = results.get('plays') if results else None

		if not summary_raw:
			if debug_MatchDetails:
				logdata("MatchDetails", "ESPN._convert: no summary data")
			self.screen.process_data(None)
			return

		try:
			data = json.loads(summary_raw.decode('utf-8', 'ignore'))
		except Exception as e:
			if debug_MatchDetails:
				logdata("MatchDetails", "ESPN summary JSON error: %s" % str(e))
			self.screen.process_data(None)
			return

		if not plays_raw:
			plays_list = data.get("plays", []) or data.get("keyEvents", []) or []
			if plays_list:
				plays_raw = json.dumps({"items": plays_list}).encode('utf-8')

		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN summary loaded, plays_raw=%s" % ("yes" if plays_raw else "no"))

		header = data.get("header", {})
		comps = header.get("competitions", [{}])
		comp = comps[0] if comps else {}
		competitors = comp.get("competitors", [])
		home = next((c for c in competitors if c.get("homeAway") == "home"), {})
		away = next((c for c in competitors if c.get("homeAway") == "away"), {})
		status = comp.get("status", {})
		status_type = status.get("type", {})

		ev_js = {
			"event": {
				"homeScore": {"current": home.get("score", 0), "display": home.get("score", 0)},
				"awayScore": {"current": away.get("score", 0), "display": away.get("score", 0)},
				"status": {
					"description": status_type.get("description", status.get("displayClock", "")),
					"type": status_type.get("name", ""),
				}
			}
		}

		incidents = []
		home_team_id = str(home.get("team", {}).get("id", ""))
		away_team_id = str(away.get("team", {}).get("id", ""))

		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN home_team_id=%s away_team_id=%s" % (home_team_id, away_team_id))

		if plays_raw:
			try:
				plays_data = json.loads(plays_raw.decode('utf-8', 'ignore'))
				items = plays_data.get('items', []) or []

				if debug_MatchDetails:
					logdata("MatchDetails", "ESPN plays items=%d" % len(items))

				for play in items:
					try:
						play_type = play.get('type', {}) or {}
						type_text = str(play_type.get('text', '')).lower()
						type_key = str(play_type.get('type', '')).lower()

						clock = play.get('clock', {}) or {}
						time_str = str(clock.get('displayValue', ''))
						time_int = 0
						m = re.search(r'(\d+)', time_str)
						if m:
							time_int = int(m.group(1))

						team_ref = ""
						team_obj = play.get('team') or {}
						if isinstance(team_obj, dict):
							team_ref = team_obj.get('$ref', '')
							if not team_ref:
								team_id = team_obj.get('id')
								if team_id:
									team_ref = "/teams/" + str(team_id)
						is_home = True
						if team_ref and home_team_id:
							tid_match = re.search(r'/teams/(\d+)', team_ref)
							if tid_match:
								tid = tid_match.group(1)
								is_home = (tid == home_team_id)

						text = str(play.get('text', ''))
						player_name = ""
						if text.startswith('Goal!') or text.startswith('Own Goal!') or text.startswith('Penalty!'):
							pm = re.search(r'\.\s*([^(]+?)(?:\s*\(|$)', text)
							if pm:
								player_name = pm.group(1).strip()
						if not player_name:
							pm = re.match(r'^\s*([^(]+?)\s*\(', text)
							if pm:
								player_name = pm.group(1).strip()

						combined = (type_key + " " + type_text).replace('-', ' ')

						if re.search(r'\bsecond\s+yellow\b', combined) or 'yellowred' in combined:
							incidents.append({
								"incidentType": "card",
								"incidentClass": "red",
								"isHome": is_home,
								"time": time_int,
								"player": {"name": player_name},
							})
							continue

						if re.search(r'\byellow\b', combined) and not re.search(r'\bred\b', combined):
							incidents.append({
								"incidentType": "card",
								"incidentClass": "yellow",
								"isHome": is_home,
								"time": time_int,
								"player": {"name": player_name},
							})
							continue

						if re.search(r'\bred\b', combined) and not re.search(r'\byellow\b', combined):
							incidents.append({
								"incidentType": "card",
								"incidentClass": "red",
								"isHome": is_home,
								"time": time_int,
								"player": {"name": player_name},
							})
							continue

						if 'penalty' in combined and 'scored' in combined and 'miss' not in combined:
							incidents.append({
								"incidentType": "goal",
								"incidentClass": "penalty",
								"isHome": is_home,
								"time": time_int,
								"player": {"name": player_name},
							})
							continue

						_tl = text.lower()
						_is_real_goal = play.get('scoringPlay', False) or text.startswith('Goal!') or text.startswith('Own Goal!')
						if not play.get('scoringPlay', False):
							if 'goal kick' in _tl or 'goalkeeper' in _tl or 'goal attempt' in _tl or 'goal saved' in _tl or 'goal disallowed' in _tl or 'no goal' in _tl:
								_is_real_goal = False

						if _is_real_goal:
							incident_class = "regular"
							if play.get('ownGoal', False) or 'own goal' in combined:
								incident_class = "owngoal"
							elif play.get('penaltyKick', False) or 'penalty' in combined:
								incident_class = "penalty"
							incidents.append({
								"incidentType": "goal",
								"incidentClass": incident_class,
								"isHome": is_home,
								"time": time_int,
								"player": {"name": player_name},
							})
							continue

						if 'substitution' in combined:
							player_in = ""
							player_out = player_name

							rm = re.search(r'(.+?)\s+replaces\s+(.+)', text, re.IGNORECASE)
							if rm:
								player_in = rm.group(1).strip()
								player_out = rm.group(2).strip()
							else:
								participants = play.get('participants', []) or []
								for p in participants:
									if not isinstance(p, dict):
										continue
									p_name = p.get('athlete', {}).get('displayName', '')
									if p_name and p_name != player_out:
										player_in = p_name
										break

							incidents.append({
								"incidentType": "substitution",
								"isHome": is_home,
								"time": time_int,
								"playerIn": {"name": player_in},
								"playerOut": {"name": player_out},
							})
							continue

					except Exception as pe:
						if debug_MatchDetails:
							logdata("MatchDetails", "ESPN play parse error: %s" % str(pe)[:150])
						continue

				if debug_MatchDetails:
					logdata("MatchDetails", "ESPN._convert produced incidents=%d" % len(incidents))

			except Exception as e:
				if debug_MatchDetails:
					logdata("MatchDetails", "ESPN plays JSON error: %s" % str(e))
		else:
			if debug_MatchDetails:
				logdata("MatchDetails", "ESPN._convert: no plays data")

		inc_js = {"incidents": incidents}
		self.screen.process_data([inc_js, ev_js])


class SportScoreMatchDetails(MatchDetailsFetcherBase):
	def fetch(self):
		if debug_MatchDetails:
			logdata("MatchDetails", "SportScore details not implemented")
		self.screen.process_data(None)


def get_match_details_fetcher(source, screen, event_id):
	if source == "espn":
		return ESPNMatchDetails(screen, event_id)
	if source == "sportscore":
		return SportScoreMatchDetails(screen, event_id)
	if source == "flashscore":
		return FlashscoreMatchDetails(screen, event_id)
	return SofaScoreMatchDetails(screen, event_id)


# =========================================================
# Match Statistics
# =========================================================

class MatchStatisticsFetcherBase(object):
	def __init__(self, screen, event_id):
		self.screen = screen
		self.event_id = event_id

	def fetch(self):
		raise NotImplementedError


class SofaScoreMatchStatistics(MatchStatisticsFetcherBase):
	def fetch(self):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "SofaScore.fetch started | event_id=%s" % self.event_id)
		url = "https://www.sofascore.com/api/v1/event/{}/statistics".format(self.event_id)
		if debug_MatchStatistics:
			logdata("MatchStatistics", "URL=%s" % url)
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
			'Referer': 'https://www.sofascore.com/',
			'Origin': 'https://www.sofascore.com',
			'Accept': 'application/json',
			'X-Requested-With': 'XMLHttpRequest'
		}
		def _fetch_stats():
			headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.sofascore.com/', 'Origin': 'https://www.sofascore.com', 'Accept': 'application/json'}
			try:
				r = requests.get(url, headers=headers, timeout=25, verify=False)
				if r.status_code == 200:
					return r.json()
			except Exception:
				pass
			return None
		d = deferToThread(_fetch_stats)
		d.addCallback(self.screen.process_stats)
		d.addErrback(lambda f: self._err(f))

	def _err(self, failure):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "SofaScore deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_stats(None)


class ESPNMatchStatistics(MatchStatisticsFetcherBase):
	ESPN_STAT_MAP = {
		"possessionPct": ("Match overview", "Ball possession"),
		"totalShots": ("Match overview", "Total shots"),
		"shotsOnTarget": ("Match overview", "Shots on target"),
		"wonCorners": ("Match overview", "Corner kicks"),
		"foulsCommitted": ("Match overview", "Fouls"),
		"yellowCards": ("Match overview", "Yellow cards"),
		"redCards": ("Match overview", "Red cards"),
		"offsides": ("Match overview", "Offsides"),
		"saves": ("Match overview", "Goalkeeper saves"),
		"blockedShots": ("Shots", "Blocked shots"),
		"hitWoodwork": ("Shots", "Hit woodwork"),
		"shotsOffTarget": ("Shots", "Shots off target"),
		"shotsFromInsideTheBox": ("Shots", "Shots inside box"),
		"shotsFromOutsideTheBox": ("Shots", "Shots outside box"),
		"bigChancesCreated": ("Attack", "Big chances"),
		"chancesCreated": ("Attack", "Big chances"),
		"touchesInOppositionBox": ("Attack", "Touches in penalty area"),
		"accuratePasses": ("Passes", "Accurate passes"),
		"totalPasses": ("Passes", "Accurate passes"),
		"accurateCrosses": ("Passes", "Crosses"),
		"crosses": ("Passes", "Crosses"),
		"accurateLongBalls": ("Passes", "Long balls"),
		"longBalls": ("Passes", "Long balls"),
		"possessionLost": ("Duels", "Dispossessed"),
		"duelsWon": ("Duels", "Duels"),
		"aerialDuelsWon": ("Duels", "Aerial duels"),
		"groundDuelsWon": ("Duels", "Ground duels"),
		"dribblesWon": ("Duels", "Dribbles"),
		"interceptions": ("Defending", "Interceptions"),
		"tacklesWon": ("Defending", "Tackles won"),
		"totalTackles": ("Defending", "Total tackles"),
		"clearances": ("Defending", "Clearances"),
		"effectiveClearance": ("Defending", "Clearances"),
		"effectiveClearances": ("Defending", "Clearances"),
		"recoveries": ("Defending", "Recoveries"),
		"errorsLeadToGoal": ("Defending", "Errors lead to a goal"),
		"penaltySaves": ("Goalkeeping", "Penalty saves"),
		"punches": ("Goalkeeping", "Punches"),
		"goalKicks": ("Goalkeeping", "Goal kicks"),
		"highClaims": ("Goalkeeping", "High claims"),
		"errorsLeadToShot": ("Goalkeeping", "Errors lead to a shot"),
		"totalSaves": ("Goalkeeping", "Total saves"),
	}
	GROUP_ORDER = ["Match overview", "Shots", "Attack", "Passes", "Duels", "Defending", "Goalkeeping"]

	def fetch(self):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN.fetch started | event_id=%s" % self.event_id)
		if "|" not in self.event_id:
			if debug_MatchStatistics:
				logdata("MatchStatistics", "ESPN: invalid event_id format")
			self.screen.process_stats(None)
			return
		league_slug, ev_id = self.event_id.split("|", 1)
		url = "https://site.web.api.espn.com/apis/site/v2/sports/soccer/{}/summary?event={}".format(league_slug, ev_id)
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN URL=%s" % url)
		def _fetch():
			try:
				r = requests.get(url, timeout=15, verify=False, headers={
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
					'Accept': 'application/json',
				})
				if debug_MatchStatistics:
					logdata("MatchStatistics", "ESPN HTTP status=%d len=%d" % (r.status_code, len(r.content) if r.content else 0))
				if r.status_code == 200:
					return r.content
				return None
			except Exception as e:
				if debug_MatchStatistics:
					logdata("MatchStatistics", "ESPN fetch error: %s" % str(e)[:200])
				return None
		d = deferToThread(_fetch)
		d.addCallback(self._convert)
		d.addErrback(self._err)

	def _err(self, failure):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_stats(None)

	def _convert(self, raw):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN._convert started | raw_len=%d" % (len(raw) if raw else 0))
		if not raw:
			if debug_MatchStatistics:
				logdata("MatchStatistics", "ESPN._convert: no raw data")
			self.screen.process_stats(None)
			return
		try:
			data = json.loads(raw.decode('utf-8', 'ignore'))
		except Exception as e:
			if debug_MatchStatistics:
				logdata("MatchStatistics", "ESPN._convert JSON error: %s" % str(e))
			self.screen.process_stats(None)
			return
		boxscore = data.get("boxscore", {})
		teams = boxscore.get("teams", [])
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN boxscore teams=%d" % len(teams))
		if len(teams) < 2:
			if debug_MatchStatistics:
				logdata("MatchStatistics", "ESPN: fewer than 2 teams in boxscore")
			self.screen.process_stats(None)
			return
		home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
		away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])
		home_stats = {}
		away_stats = {}
		for s in home.get("statistics", []) or []:
			home_stats[s.get("name", "")] = s.get("displayValue", s.get("value", ""))
		for s in away.get("statistics", []) or []:
			away_stats[s.get("name", "")] = s.get("displayValue", s.get("value", ""))
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN home_stats keys=%s" % list(home_stats.keys())[:10])

		groups = {}
		unmatched = []
		for key in home_stats:
			if key not in away_stats:
				continue
			info = self.ESPN_STAT_MAP.get(key)
			if not info:
				unmatched.append(key)
				continue
			group_name, display_name = info
			if group_name not in groups:
				groups[group_name] = []
			groups[group_name].append({
				"name": display_name,
				"home": str(home_stats[key]),
				"away": str(away_stats[key]),
			})
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN mapped groups=%s" % list(groups.keys()))
			if unmatched:
				logdata("MatchStatistics", "ESPN unmatched keys=%s" % unmatched[:20])

		stats_groups = []
		for gname in self.GROUP_ORDER:
			if gname in groups and groups[gname]:
				stats_groups.append({
					"groupName": gname,
					"statisticsItems": groups[gname],
				})

		stats_json = {
			"statistics": [{
				"period": "ALL",
				"groups": stats_groups,
			}]
		}
		if debug_MatchStatistics:
			logdata("MatchStatistics", "ESPN final groups=%d items=%d" % (len(stats_groups), sum(len(g["statisticsItems"]) for g in stats_groups)))
		self.screen.process_stats(stats_json)


class SportScoreMatchStatistics(MatchStatisticsFetcherBase):
	def fetch(self):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "SportScore statistics not implemented")
		self.screen.process_stats(None)


def get_match_statistics_fetcher(source, screen, event_id):
	if source == "espn":
		return ESPNMatchStatistics(screen, event_id)
	if source == "sportscore":
		return SportScoreMatchStatistics(screen, event_id)
	if source == "flashscore":
		return FlashscoreMatchStatistics(screen, event_id)
	return SofaScoreMatchStatistics(screen, event_id)


# =========================================================
# Match Media
# =========================================================

class MatchMediaFetcherBase(object):
	def __init__(self, screen, event_id):
		self.screen = screen
		self.event_id = event_id

	def fetch(self):
		raise NotImplementedError


class SofaScoreMatchMedia(MatchMediaFetcherBase):
	def _search_youtube(self, query, max_results=3):
		if not PY3 and isinstance(query, unicode):
			query = query.encode('utf-8', 'ignore')
		search_url = "https://www.youtube.com/results?search_query=" + compat_quote(query)
		try:
			r = requests.get(search_url, timeout=15, verify=False, headers={
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
				'Accept-Language': 'en-US,en;q=0.9',
			})
			if r.status_code != 200:
				if debug_MatchMedia:
					logdata("MatchMedia", "SofaScore YouTube search HTTP %d" % r.status_code)
				return []
			html = r.text
			video_ids = []
			for m in re.finditer(r'"videoId":"([a-zA-Z0-9_-]{11})"', html):
				vid = m.group(1)
				if vid not in video_ids:
					video_ids.append(vid)
				if len(video_ids) >= max_results:
					break
			media = []
			for vid in video_ids:
				media.append({
					'url': "https://www.youtube.com/watch?v=" + vid,
					'title': query,
					'subtitle': '',
				})
			if debug_MatchMedia:
				logdata("MatchMedia", "SofaScore YouTube search found %d videos" % len(media))
			return media
		except Exception as e:
			if debug_MatchMedia:
				logdata("MatchMedia", "SofaScore YouTube search error: %s" % str(e)[:150])
			return []

	def fetch(self):
		if debug_MatchMedia:
			logdata("MatchMedia", "SofaScore.fetch started | event_id=%s" % self.event_id)
		url = "https://www.sofascore.com/api/v1/event/{}/media".format(self.event_id)
		
		if debug_MatchMedia:
			logdata("MatchMedia", "URL=%s" % url)

		home_team = getattr(self.screen, 'home_name', '') or ''
		away_team = getattr(self.screen, 'away_name', '') or ''

		def _fetch_media():
			sofa_media = []
			headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.sofascore.com/', 'Origin': 'https://www.sofascore.com', 'Accept': 'application/json'}
			try:
				r = requests.get(url, headers=headers, timeout=25, verify=False)
				if r.status_code == 200:
					data = r.json()
					sofa_media = data.get("media", [])
			except Exception:
				pass
			
			yt_media = []
			if home_team and away_team:
				query = "%s vs %s highlights" % (home_team, away_team)
				if debug_MatchMedia:
					logdata("MatchMedia", "SofaScore YouTube query: %s" % query)
				yt_media = self._search_youtube(query)
				
			return {"media": sofa_media + yt_media}
			
		d = deferToThread(_fetch_media)
		d.addCallback(self.screen.process_media)
		d.addErrback(lambda f: self._err(f))

	def _err(self, failure):
		if debug_MatchMedia:
			logdata("MatchMedia", "SofaScore deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_media(None)


class FlashscoreStandings(StandingsFetcherBase):
	def fetch(self):
		sofa = SofaScoreStandings(self.screen, self.league, self.url)
		sofa.fetch()


class FlashscoreMatchDetails(MatchDetailsFetcherBase):
	def fetch(self):
		if debug_MatchDetails:
			logdata("MatchDetails", "Flashscore.fetch started | event_id=%s" % self.event_id)
		def _fetch():
			text = _fs_request("df_sui_1_{0}".format(self.event_id), timeout=25)
			logdata("MatchDetails_RAW_SUI", "len=%d preview=%s" % (len(text) if text else 0, (text[:800] if text else "EMPTY")))
			return _fs_parse(text) if text else []
		d = deferToThread(_fetch)
		d.addCallback(self._convert)
		d.addErrback(self._err)

	def _err(self, failure):
		if debug_MatchDetails:
			logdata("MatchDetails", "Flashscore deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_data(None)

	def _detect_team_side(self, entry, home_team, away_team):
		ict = (entry.get('ICT', '') or '').strip()
		m = re.search(r'\(([^)]+)\)', ict)
		if m:
			team = m.group(1).strip().lower()
			if home_team and team in home_team.lower():
				return True
			if away_team and team in away_team.lower():
				return False
		return None

	def _parse_minute(self, s):
		s = (s or '').replace("'", '').strip()
		if not s:
			return 0, ''
		m = re.match(r'^(\d+)(?:\+(\d+))?$', s)
		if m:
			base = int(m.group(1))
			extra = int(m.group(2)) if m.group(2) else 0
			return base + extra, s
		m = re.search(r'(\d+)', s)
		if m:
			return int(m.group(1)), s
		return 0, s

	def _convert(self, blocks):
		incidents = []
		prev_home = 0
		prev_away = 0
		final_home = 0
		final_away = 0
		pen_home = None
		pen_away = None
		is_shootout = False
		processed_pens = set()

		for block in blocks:
			context = {}
			entries = []
			current = None

			for k, v in block:
				kk = k
				if kk.endswith('X') and len(kk) > 1 and kk not in ('INX', 'IOX'):
					kk = kk[:-1]
				if kk == 'IE':
					if current is not None:
						entries.append(current)
					current = {'IE': v}
				elif current is None:
					context[kk] = v
				else:
					current[kk] = v
			if current is not None:
				entries.append(current)

			if 'IG' in context:
				try:
					val = int(context['IG'])
					if 'penalt' in str(context.get('AC', '')).lower() or is_shootout:
						pen_home = val
					else:
						final_home = val
				except Exception: pass
			if 'IH' in context:
				try:
					val = int(context['IH'])
					if 'penalt' in str(context.get('AC', '')).lower() or is_shootout:
						pen_away = val
					else:
						final_away = val
				except Exception: pass

			if str(context.get('AC', '')).lower() in ('penalties', 'penalty shootout'):
				is_shootout = True

			if not entries:
				continue

			ia = context.get('IA', '')
			ctx_is_home = True if ia == '1' else (False if ia == '2' else None)

			minute, minute_raw = self._parse_minute(context.get('IB', ''))

			goal_entries = []
			card_entries = []
			disallowed_entry = None
			sub_in = None
			sub_out = None
			sub_reason = ''

			for e in entries:
				ik = (e.get('IK', '') or '').strip()
				ik_low = ik.lower()
				ict_low = (e.get('ICT', '') or '').strip().lower()
				ie = e.get('IE', '')
				if 'pen' in ik_low or 'pen' in ict_low:
					logdata("DEBUG_FS_PEN", "PENALTY RAW ENTRY: %s" % str(e))

				if ie == '8' or 'assistance' in ik_low:
					continue
				if 'substitution' in ik_low and 'in' in ik_low:
					sub_in = e
					continue
				if 'substitution' in ik_low and 'out' in ik_low:
					sub_out = e
					continue
				if 'disallowed' in ik_low or 'disallowed' in ict_low or 'var' in ik_low:
					disallowed_entry = e
					continue
				if is_shootout and ('penalty' in ik_low or 'goal' in ik_low or 'missed' in ik_low or 'saved' in ik_low) and 'awarded' not in ik_low:
					is_missed = 'miss' in ik_low or 'sav' in ik_low or 'miss' in ict_low or 'sav' in ict_low or 'miss' in str(e.get('IL', '')).lower()
					side = ctx_is_home if ctx_is_home is not None else True
					p_key = (e.get('IF', ''), side)
					if p_key not in processed_pens:
						processed_pens.add(p_key)
						incidents.append({
							"incidentType": "penaltyShootout",
							"incidentClass": "missed" if is_missed else "scored",
							"isHome": side,
							"time": 0,
							"player": {"name": e.get('IF', '')}
						})
					continue
				if is_shootout and ('penalty' in ik_low or 'goal' in ik_low or 'missed' in ik_low or 'saved' in ik_low) and 'awarded' not in ik_low:
					is_missed = 'miss' in ik_low or 'sav' in ik_low or 'miss' in ict_low or 'sav' in ict_low or 'miss' in str(e.get('IL', '')).lower()
					side = ctx_is_home if ctx_is_home is not None else True
					incidents.append({
						"incidentType": "penaltyShootout",
						"incidentClass": "missed" if is_missed else "scored",
						"isHome": side,
						"time": 0,
						"player": {"name": e.get('IF', '')}
					})
					continue
				if 'goal' in ik_low:
					goal_entries.append(e)
					continue
				if 'yellow' in ik_low or 'red' in ik_low or 'card' in ik_low:
					card_entries.append(e)
					continue

			reason_str = ''
			for src in (sub_out, sub_in):
				if not src:
					continue
				m = re.search(r'\(([^)]+)\)', (src.get('ICT', '') or ''))
				if m:
					cand = m.group(1).strip()
					if cand and cand.lower() not in ('in', 'out'):
						reason_str = cand
						break

			if sub_in or sub_out:
				pin = sub_in.get('IF', '') if sub_in else ''
				pout = sub_out.get('IF', '') if sub_out else ''
				if reason_str and pout:
					pout = "%s (%s)" % (pout, reason_str)
				side = ctx_is_home if ctx_is_home is not None else True
				incidents.append({
					"incidentType": "substitution",
					"isHome": side,
					"time": minute,
					"time_display": minute_raw,
					"playerIn": {"name": pin},
					"playerOut": {"name": pout},
				})
				continue

			if disallowed_entry:
				side = ctx_is_home if ctx_is_home is not None else True
				v_ik = disallowed_entry.get('IK', 'Goal Disallowed')
				v_il = disallowed_entry.get('IL', '')
				v_reason = v_ik
				if v_il and v_il.lower() not in v_ik.lower():
					v_reason = "%s (%s)" % (v_ik, v_il)
				incidents.append({
					"incidentType": "var",
					"incidentClass": "goalDisallowed",
					"isHome": side,
					"time": minute,
					"time_display": minute_raw,
					"player": {"name": disallowed_entry.get('IF', '')},
					"var_reason": v_reason,
				})
				continue

			for g in goal_entries:
				try:
					new_home = int(g.get('INX', prev_home) or prev_home)
					new_away = int(g.get('IOX', prev_away) or prev_away)
				except Exception:
					new_home = prev_home
					new_away = prev_away
				is_home = new_home > prev_home
				prev_home = new_home
				prev_away = new_away
				ict = (g.get('ICT', '') or '').lower()
				ik_low = (g.get('IK', '') or '').lower()
				if 'own goal' in ict or 'own goal' in ik_low:
					ic_class = 'owngoal'
				elif 'penalty' in ict or 'penalty' in ik_low:
					ic_class = 'penalty'
				else:
					ic_class = 'regular'
				incidents.append({
					"incidentType": "goal",
					"incidentClass": ic_class,
					"isHome": is_home,
					"time": minute,
					"time_display": minute_raw,
					"player": {"name": g.get('IF', '')},
				})

			for c in card_entries:
				ik_low = (c.get('IK', '') or '').lower()
				card_class = 'red' if ('red card' in ik_low or 'second yellow' in ik_low) else 'yellow'
				side = ctx_is_home if ctx_is_home is not None else True
				incidents.append({
					"incidentType": "card",
					"incidentClass": card_class,
					"isHome": side,
					"time": minute,
					"time_display": minute_raw,
					"player": {"name": c.get('IF', '')},
				})

		if final_home == 0 and final_away == 0:
			final_home = prev_home
			final_away = prev_away

		has_pen = any(i.get('incidentType') == 'penaltyShootout' for i in incidents)
		ev_js = {"event": {
			"homeScore": {"current": final_home, "display": final_home, "penalties": pen_home},
			"awayScore": {"current": final_away, "display": final_away, "penalties": pen_away},
			"status": {"description": "Ended Match - Penalties" if pen_home is not None else ""}
		}}

		if debug_MatchDetails:
			logdata("MatchDetails", "Flashscore incidents=%d score=%d-%d" % (len(incidents), final_home, final_away))
		self.screen.process_data([{"incidents": incidents}, ev_js])


class FlashscoreMatchStatistics(MatchStatisticsFetcherBase):
	def fetch(self):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "Flashscore.fetch started | event_id=%s" % self.event_id)
		def _fetch():
			text = _fs_request("df_st_1_{0}".format(self.event_id), timeout=25)
			logdata("MatchStatistics_RAW_ST", "len=%d preview=%s" % (len(text) if text else 0, (text[:800] if text else "EMPTY")))
			return _fs_parse(text) if text else []
		d = deferToThread(_fetch)
		d.addCallback(self._convert_stats)
		d.addErrback(self._err)

	def _err(self, failure):
		if debug_MatchStatistics:
			logdata("MatchStatistics", "Flashscore deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_stats(None)

	def _convert_stats(self, blocks):
		GROUP_MAP = {
			'Match': 'Match overview',
			'Top stats': 'Match overview',
			'Shots': 'Shots',
			'Attack': 'Attack',
			'Passes': 'Passes',
			'Duels': 'Duels',
			'Defending': 'Defending',
			'Goalkeeping': 'Goalkeeping',
		}
		STAT_MAP = {
			'Expected goals (xG)': 'Expected goals',
			'Expected goals': 'Expected goals',
			'Ball possession': 'Ball possession',
			'Total shots': 'Total shots',
			'Shots on target': 'Shots on target',
			'Big chances': 'Big chances',
			'Corner kicks': 'Corner kicks',
			'Passes': 'Accurate passes',
			'Yellow cards': 'Yellow cards',
			'Red cards': 'Red cards',
			'Shots off target': 'Shots off target',
			'Blocked shots': 'Blocked shots',
			'Shots inside the box': 'Shots inside box',
			'Shots outside the box': 'Shots outside box',
			'Hit the woodwork': 'Hit woodwork',
			'Touches in opposition box': 'Touches in penalty area',
			'Fouls': 'Fouls',
			'Offsides': 'Offsides',
			'Goalkeeper saves': 'Goalkeeper saves',
			'Saves': 'Total saves',
		}

		groups = {}
		order = []
		current = None

		for block in blocks:
			d = {}
			for k, v in block:
				d.setdefault(k, []).append(v)

			if 'SE' in d:
				name = d['SE'][0]
				mapped = GROUP_MAP.get(name, name)
				if mapped not in groups:
					groups[mapped] = []
					order.append(mapped)
				current = mapped
				continue

			if 'SF' in d:
				name = d['SF'][0]
				mapped = GROUP_MAP.get(name, name)
				if mapped not in groups:
					groups[mapped] = []
					order.append(mapped)
				current = mapped
				continue

			if 'SG' in d and 'SH' in d and 'SI' in d:
				stat_name = d['SG'][0]
				home_val = d['SH'][0]
				away_val = d['SI'][0]
				mapped_name = STAT_MAP.get(stat_name, stat_name)
				if current is None:
					current = 'Match overview'
					if current not in groups:
						groups[current] = []
						order.append(current)
				groups[current].append({
					"name": mapped_name,
					"home": str(home_val),
					"away": str(away_val),
				})

		stats_groups = []
		for gname in order:
			if groups.get(gname):
				stats_groups.append({
					"groupName": gname,
					"statisticsItems": groups[gname],
				})

		stats_json = {
			"statistics": [{
				"period": "ALL",
				"groups": stats_groups,
			}]
		}
		if debug_MatchStatistics:
			logdata("MatchStatistics", "Flashscore groups=%d" % len(stats_groups))
		self.screen.process_stats(stats_json)


class FlashscoreMatchMedia(MatchMediaFetcherBase):
	def _search_youtube(self, query, max_results=3):
		if not PY3 and isinstance(query, unicode):
			query = query.encode('utf-8', 'ignore')
		search_url = "https://www.youtube.com/results?search_query=" + compat_quote(query)
		try:
			r = requests.get(search_url, timeout=15, verify=False, headers={
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
				'Accept-Language': 'en-US,en;q=0.9',
			})
			if r.status_code != 200:
				if debug_MatchMedia:
					logdata("MatchMedia", "Flashscore YouTube search HTTP %d" % r.status_code)
				return []
			html = r.text
			video_ids = []
			for m in re.finditer(r'"videoId":"([a-zA-Z0-9_-]{11})"', html):
				vid = m.group(1)
				if vid not in video_ids:
					video_ids.append(vid)
				if len(video_ids) >= max_results:
					break
			media = []
			for vid in video_ids:
				media.append({
					'url': "https://www.youtube.com/watch?v=" + vid,
					'title': query,
					'subtitle': '',
				})
			if debug_MatchMedia:
				logdata("MatchMedia", "Flashscore YouTube search found %d videos" % len(media))
			return media
		except Exception as e:
			if debug_MatchMedia:
				logdata("MatchMedia", "Flashscore YouTube search error: %s" % str(e)[:150])
			return []

	def fetch(self):
		if debug_MatchMedia:
			logdata("MatchMedia", "Flashscore.fetch started | event_id=%s" % self.event_id)
		home_team = getattr(self.screen, 'home_name', '') or ''
		away_team = getattr(self.screen, 'away_name', '') or ''
		if not home_team or not away_team:
			if debug_MatchMedia:
				logdata("MatchMedia", "Flashscore: missing team names, cannot search YouTube")
			try:
				self.screen.process_media({"media": []})
			except Exception:
				self.screen.process_media(None)
			return
		query = "%s vs %s highlights" % (home_team, away_team)
		if debug_MatchMedia:
			logdata("MatchMedia", "Flashscore YouTube query: %s" % query)
		media = self._search_youtube(query)
		self.screen.process_media({"media": media})


class ESPNMatchMedia(MatchMediaFetcherBase):
	def _search_youtube(self, query, max_results=3):
		if not PY3 and isinstance(query, unicode):
			query = query.encode('utf-8', 'ignore')
		search_url = "https://www.youtube.com/results?search_query=" + compat_quote(query)
		try:
			r = requests.get(search_url, timeout=15, verify=False, headers={
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
				'Accept-Language': 'en-US,en;q=0.9',
			})
			if r.status_code != 200:
				if debug_MatchMedia:
					logdata("MatchMedia", "YouTube search HTTP %d" % r.status_code)
				return []
			html = r.text
			video_ids = []
			for m in re.finditer(r'"videoId":"([a-zA-Z0-9_-]{11})"', html):
				vid = m.group(1)
				if vid not in video_ids:
					video_ids.append(vid)
				if len(video_ids) >= max_results:
					break
			media = []
			for vid in video_ids:
				media.append({
					'url': "https://www.youtube.com/watch?v=" + vid,
					'title': query,
					'subtitle': '',
				})
			if debug_MatchMedia:
				logdata("MatchMedia", "YouTube search found %d videos" % len(media))
			return media
		except Exception as e:
			if debug_MatchMedia:
				logdata("MatchMedia", "YouTube search error: %s" % str(e)[:150])
			return []

	def fetch(self):
		if debug_MatchMedia:
			logdata("MatchMedia", "ESPN.fetch started | event_id=%s" % self.event_id)
		if "|" not in self.event_id:
			if debug_MatchMedia:
				logdata("MatchMedia", "ESPN: invalid event_id format")
			self.screen.process_media(None)
			return
		league_slug, ev_id = self.event_id.split("|", 1)
		url = "https://site.web.api.espn.com/apis/site/v2/sports/soccer/{}/summary?event={}".format(league_slug, ev_id)
		if debug_MatchMedia:
			logdata("MatchMedia", "ESPN URL=%s" % url)
		def _fetch():
			try:
				r = requests.get(url, timeout=15, verify=False, headers={
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
					'Accept': 'application/json',
				})
				if debug_MatchMedia:
					logdata("MatchMedia", "ESPN HTTP status=%d len=%d" % (r.status_code, len(r.content) if r.content else 0))
				if r.status_code == 200:
					return r.content
				return None
			except Exception as e:
				if debug_MatchMedia:
					logdata("MatchMedia", "ESPN fetch error: %s" % str(e)[:200])
				return None
		d = deferToThread(_fetch)
		d.addCallback(self._convert)
		d.addErrback(self._err)

	def _err(self, failure):
		if debug_MatchMedia:
			logdata("MatchMedia", "ESPN deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_media(None)

	def _convert(self, raw):
		if debug_MatchMedia:
			logdata("MatchMedia", "ESPN._convert started | raw_len=%d" % (len(raw) if raw else 0))
		if not raw:
			if debug_MatchMedia:
				logdata("MatchMedia", "ESPN._convert: no raw data")
			self.screen.process_media(None)
			return
		try:
			data = json.loads(raw.decode('utf-8', 'ignore'))
		except Exception as e:
			if debug_MatchMedia:
				logdata("MatchMedia", "ESPN._convert JSON error: %s" % str(e))
			self.screen.process_media(None)
			return

		media = []
		videos = data.get("videos") or []
		if not videos:
			header = data.get("header", {})
			comps = header.get("competitions", [{}])
			if comps:
				videos = comps[0].get("videos") or []

		for v in videos:
			try:
				links = v.get("links", {})
				web_href = ""
				source_href = ""
				if isinstance(links, dict):
					web_href = links.get("web", {}).get("href", "")
					source_href = links.get("source", {}).get("href", "")
				video_url = web_href or source_href
				if not video_url:
					continue
				media.append({
					"url": video_url,
					"title": v.get("headline", v.get("description", "")),
					"subtitle": v.get("duration", ""),
				})
			except Exception:
				continue

		if not media:
			home_team = ""
			away_team = ""
			competitions = data.get("header", {}).get("competitions", [])
			if competitions:
				competitors = competitions[0].get("competitors", [])
				for c in competitors:
					if c.get("homeAway") == "home":
						home_team = c.get("team", {}).get("displayName", "")
					elif c.get("homeAway") == "away":
						away_team = c.get("team", {}).get("displayName", "")
			if home_team and away_team:
				query = "%s vs %s highlights" % (home_team, away_team)
				if debug_MatchMedia:
					logdata("MatchMedia", "ESPN no videos, searching YouTube: %s" % query)
				media = self._search_youtube(query)

		if debug_MatchMedia:
			logdata("MatchMedia", "ESPN._convert produced media=%d" % len(media))
		self.screen.process_media({"media": media})


class SportScoreMatchMedia(MatchMediaFetcherBase):
	def fetch(self):
		if debug_MatchMedia:
			logdata("MatchMedia", "SportScore media not implemented")
		try:
			self.screen.process_media({"media": []})
		except Exception:
			try:
				self.screen.process_media(None)
			except Exception:
				pass


def get_match_media_fetcher(source, screen, event_id):
	if source == "espn":
		return ESPNMatchMedia(screen, event_id)
	if source == "sportscore":
		return SportScoreMatchMedia(screen, event_id)
	if source == "flashscore":
		return FlashscoreMatchMedia(screen, event_id)
	return SofaScoreMatchMedia(screen, event_id)
