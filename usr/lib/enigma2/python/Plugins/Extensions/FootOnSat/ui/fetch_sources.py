# -*- coding: utf-8 -*-
import time
import json
import re
import random
import subprocess
import requests
from datetime import date, datetime, timedelta
from unicodedata import normalize
from difflib import SequenceMatcher
from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure
from Components.config import config
from .compat import *
from .setup import *
import os


SS_COOKIE_MAX_AGE = 1800


def _get_ss_cookie_file():
	try:
		data_dir, _, _ = get_data_paths()
		return os.path.join(data_dir, "sofa_cookies.txt")
	except Exception:
		return "/tmp/footonsat_ss_cookies.txt"


def _load_ss_cookies(session):
	cookie_file = _get_ss_cookie_file()
	if not os.path.exists(cookie_file):
		return
	try:
		jar = compat_MozillaCookieJar()
		jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
		count = 0
		for c in jar:
			session.cookies.set_cookie(c)
			count += 1
		if debug_Fetch_Live and count > 0:
			logdata("fetch_live_results", "Loaded %d cookies from %s" % (count, cookie_file))
	except Exception as e:
		if debug_Fetch_Live:
			logdata("fetch_live_results", "Cookie load error: %s" % str(e)[:100])


def _save_ss_cookies(session):
	cookie_file = _get_ss_cookie_file()
	try:
		try:
			d = os.path.dirname(cookie_file)
			if d and not os.path.exists(d):
				os.makedirs(d)
		except Exception:
			pass
		jar = compat_MozillaCookieJar()
		count = 0
		for c in session.cookies:
			jar.set_cookie(c)
			count += 1
		jar.save(cookie_file, ignore_discard=True, ignore_expires=True)
		if debug_Fetch_Live and count > 0:
			logdata("fetch_live_results", "Saved %d cookies to %s" % (count, cookie_file))
		elif debug_Fetch_Live:
			logdata("fetch_live_results", "No cookies to save (session empty)")
	except Exception as e:
		if debug_Fetch_Live:
			logdata("fetch_live_results", "Cookie save error: %s" % str(e)[:100])


# --- PY2 SSL fix: force weak ciphers globally (needed by SofaScore) ---
if not PY3:
	try:
		import ssl as _ssl_mod
		try:
			_sofa_ctx = _ssl_mod.create_default_context()
		except Exception:
			_sofa_ctx = _ssl_mod.SSLContext(_ssl_mod.PROTOCOL_TLSv1_2)
		_sofa_ctx.check_hostname = False
		_sofa_ctx.verify_mode = _ssl_mod.CERT_NONE
		for _cipher_str in ('DEFAULT@SECLEVEL=1',
		                    'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:!aNULL:!MD5:!DSS'):
			try:
				_sofa_ctx.set_ciphers(_cipher_str)
				break
			except Exception:
				continue
		try:
			_sofa_ctx.set_alpn_protocols(['http/1.1'])
		except Exception:
			pass
		_ssl_mod._create_default_https_context = lambda: _sofa_ctx
		_ssl_mod._create_unverified_context = lambda: _sofa_ctx
	except Exception:
		pass


class TLSAdapter(requests.adapters.HTTPAdapter):
	def init_poolmanager(self, *args, **kwargs):
		import ssl
		if PY3:
			ctx = ssl.create_default_context()
			try:
				ctx.minimum_version = ssl.TLSVersion.TLSv1_2
			except AttributeError:
				pass
			ctx.set_ciphers('DEFAULT@SECLEVEL=1')
			kwargs['ssl_context'] = ctx
			return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)
		else:
			# Python 2: old urllib3 does not accept ssl_context kwarg
			kwargs['cert_reqs'] = ssl.CERT_NONE
			kwargs['assert_hostname'] = False
			return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)


class LiveFetchBase(object):
	def __init__(self, screen):
		self.screen = screen
		self.current_ts = 0

	def _clean_name(self, name):
		name = name.replace('ø', 'o').replace('æ', 'ae').replace('å', 'a').replace('Ø', 'O').replace('Æ', 'AE').replace('Å', 'A')
		if not PY3 and isinstance(name, str):
			name = name.decode('ascii', 'ignore')
		try:
			if PY3:
				name = normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
			else:
				name = normalize('NFKD', name.decode('utf-8')).encode('ascii', 'ignore')
		except Exception:
			pass
		name = compat_str(name).strip().lower()
		name = name.replace('.', '')
		name = re.sub(r'[^a-z\s]', ' ', name, flags=re.IGNORECASE)
		NOISE = r'\b(nk|afc|fc|cf|as|ac|sk|fk|tsv|national|squad|sport|calcio|ploie[șs]ti|ploiești|ploieshti|aif|ifk|kf|ks|af|seinajoki|peshkopi|cd|real|nicosia)\b'
		name = re.sub(NOISE, ' ', name, flags=re.IGNORECASE)
		name = re.sub(r'\s+', ' ', name).strip()
		return name

	def _token_containment(self, a, b):
		wa = set(a.split())
		wb = set(b.split())
		if not wa or not wb:
			return 0.0
		overlap = len(wa & wb)
		return overlap / float(min(len(wa), len(wb)))

	def _do_fuzzy_matching(self, matches_list, live_matches, now_adj):
		match_perf_start = time.time()
		THRESHOLD = 0.45
		if getattr(self.screen, 'link', None):
			try:
				from Components.config import config as _cfg
				if _cfg.plugins.FootOnSat.source.value == "sportscore":
					THRESHOLD = 0.75
			except Exception:
				pass
		TIME_WINDOW = timedelta(hours=4)

		live_clean_cache = {}
		for live in live_matches:
			s_t1 = compat_str(live["team1"]).strip()
			s_t2 = compat_str(live["team2"]).strip()
			if s_t1 not in live_clean_cache:
				live_clean_cache[s_t1] = self._clean_name(s_t1)
			if s_t2 not in live_clean_cache:
				live_clean_cache[s_t2] = self._clean_name(s_t2)

		def _country_key(s):
			return re.sub(r'[^a-z]', '', compat_str(s).strip().lower())

		def _canonical_key(raw):
			return _country_key(raw)

		live_by_country = {}
		for live in live_matches:
			ck = _canonical_key(live.get('country', ''))
			if ck:
				live_by_country.setdefault(ck, []).append(live)
		distinct_sofa_keys = list(live_by_country.keys())
		local_country_resolve_cache = {}

		def _resolve_country_bucket(raw_country):
			if raw_country in local_country_resolve_cache:
				return local_country_resolve_cache[raw_country]
			key = _canonical_key(raw_country)
			bucket = live_by_country.get(key)
			if bucket is None and key:
				sorted_key = sorted(key)
				for sofa_key in distinct_sofa_keys:
					if sorted(sofa_key) == sorted_key:
						bucket = live_by_country.get(sofa_key)
						break
			local_country_resolve_cache[raw_country] = bucket
			return bucket

		word_index_by_country = {}
		for ck, bucket in live_by_country.items():
			idx = {}
			for live in bucket:
				for nm in (live_clean_cache[compat_str(live["team1"]).strip()], live_clean_cache[compat_str(live["team2"]).strip()]):
					for w in nm.split():
						if len(w) < 3:
							continue
						idx.setdefault(w, []).append(live)
			word_index_by_country[ck] = idx

		schedule_clean_cache = {}
		for match in matches_list:
			if getattr(self.screen, 'is_closed', True):
				return
			try:
				local_name = compat_str(match[0])
				teams = re.split(r'\s+(?:vs\.|vs|v\.|v|VS|Vs|VS\.)\s+|\s+-\s+', local_name, flags=re.IGNORECASE)
				if len(teams) != 2:
					continue
				l_t1 = compat_str(teams[0]).strip()
				l_t2 = compat_str(teams[1]).strip()
				if l_t1 not in schedule_clean_cache:
					schedule_clean_cache[l_t1] = self._clean_name(l_t1)
				if l_t2 not in schedule_clean_cache:
					schedule_clean_cache[l_t2] = self._clean_name(l_t2)
			except Exception:
				continue

		for match_idx, match in enumerate(matches_list):
			if getattr(self.screen, 'is_closed', True):
				return
			try:
				if debug_Fetch_Live:
					_dbg_name = compat_str(match[0]).lower()
					if "new york" in _dbg_name or "red bull" in _dbg_name or "medellin" in _dbg_name or "millonarios" in _dbg_name:
						logdata("fetch_live_results", "NY_MED_DEBUG local_raw='%s' country1='%s' country2='%s'" % (compat_str(match[0]), compat_str(match[3]) if len(match) > 3 else '', compat_str(match[4]) if len(match) > 4 else ''))
				time_str = compat_str(match[1])
				try:
					time_str_local = self.screen.getTime(time_str)
					local_dt = datetime.strptime(time_str_local.split(' - ')[1] + ' ' + time_str_local.split(' - ')[0], "%Y-%m-%d %H:%M")
				except Exception:
					local_dt = now_adj

				local_name = compat_str(match[0])
				teams = re.split(r'\s+(?:vs\.|vs|v\.|v|VS|Vs|VS\.)\s+|\s+-\s+', local_name, flags=re.IGNORECASE)
				if len(teams) != 2:
					match[5] = match[6] = match[7] = ""
					continue

				l_t1 = compat_str(teams[0]).strip()
				l_t2 = compat_str(teams[1]).strip()

				l_t1_clean = schedule_clean_cache.get(l_t1, "")
				l_t2_clean = schedule_clean_cache.get(l_t2, "")

				if debug_Fetch_Live:
					_dbg = compat_str(match[0]).lower()
					if "new york" in _dbg or "red bull" in _dbg or "medellin" in _dbg or "millonarios" in _dbg:
						logdata("fetch_live_results", "NY_MED_CLEANED l_t1='%s' l_t2='%s' local_dt=%s" % (l_t1_clean, l_t2_clean, local_dt))
				if not l_t1_clean or not l_t2_clean:
					match[5] = match[6] = match[7] = ""
					continue

				best_sim = 0.0
				best_live = None
				best_live_name_debug = None

				local_country1 = compat_str(match[3]) if len(match) > 3 else ''
				local_country2 = compat_str(match[4]) if len(match) > 4 else ''
				bucket1 = _resolve_country_bucket(local_country1) if local_country1 else None
				bucket2 = _resolve_country_bucket(local_country2) if local_country2 else None
				if bucket1 is not None and bucket2 is not None:
					search_pool = list(bucket1)
					if bucket2 is not bucket1:
						search_pool += bucket2
				else:
					search_pool = live_matches

				word_candidates = None
				seen_ids = set()
				for ck_try in filter(None, [
					_canonical_key(local_country1) if bucket1 is not None else None,
					_canonical_key(local_country2) if bucket2 is not None else None,
				]):
					idx = word_index_by_country.get(ck_try, {})
					for w in (l_t1_clean.split() + l_t2_clean.split()):
						if len(w) < 3:
							continue
						for live in idx.get(w, []):
							live_id = id(live)
							if live_id not in seen_ids:
								seen_ids.add(live_id)
								if word_candidates is None:
									word_candidates = []
								word_candidates.append(live)
				if word_candidates:
					search_pool = word_candidates

				relevant_live_events = [
					live for live in search_pool
					if abs(live["match_dt"] - local_dt) <= TIME_WINDOW
				]

				sm1 = SequenceMatcher(None, l_t1_clean, "")
				sm2 = SequenceMatcher(None, l_t2_clean, "")

				for live in relevant_live_events:
					s_t1 = compat_str(live["team1"]).strip()
					s_t2 = compat_str(live["team2"]).strip()
					s_t1_clean = live_clean_cache[s_t1]
					s_t2_clean = live_clean_cache[s_t2]

					len_l1 = len(l_t1_clean)
					len_s1 = len(s_t1_clean)
					len_l2 = len(l_t2_clean)
					len_s2 = len(s_t2_clean)

					straight_possible = (abs(len_l1 - len_s1) <= 20 and abs(len_l2 - len_s2) <= 20)
					swap_possible = (abs(len_l1 - len_s2) <= 20 and abs(len_l2 - len_s1) <= 20)
					if not (straight_possible or swap_possible):
						continue

					sm1.set_seq2(s_t1_clean)
					sim1 = max(sm1.ratio(), self._token_containment(l_t1_clean, s_t1_clean))
					sm2.set_seq2(s_t2_clean)
					sim2 = max(sm2.ratio(), self._token_containment(l_t2_clean, s_t2_clean))
					avg_straight = (sim1 + sim2) / 2.0

					sm1.set_seq2(s_t2_clean)
					sim1s = max(sm1.ratio(), self._token_containment(l_t1_clean, s_t2_clean))
					sm2.set_seq2(s_t1_clean)
					sim2s = max(sm2.ratio(), self._token_containment(l_t2_clean, s_t1_clean))
					avg_swap = (sim1s + sim2s) / 2.0

					cur_sim = max(avg_straight, avg_swap)

					if cur_sim > best_sim:
						best_sim = cur_sim
						best_live_name_debug = "%s vs %s" % (s_t1, s_t2)
						if avg_straight >= avg_swap:
							best_live = {
								"team1_score": live["team1_score"],
								"team2_score": live["team2_score"],
								"match_status": live["match_status"],
								"id": live.get("id", "")
							}
						else:
							best_live = {
								"team1_score": live["team2_score"],
								"team2_score": live["team1_score"],
								"match_status": live["match_status"],
								"id": live.get("id", "")
							}

				if best_sim >= THRESHOLD and best_live:
					if config.plugins.FootOnSat.livescore.value == "2":
						match[5] = compat_str(best_live["team1_score"]).strip()
						match[6] = compat_str(best_live["team2_score"]).strip()
						match[7] = compat_str(best_live["match_status"]).strip()
						if len(match) > 8:
							match[8] = str(best_live["id"])
						else:
							match.append(str(best_live["id"]))
					else:
						match[5] = match[6] = match[7] = ""
				else:
					if debug_Fetch_Live and best_sim > 0.30:
						best_name = best_live_name_debug if best_live_name_debug else 'N/A'
						logdata("fetch_live_results", "NO MATCH: local='%s' country=(%s,%s) candidates_checked=%d best_sim=%.2f (threshold=%.2f) closest_sofascore='%s'" % (local_name, compat_str(match[3]) if len(match) > 3 else 'N/A', compat_str(match[4]) if len(match) > 4 else 'N/A', len(relevant_live_events), best_sim, THRESHOLD, best_name))
					match[5] = match[6] = match[7] = ""
			except Exception:
				continue

		if debug_Fetch_Live:
			logdata("fetch_live_results", "FUZZY MATCH done in %.2fs for matches_list=%d against live_matches=%d" % (time.time() - match_perf_start, len(matches_list), len(live_matches)))
		return matches_list

	def _matching_complete(self, updated_matches_list):
		if self.screen.fetch_timestamp != self.current_ts:
			if debug_Fetch_Live:
				logdata("fetch_live_results", "DROP: Ignoring outdated results from previous session.")
			return
		if debug_Fetch_Live:
			logdata("fetch_live_results", "TOTAL fetch_live_results elapsed: %.2fs" % (time.time() - self.screen.fetch_timestamp))
		from .launcher import get_terminated_file
		cache_file, terminated_cache, changed, final_list = get_terminated_file(), {}, False, []
		try:
			if exists(cache_file):
				with open(cache_file, 'r') as f:
					data = json.load(f)
					terminated_cache = data if isinstance(data, dict) else {name: datetime.now().strftime("%H:%M - %Y-%m-%d") for name in data}
		except Exception:
			pass
		now_dt = datetime.now()
		cleaned_cache = {}
		for name, ts in terminated_cache.items():
			try:
				record_dt = datetime.strptime(ts, "%H:%M - %Y-%m-%d")
				if record_dt.date() == now_dt.date() or (now_dt - record_dt < timedelta(hours=4)):
					cleaned_cache[name] = ts
				else:
					changed = True
			except Exception:
				changed = True
		terminated_cache = cleaned_cache
		for m in updated_matches_list:
			m_name, m_status = str(m[0]), str(m[7]).upper()
			m_time_str = self.screen.getTime(str(m[1]))
			if 'DELAYED' in m_status:
				m_time_str = "%s - %s" % (title130, m_time_str.split(' - ')[1])
			is_term = any(x in m_status for x in ('FINISHED', 'CANCELED', 'POSTPONED'))
			in_cache = m_name in terminated_cache
			if getattr(self.screen, 'link', None) == "live":
				if is_term and not in_cache:
					terminated_cache[m_name] = m_time_str
					changed = True
				if is_term or in_cache:
					continue
			elif getattr(self.screen, 'link', None) == "end":
				# Do not re-filter here. The initial "end" filter is already
				# applied in getData() based on JSON data (stype / match date).
				# Re-filtering based on live-event status would wrongly remove
				# matches whose events could not be matched in the current
				# live data (e.g. leagues not covered by the selected source).
				pass
			final_list.append(m)
		if debug_Fetch_Live:
			logdata("fetch_live_results", "MATCHES AFTER: %d" % len(final_list))
		self.screen.matches = final_list
		if changed and self.screen.link == "live":
			try:
				with open(cache_file, 'w') as f:
					json.dump(terminated_cache, f, ensure_ascii=False)
			except Exception:
				pass
		try:
			self.screen.iniMenu()
		except Exception:
			pass

	def _handle_live_matches(self, live_matches):
		if self.screen.is_closed:
			return
		if live_matches is None:
			return
		if not live_matches:
			self.screen.matches = [list(m) for m in self.screen.matches]
			try:
				self.screen.iniMenu()
			except Exception:
				pass
			return
		matches_list = [list(m) for m in self.screen.matches]
		now_adj = datetime.now() - timedelta(minutes=3)
		d_match = deferToThread(self._do_fuzzy_matching, matches_list, live_matches, now_adj)
		d_match.addCallback(self._matching_complete)
		d_match.addErrback(lambda f: logdata("fetch_live_results", "Fuzzy matching thread failed: %s" % f.getErrorMessage()) if not getattr(self.screen, 'is_closed', True) else None)

	def _decode_and_build(self, raw_list):
		all_events = []
		for idx, raw in enumerate(raw_list):
			if self.screen.is_closed:
				return None
			if raw is None:
				continue
			try:
				data_str = raw.decode('utf-8', errors='ignore')
				data = json.loads(data_str)
				events = data.get('events', [])
				all_events.extend(events)
			except ValueError as e:
				if debug_Fetch_Live:
					logdata("fetch_live_results", "JSON parse error (ValueError): %s" % str(e))
					logdata("fetch_live_results", "Corrupt Data Snippet: %s..." % data_str[:256].replace('\n', ' '))
				continue
			except Exception as e:
				if debug_Fetch_Live:
					logdata("fetch_live_results", "Decode/General error: %s" % str(e))
				continue

		if debug_Fetch_Live:
			logdata("fetch_live_results", "JSON DECODE/EXTRACT done, total events=%d" % len(all_events))

		if not all_events:
			return []

		events = all_events
		now = datetime.now()
		now_adj = now - timedelta(minutes=3)
		live_matches = []
		build_start = time.time()
		for ev in events:
			if self.screen.is_closed:
				break
			try:
				try:
					home_team = ev.get('homeTeam') or {}
					away_team = ev.get('awayTeam') or {}
					home = compat_str(home_team.get('shortName') or home_team.get('name', 'Unknown Home'))
					away = compat_str(away_team.get('shortName') or away_team.get('name', 'Unknown Away'))
					if home == 'Unknown Home' or away == 'Unknown Away':
						continue
					tourn_cat = (ev.get('tournament') or {}).get('category', {}) or (ev.get('uniqueTournament') or {}).get('category', {})
					ev_country = tourn_cat.get('country', {}).get('name', '') or home_team.get('country', {}).get('name', '') or away_team.get('country', {}).get('name', '')
				except Exception as e:
					if debug_Fetch_Live:
						logdata("fetch_live_results", "Team name parse error: %s" % str(e))
					continue
				match_name = "{0} vs {1}".format(home, away)

				h_score_raw = compat_str(ev.get('homeScore', {}).get('current', '')) or ''
				a_score_raw = compat_str(ev.get('awayScore', {}).get('current', '')) or ''
				h_score = h_score_raw
				a_score = a_score_raw

				status_obj = ev.get('status', {})
				stype = status_obj.get('type', '')
				descr = status_obj.get('description', '')

				ts = ev.get('startTimestamp')
				match_dt = datetime.fromtimestamp(ts) if ts else now_adj

				status = ''
				if stype == 'canceled':
					status = title214
				elif stype == 'finished':
					status = title125
				elif stype == 'postponed':
					status = title152
					h_score = a_score = ''
				elif stype == 'interrupted':
					status = title299
				elif stype == 'inprogress':
					m = re.search(r'(\d{1,3}[\'+]*\+?\d*)\s*\'', descr)
					if m:
						status = '{0} min'.format(m.group(1))
					elif 'extra time' in descr.lower():
						status = title153
					elif 'penalties' in descr.lower():
						status = title154
					elif descr.lower() in ['half time', 'halftime']:
						status = title155
					elif 'delayed' in descr.lower():
						status = title156
					else:
						try:
							status_time_ts = ev.get('statusTime', {}).get('timestamp')
							if status_time_ts:
								minutes_diff = int((datetime.now() - datetime.fromtimestamp(status_time_ts)).total_seconds() // 60)
								if descr.lower() == '2nd half':
									minutes_diff += 45
								status = '{0} min'.format(minutes_diff)
							else:
								status = ''
						except Exception:
							status = ''

				if match_dt > now + timedelta(minutes=10) and stype not in ['inprogress', 'canceled', 'postponed', 'afterextra', 'penaltyshootout', 'interrupted']:
					h_score = a_score = ''
					status = ''
				elif stype in ['notstarted', 'canceled']:
					h_score = a_score = ''
					if stype == 'canceled':
						status = '%s' % title124
					else:
						status = ''

				tournament_name = ev.get('tournament', {}).get('name', '') or ev.get('uniqueTournament', {}).get('name', '')

				live_matches.append({
					"match_name": match_name,
					"team1": home,
					"team2": away,
					"team1_score": h_score,
					"team2_score": a_score,
					"match_status": status,
					"match_dt": match_dt,
					"raw_descr": descr,
					"id": ev.get('id', ''),
					"tournament_name": tournament_name,
					"country": ev_country
				})
			except Exception as e:
				if debug_Fetch_Live:
					logdata("fetch_live_results", "Error building live_matches for an event: %s" % str(e))
				continue

		if debug_Fetch_Live:
			logdata("fetch_live_results", "EVENT BUILD done in %.2fs, live_matches=%d" % (time.time() - build_start, len(live_matches)))
		return live_matches

	def _process_response(self, raw_list):
		if self.screen.fetch_timestamp != self.current_ts:
			return
		if debug_Fetch_Live:
			logdata("fetch_live_results", "MATCHES BEFORE: %d" % len(self.screen.matches))
			logdata("fetch_live_results", "NETWORK FETCH done, %d responses" % len(raw_list))
			logdata("fetch_live_results", "DEBUG_RAW_LIST_TYPES: total=%d types=%s" % (len(raw_list), list(set(type(x).__name__ for x in raw_list))))
		for _i, _r in enumerate(raw_list):
			if debug_Fetch_Live:
				logdata("fetch_live_results", "DEBUG_RAW_LIST_%d: len=%s preview=%s" % (_i, len(_r) if _r else 0, (_r[:200] if _r else b'')))

		def _decode_wrapper(raw_list):
			if self.screen.is_closed:
				return None
			return self._decode_and_build(raw_list)

		def _done(live_matches):
			if self.screen.fetch_timestamp != self.current_ts:
				return
			self._handle_live_matches(live_matches)

		deferToThread(_decode_wrapper, raw_list).addCallback(_done).addErrback(lambda f: logdata("fetch_live_results", "Decode/build thread failed: %s" % f.getErrorMessage()) if not getattr(self.screen, 'is_closed', True) else None)


	def fetch(self):
		raise NotImplementedError


class SofaScoreFetcher(LiveFetchBase):
	def _ss_bootstrap(self, cookie_file):
		try:
			os.remove(cookie_file)
		except Exception:
			pass
		try:
			subprocess.call([
				"/usr/bin/curl_chrome150", "-s", "-L", "-k",
				"--max-time", "15",
				"-c", cookie_file,
				"https://www.sofascore.com/",
				"-o", "/dev/null"
			], stderr=subprocess.PIPE)
		except Exception:
			pass

	def _ss_get(self, url, cookie_file, timeout=20):
		url_str = url.decode('utf-8') if isinstance(url, bytes) else url
		def _worker():
			try:
				out = subprocess.check_output([
					"/usr/bin/curl_chrome150", "-s", "-L", "-k",
					"--max-time", str(timeout),
					"-b", cookie_file,
					"-H", "X-Requested-With: XMLHttpRequest",
					"-H", "Accept: application/json, text/plain, */*",
					"-H", "Referer: https://www.sofascore.com/",
					"-H", "Origin: https://www.sofascore.com",
					url_str
				], stderr=subprocess.PIPE)
				return out
			except Exception:
				return None
		d = defer.Deferred()
		deferToThread(_worker).addCallback(d.callback).addErrback(d.errback)
		return d

	def fetch(self):
		if not os.path.exists("/usr/bin/curl_chrome150"):
			if debug_Fetch_Live:
				logdata("fetch_live_results", "WARNING: curl-impersonate not installed, live data will be unavailable")
			return
		if not self.screen.matches:
			self.screen.onWindowShow()
			return
		self.screen.fetch_timestamp = time.time()
		self.current_ts = self.screen.fetch_timestamp
		if debug_Fetch_Live:
			logdata("fetch_live_results", "fetch_live_results initiated.")

		index = self.screen['list1'].getSelectionIndex()
		current_match = self.screen.matches[index]
		if self.screen.link == "yesterday":
			selected_date = current_match[1].split(' - ')[1]
		else:
			selected_date = date.today().isoformat()
		if debug_Fetch_Live:
			logdata("fetch_live_results", "Current Link: %s" % self.screen.link)
			logdata("fetch_live_results", "Selected Date: %s" % selected_date)

		cookie_file = "/tmp/ss_cf_cookies.txt"
		self._ss_bootstrap(cookie_file)

		d = defer.Deferred()

		def _fetch_page(page, urls, d_final):
			url = 'https://www.sofascore.com/api/v1/sport/football/scheduled-tournaments/{0}/page/{1}'.format(selected_date, page)
			def _cb(raw):
				try:
					data = json.loads(raw.decode('utf-8', 'ignore'))
					scheduled = data.get("scheduled", [])
					for item in scheduled:
						t = item.get("tournament", {})
						ut = t.get("uniqueTournament")
						if ut and ut.get("id"):
							urls.append("https://www.sofascore.com/api/v1/unique-tournament/{0}/scheduled-events/{1}".format(ut["id"], selected_date))
						elif t.get("id"):
							urls.append("https://www.sofascore.com/api/v1/tournament/{0}/scheduled-events/{1}".format(t["id"], selected_date))
					if data.get("hasNextPage", False) and config.plugins.FootOnSat.livescoresearchlevel.value == "2":
						_fetch_page(page + 1, urls, d_final)
					else:
						urls_unique = list(set(urls))
						if debug_Fetch_Live:
							logdata("fetch_live_results", "DISCOVERY DONE: %d tournament URLs" % len(urls_unique))
						deferreds = [self._ss_get(u, cookie_file, timeout=20) for u in urls_unique]
						if not deferreds:
							d_final.callback([b'{"events":[]}'])
						else:
							def _unwrap(dl_results):
								out = []
								for ok, value in dl_results:
									if ok and value:
										out.append(value)
								return out or [b'{"events":[]}']
							defer.DeferredList(deferreds, consumeErrors=True).addCallback(_unwrap).chainDeferred(d_final)
				except Exception:
					d_final.callback([b'{"events":[]}'])
			def _eb(err):
				if debug_Fetch_Live:
					logdata("fetch_live_results", "DISCOVERY_ERR: %s" % str(err))
				d_final.callback([b'{"events":[]}'])
			self._ss_get(url, cookie_file, timeout=20).addCallback(_cb).addErrback(_eb)

		_fetch_page(1, [], d)
		self.screen.fetch_deferred = d

		def process_results(results):
			valid = []
			for r in results:
				if r and not isinstance(r, Failure):
					valid.append(r)
			return valid or [b'{"events":[]}']

		d.addCallback(process_results)

		def _error(failure):
			if self.screen.is_closed:
				return
			if debug_Fetch_Live:
				logdata("fetch_live_results", "Twisted Request failed: %s" % failure.getErrorMessage())

		d.addCallback(self._process_response)
		d.addErrback(_error)


class SportScoreFetcher(LiveFetchBase):
	def _sportscore_get(self, endpoint, timeout=20):
		url = "https://sportscore.com/api/widget/" + endpoint
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
			'Accept': 'application/json',
		}
		try:
			r = requests.get(url, headers=headers, timeout=timeout, verify=False)
			if r.status_code == 200:
				return r.json()
			if debug_Fetch_Live:
				logdata("fetch_live_results", "SportScore HTTP %s" % r.status_code)
			return None
		except Exception as e:
			if debug_Fetch_Live:
				logdata("fetch_live_results", "SportScore exception: %s" % str(e)[:200])
			return None

	def _convert_match_to_event(self, m):
		if not isinstance(m, dict):
			return None
		home_name = m.get("home")
		away_name = m.get("away")
		if not home_name or not away_name:
			return None
		if not isinstance(home_name, str):
			home_name = str(home_name)
		if not isinstance(away_name, str):
			away_name = str(away_name)

		status_short = str(m.get("status", "")).strip().lower()
		status_long = str(m.get("status_text", ""))

		if status_short in ("finished", "ft", "aet", "pen"):
			ss_type = "finished"
			if status_short == "aet":
				status_long = "After Extra Time"
			elif status_short == "pen":
				status_long = "Penalties"
			else:
				status_long = "Ended"
		elif status_short == "ht":
			ss_type = "inprogress"
			status_long = "Halftime"
		elif status_short in ("live", "inprogress", "1h", "2h", "et", "p"):
			ss_type = "inprogress"
		elif status_short in ("postponed", "pst"):
			ss_type = "postponed"
			status_long = "Postponed"
		elif status_short in ("canceled", "canc", "abd", "awd", "wo"):
			ss_type = "canceled"
			status_long = "Canceled"
		elif status_short in ("susp", "interrupted", "int"):
			ss_type = "interrupted"
			status_long = "Interrupted"
		else:
			ss_type = "notstarted"

		home_score = m.get("home_score", "")
		away_score = m.get("away_score", "")
		if home_score is None:
			home_score = ""
		if away_score is None:
			away_score = ""

		ts = 0
		time_str = m.get("time")
		if time_str:
			ts = compat_parse_iso(time_str)

		competition = m.get("competition", "")
		if not isinstance(competition, str):
			competition = str(competition)

		return {
			"homeTeam": {"name": home_name, "shortName": home_name},
			"awayTeam": {"name": away_name, "shortName": away_name},
			"homeScore": {"current": str(home_score)},
			"awayScore": {"current": str(away_score)},
			"status": {"type": ss_type, "description": status_long},
			"startTimestamp": ts,
			"id": str(m.get("id", "")),
			"tournament": {"name": competition, "category": {"country": {"name": ""}}}
		}

	def fetch(self):
		if not self.screen.matches:
			self.screen.onWindowShow()
			return
		self.screen.fetch_timestamp = time.time()
		self.current_ts = self.screen.fetch_timestamp
		if debug_Fetch_Live:
			logdata("fetch_live_results", "SportScore fetch started")

		data = self._sportscore_get("matches/?sport=football&limit=50")
		if not data or not data.get("matches"):
			data = self._sportscore_get("matches/?sport=football&limit=500")
		if not data or not data.get("matches"):
			data = self._sportscore_get("matches/")
		if not data or not data.get("matches"):
			data = self._sportscore_get("matches/?sport=football&day=today")
		if not data or not data.get("matches"):
			data = self._sportscore_get("matches/?sport=football&type=top")
		if not data or not data.get("matches"):
			data = self._sportscore_get("matches/?sport=football&type=all")
		if not data or not data.get("matches"):
			if debug_Fetch_Live:
				logdata("fetch_live_results", "SportScore no data")
			try:
				self.screen.iniMenu()
			except Exception:
				pass
			return

		events = []
		for m in data["matches"]:
			ev = self._convert_match_to_event(m)
			if ev:
				events.append(ev)

		if debug_Fetch_Live:
			first = data["matches"][0] if data.get("matches") else {}
			logdata("fetch_live_results", "SportScore FIRST_MATCH_KEYS: %s" % list(first.keys()))
			logdata("fetch_live_results", "SportScore FIRST_MATCH: %s" % str(first)[:600])

		raw_json = json.dumps({"events": events}).encode('utf-8')
		raw_list = [raw_json]

		self._process_response(raw_list)


class SportsDBFetcher(LiveFetchBase):
	def _sportsdb_get(self, day, timeout=20):
		url = "https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={0}&s=Soccer".format(day)
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
			'Accept': 'application/json',
		}
		try:
			r = requests.get(url, headers=headers, timeout=timeout, verify=False)
			if r.status_code == 200:
				return r.json()
			if debug_Fetch_Live:
				logdata("fetch_live_results", "TheSportsDB HTTP %s" % r.status_code)
			return None
		except Exception as e:
			if debug_Fetch_Live:
				logdata("fetch_live_results", "TheSportsDB exception: %s" % str(e)[:200])
			return None

	def _convert_event(self, ev):
		if not isinstance(ev, dict):
			return None
		home_name = ev.get("strHomeTeam")
		away_name = ev.get("strAwayTeam")
		if not home_name or not away_name:
			return None
		if not isinstance(home_name, str):
			home_name = str(home_name)
		if not isinstance(away_name, str):
			away_name = str(away_name)

		status_raw = str(ev.get("strStatus", "")).strip()
		status_low = status_raw.lower()

		if status_low in ("ft", "aet", "pen", "ft_pen", "match finished"):
			ss_type = "finished"
			status_long = "Ended"
			if status_low == "aet":
				status_long = "After Extra Time"
			elif status_low in ("pen", "ft_pen"):
				status_long = "Penalties"
		elif status_low in ("1h", "2h", "ht", "et", "live", "inprogress"):
			ss_type = "inprogress"
			status_long = status_raw
		elif status_low in ("postponed", "pst"):
			ss_type = "postponed"
			status_long = "Postponed"
		elif status_low in ("canceled", "cancelled", "canc", "abd", "awd", "wo"):
			ss_type = "canceled"
			status_long = "Canceled"
		elif status_low in ("susp", "interrupted", "int"):
			ss_type = "interrupted"
			status_long = "Interrupted"
		else:
			ss_type = "notstarted"
			status_long = ""

		home_score = ev.get("intHomeScore")
		away_score = ev.get("intAwayScore")
		if home_score is None:
			home_score = ""
		if away_score is None:
			away_score = ""

		ts = 0
		time_str = ev.get("strTimestamp")
		if time_str:
			ts = compat_parse_iso(time_str)

		league = ev.get("strLeague", "")
		if not isinstance(league, str):
			league = str(league)
		country = ev.get("strCountry", "")
		if not isinstance(country, str):
			country = str(country)

		return {
			"homeTeam": {"name": home_name, "shortName": home_name},
			"awayTeam": {"name": away_name, "shortName": away_name},
			"homeScore": {"current": str(home_score)},
			"awayScore": {"current": str(away_score)},
			"status": {"type": ss_type, "description": status_long},
			"startTimestamp": ts,
			"id": str(ev.get("idEvent", "")),
			"tournament": {"name": league, "category": {"country": {"name": country}}}
		}

	def fetch(self):
		if not self.screen.matches:
			self.screen.onWindowShow()
			return
		self.screen.fetch_timestamp = time.time()
		self.current_ts = self.screen.fetch_timestamp
		if debug_Fetch_Live:
			logdata("fetch_live_results", "TheSportsDB fetch started")

		if self.screen.link == "yesterday":
			selected_date = date.today() - timedelta(days=1)
		else:
			selected_date = date.today()
		selected_date_str = selected_date.isoformat()

		if debug_Fetch_Live:
			logdata("fetch_live_results", "TheSportsDB date: %s" % selected_date_str)

		data = self._sportsdb_get(selected_date_str)
		raw_events = []
		if data and isinstance(data, dict):
			raw_events = data.get("events") or []

		if debug_Fetch_Live:
			logdata("fetch_live_results", "TheSportsDB raw events=%d" % len(raw_events))

		events = []
		for ev in raw_events:
			converted = self._convert_event(ev)
			if converted:
				events.append(converted)

		if debug_Fetch_Live:
			logdata("fetch_live_results", "TheSportsDB events=%d" % len(events))

		if not events:
			try:
				self.screen.iniMenu()
			except Exception:
				pass
			return

		raw_json = json.dumps({"events": events}).encode('utf-8')
		raw_list = [raw_json]

		self._process_response(raw_list)


class ESPNFetcher(LiveFetchBase):
	def _espn_get(self, url, timeout=20):
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
			'Accept': 'application/json',
		}
		try:
			r = requests.get(url, headers=headers, timeout=timeout, verify=False)
			if r.status_code == 200:
				return r.json()
			if debug_Fetch_Live:
				logdata("fetch_live_results", "ESPN HTTP %s" % r.status_code)
			return None
		except Exception as e:
			if debug_Fetch_Live:
				logdata("fetch_live_results", "ESPN exception: %s" % str(e)[:200])
			return None

	def _convert_event(self, ev, league_name, league_slug=""):
		if not isinstance(ev, dict):
			return None
		competitions = ev.get("competitions", [])
		if not competitions:
			return None
		comp = competitions[0]
		competitors = comp.get("competitors", [])
		if len(competitors) < 2:
			return None

		home = None
		away = None
		for c in competitors:
			if c.get("homeAway") == "home":
				home = c
			elif c.get("homeAway") == "away":
				away = c
		if not home or not away:
			return None

		home_team = home.get("team", {})
		away_team = away.get("team", {})
		home_name = home_team.get("displayName", "Unknown Home")
		away_name = away_team.get("displayName", "Unknown Away")
		if not isinstance(home_name, str):
			home_name = str(home_name)
		if not isinstance(away_name, str):
			away_name = str(away_name)

		home_abbrev = home_team.get("abbreviation", "")
		away_abbrev = away_team.get("abbreviation", "")
		if not isinstance(home_abbrev, str):
			home_abbrev = ""
		if not isinstance(away_abbrev, str):
			away_abbrev = ""
		home_abbrev = home_abbrev.strip()
		away_abbrev = away_abbrev.strip()
		if home_abbrev:
			home_short = home_name + " " + home_abbrev
		else:
			home_short = home_name
		if away_abbrev:
			away_short = away_name + " " + away_abbrev
		else:
			away_short = away_name

		status_obj = comp.get("status", {})
		status_type = status_obj.get("type", {})
		state = status_type.get("state", "pre")
		description = status_type.get("description", "")
		detail = status_type.get("detail", "")
		if not isinstance(detail, str):
			detail = ""
		if debug_Fetch_Live:
			logdata("fetch_live_results", "ESPN_STATUS: state=%s descr='%s' detail='%s'" % (state, description, detail))

		detail = status_type.get("detail", "")
		if not isinstance(detail, str):
			detail = ""

		if state == "post":
			ss_type = "finished"
			status_long = "Ended"
		elif state == "in":
			ss_type = "inprogress"
			if detail:
				status_long = detail
			else:
				status_long = description
		else:
			ss_type = "notstarted"
			status_long = ""

		home_score = home.get("score")
		away_score = away.get("score")
		if home_score is None:
			home_score = ""
		if away_score is None:
			away_score = ""

		ts = 0
		date_str = ev.get("date")
		if date_str:
			ts = compat_parse_iso(date_str)

		return {
			"homeTeam": {"name": home_name, "shortName": home_short},
			"awayTeam": {"name": away_name, "shortName": away_short},
			"homeScore": {"current": str(home_score)},
			"awayScore": {"current": str(away_score)},
			"status": {"type": ss_type, "description": status_long},
			"startTimestamp": ts,
			"id": ("%s|%s" % (league_slug, ev.get("id", ""))) if league_slug else str(ev.get("id", "")),
			"tournament": {"name": league_name, "category": {"country": {"name": ""}}}
		}

	def fetch(self):
		if not self.screen.matches:
			self.screen.onWindowShow()
			return
		self.screen.fetch_timestamp = time.time()
		self.current_ts = self.screen.fetch_timestamp
		if debug_Fetch_Live:
			logdata("fetch_live_results", "ESPN fetch started")

		if self.screen.link == "yesterday":
			selected_date = date.today() - timedelta(days=1)
		else:
			selected_date = date.today()
		date_compact = selected_date.strftime("%Y%m%d")

		date_prev = (selected_date - timedelta(days=1)).strftime("%Y%m%d")
		date_next = (selected_date + timedelta(days=1)).strftime("%Y%m%d")
		try:
			limit = config.plugins.FootOnSat.espn_limit.value
		except Exception:
			limit = "500"
		if debug_Fetch_Live:
			logdata("fetch_live_results", "ESPN dates: %s/%s/%s limit: %s" % (date_prev, date_compact, date_next, limit))

		leagues_data = self._espn_get("https://sports.core.api.espn.com/v2/sports/soccer/leagues?limit={0}".format(limit))
		if debug_Fetch_Live:
			logdata("fetch_live_results", "ESPN leagues RAW_TYPE: %s" % type(leagues_data).__name__)
			if leagues_data:
				logdata("fetch_live_results", "ESPN leagues RAW_KEYS: %s" % (list(leagues_data.keys()) if isinstance(leagues_data, dict) else "not-dict"))
				logdata("fetch_live_results", "ESPN leagues PREVIEW: %s" % str(leagues_data)[:500])
		if not leagues_data:
			if debug_Fetch_Live:
				logdata("fetch_live_results", "ESPN no leagues data")
			try:
				self.screen.iniMenu()
			except Exception:
				pass
			return

		league_items = leagues_data.get("items", [])
		if debug_Fetch_Live:
			logdata("fetch_live_results", "ESPN total leagues: %d" % len(league_items))
			if league_items:
				logdata("fetch_live_results", "ESPN FIRST_LEAGUE: %s" % str(league_items[0])[:300])

		import threading

		all_events = []
		seen_ids = set()
		lock = threading.Lock()

		def _fetch_league(league_ref):
			try:
				ref_url = league_ref.get("$ref")
				if not ref_url:
					return
				ref_data = self._espn_get(ref_url, timeout=10)
				if not ref_data:
					return
				slug = ref_data.get("slug", "")
				name = ref_data.get("name", "")
				if not slug:
					return
				events = []
				seen_local = set()
				for d in (date_prev, date_compact, date_next):
					scoreboard_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/{0}/scoreboard?dates={1}".format(slug, d)
					data = self._espn_get(scoreboard_url, timeout=15)
					if not data:
						continue
					for ev in data.get("events", []):
						ev_id = str(ev.get("id", ""))
						if ev_id and ev_id in seen_local:
							continue
						events.append(ev)
						if ev_id:
							seen_local.add(ev_id)
				if not events:
					return
				if debug_Fetch_Live and events:
					logdata("fetch_live_results", "ESPN_LEAGUE_HIT [%s/%s]: %d events" % (slug, name, len(events)))
					if slug in ("col.1", "usa.1"):
						for _ev in events:
							try:
								_comps = _ev.get("competitions", [{}])[0]
								_competitors = _comps.get("competitors", [])
								_h = next((c for c in _competitors if c.get("homeAway") == "home"), {})
								_a = next((c for c in _competitors if c.get("homeAway") == "away"), {})
								_hn = _h.get("team", {}).get("displayName", "?")
								_an = _a.get("team", {}).get("displayName", "?")
								_dt = _ev.get("date", "?")
								_st = _comps.get("status", {}).get("type", {}).get("state", "?")
								logdata("fetch_live_results", "ESPN_SAMPLE [%s] %s vs %s | date=%s | state=%s" % (slug, _hn, _an, _dt, _st))
							except Exception:
								continue
				local_converted = []
				for ev in events:
					ev_id = str(ev.get("id", ""))
					if ev_id and ev_id in seen_ids:
						continue
					converted = self._convert_event(ev, name, slug)
					if converted:
						local_converted.append((ev_id, converted))
				with lock:
					for ev_id, conv in local_converted:
						if ev_id and ev_id in seen_ids:
							continue
						all_events.append(conv)
						if ev_id:
							seen_ids.add(ev_id)
			except Exception as e:
				if debug_Fetch_Live:
					logdata("fetch_live_results", "ESPN league fetch error: %s" % str(e)[:100])

		def _run_all():
			threads = []
			for item in league_items:
				t = threading.Thread(target=_fetch_league, args=(item,))
				t.daemon = True
				threads.append(t)
			max_parallel = 20
			for i in range(0, len(threads), max_parallel):
				batch = threads[i:i+max_parallel]
				for t in batch:
					t.start()
				for t in batch:
					t.join()
			return all_events

		def _done(events):
			if self.screen.fetch_timestamp != self.current_ts:
				return
			if debug_Fetch_Live:
				logdata("fetch_live_results", "ESPN events=%d" % len(events))
			if not events:
				try:
					self.screen.iniMenu()
				except Exception:
					pass
				return
			raw_json = json.dumps({"events": events}).encode('utf-8')
			self._process_response([raw_json])

		d = deferToThread(_run_all)
		d.addCallback(_done)
		d.addErrback(lambda f: logdata("fetch_live_results", "ESPN fetch failed: %s" % f.getErrorMessage()))


def get_live_fetcher(source, screen):
	if source == "sportscore":
		return SportScoreFetcher(screen)
	if source == "espn":
		return ESPNFetcher(screen)
	return SofaScoreFetcher(screen)
