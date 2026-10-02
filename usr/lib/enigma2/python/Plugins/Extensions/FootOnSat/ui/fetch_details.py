# -*- coding: utf-8 -*-
import json
import re
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
	if source == "espn":
		return link.lower() in ESPN_SLUGS
	if source == "sportscore":
		return False
	return link in json_urls


def get_standings_url(source, link):
	if source == "espn":
		return link if link.lower() in ESPN_SLUGS else None
	if source == "sportscore":
		return None
	return json_urls.get(link)


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
		api_url = "https://api.sofascore.com/api/v1/unique-tournament/{}/season/{}/standings/total".format(tournament_id, season_id)
		if debug_Standings:
			logdata("StandingsScreen", "Using SofaScore API URL: %s" % api_url)
		AGENT = b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
		if PY3:
			try:
				sniFactory = WebClientContextFactory(api_url)
			except Exception as e:
				if debug_Standings:
					logdata("StandingsScreen", "Failed to create WebClientContextFactory: %s" % str(e))
				self.screen.display_standings()
				return
			headers = {
				b'User-Agent': [AGENT],
				b'Accept': [b'application/json, text/plain, */*'],
				b'Accept-Language': [b'en-US,en;q=0.9'],
				b'Connection': [b'close'],
				b'Referer': [b'https://www.sofascore.com/'],
				b'Origin': [b'https://www.sofascore.com'],
				b'Cache-Control': [b'no-cache'],
			}
			d = getPage(str.encode(api_url), contextFactory=sniFactory, timeout=10, headers=headers)
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
		url = "https://site.api.espn.com/apis/v2/sports/soccer/{}/standings".format(slug)
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
				standings.append("Table %s" % group_name)
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
	if source == "espn":
		return ESPNStandings(screen, league, url)
	if source == "sportscore":
		return SportScoreStandings(screen, league, url)
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
		url_incidents = "https://api.sofascore.com/api/v1/event/{}/incidents".format(self.event_id)
		url_event = "https://api.sofascore.com/api/v1/event/{}".format(self.event_id)
		if debug_MatchDetails:
			logdata("MatchDetails", "URL incidents=%s" % url_incidents)
			logdata("MatchDetails", "URL event=%s" % url_event)
		if PY3:
			sniFactory = WebClientContextFactory(url_incidents)
			headers = {
				b'User-Agent': [b'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'],
				b'Accept': [b'application/json'],
				b'Referer': [b'https://www.sofascore.com/'],
				b'Origin': [b'https://www.sofascore.com'],
				b'X-Requested-With': [b'XMLHttpRequest']
			}
			d1 = getPage(str.encode(url_incidents), contextFactory=sniFactory, timeout=25, headers=headers)
			d2 = getPage(str.encode(url_event), contextFactory=sniFactory, timeout=25, headers=headers)
			d = defer.gatherResults([d1, d2], consumeErrors=True)
			def _process(results):
				raw = [r if not isinstance(r, Failure) else None for r in results]
				if debug_MatchDetails:
					logdata("MatchDetails", "PY3 gather results: len=%d, all_none=%s" % (len(raw), all(x is None for x in raw)))
				if all(x is None for x in raw):
					return self.screen.process_data(None)
				try:
					parsed = [json.loads(r.decode('utf-8')) for r in raw if r]
					if debug_MatchDetails:
						logdata("MatchDetails", "PY3 parsed items=%d" % len(parsed))
					return self.screen.process_data(parsed)
				except Exception as e:
					if debug_MatchDetails:
						logdata("MatchDetails", "PY3 parse error: %s" % str(e))
					return self.screen.process_data(None)
			d.addCallback(_process)
		else:
			def _get_data():
				s = _make_sofa_session_py2()
				s.headers.update({
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
					'Referer': 'https://api.sofascore.com/',
					'Origin': 'https://api.sofascore.com',
					'Accept': 'application/json',
					'X-Requested-With': 'XMLHttpRequest'
				})
				try:
					results = []
					for u in [url_incidents, url_event]:
						r = s.get(u, timeout=25, verify=False)
						if debug_MatchDetails:
							logdata("MatchDetails", "PY2 GET %s status=%d" % (u, r.status_code))
						r.raise_for_status()
						results.append(json.loads(r.content.decode('utf-8')))
					return results
				except Exception as e:
					if debug_MatchDetails:
						logdata("MatchDetails", "PY2 fetch error: %s" % str(e))
					return None
			d = deferToThread(_get_data)
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
		url = "https://site.web.api.espn.com/apis/site/v2/sports/soccer/{}/summary?event={}".format(league_slug, ev_id)
		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN URL=%s" % url)
		def _fetch():
			try:
				r = requests.get(url, timeout=15, verify=False, headers={
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
					'Accept': 'application/json',
				})
				if debug_MatchDetails:
					logdata("MatchDetails", "ESPN HTTP status=%d len=%d" % (r.status_code, len(r.content) if r.content else 0))
				if r.status_code == 200:
					return r.content
				return None
			except Exception as e:
				if debug_MatchDetails:
					logdata("MatchDetails", "ESPN fetch error: %s" % str(e)[:200])
				return None
		d = deferToThread(_fetch)
		d.addCallback(self._convert)
		d.addErrback(self._err)

	def _err(self, failure):
		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_data(None)

	def _convert(self, raw):
		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN._convert started | raw_len=%d" % (len(raw) if raw else 0))
		if not raw:
			if debug_MatchDetails:
				logdata("MatchDetails", "ESPN._convert: no raw data")
			self.screen.process_data(None)
			return
		try:
			data = json.loads(raw.decode('utf-8', 'ignore'))
		except Exception as e:
			if debug_MatchDetails:
				logdata("MatchDetails", "ESPN._convert JSON error: %s" % str(e))
			self.screen.process_data(None)
			return

		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN TOP_KEYS: %s" % list(data.keys()))
			logdata("MatchDetails", "ESPN keyEvents=%d commentary=%d videos=%d" % (len(data.get("keyEvents", [])), len(data.get("commentary", [])), len(data.get("videos", []))))

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

		raw_events = data.get("keyEvents") or []
		if not raw_events:
			raw_events = data.get("commentary") or []
		if not raw_events:
			raw_events = data.get("plays") or []

		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN processing raw_events=%d" % len(raw_events))

		for ev in raw_events:
			try:
				ev_type_obj = ev.get("type", {})
				ev_type_text = str(ev_type_obj.get("text", "")).lower()
				ev_text = str(ev.get("text", "")).lower()
				combined = ev_type_text + " " + ev_text

				clock_obj = ev.get("clock", {})
				clock = str(clock_obj.get("displayValue", ""))
				m_time = re.search(r'(\d+)', clock)
				time_int = int(m_time.group(1)) if m_time else 0

				team_obj = ev.get("team", {})
				team_id = str(team_obj.get("id", ""))
				is_home = (team_id == home_team_id) if team_id else True

				participants = ev.get("participants", []) or []
				player_name = ""
				player_in = ""
				player_out = ""

				for idx, p in enumerate(participants):
					if not isinstance(p, dict):
						continue
					athlete = p.get("athlete", {})
					if not isinstance(athlete, dict):
						continue
					name = athlete.get("displayName", "")
					if idx == 0:
						player_name = name
					elif idx == 1:
						if "substitution" in combined:
							player_in = player_name
							player_out = name
						else:
							player_out = name

				if "substitution" in combined:
					incidents.append({
						"incidentType": "substitution",
						"isHome": is_home,
						"time": time_int,
						"playerIn": {"name": player_in},
						"playerOut": {"name": player_out},
					})
					continue

				if "own goal" in combined:
					incidents.append({
						"incidentType": "goal",
						"incidentClass": "owngoal",
						"isHome": is_home,
						"time": time_int,
						"player": {"name": player_name},
					})
					continue

				if "penalty" in combined and "goal" in combined and "miss" not in combined:
					incidents.append({
						"incidentType": "goal",
						"incidentClass": "penalty",
						"isHome": is_home,
						"time": time_int,
						"player": {"name": player_name},
					})
					continue

				if "goal" in combined and "disallow" not in combined and "no goal" not in combined:
					incidents.append({
						"incidentType": "goal",
						"incidentClass": "regular",
						"isHome": is_home,
						"time": time_int,
						"player": {"name": player_name},
					})
					continue

				if "yellow" in combined and "red" not in combined:
					incidents.append({
						"incidentType": "card",
						"incidentClass": "yellow",
						"isHome": is_home,
						"time": time_int,
						"player": {"name": player_name},
					})
					continue

				if "red" in combined:
					incidents.append({
						"incidentType": "card",
						"incidentClass": "red",
						"isHome": is_home,
						"time": time_int,
						"player": {"name": player_name},
					})
					continue
			except Exception as e:
				if debug_MatchDetails:
					logdata("MatchDetails", "ESPN event parse error: %s" % str(e)[:150])
				continue

		if debug_MatchDetails:
			logdata("MatchDetails", "ESPN._convert produced incidents=%d" % len(incidents))

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
		url = "https://api.sofascore.com/api/v1/event/{}/statistics".format(self.event_id)
		if debug_MatchStatistics:
			logdata("MatchStatistics", "URL=%s" % url)
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
			'Referer': 'https://api.sofascore.com/',
			'Origin': 'https://api.sofascore.com',
			'Accept': 'application/json',
			'X-Requested-With': 'XMLHttpRequest'
		}
		if PY3:
			d = getPage(str.encode(url), contextFactory=WebClientContextFactory(url), timeout=25, headers={k.encode(): [v.encode()] for k, v in headers.items()})
			d.addCallback(lambda raw: self.screen.process_stats(json.loads(raw.decode('utf-8'))))
			d.addErrback(lambda f: self._err(f))
		else:
			def _get():
				s = _make_sofa_session_py2()
				s.headers.update(headers)
				r = s.get(url, timeout=25, verify=False)
				if debug_MatchStatistics:
					logdata("MatchStatistics", "PY2 status=%d" % r.status_code)
				return json.loads(r.content.decode('utf-8')) if r.status_code == 200 else None
			d = deferToThread(_get)
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
	def fetch(self):
		if debug_MatchMedia:
			logdata("MatchMedia", "SofaScore.fetch started | event_id=%s" % self.event_id)
		url = "https://api.sofascore.com/api/v1/event/{}/media".format(self.event_id)
		if debug_MatchMedia:
			logdata("MatchMedia", "URL=%s" % url)
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
			'Referer': 'https://api.sofascore.com/',
			'Origin': 'https://api.sofascore.com',
			'Accept': 'application/json',
			'X-Requested-With': 'XMLHttpRequest'
		}
		if PY3:
			d = getPage(str.encode(url), contextFactory=WebClientContextFactory(url), timeout=25, headers={k.encode(): [v.encode()] for k, v in headers.items()})
			d.addCallback(lambda raw: self.screen.process_media(json.loads(raw.decode('utf-8'))))
			d.addErrback(lambda f: self._err(f))
		else:
			def _get():
				s = _make_sofa_session_py2()
				s.headers.update(headers)
				r = s.get(url, timeout=25, verify=False)
				if debug_MatchMedia:
					logdata("MatchMedia", "PY2 status=%d" % r.status_code)
				return json.loads(r.content.decode('utf-8')) if r.status_code == 200 else None
			d = deferToThread(_get)
			d.addCallback(self.screen.process_media)
			d.addErrback(lambda f: self._err(f))

	def _err(self, failure):
		if debug_MatchMedia:
			logdata("MatchMedia", "SofaScore deferred errback: %s" % failure.getErrorMessage())
		self.screen.process_media(None)


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
	return SofaScoreMatchMedia(screen, event_id)
