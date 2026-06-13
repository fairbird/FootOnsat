# -*- coding: utf-8 -*-
import os, io, re, gc, sys, math, codecs, random, time, shutil, difflib, requests, subprocess, signal
from time import strftime
from sqlite3 import connect
from bs4 import BeautifulSoup
from unicodedata import normalize
from difflib import SequenceMatcher
from datetime import date, datetime, timedelta
from os.path import join, exists
from enigma import eSize, eTimer, gRGB, loadPNG, gPixmapPtr, RT_WRAP, ePoint, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, \
				gFont, eConsoleAppContainer, eServiceCenter, eServiceReference
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaBlend
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Button import Button
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Components.config import config
from Components.PluginComponent import plugins
from Screens.Screen import Screen
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.ChannelSelection import ChannelSelection
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
from Tools.LoadPixmap import LoadPixmap
from twisted.internet import defer, reactor
from twisted.python.failure import Failure
from twisted.internet.ssl import ClientContextFactory
from twisted.internet.threads import deferToThread
from twisted.internet._sslverify import ClientTLSOptions
from twisted.internet.threads import blockingCallFromThread
from twisted.web.client import getPage, downloadPage
from .YouTubeVideoUrl import YouTubeVideoUrl
from .compat import *
from .setup import *

try:
	from skin import parseColor
except ImportError:
	parseColor = False

try:
	import ujson as json
except ImportError:
	import json

### images path
OPENBH="/usr/lib/enigma2/python/Screens/BpBlue.py"
OPENBH2="/usr/lib/enigma2/python/Screens/BpBlue.pyc"
OPENVIX="/usr/lib/enigma2/python/Plugins/SystemPlugins/ViX"

PLUGINPATH="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"

# debug
debug_Notif = config.plugins.FootOnSat.debug_Notif.value
debug_Standings = config.plugins.FootOnSat.debug_Standings.value
debug_MatchMedia = config.plugins.FootOnSat.debug_MatchMedia.value
debug_MatchStatistics = config.plugins.FootOnSat.debug_MatchStatistics.value
debug_MatchDetails = config.plugins.FootOnSat.debug_MatchDetails.value
debug_ZAP = config.plugins.FootOnSat.debug_ZAP.value
debug_Fetch_Live = config.plugins.FootOnSat.debug_Fetch_Live.value
debug_Ignore = config.plugins.FootOnSat.debug_Ignore.value
debug_favorite = config.plugins.FootOnSat.debug_favorite.value

# Check for PIL availability first, and import if found
try:
	from PIL import Image
	PIL_AVAILABLE = True
except ImportError:
	PIL_AVAILABLE = False
	# Log a warning if PIL is not available, as conversion will fail
	if debug_Standings: logdata("Logos", "WARNING: PIL/Pillow library not found. Non-PNG logo conversion will fail.")

try:
	from enigma import BT_SCALE, RT_VALIGN_CENTER, RT_HALIGN_LEFT
except ImportError:
	BT_SCALE = 0
	RT_VALIGN_CENTER = 0
	RT_HALIGN_LEFT = 0

try:
	from enigma import RT_HALIGN_RIGHT
except ImportError:
	RT_HALIGN_RIGHT = 2

if isUHD():
        from Plugins.Extensions.FootOnSat.assets.skin.skinUHD import *
else:
        from Plugins.Extensions.FootOnSat.assets.skin.skinFHD import *

## url for Standings table
json_urls = {
	# Champions league
	"championsleague": "https://www.sofascore.com/tournament/football/europe/uefa-champions-league/7#id:76953",
	# Europa league
	"europaleague": "https://www.sofascore.com/tournament/football/europe/uefa-europa-league/679#id:76984",
	# Conference league
	"ConferenceLeague": "https://www.sofascore.com/tournament/football/europe/uefa-europa-conference-league/17015#id:76960",
	# England league
	"premierleague": "https://www.sofascore.com/tournament/football/england/premier-league/17#id:76986",
	# champion ship league
	"championship": "https://www.sofascore.com/tournament/football/england/championship/18#id:77347",
	# Italy league
	"seriea": "https://www.sofascore.com/tournament/football/italy/serie-a/23#id:76457",
	# France league
	"ligue1": "https://www.sofascore.com/tournament/football/france/ligue-1/34#id:77356",
	# Spain league 1 + 2
	"laliga": "https://www.sofascore.com/tournament/football/spain/laliga/8#id:77559",
	"laliga2": "https://www.sofascore.com/tournament/football/spain/laliga-2/54#id:77558",
	# Germany league 1 + 2
	"bundesliga": "https://www.sofascore.com/tournament/football/germany/bundesliga/35#id:77333",
	"bundesliga2": "https://www.sofascore.com/tournament/football/germany/2-bundesliga/44#id:77354",
	# Portugal league
	"liganos": "https://www.sofascore.com/tournament/football/portugal/liga-portugal-betclic/238#id:77806",
	# Belgium league
	"belgianpro": "https://www.sofascore.com/tournament/football/belgium/pro-league/38#id:77040",
	# Turkey league
	"superLig": "https://www.sofascore.com/tournament/football/turkey/trendyol-super-lig/52#id:77805",
	# Netherlands league
	"eredivisie": "https://www.sofascore.com/tournament/football/netherlands/eredivisie/37#id:77012",
	# Saudi Arabia league
	"saudiarabia": "https://www.sofascore.com/tournament/football/saudi-arabia/saudi-pro-league/955#id:80443",
	# Asia Champions league Elite
	"afcchampions": "https://www.sofascore.com/tournament/football/asia/afc-champions-league/463#id:77010",
	# Asia Champions league two
	"afcchampionstwo": "https://www.sofascore.com/tournament/football/asia/afc-cup/668#id:77009",
	# euroleague basketball
	"basketball": "https://www.sofascore.com/tournament/basketball/international/euroleague/138#id:78545",	
	# nba basketball
	"nba": "https://www.sofascore.com/tournament/basketball/usa/nba/132#id:80229",
	# hockey
	"hockey": "https://www.sofascore.com/tournament/ice-hockey/usa/nhl/234#id:78476",
	# american football
	"nfl": "https://www.sofascore.com/tournament/american-football/usa/nfl/9464#id:75522",
	# World Cup
	"worldcup": "https://www.sofascore.com/football/tournament/world/world-championship/16#id:58210",
}

# Use thess url to download missing log of team (Extra code)
log_urls = {
	# Champions league
	"championsleague": "https://www.worldfootball.net/competition/champions-league/",
	# Europa league
	"europaleague": "https://www.worldfootball.net/competition/europa-league/",
	# Conference league
	"ConferenceLeague": "https://www.worldfootball.net/competition/conference-league/",
	# England league
	"premierleague": "https://www.worldfootball.net/competition/eng-premier-league/",
	# champion ship league
	"championship": "https://www.worldfootball.net/competition/eng-championship/",
	# Italy league
	"seriea": "https://www.worldfootball.net/competition/ita-serie-a/",
	# France league
	"ligue1": "https://www.worldfootball.net/competition/fra-ligue-1/",
	# Spain league 1 + 2
	"laliga": "https://www.worldfootball.net/competition/esp-primera-division/",
	"laliga2": "https://www.worldfootball.net/competition/esp-segunda-division/",
	# Germany league 1 + 2
	"bundesliga": "https://www.worldfootball.net/competition/bundesliga/",
	"bundesliga2": "https://www.worldfootball.net/competition/co3/germany-2-bundesliga/",
	# Portugal league
	"liganos": "https://www.worldfootball.net/competition/por-primeira-liga/",
	# Belgium league
	"belgianpro": "https://www.worldfootball.net/competition/bel-pro-league/",
	# Turkey league
	"superLig": "https://www.worldfootball.net/competition/tur-sueperlig/",
	# Netherlands league
	"eredivisie": "https://www.worldfootball.net/competition/ned-eredivisie/",
	# Saudi Arabia league
	"saudiarabia": "https://www.worldfootball.net/competition/ksa-saudi-pro-league/",
	# Asia Champions league Elite
	"afcchampions": "https://www.worldfootball.net/competition/afc-champions-league-elite/",
	# Asia Champions league two
	"afcchampionstwo": "https://www.worldfootball.net/competition/afc-champions-league-two/",
	# World Cup
	"worldcup": "https://www.worldfootball.net/competition/co139/fifa-world-cup/",
}

SPORTS = {
	"basketball", "nba", "hockey", "nfl"
}
FOOTBALL = {
	"championsleague", "europaleague", "ConferenceLeague", "premierleague",
	"laliga", "laliga2", "championship", "seriea", "ligue1", "eredivisie", "saudiarabia",
	"bundesliga", "bundesliga2", "belgianpro", "superLig", "liganos", "afcchampions", "afcchampionstwo", "worldcup"
}

def getSTBModel():
	if exists("/proc/stb/info/model"):
		with open("/proc/stb/info/model", "r") as f:
			return f.read().strip().lower()
	return ""

# Place this function at the top level of your script (outside the StandingsScreen class)
def sanitize_team_name(team):
	"""Replaces problematic characters (non-ASCII, spaces, etc.) for use in permanent filenames."""
	# 1. Standard Replacements (spaces, slashes, quotes)
	name = team.replace(" ", "_").replace("/", "_").replace("'", "")
	
	# 2. Universal Character Replacements for ASCII safety
	name = name.replace("ü", "ue").replace("ä", "ae").replace("ö", "oe").replace("ß", "ss") 
	name = name.replace("å", "aa").replace("æ", "ae").replace("ø", "oe") 
	name = name.replace("ç", "c").replace("ş", "s").replace("ğ", "g") 
	name = name.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u") 
	return name


# The CRITICAL class for TLS SNI support
class WebClientContextFactory(ClientContextFactory):
	def __init__(self, url=None):
		domain = compat_urlparse(url).netloc
		self.hostname = domain.split(':')[0] if ':' in domain else domain

	def getContext(self, hostname=None, port=None):
		ctx = ClientContextFactory.getContext(self)
		if self.hostname and ClientTLSOptions is not None:
			try:
				ClientTLSOptions(self.hostname, ctx)
			except Exception:
				pass
		return ctx


class FootOnSat(Screen):
	def __init__(self, session, link, *args):
		#logdata("FootOnSat", "Plugin initialization started.")
		self.session = session
		Screen.__init__(self, session)
		self.link = link
		if self.link == "yesterday":
			y_date = date.today() - timedelta(days=1)
			day_name = y_date.strftime('%A')
			self.MENUTEXT = "{0} - {1} - {2}".format(title114, day_name, y_date.strftime('%d-%m-%Y'))
		elif self.link in ["live", "end"]:
			t_date = date.today()
			day_name = t_date.strftime('%A')
			self.MENUTEXT = "{0} - {1} - {2}".format(title115, day_name, t_date.strftime('%d-%m-%Y'))
		elif self.link == "tomorrow":
			tm_date = date.today() + timedelta(days=1)
			day_name = tm_date.strftime('%A')
			self.MENUTEXT = "{0} - {1} - {2}".format(title296, day_name, tm_date.strftime('%d-%m-%Y'))
		elif self.link == "favorite":
			self.MENUTEXT = "{0}".format(title284)
		elif self.link not in json_urls:
			self.MENUTEXT = _("%s") % title116
		else:
			self.MENUTEXT = ""
		self.skin = SKIN_interface
		self["setupActions"] = ActionMap(["FootOnsatActions", "ColorActions"],
		{
			"menu": self.menu,
			"ok": self.ok,
			"down": self.listDOWN,
			"up": self.listUP,
			"left": self.left,
			"right": self.right,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"cancel": self.exit,
			"Forward": self.forward,
			"Backward": self.backward,
		}, -1)
		self["counter"] = Label()
		self["channel"] = Label()
		self["sat"] = Label()
		self["freq"] = Label()
		self["enc"] = Label()
		self["menu"] = Label()
		self["menu2"] = Label()
		self["key_red"] = Button(_("%s") % title117)
		self["key_yellow"] = Button(_("%s") % title118)
		self["key_blue"] = Button(_("%s") % title119)
		self["key_green"] = Button(_("%s") % title120)
		self["key_red"].hide()
		self["key_yellow"].hide()
		self["key_blue"].hide()
		self["key_green"].hide()
		self["list1"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self["list2"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.selectedList = self["list1"]
		self.canScan = False
		self.execing = False
		self.is_closed = False
		self.fetch_timestamp = 0
		self.channelData = []
		self.matches = []
		# Set items per page based on resolution (5 for QHD/2560, 4 for others)
		self.items_per_page = 5 if isUHD() else 4
		self.create_table()
		self.callAPI()

	def onWindowShow(self):
		self["list1"].onSelectionChanged.append(self.getChannels)
		self.enablelist1()
		self.disablelist2()
		self.iniMenu()

	def iniMenu(self):
		LIVECOLORE = int(config.plugins.FootOnSat.livecolor.value, 16)
		if len(self.matches) > 0:
			# This code only for test 
			#self.matches[0][5] = "6"
			#self.matches[0][6] = "8"
			#self.matches[0][7] = "70 min"
			res = []
			gList = []
			self["list1"].l.setItemHeight(175)
			sel = self["list1"].getSelectionIndex()
			if sel >= 0 and sel < len(self.matches):
				match = self.matches[sel][0] 
				if self.checkIfexist(match):
					self["menu"].setText(_("%s") % title121)
					if parseColor and self["menu"].instance:
						self["menu"].instance.setForegroundColor(parseColor("#ff0000"))
					if PY3:
						key = re.sub(r'\s+', '', match.replace(u'\xa0', u''))
					else:
						key = re.sub(r'\s+', '', match.decode('utf-8').replace(u'\xa0', u''))
					if not PY3:
						key = key.decode('utf-8') if isinstance(key, str) else key
					try:
						with connect(join(PLUGINPATH, "db/footonsat.db")) as conn: # <-- FIX: Use 'with' statement for guaranteed closing
							c = conn.cursor()
							c.execute("SELECT ref FROM zap_channels WHERE match = ?", (key,))
							z = c.fetchone()
						if z:
							service_ref_string = z[0]
							if debug_ZAP: logdata("iniMenu ZAP_DEBUG", "Raw zap ref from DB: '%s' (type: %s)" % (service_ref_string, type(service_ref_string)))
							if not PY3 and isinstance(service_ref_string, unicode):
								service_ref_string = service_ref_string.encode('utf-8', 'ignore')
							service_ref = eServiceReference(service_ref_string)
							info = eServiceCenter.getInstance().info(service_ref)
							channel_name = info.getName(service_ref) if info else ""
							if debug_ZAP: logdata("iniMenu ZAP_DEBUG", "Fetched channel name: '%s'" % channel_name)
							if channel_name:
								self["menu2"].setText("%s >> %s" % (title275, channel_name))
								if parseColor and self["menu2"].instance:
									self["menu2"].instance.setForegroundColor(parseColor("#ff0000"))
							else:
								self["menu2"].setText("")
						else:
							if debug_ZAP: logdata("iniMenu ZAP_DEBUG", "No zap ref found for match → '%s'" % key)
							self["menu2"].setText("")
					except Exception as e:
						if debug_ZAP: logdata("iniMenu ZAP_DEBUG", "Error fetching zap ref: %s" % str(e))
						self["menu2"].setText("")
				else:
					# Force update based on current link
					if self.link == "yesterday":
						y_date = date.today() - timedelta(days=1)
						display_text = "{0} - {1} - {2}".format(title114, y_date.strftime('%A'), y_date.strftime('%d-%m-%Y'))
					elif self.link in ["live", "end"]:
						t_date = date.today()
						display_text = "{0} - {1} - {2}".format(title115, t_date.strftime('%A'), t_date.strftime('%d-%m-%Y'))
					elif self.link == "tomorrow":
						tm_date = date.today() + timedelta(days=1)
						display_text = "{0} - {1} - {2}".format(title296, tm_date.strftime('%A'), tm_date.strftime('%d-%m-%Y'))
					elif self.link == "favorite":
						display_text = "{0}".format(title284)
					else:
						display_text = self.MENUTEXT

					self["menu"].setText(display_text)
					if parseColor and self["menu"].instance:
						m_color = "#0000ff00" if self.link == "yesterday" else "#00ffffff"
						self["menu"].instance.setForegroundColor(parseColor(m_color))
					self["menu2"].setText("")
			else:
				# Same logic for the second branch to ensure sync
				if self.link == "yesterday":
					y_date = date.today() - timedelta(days=1)
					display_text = "{0} - {1} - {2}".format(title114, y_date.strftime('%A'), y_date.strftime('%d-%m-%Y'))
				elif self.link in ["live", "end"]:
					t_date = date.today()
					display_text = "{0} - {1} - {2}".format(title115, t_date.strftime('%A'), t_date.strftime('%d-%m-%Y'))
				elif self.link == "tomorrow":
					tm_date = date.today() + timedelta(days=1)
					display_text = "{0} - {1} - {2}".format(title296, tm_date.strftime('%A'), tm_date.strftime('%d-%m-%Y'))
				elif self.link == "favorite":
						display_text = "{0}".format(title284)
				else:
					display_text = self.MENUTEXT

				self["menu"].setText(display_text)
				if parseColor and self["menu"].instance:
					m_color = "#0000ff00" if self.link == "yesterday" else "#00ffffff"
					self["menu"].instance.setForegroundColor(parseColor(m_color))
				self["menu2"].setText("")

			if isUHD():
				self["list1"].l.setFont(0, gFont('Regular', 36))
			else:
				self["list1"].l.setFont(0, gFont('Regular', 28))
			for i in range(0, len(self.matches)):
				match = self.matches[i][0]
				match_date = self.matches[i][1]
				compet = self.matches[i][2]
				team1 = self.matches[i][3]
				team2 = self.matches[i][4]
				parts = re.split(r'\s+v[s]?\s+', match, 1, flags=re.IGNORECASE)
				if len(parts) < 2:
					parts = [match, match]
				log1 = parts[0].strip()
				log2 = parts[1].strip()
				team1_score = self.matches[i][5]  # Team1 score
				team2_score = self.matches[i][6]  # Team2 score
				match_status = self.matches[i][7]  # Match status (e.g., '70', 'HT', 'FT')

				# =======================================================
				# *** NEW LOGIC START: Format the Status/Time ***
				# =======================================================
				display_status = str(match_status).strip()
				
				# 1. Remove the single quote and plus sign for cleaning purposes
				clean_status = display_status.replace("'", "").replace("+", "").strip()

				# 2. Map known status abbreviations to full text and check for running time
				# NOTE: Assuming clean_status is the uppercased status from the scraper (e.g., 'FINISHED', 'HALFTIME', '90')
				# NOTE: Assuming display_status is the original status (e.g., 'Half Time', '90+', 'FINISHED')				
				STATUS_DISPLAY = {
					'CANCELED': (title124, title122),
					'FINISHED': (title125, title122),
					'FT':       (title126, title122),
					'AET':      (title127, title122),
					'PEN':      (title128, title122),
					'HALFTIME': (title129, title123),
					'DELAYED':  (title130, title123),
					'DELAY':    (title130, title123),
				}
				if clean_status in STATUS_DISPLAY:
					status_text, prefix_key = STATUS_DISPLAY[clean_status]
					display_prefix = "%s : " % prefix_key
				elif clean_status.isdigit() or re.search(r'^\d+[\'+]*\+?\d*$', clean_status):
					status_text = "%s %s" % (display_status, title131)
					display_prefix = "%s : " % title123
				else:
					status_text = display_status
					display_prefix = "%s : " % title123
				# =======================================================
				# *** NEW LOGIC END ***
				# =======================================================
				flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team1))
				flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team2))
				teamlog1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/{}.png".format(log1))
				teamlog2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/{}.png".format(log2))
				basketdefault = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/baskedefault.png")
				footdefault = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/footdefault.png")
				hockeydefault = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/hockeydefault.png")
				nfldefault = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/nfldefault.png")
				banner = FootOnSat.setCompet(str(compet).lower())
				match_date = self.getTime(match_date)
				if not fileExists(flagTeam1):
					flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
				if not fileExists(flagTeam2):
					flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
				if not fileExists(teamlog1):
					if self.link in ("basketball", "nba"):
						teamlog1 = basketdefault
					elif self.link in ("hockey"):
						teamlog1 = hockeydefault
					elif self.link in ("nfl"):
						teamlog1 = nfldefault
					else:
						teamlog1 = footdefault
				if not fileExists(teamlog2):
					if self.link in ("basketball", "nba"):
						teamlog2 = basketdefault
					elif self.link in ("hockey"):
						teamlog2 = hockeydefault
					elif self.link in ("nfl"):
						teamlog2 = nfldefault
					else:
						teamlog2 = footdefault
				notif_status = self.checkIfexist(match)
				if notif_status == 2:
					notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_on2.png")
				elif notif_status == 1:
					notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_on.png")
				else:
					notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_off.png")
				# Initialize list entry
				res.append(MultiContentEntryText())
				# Team 1 flag/logteam
				if self.link in (SPORTS | FOOTBALL):
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(70, 5), size=(160, 160), png=loadPNG(teamlog1)))
					if config.plugins.FootOnSat.enableflag.value:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(212, 70), size=(40, 30), png=loadPNG(flagTeam1)))
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(420, 74), size=(40, 30), png=loadPNG(flagTeam1)))
				# Score team 1
				if self.link not in SPORTS:
					if isUHD():
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(1020, 120), size=(50, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(500, 69), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=LIVECOLORE))
					else:
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(700, 120), size=(50, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(482, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=LIVECOLORE))
				# Place a checkmark (-) between the results in the section FOOTBALL
				if (team1_score != "" or match_status != "") and self.link in FOOTBALL:
					if isUHD():
						res.append(MultiContentEntryText(pos=(1050, 120), size=(50, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str("-"), color=LIVECOLORE))
					else:
						res.append(MultiContentEntryText(pos=(750, 120), size=(50, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str("-"), color=LIVECOLORE))
				# Team 2 flag/logteam
				if isUHD():
					if self.link in (SPORTS | FOOTBALL):
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1440, 5), size=(160, 160), png=loadPNG(teamlog2)))
						if config.plugins.FootOnSat.enableflag.value:
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(1420, 70), size=(40, 30), png=loadPNG(flagTeam2)))
					else:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1550, 74), size=(40, 30), png=loadPNG(flagTeam2)))
				else:
					if self.link in (SPORTS | FOOTBALL):
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1030, 10), size=(160, 160), png=loadPNG(teamlog2)))
						if config.plugins.FootOnSat.enableflag.value:
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(1012, 70), size=(40, 30), png=loadPNG(flagTeam2)))
					else:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1142, 70), size=(40, 30), png=loadPNG(flagTeam2)))
				# Score team 2
				if self.link not in SPORTS:
					if isUHD():
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(1110, 120), size=(50, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(1490, 69), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=LIVECOLORE))
					else:
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(792, 120), size=(50, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(1092, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=LIVECOLORE))
				# Competition banner
				if self.link not in (SPORTS | FOOTBALL):
					try:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(65, 6), size=(320, 163), png=loadPNG(banner), flags=BT_SCALE))
					except TypeError:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(65, 6), size=(320, 163), png=loadPNG(banner)))
				# Notification icon
				if self.link not in ["live", "end", "yesterday"]:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(-20, 63), size=(70, 50), png=loadPNG(notif)))
				# Match name
				if isUHD():
					if self.link in (SPORTS | FOOTBALL):
						res.append(MultiContentEntryText(pos=(332, 69), size=(1000, 40), font=0, flags=RT_HALIGN_LEFT | RT_HALIGN_CENTER, text=str(match)))
					else:
						res.append(MultiContentEntryText(pos=(550, 69), size=(900, 40), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(match)))
				else:
					if self.link in (SPORTS | FOOTBALL):
						res.append(MultiContentEntryText(pos=(310, 66), size=(660, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(match)))
					else:
						res.append(MultiContentEntryText(pos=(500, 66), size=(570, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(match)))
				# status_text + match_status
				if (team1_score != "" or match_status != "") and self.link not in SPORTS:
					# If score or status exists, display the dynamic status/time (e.g., "Live: 70 min" or "Status : FT")
					if isUHD():
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(430, 120), size=(400, 48), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(1000, 48), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
					else:
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(320, 120), size=(240, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
				else:
					# Otherwise, display the scheduled Kick-off time
					if self.link in ["end", "yesterday"]:
						KICKOFF = "%s" % title132
					else:
						KICKOFF = "%s : %s" % (title133, match_date)
					if isUHD():
						if self.link in (SPORTS | FOOTBALL):
							res.append(MultiContentEntryText(pos=(430, 120), size=(1000, 48), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(KICKOFF)))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(1000, 48), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(KICKOFF)))
					else:
						if self.link in (SPORTS | FOOTBALL):
							res.append(MultiContentEntryText(pos=(320, 120), size=(500, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(KICKOFF)))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(KICKOFF)))
				# Competition name
				if isUHD():
					if self.link in (SPORTS | FOOTBALL):
						res.append(MultiContentEntryText(pos=(430, 15), size=(1000, 40), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
					else:
						res.append(MultiContentEntryText(pos=(420, 15), size=(1000, 40), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
				else:
					if self.link in (SPORTS | FOOTBALL):
						res.append(MultiContentEntryText(pos=(320, 15), size=(650, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
					else:
						res.append(MultiContentEntryText(pos=(420, 15), size=(785, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
				gList.append(res)
				res = []
			self["list1"].setList(gList)
			if self.link in ["today", "tomorrow"]:
				self['key_red'].show()
				self['key_yellow'].show()
				self['key_green'].hide()
				self['key_blue'].hide()
			elif self.link == "favorite":
				self['key_red'].show()
				self['key_red'].setText(_("%s") % title285)
				self['key_yellow'].show()
				self['key_yellow'].setText(_("%s") % title286)
				self['key_green'].hide()
				self['key_blue'].hide()
			elif self.link in ["end", "yesterday"]:
				if getattr(self, 'is_yesterday', False):
					self['key_red'].show()
					self['key_red'].setText(_("%s") % title134)
					self['key_green'].hide()
				else:
					self['key_green'].show()
					self['key_green'].setText(_("%s") % title114)
			elif self.link in json_urls:
				self['key_red'].hide()
				self['key_yellow'].hide()
				self['key_green'].show()
				self['key_green'].setText(_("%s") % title120)
			else:
				self['key_red'].hide()
				self['key_yellow'].hide()
				self['key_green'].hide()
			self.updateCounter()
			self.getChannels()  # Update channel for selected match
		else:
			# If no data is found, display message in the list instead of a MessageBox
			gList = []
			if self.link == "live":
				no_schedules_text = _("%s") % title136
			elif self.link == "end":
				no_schedules_text = _("%s") % title137
			elif self.link == "yesterday":
				no_schedules_text = _("%s") % title138
			elif self.link == "favorite":
				no_schedules_text = _("%s") % title292
			else:
				no_schedules_text = _("%s") % title139
			# Set font and height (mirroring the 'if' block setup)
			self["list1"].l.setItemHeight(175)
			if isUHD():
				self["list1"].l.setFont(0, gFont('Regular', 36))
			else:
				self["list1"].l.setFont(0, gFont('Regular', 28))
			# Create the single list entry with centered text
			res = []
			res.append(MultiContentEntryText()) # Starts the list item
			# Text centered vertically (y=70 is roughly the center of 175 height item) and horizontally
			res.append(MultiContentEntryText(
				pos=(0, 70), 
				size=(850 if isUHD() else 660, 48 if isUHD() else 36),
				font=0, 
				flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, 
				text=no_schedules_text
			))
			gList.append(res)
			# Set the list
			self["list1"].setList(gList)
			# Clear all auxiliary information and hide buttons
			if self.link in ["today", "tomorrow"]:
				self['key_red'].show()
				self['key_red'].setText(_("%s") % title117)
				self['key_yellow'].show()
				self['key_yellow'].setText(_("%s") % title118)
				self['key_green'].hide()
				self['key_blue'].hide()
			elif self.link == "live":
				self['key_red'].hide()
				self['key_yellow'].hide()
				self['key_blue'].hide()
				self['key_green'].hide()
			elif self.link == "favorite":
				self['key_red'].show()
				self['key_red'].setText(_("%s") % title285)
				self['key_yellow'].show()
				self['key_yellow'].setText(_("%s") % title286)
				self['key_green'].hide()
				self['key_blue'].hide()
			elif self.link in ["end", "yesterday"]:
				if getattr(self, "is_yesterday", False):
					self['key_green'].hide()
				else:
					self['key_green'].show()
					self['key_green'].setText(title114)
			elif self.link in json_urls:
				self['key_green'].show()
				self['key_green'].setText(_("%s") % title135)
			else:
				self['key_green'].hide()
			self["counter"].setText("0/0")
			self["channel"].setText("")
			self["sat"].setText("")
			self["freq"].setText("")
			self["enc"].setText("")
			self.getChannels() # This will ensure list2 is also cleared
			#self.session.openWithCallback(self.exit, MessageBox, _('No schedules in this section at this time'), MessageBox.TYPE_INFO, timeout=10)

	def enablelist1(self):
		instance = self["list1"].instance
		instance.setSelectionEnable(1)

	def enablelist2(self):
		instance = self["list2"].instance
		instance.setSelectionEnable(1)

	def disablelist1(self):
		instance = self["list1"].instance
		instance.setSelectionEnable(0)

	def disablelist2(self):
		instance = self["list2"].instance
		instance.setSelectionEnable(0)

	def forward(self):
		if len(self.matches) > 0:
			current_index = self["list1"].getSelectionIndex()
			total_pages = int(math.ceil(float(len(self.matches)) / self.items_per_page))
			current_page = int(math.ceil((current_index + 1) / float(self.items_per_page)))
			if current_page < total_pages:
				new_index = min(current_page * self.items_per_page, len(self.matches) - 1)
				self["list1"].instance.moveSelectionTo(new_index)
				self.updateCounter()
				self.resetChannelinfo()

	def backward(self):
		if len(self.matches) > 0:
			current_index = self["list1"].getSelectionIndex()
			current_page = int(math.ceil((current_index + 1) / float(self.items_per_page)))
			if current_page > 1:
				new_index = max((current_page - 2) * self.items_per_page, 0)
				self["list1"].instance.moveSelectionTo(new_index)
				self.updateCounter()
				self.resetChannelinfo()

	def updateCounter(self):
		if len(self.matches) > 0:
			current_index = self["list1"].getSelectionIndex()
			total_pages = int(math.ceil(float(len(self.matches)) / self.items_per_page))
			current_page = int(math.ceil((current_index) // self.items_per_page)) +1
			self["counter"].setText("{}/{}".format(current_page, total_pages))

	def left(self):
		if self.selectedList == self["list2"]:
			self.selectedList = self["list1"]
			self.enablelist1()
			self.disablelist2()
			self.resetChannelinfo()
		#elif self.selectedList == self["list1"]:
		#	self.exit()

	def right(self):
		if self.selectedList.getCurrent():
			self.selectedList = self["list2"]
			self.enablelist2()
			self.updateChannelData()

	def updateMenuWidgets(self):
		if self.selectedList == self["list1"]:
			self.disablelist2()
			self.updateCounter()
			self.resetChannelinfo()
			sel = self["list1"].getSelectionIndex()
			if sel >= 0 and sel < len(self.matches):
				match = self.matches[sel][0] 
				if self.checkIfexist(match):
					self["menu"].setText(_("%s") % title121)
					if parseColor and self["menu"].instance:
						self["menu"].instance.setForegroundColor(parseColor("#ff0000"))
					if PY3:
						key = re.sub(r'\s+', '', match.replace(u'\xa0', u''))
					else:
						key = re.sub(r'\s+', '', match.decode('utf-8').replace(u'\xa0', u''))
					if not PY3:
						key = key.decode('utf-8') if isinstance(key, str) else key
					try:
						with connect(join(PLUGINPATH, "db/footonsat.db")) as conn: # <-- FIX: Use 'with' statement for guaranteed closing
							c = conn.cursor()
							c.execute("SELECT ref FROM zap_channels WHERE match = ?", (key,))
							z = c.fetchone()
						if z:
							service_ref_string = z[0]
							if debug_ZAP: logdata("updateMenuWidgets ZAP_DEBUG", "Raw zap ref from DB: '%s' (type: %s)" % (service_ref_string, type(service_ref_string)))
							if not PY3 and isinstance(service_ref_string, unicode):
								service_ref_string = service_ref_string.encode('utf-8', 'ignore')
							service_ref = eServiceReference(service_ref_string)
							info = eServiceCenter.getInstance().info(service_ref)
							channel_name = info.getName(service_ref) if info else ""
							if debug_ZAP: logdata("updateMenuWidgets ZAP_DEBUG", "Fetched channel name: '%s'" % channel_name)
							if channel_name:
								self["menu2"].setText("%s >> %s" % (title275, channel_name))
								if parseColor and self["menu2"].instance:
									self["menu2"].instance.setForegroundColor(parseColor("#ff0000"))
							else:
								self["menu2"].setText("")
						else:
							if debug_ZAP: logdata("updateMenuWidgets ZAP_DEBUG", "No zap ref found for match → '%s'" % key)
							self["menu2"].setText("")
					except Exception as e:
						if debug_ZAP: logdata("updateMenuWidgets ZAP_DEBUG", "Error fetching zap ref: %s" % str(e))
						self["menu2"].setText("")
				else:
					if self.link == "yesterday":
						y_date = date.today() - timedelta(days=1)
						display_text = "{0} - {1} - {2}".format(title114, y_date.strftime('%A'), y_date.strftime('%d-%m-%Y'))
					elif self.link in ["live", "end"]:
						t_date = date.today()
						display_text = "{0} - {1} - {2}".format(title115, t_date.strftime('%A'), t_date.strftime('%d-%m-%Y'))
					elif self.link == "tomorrow":
						tm_date = date.today() + timedelta(days=1)
						display_text = "{0} - {1} - {2}".format(title296, tm_date.strftime('%A'), tm_date.strftime('%d-%m-%Y'))
					elif self.link == "favorite":
						display_text = "{0}".format(title284)
					else:
						display_text = self.MENUTEXT
					self["menu"].setText(display_text)
					if parseColor and self["menu"].instance:
						m_color = "#0000ff00" if self.link == "yesterday" else "#00ffffff"
						self["menu"].instance.setForegroundColor(parseColor(m_color))
					self["menu2"].setText("")
			else:
				if self.link == "yesterday":
					y_date = date.today() - timedelta(days=1)
					display_text = "{0} - {1} - {2}".format(title114, y_date.strftime('%A'), y_date.strftime('%d-%m-%Y'))
				elif self.link in ["live", "end"]:
					t_date = date.today()
					display_text = "{0} - {1} - {2}".format(title115, t_date.strftime('%A'), t_date.strftime('%d-%m-%Y'))
				elif self.link == "tomorrow":
					tm_date = date.today() + timedelta(days=1)
					display_text = "{0} - {1} - {2}".format(title296, tm_date.strftime('%A'), tm_date.strftime('%d-%m-%Y'))
				elif self.link == "favorite":
						display_text = "{0}".format(title284)
				else:
					display_text = self.MENUTEXT
				self["menu"].setText(display_text)
				if parseColor and self["menu"].instance:
					m_color = "#0000ff00" if self.link == "yesterday" else "#00ffffff"
					self["menu"].instance.setForegroundColor(parseColor(m_color))
				self["menu2"].setText("")

		if self.selectedList == self["list2"]:
			self.updateChannelData()

	def listDOWN(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveDown)
		self.updateMenuWidgets()

	def listUP(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveUp)
		self.updateMenuWidgets()

	def create_table(self):
		try:
			with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
				cur = conn.cursor()
				cur.execute('CREATE TABLE IF NOT EXISTS LIVE_NOTIF (MATCH TEXT primary key , COMPET TEXT , DATE TEXT , TEAM1_FLAG TEXT , TEAM2_FLAG TEXT , FIRST_NOTIF TEXT , FIRST_NOTIF_STATUS TEXT , LIVE_NOTIF_STATUS TEXT,MESSAGE TEXT)')
		except DatabaseError as e:
			# If the file is corrupted, delete it and try again.
			if debug_Notif: logdata("Database", "Corruption detected, re-creating: %s" % str(e))
			if exists(join(PLUGINPATH, "db/footonsat.db")):
				os.remove(join(PLUGINPATH, "db/footonsat.db"))
			with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
				cur = conn.cursor()
				cur.execute('CREATE TABLE IF NOT EXISTS LIVE_NOTIF (MATCH TEXT primary key , COMPET TEXT , DATE TEXT , TEAM1_FLAG TEXT , TEAM2_FLAG TEXT , FIRST_NOTIF TEXT , FIRST_NOTIF_STATUS TEXT , LIVE_NOTIF_STATUS TEXT,MESSAGE TEXT)')
		except Exception as e:
			if debug_Notif: logdata("Database", "Fatal Error: %s" % str(e))
			pass

	def menu(self):
		if self.link not in ["live", "end", "yesterday"]:
			if self.selectedList != self["list1"] or len(self.matches) == 0:
				return

			index = self['list1'].getSelectionIndex()
			match = self.matches[index][0] if PY3 else self.matches[index][0].decode('utf-8')

			if not self.checkIfexist(match):
				self.session.open(MessageBox, title140, MessageBox.TYPE_INFO, timeout=6)
				return

			self.current_selected_match = match
			if debug_ZAP: logdata("ZAPMenu", "Opening channel selection for: %s" % str(match))

			# YOUR ORIGINAL UNIVERSAL CODE — 100% UNCHANGED
			try:
				from Screens.ChannelSelection import ChannelSelectionSimple
				sel_class = ChannelSelectionSimple
			except:
				try:
					from Screens.ChannelSelection import SimpleChannelSelection
					sel_class = SimpleChannelSelection
				except:
					from Screens.ChannelSelection import ChannelSelection
					sel_class = ChannelSelection

			self.session.openWithCallback(self.channelSelected, sel_class,  title141)

	def channelSelected(self, service_ref=None):
		if not service_ref:
			return

		info = eServiceCenter.getInstance().info(service_ref)
		channel_name = info.getName(service_ref) if info else "Unknown"
		ref_string = service_ref.toString()

		index = self['list1'].getSelectionIndex()
		exact_match = self.matches[index][0]
		
		# 1. Handle non-breaking space (Py2/3 safe)
		try:
			normalized_match = exact_match.replace(u'\xa0', u' ')
		except:
			normalized_match = exact_match.replace('\xa0', ' ')
			
		# 2. Collapse all sequences of whitespace to a single space, strip edges, then remove ALL spaces
		normalized_match = re.sub(r'\s+', ' ', normalized_match).strip()
		normalized_match = normalized_match.replace(' ', '') # REMOVE ALL SPACES to match original SQL intent
		# END FIX

		if debug_ZAP: logdata("channelSelected ZAP_DEBUG", "SAVING ZAP REF → '%s' → %s (%s)" % (normalized_match, channel_name, ref_string))

		try:
			with connect(join(PLUGINPATH, "db/footonsat.db")) as conn: # <-- FIX: Use 'with' for transaction safety and guaranteed close
				c = conn.cursor()
				c.execute('CREATE TABLE IF NOT EXISTS zap_channels (match TEXT primary key, ref TEXT)''')
				# Insert using the fully normalized key (which has no spaces)
				c.execute("INSERT OR REPLACE INTO zap_channels (match, ref) VALUES (?, ?)", (normalized_match, ref_string))
				# conn.commit() is implicitly called if the 'with' block exits without error
			if debug_ZAP: logdata("channelSelected ZAP_DEBUG", "ZAP REF SAVED SUCCESSFULLY → %s" % ref_string)
		except Exception as e:
			if debug_ZAP: logdata("channelSelected ZAP_DEBUG", "SAVE ERROR: %s" % str(e))
			pass

		self.iniMenu()

		self.session.open(MessageBox, "%s\n\n" % title142 + "%s: " % title143 + exact_match + "\n" +
			"%s: " % title144 + channel_name + "\n\n" + title145, MessageBox.TYPE_INFO, timeout=10)

	def ok(self):
		if self.selectedList != self["list1"] or len(self.matches) == 0:
			return

		index = self['list1'].getSelectionIndex()
		current_match = self.matches[index]
		if PY3:
			match_date = self.getTime(current_match[1])
		else:
			match_date = self.getTime(current_match[1].decode('utf8'))

		match_time_obj = datetime.strptime(match_date, "%H:%M - %Y-%m-%d")
		match_in_past = match_time_obj < datetime.now()
		is_live_or_end = (self.link in ["live", "end", "yesterday"]) or (match_in_past)
		if is_live_or_end:
			if len(current_match) > 8 and current_match[8]:
				event_id = current_match[8]
				match_str = current_match[0]
				if debug_MatchDetails: logdata("ok", "Opening Details for: %s (ID: %s)" % (str(match_str), str(event_id)))
				parts = re.split(r'\s+v[s]?\s+', match_str, 1, flags=re.IGNORECASE)
				home_full = parts[0].strip() if len(parts) > 1 else "Home"
				away_full = parts[1].strip() if len(parts) > 1 else "Away"
				self.session.open(MatchDetailsScreen, 
					event_id, 
					current_match[2], 
					home_full, 
					away_full, 
					current_match[3], 
					current_match[4])
				return
			else:
				self.session.open(MessageBox,  title146, MessageBox.TYPE_INFO, timeout=3)
				return

		if PY3:
			match = self.matches[index][0]
			match_date = self.getTime(self.matches[index][1])
			compet = self.matches[index][2]
			flag1 = self.matches[index][3]
			flag2 = self.matches[index][4]
		else:
			match = self.matches[index][0].decode('utf8')
			match_date = self.getTime(self.matches[index][1].decode('utf8'))
			compet = self.matches[index][2].decode('utf8')
			flag1 = self.matches[index][3].decode('utf8')
			flag2 = self.matches[index][4].decode('utf8')

		if datetime.strptime(match_date, "%H:%M - %Y-%m-%d") > datetime.now():
			with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
				cur = conn.cursor()
				cur.execute("CREATE TABLE IF NOT EXISTS zap_channels (match TEXT primary key, ref TEXT)")
				if self.checkIfexist(match):
					if debug_Notif: logdata("Ok Database", "Removing match: %s" % str(match))
					clean_match_key = re.sub(r'\s+', '', match.replace(u'\xa0', u''))
					cur.execute("DELETE FROM LIVE_NOTIF WHERE MATCH = ?", (match,))
					cur.execute("DELETE FROM zap_channels WHERE match = ?", (clean_match_key,))
				else:
					if debug_Notif: logdata("Ok Database", "Adding match to notifications: %s" % str(match))
					first_notif, message = self.setFirstNotifTime(match_date)
					cur.execute("INSERT INTO LIVE_NOTIF(MATCH,COMPET,DATE,TEAM1_FLAG,TEAM2_FLAG,FIRST_NOTIF,FIRST_NOTIF_STATUS,LIVE_NOTIF_STATUS,MESSAGE) values (?,?,?,?,?,?,?,?,?)", (
						match, compet, match_date, flag1, flag2, first_notif, "Waiting", "Waiting", message,))
		self.iniMenu()


	def setFirstNotifTime(self, dt):
		dt_obj = datetime.strptime(dt, "%H:%M - %Y-%m-%d")
		now = datetime.now()
		# 1. 30-minute reminder
		notif_30min_time = dt_obj - timedelta(minutes=30)
		if notif_30min_time > now:
			first_notif_str = notif_30min_time.strftime("%H:%M - %Y-%m-%d")
			message = title147 if PY3 else title147.decode('utf-8')
			return [first_notif_str, message]
		# 2. 15-minute reminder
		notif_15min_time = dt_obj - timedelta(minutes=15)
		if notif_15min_time > now:
			first_notif_str = notif_15min_time.strftime("%H:%M - %Y-%m-%d")
			message = title148 if PY3 else title148.decode('utf-8')
			return [first_notif_str, message]
		# 3. Match Start time reminder
		if dt_obj > now:
			first_notif_str = dt_obj.strftime("%H:%M - %Y-%m-%d")
			message = title149 if PY3 else title149.decode('utf-8')
			return [first_notif_str, message]
		# 4. Fallback: Match already started or passed (should be immediately deleted by cleanup)
		first_notif_str = dt_obj.strftime("%H:%M - %Y-%m-%d")
		message = title150 if PY3 else title150.decode('utf-8')
		return [first_notif_str, message]

	def sameDate(self, dt):
		with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
			cur = conn.cursor()
			cur.execute("SELECT DATE FROM LIVE_NOTIF WHERE DATE = ?", (dt,))
			data = cur.fetchone()
			if data is None:
				return False
			else:
				return True

	def checkIfexist(self, match):
		if PY3:
			match_key = match
		else:
			match_key = match.decode('utf-8')
		
		# Connection 1: Using 'with' (Good)
		with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
			cur = conn.cursor()
			cur.execute("SELECT MATCH FROM LIVE_NOTIF WHERE MATCH = ?", (match_key,))
			data = cur.fetchone()
			if data is None:
				return 0
		
		key = re.sub(r'\s+', '', match_key)
		if not PY3:
			key = key.decode('utf-8') if isinstance(key, str) else key
		try:
			# Connection 2: FIX! Use 'with' here to ensure the connection is closed
			with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
				c = conn.cursor()
				c.execute("SELECT ref FROM zap_channels WHERE match = ?", (key,))
				z = c.fetchone()
			# 'conn.close()' is now called automatically when the 'with' block exits
			
			if z:
				return 2
			else:
				return 1
		except Exception as e: # It's good practice to catch a specific exception or log the error
			return 1

	def getTime(self, match_date):
		timezone = strftime("%z")
		if timezone.startswith('+') and timezone != '+0000':
			dif = int(timezone.replace('+', '').replace('00', ''))
			calc = (datetime.strptime(match_date, '%H:%M - %Y-%m-%d') + timedelta(hours=dif)).strftime('%H:%M - %Y-%m-%d')
		elif timezone == '+0000':
			calc = match_date
		else:
			dif = int(timezone.replace('-', '').replace('00', ''))
			calc = (datetime.strptime(match_date, '%H:%M - %Y-%m-%d') - timedelta(hours=dif)).strftime('%H:%M - %Y-%m-%d')
		return calc

	@classmethod
	def setCompet(cls, compet):
		with open('/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/compet/package.json', 'r') as f:
			data = json.load(f)
		for c in data['compet']:
			if c['label'] in compet:
				return resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/compet/FHD/{}.png".format(c['banner']))
		banner = random.choice(['default', 'default1', 'default2', 'default3'])
		return resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/compet/default/FHD/{}.png".format(banner))

	def callAPI(self):
		if self.is_closed:
			if debug_Fetch_Live: logdata("FootOnSat", "SKIP: callAPI blocked. Plugin already closed.")
			return
		url_link = "tomorrow" if self.link == "tomorrow" else ("today" if self.link in ["live", "end", "favorite"] else self.link)
		url = 'https://raw.githubusercontent.com/fairbird/footonsat-api/main/{}.json'.format(url_link)
		sniFactory = WebClientContextFactory(url)
		getPage(str.encode(url), contextFactory=sniFactory).addCallback(self.getData).addErrback(self.error)
		# This code only for test locale json files
#		from twisted.internet import reactor
#		json_file_path = '/media/hdd/today.json'
#		with open(json_file_path, 'r') as f:
#			json_data = f.read()
#		reactor.callLater(0.1, self.getData, json_data)

	def error(self, error=None):
		if error:
			if debug_Fetch_Live: logdata("FootOnSat-Error", "HTTP Error: " + str(error))
			error_msg = _("%s") % title151
			self.session.openWithCallback(self.exit, MessageBox, error_msg, MessageBox.TYPE_ERROR, timeout=10)

	def fetch_live_results(self):
		self.fetch_timestamp = time.time()
		current_ts = self.fetch_timestamp
		if not self.matches:
			self.onWindowShow()
			return
		# Define the fixed time windows
		LIVE_DURATION = timedelta(hours=4) # 4 hours limit for finished matches
		TIME_WINDOW = timedelta(hours=4) # Generous fuzzy matching time tolerance
		
		live_start_time = time.time()
		if debug_Fetch_Live: logdata("fetch_live_results", "fetch_live_results initiated.")

		index = self['list1'].getSelectionIndex()
		current_match = self.matches[index]
		if self.link == "yesterday":
			selected_date = current_match[1].split(' - ')[1]
		else:
			selected_date = date.today().isoformat()
		if debug_Fetch_Live: logdata("fetch_live_results", "Current Link: %s" % self.link)
		if debug_Fetch_Live: logdata("fetch_live_results", "Selected Date: %s" % selected_date)
		url1 = 'https://api.sofascore.com/api/v1/sport/football/scheduled-events/{0}/'.format(selected_date)
		url2 = 'https://api.sofascore.com/api/v1/sport/football/scheduled-events/{0}/inverse'.format(selected_date)

		# === Headers/Agent (Minimal and robust headers) ===
		AGENT = b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
		USER_AGENTS = [
			'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
			'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
			'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
		]
		ua = random.choice(USER_AGENTS)

		headers2 = {
			'User-Agent': ua,
			'Accept': 'application/json, text/plain, */*',
			'Referer': 'https://www.sofascore.com/',
			'Origin': 'https://www.sofascore.com',
			'Cache-Control': 'no-cache',
		}

		# === SMART DYNAMIC FETCH ===
		# On Saturday/Sunday → url2 = 30 MB = DEATH
		# So we check day: if weekend → SKIP url2 completely
		weekday = date.today().weekday()  # 5 = Saturday, 6 = Sunday
		is_weekend = weekday >= 5
		if config.plugins.FootOnSat.extrafetch.value:
			if is_weekend:
				fetch_url2 = self.link in ["live", "end", "yesterday"]
			else:
				fetch_url2 = True
		else:
			fetch_url2 = not is_weekend  # ONLY try url2 on Mon–Fri

		# === Twisted HTTP Request Handling (with Py3 compatibility) ===
		deferred_list = []
		if PY3:
			try:
				sniFactory = WebClientContextFactory(url1)
			except Exception as e:
				if debug_Fetch_Live: logdata("fetch_live_results", "Failed to create WebClientContextFactory: %s" % str(e))
				self.matches = [list(m) for m in self.matches]
				self.iniMenu()
				return

			twisted_live_headers = {
				b'User-Agent': [AGENT],
				b'Connection': [b'close'],
				b'Accept': [b'application/json, text/plain, */*'],
				b'Referer': [b'https://www.sofascore.com/'],
				b'Origin': [b'https://www.sofascore.com'],
				b'Cache-Control': [b'no-cache'],
			}

			# Always fetch url1 (main clean data)
			d1 = getPage(str.encode(url1), contextFactory=sniFactory, timeout=20, headers=twisted_live_headers)
			deferred_list.append(d1)

			# Conditionally fetch url2 (only on safe days)
			d2 = None
			if fetch_url2:
				def safe_url2():
					try:
						# Aggressive anti-block headers
						headers2 = twisted_live_headers.copy()
						headers2[b'User-Agent'] = [b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/129.0 Safari/537.36']
						headers2[b'Accept-Encoding'] = [b'identity']
						return getPage(str.encode(url2), contextFactory=sniFactory, timeout=120, headers=headers2)
					except:
						return defer.succeed(None)
				d2 = safe_url2()
				deferred_list.append(d2)
			else:
				# Weekend: inject None so gatherResults keeps order
				deferred_list.append(defer.succeed(None))

			self.fetch_deferred = defer.gatherResults(deferred_list, consumeErrors=True)
			d = self.fetch_deferred

			def process_results(results):
				if self.is_closed:
					if debug_Fetch_Live: logdata("fetch_live_results", "ABORTED: Background process stopped because plugin is closed.")
					return
				raw1, raw2 = results

				if debug_Fetch_Live:
					# Log url1
					if isinstance(raw1, Failure):
						logdata("fetch_live_results", "DEBUG URL1 FAILED: %s" % raw1.getErrorMessage())
					else:
						logdata("fetch_live_results", "DEBUG URL1 OK (Bytes: %d)" % len(raw1))
					# Log url2
					if not fetch_url2:
						logdata("fetch_live_results", "DEBUG URL2 SKIPPED (weekend protection active)")
					elif raw2 is None:
						logdata("fetch_live_results", "DEBUG URL2 SKIPPED (setup failed)")
					elif isinstance(raw2, Failure):
						logdata("fetch_live_results", "DEBUG URL2 FAILED → SKIPPED SAFELY")
					else:
						logdata("fetch_live_results", "DEBUG URL2 OK (Bytes: %d) → using extra data" % len(raw2))

				# Return only valid data
				valid = []
				if raw1 and not isinstance(raw1, Failure):
					valid.append(raw1)
				if raw2 and not isinstance(raw2, Failure) and fetch_url2:
					valid.append(raw2)

				# Fallback if both fail
				if not valid:
					valid = [b'{"events":[]}']

				return valid

			d.addCallback(process_results)

		else:
			# PY2 version — fixed with Session and Referer
			def _fetch_smart():
				if self.is_closed:
					if debug_Fetch_Live: logdata("fetch_live_results", "ABORTED: Background process stopped because plugin is closed.")
					return
				results = []
				s = requests.Session()
				s.headers.update({
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
					'Referer': 'https://www.sofascore.com/',
					'Accept': 'application/json',
					'Origin': 'https://www.sofascore.com'
				})
				# url1 always
				try:
					s.get('https://www.sofascore.com')
					r = s.get(url1, timeout=20)
					if r.status_code == 403:
						s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
						r = s.get(url1, timeout=20)
					r.raise_for_status()
					results.append(r.content)
					if debug_Fetch_Live: logdata("fetch_live_results", "DEBUG URL1 (Py2) OK (%d KB)" % (len(r.content)//1024))
				except Exception as e:
					if debug_Fetch_Live: logdata("fetch_live_results", "DEBUG URL1 (Py2) FAILED: %s" % str(e))
					results.append(None)

				# url2 only if safe
				if fetch_url2:
					try:
						r2 = s.get(url2, timeout=120)
						r2.raise_for_status()
						results.append(r2.content)
						if debug_Fetch_Live: logdata("fetch_live_results", "DEBUG URL2 (Py2) OK (%d MB) → extra data" % (len(r2.content)//1024//1024))
					except Exception as e:
						if debug_Fetch_Live: logdata("fetch_live_results", "DEBUG URL2 (Py2) FAILED → SKIPPED")
						results.append(None)
				else:
					if debug_Fetch_Live: logdata("fetch_live_results", "DEBUG URL2 (Py2) SKIPPED (weekend mode)")
					results.append(None)

				valid = [r for r in results if r is not None]
				return valid or [b'{"events":[]}']

			self.fetch_deferred = deferToThread(_fetch_smart)
			d = self.fetch_deferred
		
		# === _process_response (Twisted Callback from network fetch) ===
		def _process_response(raw_list): # <--- Argument changed from 'raw' to 'raw_list'
			if self.fetch_timestamp != current_ts: return
			if debug_Fetch_Live: logdata("fetch_live_results", "MATCHES BEFORE: %d" % len(self.matches))
			process_start = time.time()
			all_events = []
			# Decode and JSON Load
			for idx, raw in enumerate(raw_list):
				if self.is_closed: return # KILL JOB IMMEDIATELY
				if raw is None:
					continue
				# Decode and JSON Load
				try:
					data_str = raw.decode('utf-8', errors='ignore')
					data = json.loads(data_str)
					# === DEBUG: Save SofaScore JSON to /tmp (Pretty Print) ===
#					try:
#						sofa_debug_path = "/tmp/sofascore_data_%d.json" % idx
#						events = data.get('events', [])
#						formatted_data_str = json.dumps(events, indent=4, ensure_ascii=False)
#						with codecs.open(sofa_debug_path, "w", encoding="utf-8") as f:
#							f.write(formatted_data_str)
#						logdata("fetch_live_results", "Saved PRETTY-PRINTED SofaScore EVENTS to %s" % sofa_debug_path)
#					except Exception as e:
#						logdata("fetch_live_results", "Failed to save SofaScore JSON: %s" % str(e))
					# === END DEBUG ===
					events = data.get('events', [])
					all_events.extend(events)
				except ValueError as e:
					# Log the actual JSON parsing error
					if debug_Fetch_Live: logdata("fetch_live_results", "JSON parse error (ValueError): %s" % str(e))
					# Log the beginning of the raw data that caused the crash (first 256 characters)
					if debug_Fetch_Live: logdata("fetch_live_results", "Corrupt Data Snippet: %s..." % data_str[:256].replace('\n', ' '))
					continue # Continue to the next response in the list
				except Exception as e:
					# Log any other unexpected decode/general error
					if debug_Fetch_Live: logdata("fetch_live_results", "Decode/General error: %s" % str(e))
					continue # Continue to the next response in the list

			if not all_events:
				self.matches = [list(m) for m in self.matches]
				try:
					self.iniMenu()
				except Exception as e:
					pass
				return

			events = all_events

			# === STEP 1: EVENT BUILDING & STRICT FILTERING (Main thread) ===
			now = datetime.now()
			now_adj = now - timedelta(minutes=3)
			
			live_matches = []
			build_start = time.time()
			for ev in events:
				if self.is_closed:
					if debug_Fetch_Live: logdata("fetch_live_results", "TERMINATED: Loop broken mid-process. System is now safe for Restart.")
					break
				try:
					try:
						home_team = ev.get('homeTeam') or {}
						away_team = ev.get('awayTeam') or {}
						home = compat_str(home_team.get('name', 'Unknown Home'))
						away = compat_str(away_team.get('name', 'Unknown Away'))
						if home == 'Unknown Home' or away == 'Unknown Away':
							continue
					except Exception as e:
						if debug_Fetch_Live: logdata("fetch_live_results", "Team name parse error: %s" % str(e))
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

					# --- Status Logic (Match Time Calculation) ---
					status = ''
					if stype == 'canceled':
						status = 'CANCELED'
					elif stype == 'finished':
						status = 'FINISHED'
					elif stype == 'postponed':
						status = 'POSTPONED'
						h_score = a_score = ''
					elif stype == 'inprogress':
						m = re.search(r'(\d{1,3}[\'+]*\+?\d*)\s*\'', descr)
						if m:
							status = '{0} min'.format(m.group(1))
						elif 'extra time' in descr.lower():
							status = 'AET'
						elif 'penalties' in descr.lower():
							status = 'title154'
						elif descr.lower() in ['half time', 'halftime']:
							status = 'HALFTIME'
						elif 'delayed' in descr.lower():
							status = 'DELAYED'
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
							except:
								status = ''
					elif stype == 'notstarted':
						status = ''
					else:
						status = ''

					# === CRITICAL DATA INTEGRITY FIREWALL (Preserved) ===
					
					# 1. Clear score/status if the match is scheduled to start in the next 10 minutes or later.
					if match_dt > now + timedelta(minutes=10) and stype not in ['inprogress', 'canceled', 'postponed', 'afterextra', 'penaltyshootout']:
						h_score = a_score = ''
						status = ''

					# 2. Ensure 'notstarted' or 'canceled' matches show no score.
					elif stype in ['notstarted', 'canceled']:
						h_score = a_score = ''
						if stype == 'canceled':
							status = '%s' % title124
						else:
							status = ''

					live_matches.append({
						"match_name": match_name,
						"team1": home,
						"team2": away,
						"team1_score": h_score,
						"team2_score": a_score,
						"match_status": status,
						"match_dt": match_dt,
						"raw_descr": descr,
						"id": ev.get('id', '')
					})
				except Exception as e:
					if debug_Fetch_Live: logdata("fetch_live_results", "Error building live_matches for an event: %s" % str(e))
					continue

			# === STEP 2: INSTANT UI DRAW ===
			matches_list = [list(m) for m in self.matches]
			
			try:
				self.iniMenu()
				#logdata("FootOnSat-PERF", "LIVESCORE: Initial UI drawn instantly with schedule data.")
			except Exception as e:
				pass

			def _clean_name(name):
				#logdata("FuzzyDebug", "RAW NAME    : %s" % repr(name))
				if not PY3 and isinstance(name, str):
					name = name.decode('ascii', 'ignore')
				try:
					if PY3:
						name = normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
					else:
						name = normalize('NFKD', name.decode('utf-8')).encode('ascii', 'ignore')
				except:
					pass
				name = compat_str(name).strip().lower()
				name = re.sub(r'[^a-z\s]', ' ', name, flags=re.IGNORECASE) 
				NOISE = r'\b(nk|afc|fc|cf|as|ac|sk|fk|tsv|national|squad|sport|calcio|ploie[șs]ti|ploiești|ploieshti|aif|ifk|goteborg|göteborg|kf|ks|af|seinajoki|peshkopi)\b'
				name = re.sub(NOISE, ' ', name, flags=re.IGNORECASE)
				name = re.sub(r'\s+', ' ', name).strip()
				#logdata("FuzzyDebug", "CLEANED NAME: %s" % repr(name))
				return name

			def _do_fuzzy_matching(matches_list, live_matches, now_adj):
				match_perf_start = time.time()			
				# --- FIX: THRESHOLD ADJUSTMENT for maximum accuracy ---
				THRESHOLD = 0.50 # Lowered from 0.60 to 0.55 to ensure all challenging names match
				TIME_WINDOW = timedelta(hours=4)
				
				# --- Caching for Live Matches ---
				live_clean_cache = {}
				for live in live_matches:
					s_t1 = compat_str(live["team1"]).strip()
					s_t2 = compat_str(live["team2"]).strip()
					if s_t1 not in live_clean_cache:
						live_clean_cache[s_t1] = _clean_name(s_t1)
					if s_t2 not in live_clean_cache:
						live_clean_cache[s_t2] = _clean_name(s_t2)
						
				# === RESTORED SPEED OPTIMIZATION: Pre-calculate schedule clean cache ONCE ===
				schedule_clean_cache = {}
				for match in matches_list:
					if getattr(self, 'is_closed', True): return
					try:
						local_name = compat_str(match[0])
						#teams = re.split(r'\s+vs\s+|\s+-\s+', local_name)
						teams = re.split(r'\s+(?:vs\.|vs|v\.|v|VS|Vs|VS\.)\s+|\s+-\s+', local_name, flags=re.IGNORECASE)
						if len(teams) != 2:
							continue
							
						l_t1 = compat_str(teams[0]).strip()
						l_t2 = compat_str(teams[1]).strip()
						
						if l_t1 not in schedule_clean_cache:
							schedule_clean_cache[l_t1] = _clean_name(l_t1)
						if l_t2 not in schedule_clean_cache:
							schedule_clean_cache[l_t2] = _clean_name(l_t2)
					except:
						continue
				# ===================================================================================

				for match in matches_list:
					if getattr(self, 'is_closed', True): return
					try:
						time_str = compat_str(match[1])
						try:
							local_dt = datetime.strptime(time_str.split(' - ')[1] + ' ' + time_str.split(' - ')[0], "%Y-%m-%d %H:%M")
						except:
							local_dt = now_adj

						local_name = compat_str(match[0])
						#teams = re.split(r'\s+vs\s+|\s+-\s+', local_name)
						teams = re.split(r'\s+(?:vs\.|vs|v\.|v|VS|Vs|VS\.)\s+|\s+-\s+', local_name, flags=re.IGNORECASE)
						if len(teams) != 2:
							match[5] = match[6] = match[7] = ""
							continue

						l_t1 = compat_str(teams[0]).strip()
						l_t2 = compat_str(teams[1]).strip()
						
						# Retrieve pre-calculated clean names
						l_t1_clean = schedule_clean_cache.get(l_t1, "")
						l_t2_clean = schedule_clean_cache.get(l_t2, "")
						
						if not l_t1_clean or not l_t2_clean:
							match[5] = match[6] = match[7] = ""
							continue

						best_sim = 0.0
						best_live = None
						
						# --- Time-based Pre-Filter (Tier 1 Speed) ---
						relevant_live_events = [
							live for live in live_matches 
							if abs(live["match_dt"] - local_dt) <= TIME_WINDOW
						]

						for live in relevant_live_events:
							s_t1 = compat_str(live["team1"]).strip()
							s_t2 = compat_str(live["team2"]).strip()
							
							s_t1_clean = live_clean_cache[s_t1]
							s_t2_clean = live_clean_cache[s_t2]

							# === FIX: Reintroducing a very loose length filter for speed optimization (Tier 2) ===
							len_l1 = len(l_t1_clean)
							len_s1 = len(s_t1_clean)
							len_l2 = len(l_t2_clean)
							len_s2 = len(s_t2_clean)

							# Loosened tolerance to 15 to eliminate only extreme mismatches
							straight_possible = (abs(len_l1 - len_s1) <= 15 and abs(len_l2 - len_s2) <= 15)
							swap_possible = (abs(len_l1 - len_s2) <= 15 and abs(len_l2 - len_s1) <= 15)

							if not (straight_possible or swap_possible):
								continue	

							#if debug_Fetch_Live: logdata("fetch_live_results FuzzyDebug","COMPARE | SCHED: '%s' vs '%s' | LIVE: '%s' vs '%s'" % (
							#	l_t1_clean, l_t2_clean,
							#	s_t1_clean, s_t2_clean))

							sim1 = SequenceMatcher(None, l_t1_clean, s_t1_clean).ratio()
							sim2 = SequenceMatcher(None, l_t2_clean, s_t2_clean).ratio()
							avg_straight = (sim1 + sim2) / 2.0

							sim1s = SequenceMatcher(None, l_t1_clean, s_t2_clean).ratio()
							sim2s = SequenceMatcher(None, l_t2_clean, s_t1_clean).ratio()
							avg_swap = (sim1s + sim2s) / 2.0

							cur_sim = max(avg_straight, avg_swap)
							#if debug_Fetch_Live: logdata("fetch_live_results FuzzyDebug", "Match '%s': sim=%.2f (straight=%.2f, swap=%.2f)" % (local_name, cur_sim, avg_straight, avg_swap))

							if cur_sim > best_sim:
								best_sim = cur_sim
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
								# Append ID safely at the end (Index 8)
								if len(match) > 8:
									match[8] = str(best_live["id"])
								else:
									match.append(str(best_live["id"]))
							else:
								match[5] = match[6] = match[7] = ""
						else:
							match[5] = match[6] = match[7] = ""
					except Exception as e:
						continue

				return matches_list

			def _matching_complete(updated_matches_list):
				if self.fetch_timestamp != current_ts:
					if debug_Fetch_Live: logdata("fetch_live_results", "DROP: Ignoring outdated results from previous session.")
					return
				cache_file, terminated_cache, changed, final_list = join(PLUGINPATH, "db/terminated_matches.json"), {}, False, []
				try:
					if exists(cache_file):
						with open(cache_file, 'r') as f:
							data = json.load(f)
							terminated_cache = data if isinstance(data, dict) else {name: datetime.now().strftime("%H:%M - %Y-%m-%d") for name in data}
				except: pass
				now_dt = datetime.now()
				cleaned_cache = {}
				for name, ts in terminated_cache.items():
					try:
						# Match your getTime format: '%H:%M - %Y-%m-%d'
						record_dt = datetime.strptime(ts, "%H:%M - %Y-%m-%d")
						if record_dt.date() == now_dt.date() or (now_dt - record_dt < timedelta(hours=4)):
							cleaned_cache[name] = ts
						else: changed = True
					except: changed = True
				terminated_cache = cleaned_cache
				for m in updated_matches_list:
					m_name, m_status = str(m[0]), str(m[7]).upper()
					# Apply getTime to match what user sees on screen
					m_time_str = self.getTime(str(m[1]))
					is_term = any(x in m_status for x in ('FINISHED', 'CANCELED', 'POSTPONED'))
					in_cache = m_name in terminated_cache
					if getattr(self, 'link', None) == "live":
						if is_term and not in_cache:
							terminated_cache[m_name] = m_time_str
							changed = True
						if is_term or in_cache: continue
					elif getattr(self, 'link', None) == "end":
						if not (is_term or in_cache): continue
					final_list.append(m)
				if debug_Fetch_Live: logdata("fetch_live_results", "MATCHES AFTER: %d" % len(final_list))
				self.matches = final_list
				if changed and self.link == "live":
					try:
						with open(cache_file, 'w') as f: json.dump(terminated_cache, f, ensure_ascii=False)
					except: pass
				try: self.iniMenu()
				except: pass

			d_match = deferToThread(_do_fuzzy_matching, matches_list, live_matches, now_adj)
			d_match.addCallback(_matching_complete)
			d_match.addErrback(lambda f: logdata("fetch_live_results", "Fuzzy matching thread failed: %s" % f.getErrorMessage()) if not getattr(self, 'is_closed', True) else None)

		def _error(failure):
			if self.is_closed: return
			if debug_Fetch_Live: logdata("fetch_live_results", "Twisted Request failed: %s" % failure.getErrorMessage())
			pass

		d.addCallback(_process_response)
		d.addErrback(_error)
		
		#logdata("FootOnSat-PERF", "LIVESCORE: Network request fired. Time elapsed until non-blocking request: %.3f s." % (time.time() - live_start_time))

	def getData(self, data):
		list = []
		try:
			# Ensure data is string/unicode for json.loads
			if not PY3 and isinstance(data, str):
				data = data.decode("utf-8", "ignore")
			self.js = json.loads(data)
#			data_str = data.decode('utf-8', 'ignore')
#			self.js = json.loads(data_str) # Use the decoded string
			if getattr(self, 'is_yesterday', False) and self.link == "end":
				self['key_red'].show()
				self['key_red'].setText(_("Close"))
				self['key_green'].hide()
		except Exception as e:
			# This is where the missing/corrupted message is triggered
			error_msg = _('%s') % title157 if getattr(self, 'is_yesterday', False) else _('%s') % title158
			self.session.openWithCallback(self.exit, MessageBox, error_msg, MessageBox.TYPE_ERROR, timeout=10)
			return
		# === DEBUG: Save LiveOnSat/GitHub JSON to /tmp (Pretty Print) ===
#		try:
#			liveonsat_debug_path = "/tmp/liveonsat_data.json"
#			# Dump the parsed JSON object back to a pretty-printed string
#			formatted_data_str = json.dumps(self.js, indent=4, ensure_ascii=False)
#			with codecs.open(liveonsat_debug_path, "w", encoding="utf-8") as f:
#				f.write(formatted_data_str)
#			logdata("FootOnSat-DEBUG", "Saved PRETTY-PRINTED LiveOnSat (GitHub) JSON to %s" % liveonsat_debug_path)
#		except Exception as e:
#			logdata("FootOnSat-DEBUG-ERROR", "Failed to save LiveOnSat JSON: %s" % str(e))
		# === END DEBUG ===

		cache_file = join(PLUGINPATH, "db/terminated_matches.json")
		terminated_cache = []
		cache_changed = False
		try:
			if exists(cache_file):
				with open(cache_file, 'r') as f: terminated_cache = json.load(f)
		except: pass

		ignored_competitions = []
		try:
			ignored_competitions = self.manageIgnoreFile()
			if debug_Ignore: logdata("getData", "Ignored competitions loaded: %s" % str(ignored_competitions))
		except Exception as e:
			if debug_Ignore: logdata("getData", "Failed to load ignored competitions: %s" % str(e))
			pass

		from .launcher import get_data_paths
		_, _, fav_file = get_data_paths()
		favs = []
		if self.link == "favorite":
			if exists(fav_file):
				try:
					with open(fav_file, 'r') as f: favs = json.load(f)
				except: pass
			favs = [str(f).lower() for f in favs]

		now = datetime.now()
		# 1. UPDATED: Consider matches live for 2 hours
		try:
			# Check the configuration value for the "finished" duration
			# Skip expiration check if we are viewing yesterday's matches
			if self.link == "yesterday":
				HOUR = 9999
			# Check the configuration value for the "finished" duration
			elif config.plugins.FootOnSat.finished.value == "3":
				HOUR = 3
			elif config.plugins.FootOnSat.finished.value == "4":
				HOUR = 4
			elif config.plugins.FootOnSat.finished.value == "5":
				HOUR = 5
			elif config.plugins.FootOnSat.finished.value == "6":
				HOUR = 6
			elif config.plugins.FootOnSat.finished.value == "7":
				HOUR = 7
			elif config.plugins.FootOnSat.finished.value == "8":
				HOUR = 8
			elif config.plugins.FootOnSat.finished.value == "9999":
				HOUR = 9999
			else:
				HOUR = 3
		except AttributeError:
			HOUR = 3

		# Define the duration for how long a match is considered 'live' or recent
		LIVE_DURATION = timedelta(hours=HOUR) 
		#logdata("FootOnSat-Duration", "Set live duration to %d hours." % HOUR)
		
		# ... (rest of the fetching and parsing logic) ...

		if self.js.get('footonsat') or self.link in ["live", "end", "yesterday"]:
			target_data = self.js.get('footonsat', [])
			for match in target_data:
				try:
					compet = str(match['compet']).strip()
					for suffix in [' - Week ', ' - Matchday ', ' - Round ']:
						if suffix in compet:
							compet = compet.split(suffix)[0].strip()

					if compet not in ignored_competitions or self.link not in ["today", "tomorrow", "live", "end", "yesterday", "favorite"]:
						match_date = datetime.strptime(match['date'] + ' ' + match['time'], '%Y-%m-%d %H:%M')
						match_date_adjusted = datetime.strptime(self.getTime(match['time'] + ' - ' + match['date']), '%H:%M - %Y-%m-%d')

						is_upcoming = match_date_adjusted > now
						is_live = now >= match_date_adjusted and now <= match_date_adjusted + LIVE_DURATION

						# 2. UPDATED: Initialize scores/status from JSON for all live/past matches
						team1_score = str(match.get('score1', "")).strip()
						team2_score = str(match.get('score2', "")).strip()
						match_status = "" # This will be overwritten by fetch_live_results if needed

						# Get status from JSON
						stype = match.get('stype', '').lower()
						match_status = ""
						if stype == 'live': match_status = 'LIVE'
						elif stype == 'canceled': match_status = 'CANCELED'
						elif stype == 'finished': match_status = 'FINISHED'
						elif stype == 'postponed': match_status = 'POSTPONED'

						# This code to correction the names
						match_name = match['match'] \
							.replace("Bodø/Glimt", "Bodø Glimt") \
							.replace("Preston N.E.", "Preston N.E")

						# Logic for moving matches between sections (Row visibility)
						is_really_finished = now > (match_date_adjusted + timedelta(minutes=180))
						is_terminated = any(x in str(match_status).upper() for x in ['FINISHED', 'CANCELED', 'POSTPONED'])
						in_cache = match_name in terminated_cache
						if getattr(self, 'link', None) == "favorite":
							m_lower = match_name.lower()
							# Check if any part of the saved favorite matches the current match name
							if not any(f in m_lower for f in favs):
								continue
							show_match_row = True
							show_scores_status = True
						if getattr(self, 'link', None) == "live":
							if is_really_finished and in_cache:
								terminated_cache.pop(match_name, None)
								cache_changed, in_cache = True, False
							show_match_row = False if (is_terminated or in_cache or is_really_finished) else True
						elif getattr(self, 'link', None) == "end":
							show_match_row = True if (is_terminated or in_cache or is_really_finished) else False
						elif getattr(self, 'link', None) == "today":
							show_match_row = True if is_upcoming else False
						else:
							show_match_row = True
						if not show_match_row:
							continue

						show_scores_status = False
						if is_upcoming:
							show_scores_status = False if getattr(self, 'link', None) in ["live", "end"] else True
							team1_score = "" 
							team2_score = ""
						elif is_live:
							# Keep live matches not visible in today sections
							if getattr(self, 'link', None) == "today":
								show_scores_status = False
							# Keep live matches visible in live and end sections
							elif getattr(self, 'link', None) in ["live", "end"]:
								show_scores_status = True
							else:
								# Keep live matches visible in specific league sections
								if config.plugins.FootOnSat.livescore.value == "2":
									show_scores_status = True
						else:
							# We allow it for both 'live' and 'end' sections here
							if getattr(self, 'link', None) in ["live", "end"]:
								show_scores_status = True
							else:
								show_scores_status = False

						# Final check: if show_scores_status is False, we clear scores but status remains based on config
						if not show_scores_status:
							team1_score = ""
							team2_score = ""
							# If user chose "1" (No live Score + Status), clear status too
							if config.plugins.FootOnSat.livescore.value == "1":
								match_status = ""

						if show_scores_status:
							if getattr(self, 'link', None) == "end":
								if now > (match_date_adjusted + timedelta(hours=HOUR)):
									continue

							list.append([
									str(match_name),
									str(match['time']) + ' - ' + str(match['date']),
									str(match['compet']),
									str(match['flags']['team1']),
									str(match['flags']['team2']),
									team1_score,
									team2_score,
									match_status,
									match.get('event_id', '')])
					else:
						if debug_Fetch_Live: logdata("getData", "Ignored competition: " + str(match['match']) + ", Compet: " + compet)
						pass
				except KeyError:
					#if debug_Fetch_Live: logdata("getData", "KeyError on match: " + str(match))
					pass

			self.matches = list

			if cache_changed:
				try:
					with open(cache_file, 'w') as f: json.dump(terminated_cache, f, ensure_ascii=False)
				except: pass

			#logdata("DEBUG_VALUE", "Value is: %s | Link is: %s" % (str(config.plugins.FootOnSat.livescore.value), str(self.link)))
			# Only fetch live results for live/finished matches if livescore is set to "3"					
			if config.plugins.FootOnSat.livescore.value == "2":
				if config.plugins.FootOnSat.livescoresections.value == "1" and self.link != "today":
					self.fetch_live_results()
				elif config.plugins.FootOnSat.livescoresections.value == "2":
					if self.link == "live" or self.link == "end" or self.link == "yesterday":
						self.fetch_live_results()

			self.onWindowShow()
		else:
			self.matches = []  # dummy entry to force iniMenu to show "no schedules"
			self.onWindowShow()
			#self.session.openWithCallback(self.exit, MessageBox, _('No schedules in this section at this time'), MessageBox.TYPE_ERROR, timeout=10)
		
	def getChannels(self):
		list = []
		res = []
		gList = []
		self["list2"].l.setItemHeight(50)
		if isUHD():
			self["list2"].l.setFont(0, gFont('Regular', 32))
		else:
			self["list2"].l.setFont(0, gFont('Regular', 30))
		index = self['list1'].getSelectionIndex()
		if len(self.matches) > 0:
			self.match = self.matches[index][0]
			for data in self.js['footonsat']:
				try:
					if data['related_to'] == self.match:
						list.append((str(data['channel']), str(data['sat']), str(data['freq']), str(data['encry']), str(data['link'])))
						res.append(MultiContentEntryText())
						res.append(MultiContentEntryText(pos=(7, 6), size=(510, 40), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(data['channel'])))
						gList.append(res)
						res = []
				except KeyError:
					pass
			self["list2"].setList([])
			self["list2"].setList(gList)
			self.channelData = list

	def updateChannelData(self):
		if len(self.channelData) > 0:
			index = self['list2'].getSelectionIndex()
			channel = str(self.channelData[index][0] or "")
			sat = str(self.channelData[index][1] or "")
			freq = str(self.channelData[index][2] or "")
			enc = str(self.channelData[index][3] or "")
			self["channel"].setText(channel)
			self["sat"].setText(sat)
			self["freq"].setText(freq)
			self["enc"].setText(enc)
			if 'V' in freq or 'H' in freq:
				self['key_blue'].show()
				self.canScan = True
			else:
				self['key_blue'].hide()
				self.canScan = False

	def resetChannelinfo(self):
		self["channel"].setText("")
		self["sat"].setText("")
		self["freq"].setText("")
		self["enc"].setText("")
		self['key_blue'].hide()
		self.canScan = False

	def keyGreen(self):
		if self.link == "end":
			if getattr(self, 'is_yesterday', False):
				return
			# Update timestamp to kill old fetch jobs
			self.fetch_timestamp = time.time()
			if hasattr(self, 'fetch_deferred') and self.fetch_deferred:
				try: self.fetch_deferred.cancel()
				except: pass
			if debug_Fetch_Live: logdata("keyGreen", "Switching to Yesterday matches")
			self.is_yesterday = True
			self.link = "yesterday"
			self.matches = []
			self['list1'].setList([])
			self['key_green'].setText(title283)
			self.fetchYesterdayData(yesterday=True)
		elif self.link in json_urls:
			if debug_Standings: logdata("keyGreen", "Opening Standings for: %s" % str(self.link))
			self.session.open(StandingsScreen, self.link, json_urls[self.link])

	def fetchYesterdayData(self, yesterday=True):
		self.is_yesterday = yesterday
		url_link = "yesterday"
		self.link = "yesterday"
		url = 'https://raw.githubusercontent.com/fairbird/footonsat-api/main/{}.json'.format(url_link)
		if debug_Fetch_Live: logdata("fetchYesterday", "Requesting URL: %s" % url)
		sniFactory = WebClientContextFactory(url)
		getPage(str.encode(url), contextFactory=sniFactory).addCallback(self.getData).addErrback(self.Yesterdayerror)

	def Yesterdayerror(self, failure):
		if debug_Fetch_Live: logdata("API-Error", "Error: %s" % str(failure.getErrorMessage()))
		if getattr(self, 'is_yesterday', False):
			error_msg = title159
		else:
			error_msg = title151
		self.session.openWithCallback(self.exit, MessageBox, error_msg, MessageBox.TYPE_ERROR, timeout=10)

	def keyBlue(self):
		if self.canScan:
			self.scan()

	def scan(self):
		if (nimmanager.hasNimType("DVB-S")):
			nims = nimmanager.getNimListOfType('DVB-S')
			nimList = []
			self.openatv = False
			self.openpli = False
			for elem in nims:
				nim = nimmanager.getNimConfig(elem)
				if hasattr(nim, 'dvbs'):
					self.openatv = True
					if nim.dvbs.configMode.value not in ('loopthrough', 'satposdepends','nothing'):
						nimList.append(elem)
				elif hasattr(nim, 'configMode'):
					self.openpli = True
					if nim.configMode.value not in ('loopthrough', 'satposdepends', 'nothing'):
						nimList.append(elem)

			index = self['list2'].getSelectionIndex()
			freq = self.channelData[index][2].split(' ')[0]
			try:
				freq = int(float(freq))
			except Exception as e:
				if debug_Fetch_Live: logdata("scan_exception", "Failed to parse freq '{}': {}".format(freq, e))
				pass
			symbolrate = self.channelData[index][2].split(' ')[2]
			pos = self.channelData[index][1].split(' ')[-1].replace('°', ' ').split(' ')
			sat = self.getSat(pos)
			fec = self.channelData[index][2].split(' ')[-1]
			polarization = 'V' if 'V' in self.channelData[index][2] else 'H'

			if len(nimList) == 0:
				self.session.open(MessageBox, title160, MessageBox.TYPE_ERROR, timeout=10)
			elif fileExists('/var/lib/dpkg/status'):
				from Plugins.Extensions.FootOnSat.satfinder.dreamos import Satfinder
				self.session.open(Satfinder, self.getfeid(), freq, symbolrate, sat, polarization, fec)
			elif self.openatv:
				from Plugins.Extensions.FootOnSat.satfinder.openatv import Satfinder
				self.session.open(Satfinder, freq, symbolrate, sat, polarization, fec)
			elif self.openpli:
				from Plugins.Extensions.FootOnSat.satfinder.openpli import Satfinder
				self.session.open(Satfinder, freq, symbolrate, sat, polarization, fec)
			else:
				self.session.open(MessageBox, title161, MessageBox.TYPE_ERROR, timeout=10)
		else:
			self['key_blue'].hide()

	def getfeid(self):
		nims = nimmanager.getNimListOfType("DVB-S")
		nimList = []
		for x in nims:
			nim = nimmanager.getNimConfig(x)
			if not nim.sat.configMode.value in ("loopthrough", "satposdepends", "nothing"):
				nimList.append(x)
		if len(nimList) == 1:
			return nimList[0]

	def getSat(self, pos):
		if pos[-1] == 'w':
			sat = int(float(pos[0]) * -1 * 10 + 3600)
		else:
			sat = int(float(pos[0]) * 10)
		return sat

	def exit(self, ret=None):
		self.is_closed = True
		if hasattr(self, 'fetch_deferred') and self.fetch_deferred:
			try:
				# This kills the network socket (Twisted) or the thread callback
				self.fetch_deferred.cancel()
				self.fetch_deferred = None 
				if debug_Fetch_Live: logdata("FootOnSat", "STOP JOB: fetch_deferred killed.")
			except:
				pass
		try:
			gc.collect()
		except:
			if debug_Fetch_Live: logdata("FootOnSat", "Garbage Collector: Failed.")
			pass
		self.close()

	def manageIgnoreFile(self, compet=None, reset=False, remove=None):
		if debug_Ignore: logdata("manageIgnoreFile", "Called with compet={}, reset={}, remove={}".format(compet, reset, remove))
		# Create ignore directory if it doesn't exist
		from .launcher import get_data_paths
		ignore_dir, ignore_file, fav_file = get_data_paths()
		if not exists(ignore_dir):
			try:
				os.makedirs(ignore_dir, 0o755)
				if debug_Ignore: logdata("manageIgnoreFile", "Created ignore directory: " + ignore_dir)
			except Exception as e:
				if debug_Ignore: logdata("manageIgnoreFile", "Failed to create ignore dir: " + str(e))
				return []
		# Determine file open function for Python 2 and 3
		try:
			PY3 = True
		except NameError:
			PY3 = False
		if not PY3:
			def fopen(fname, mode):
				return io.open(fname, mode, encoding='utf-8')
		else:
			fopen = open
		# Handle reset case
		if reset:
			try:
				with fopen(ignore_file, 'w') as f:
					json.dump({"ignored_competitions": []}, f)
				if debug_Ignore: logdata("manageIgnoreFile", "Reset ignore-match.json to empty")
				return []
			except Exception as e:
				if debug_Ignore: logdata("manageIgnoreFile", "Failed to reset ignore file: " + str(e))
				return []
		# Load or initialize ignored competitions
		ignored = []
		if exists(ignore_file):
			try:
				with fopen(ignore_file, 'r') as f:
					data = json.load(f)
					ignored = data.get("ignored_competitions", [])
				if debug_Ignore: logdata("manageIgnoreFile", "Loaded ignored competitions: " + str(ignored))
			except Exception as e:
				if debug_Ignore: logdata("manageIgnoreFile", "Failed to read ignore file: " + str(e))
				# Create empty file if reading fails
				try:
					with fopen(ignore_file, 'w') as f:
						json.dump({"ignored_competitions": []}, f)
					if debug_Ignore: logdata("manageIgnoreFile", "Created empty ignore-match.json after read failure")
				except Exception as e:
					if debug_Ignore: logdata("manageIgnoreFile", "Failed to create ignore file: " + str(e))
					return []
		else:
			try:
				with fopen(ignore_file, 'w') as f:
					json.dump({"ignored_competitions": []}, f)
				if debug_Ignore: logdata("manageIgnoreFile", "Created empty ignore-match.json")
			except Exception as e:
				if debug_Ignore: logdata("manageIgnoreFile", "Failed to create ignore file: " + str(e))
				return []
		# Remove competition if provided
		if remove:
			try:
				compet_str = str(remove).strip()
			except UnicodeEncodeError:
				compet_str = unicode(remove).encode('utf-8').strip()  # Python 2 compatibility
			if debug_Ignore: logdata("manageIgnoreFile", "Attempting to remove compet: " + (compet_str if compet_str else "None"))
			if compet_str in ignored:
				ignored.remove(compet_str)
				try:
					with fopen(ignore_file, 'w') as f:
						json.dump({"ignored_competitions": ignored}, f)
					if debug_Ignore: logdata("manageIgnoreFile", "Removed competition: " + compet_str + ", New list: " + str(ignored))
				except Exception as e:
					if debug_Ignore: logdata("manageIgnoreFile", "Failed to update ignore file after removing " + compet_str + ": " + str(e))
					return ignored
			else:
				if debug_Ignore: logdata("manageIgnoreFile", "Competition not removed: " + (compet_str if compet_str else "None") + " (not in ignore list)")
				pass
			return ignored
		# Add competition if provided
		if compet:
			try:
				compet_str = str(compet).strip()
			except UnicodeEncodeError:
				compet_str = unicode(compet).encode('utf-8').strip()  # Python 2 compatibility
			if debug_Ignore: logdata("manageIgnoreFile", "Received compet: " + (compet_str if compet_str else "None"))
			if compet_str and compet_str not in ignored:
				ignored.append(compet_str)
				try:
					with fopen(ignore_file, 'w') as f:
						json.dump({"ignored_competitions": ignored}, f)
					if debug_Ignore: logdata("manageIgnoreFile", "Added competition to ignore: " + compet_str + ", New list: " + str(ignored))
					return ignored
				except Exception as e:
					if debug_Ignore: logdata("manageIgnoreFile", "Failed to update ignore file with " + compet_str + ": " + str(e))
					return ignored
			else:
				if debug_Ignore: logdata("manageIgnoreFile", "Competition not added: " + (compet_str if compet_str else "None") + " (already ignored or empty)")
				pass
		return ignored

	def selectCompetitionToRemove(self, selected):
		if not selected or not selected[1]:
			self.session.open(MessageBox, title162, MessageBox.TYPE_INFO, timeout=5)
			return
		compet = selected[1]
		if debug_Ignore: logdata("selectCompetitionToRemove", "Removing competition: " + compet)
		self.manageIgnoreFile(remove=compet)
		self.session.open(MessageBox, title163 % compet, MessageBox.TYPE_INFO, timeout=5)
		# Refresh the match list to include removed competition's matches
		self.matches = []
		self["list1"].setList([])
		self.callAPI()

	def searchTeam(self, text):
		if text:
			if debug_favorite: logdata("searchTeam", "Searching for team: " + str(text))
			url = 'http://suggestqueries.google.com/complete/search?client=chrome&q={}'.format(text.replace(' ', '%20'))
			getPage(str.encode(url)).addCallback(self.showSuggestions).addErrback(self.error)

	def showSuggestions(self, data):
		try:
			if not PY3 and isinstance(data, str):
				data = data.decode('utf-8', 'ignore')
			js = json.loads(data)
			search_term = js[0]
			suggestions = js[1]
			if debug_favorite: logdata("showSuggestions", "Suggestions received for: " + str(search_term))
			display_list = []
			if search_term:
				display_list.append((str(search_term).title(), str(search_term).title()))
			if suggestions:
				for s in suggestions:
					s_title = str(s).title()
					if (s_title, s_title) not in display_list:
						display_list.append((s_title, s_title))
			if display_list:
				self.session.openWithCallback(self.addFavorite, TeamListScreen, list_data=display_list, title_text=_("%s") % title287)
			else:
				self.session.open(MessageBox, title288, MessageBox.TYPE_INFO, timeout=5)
		except Exception as e:
			pass

	def addFavorite(self, ret):
		if ret:
			team = ret[0]
			if debug_favorite: logdata("addFavorite", "Adding team to favorites: " + str(team))
			from .launcher import get_data_paths
			_, _, fav_file = get_data_paths() # Ensure this points to the correct new path
			favs = []
			if exists(fav_file):
				try:
					with open(fav_file, 'r') as f: favs = json.load(f)
				except: pass
			if team not in favs:
				favs.append(team)
				with open(fav_file, 'w') as f: json.dump(favs, f)
			self.matches = []
			self["list1"].setList([])
			self.callAPI()

	def removeFavorite(self, ret):
		if ret:
			team = ret[0]
			if debug_favorite: logdata("removeFavorite", "Removing team from favorites: " + str(team))
			from .launcher import get_data_paths
			_, _, fav_file = get_data_paths()
			favs = []
			if exists(fav_file):
				try:
					with open(fav_file, 'r') as f: favs = json.load(f)
				except: pass
			if team in favs:
				favs.remove(team)
				with open(fav_file, 'w') as f: json.dump(favs, f)
			self.matches = []
			self["list1"].setList([])
			self.callAPI()

	def keyRed(self):
		if getattr(self, 'is_yesterday', False) and self.link == "end":
			self.is_yesterday = False
			self['key_red'].hide()
			self.close()
			return
		if getattr(self, 'link', None) == "favorite":
			if debug_favorite: logdata("keyRed", "Opening remove favorite screen")
			from .launcher import get_data_paths
			_, _, fav_file = get_data_paths()
			favs = []
			if exists(fav_file):
				try:
					with open(fav_file, 'r') as f: favs = json.load(f)
				except: pass
			if favs:
				list = [(str(f), str(f)) for f in favs]
				self.session.openWithCallback(self.removeFavorite, TeamListScreen, list_data=list, title_text=title289)
			else:
				self.session.open(MessageBox, title290, MessageBox.TYPE_INFO, timeout=5)
			return
		from .launcher import get_data_paths
		ignore_dir_path, ignore_file_path, _ = get_data_paths()
		if self.link in ["today", "tomorrow"] and self.selectedList == self["list1"] and len(self.matches) > 0:
			try:
				index = self['list1'].getSelectionIndex()
				compet = str(self.matches[index][2]).strip()
				# Remove week/round/matchday suffixes
				for suffix in [' - Week ', ' - Matchday ', ' - Round ']:
					if suffix in compet:
						compet = compet.split(suffix)[0].strip()
				if not compet:
					self.session.open(MessageBox, title164, MessageBox.TYPE_ERROR, timeout=5)
					return
				# Load current ignored competitions
				ignored_before = self.manageIgnoreFile()
				# Add selected competition to ignore list
				self.manageIgnoreFile(compet=compet)
				ignored_after = self.manageIgnoreFile()
				if compet in ignored_after and compet not in ignored_before:
					# Use the variable containing only the file path string
					path_info = ignore_file_path
					msg = title165 % (compet, path_info)
					self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=5)
				else:
					if debug_Ignore: logdata("keyRed", "Competition " + compet + " not added (already ignored or failed)")
					pass
				# Refresh the match list to exclude ignored competitions
				self.matches = []
				self["list1"].setList([])
				self.callAPI()
			except Exception as e:
				if debug_Ignore: logdata("keyRed", "Error ignoring competition: " + str(e))
				self.session.open(MessageBox, title166, MessageBox.TYPE_ERROR, timeout=5)

	def keyYellow(self):
		if getattr(self, 'link', None) == "favorite":
			if debug_favorite: logdata("keyYellow", "Opening search team keyboard")
			self.session.openWithCallback(self.searchTeam, VirtualKeyBoard, title=title293, text="")
			return
		if self.link in ["today", "tomorrow"]:
			try:
				ignored_list = self.manageIgnoreFile()
				if not ignored_list:
					self.session.open(MessageBox, title167, MessageBox.TYPE_INFO, timeout=5)
					return
				if debug_Ignore: logdata("keyYellow", "Ignored competitions: " + str(ignored_list))
				list = []
				for comp in ignored_list:
					# Ensure competition name is a string/byte string suitable for ChoiceBox in PY2 and PY3
					if PY3:
						# Python 3: Competition names loaded from JSON are standard strings
						comp_str = comp
					else:
						# Python 2: Competition names loaded from JSON are unicode (u'...')
						# We convert them to a utf-8 encoded byte string for compatibility with ChoiceBox
						try:
							comp_str = comp.encode('utf-8') if isinstance(comp, unicode) else comp
						except Exception as e:
							if debug_Ignore: logdata("keyYellow", "Error converting competition to byte string: " + str(e))
							comp_str = str(comp) # Fallback
					list.append((comp_str, comp_str))
				# If the list is empty after processing, stop
				if not list:
					self.session.open(MessageBox, title168, MessageBox.TYPE_ERROR, timeout=5)
					return
				self.session.openWithCallback(self.selectCompetitionToRemove, TeamListScreen, title_text=_("%s") % title169, list_data=list)
			except Exception as e:
				if debug_Ignore: logdata("keyYellow", "Error selecting competition to remove: " + str(e))
				# This addresses the original error which likely occurred here due to string conversion failure
				self.session.open(MessageBox, title170, MessageBox.TYPE_ERROR, timeout=5)


class TeamListScreen(Screen):
	def __init__(self, session, list_data, title_text=title291):
		Screen.__init__(self, session)
		self.skin = SKIN_TeamListScreen
		self.setTitle(title_text)
		self.list_data = list_data
		if debug_favorite: logdata("TeamListScreen", "Opened with title: %s, data count: %d" % (str(title_text), len(list_data)))
		display_list = [item[0] if isinstance(item, tuple) else item for item in list_data]
		self["list"] = MenuList(display_list)
		self["actions"] = ActionMap(["OkCancelActions"], {
			"ok": self.okClicked,
			"cancel": self.cancelClicked
		}, -1)

	def okClicked(self):
		idx = self["list"].getSelectedIndex()
		if debug_favorite: logdata("TeamListScreen", "OK clicked, selected index: %d, data: %s" % (idx, str(self.list_data[idx])))
		self.close(self.list_data[idx])

	def cancelClicked(self):
		if debug_favorite: logdata("TeamListScreen", "Cancel clicked")
		self.close(None)


class MatchDetailsScreen(Screen):
	def __init__(self, session, event_id, match_name, home_full, away_full, home_country, away_country):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_MatchDetails
		self.event_id = str(event_id)
		if debug_MatchDetails: logdata("MatchDetails", "Initializing MatchDetails for event_id: %s, match_name: %s, home_full: %s, away_full: %s, home_country: %s, away_country: %s" % (event_id, match_name, home_full, away_full, home_country, away_country))
		self["title"] = Label(str(match_name) + " - " + title171)
		self["home_name_big"] = Label(str(home_full))
		self["away_name_big"] = Label(str(away_full))
		self["home_team"] = Pixmap()
		self["away_team"] = Pixmap()
		self["score"] = Label("- : -")
		self["status"] = Label(_("%s...") % title172)
		self["key_red"] = Label(_("%s") % title134)
		
		self["details_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		
		self["setupActions"] = ActionMap(["FootOnsatActions", "ColorActions"], {
			"cancel": self.close,
			"back": self.close,
			"red": self.close,
			"ok": self.close,
			"up": self.up,
			"down": self.down,
			"left": self.openMedia,
			"right": self.openStats,
		}, -1)

		self.home_country = home_country
		self.away_country = away_country
		self.onLayoutFinish.append(self.onLayoutFinished)

	def onLayoutFinished(self):
		self.fetch_details()
		self.showFlags(self.home_country, self.away_country)

	def showFlags(self, team1, team2):
		if isUHD():
			h_pos, a_pos = (460, 400), (1955, 400)
			# info: Set specific big size for UHD (Width, Height)
			flag_size = eSize(150, 50)
		else:
			h_pos, a_pos = (370, 330), (1400, 330)
			# info: Set specific big size for FHD (Width, Height)
			flag_size = eSize(100, 60)

		flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team1))
		flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team2))

		if not fileExists(flagTeam1):
			flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
		if not fileExists(flagTeam2):
			flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")

		for side, path, pos in [("home_team", flagTeam1, h_pos), ("away_team", flagTeam2, a_pos)]:
			if self[side].instance:
				# info: setScale(1) forces the image to stretch to the new widget size
				self[side].instance.setScale(1)
				self[side].instance.resize(flag_size)
				self[side].instance.setPixmapFromFile(path)
				self[side].instance.move(ePoint(pos[0], pos[1]))
				self[side].instance.show()

	def openMedia(self):
		home_val = self["home_name_big"].getText() if "home_name_big" in self else ""
		away_val = self["away_name_big"].getText() if "away_name_big" in self else ""
		self.session.openWithCallback(self.navCallback, MatchMediaScreen, self.event_id, self["title"].getText().replace(" - " + title171, ""), home_val, away_val)

	def openStats(self):
		self.session.openWithCallback(self.navCallback, MatchStatisticsScreen, self.event_id, self["title"].getText().replace(" - " + title171, ""), self["home_name_big"].getText(), self["away_name_big"].getText())

	def navCallback(self, answer=None):
		if answer == "exit_all":
			self.close()

	def up(self):
		self["details_list"].up()

	def down(self):
		self["details_list"].down()

	def fetch_details(self):
		url_incidents = "https://api.sofascore.com/api/v1/event/{}/incidents".format(self.event_id)
		url_event = "https://api.sofascore.com/api/v1/event/{}".format(self.event_id)
		
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
			
			def process_twisted(results):
				raw = [r if not isinstance(r, Failure) else None for r in results]
				if all(x is None for x in raw): return self.process_data(None)
				try:
					return self.process_data([json.loads(r.decode('utf-8')) for r in raw if r])
				except: return self.process_data(None)
			
			d.addCallback(process_twisted)
			
		else:
			def _get_data():
				s = requests.Session()
				s.headers.update({
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
					'Referer': 'https://www.sofascore.com/',
					'Origin': 'https://www.sofascore.com',
					'Accept': 'application/json',
					'X-Requested-With': 'XMLHttpRequest'
				})
				try:
					s.get('https://www.sofascore.com', timeout=10)
					results = []
					for u in [url_incidents, url_event]:
						r = s.get(u, timeout=25)
						r.raise_for_status()
						results.append(json.loads(r.content.decode('utf-8')))
					return results
				except Exception as e:
					if debug_MatchDetails: logdata("MatchDetails", "Error: %s" % str(e))
					return None
			
			d = deferToThread(_get_data)
			d.addCallback(self.process_data)

	def process_data(self, data):
		if not data:
			self["details_list"].setList([])
			return
		try:
			inc_js, ev_js = data
		except (TypeError, ValueError):
			inc_js, ev_js = None, None
		if ev_js and 'event' in ev_js:
			ev = ev_js['event']
			h = ev.get('homeScore', {}).get('current', 0)
			a = ev.get('awayScore', {}).get('current', 0)
			self["score"].setText(str(h) + " - " + str(a))
			STATUS_MAP = {
				"Ended":       title209,
				"1st half":    title210,
				"2nd half":    title211,
				"Halftime":    title212,
				"Postponed":   title213,
				"Canceled":    title214,
				"Delayed":     title215,
				"Extra Time":  title216,
				"Penalties":   title217,
				"Not started": title218,
			}
			raw_status = str(ev.get('status', {}).get('description', ''))
			self["status"].setText(STATUS_MAP.get(raw_status, raw_status))

		gList = []
		if inc_js and 'incidents' in inc_js:
			if isUHD():
				ITEM_H = 65   # Row Height
				FONT_S = 40    # Font Size
				C_X    = 1200  # Minute X Position
				T_W    = 100   # Minute Width
				T_W_Y  = 13    # Vertical Offset
				# --- HOME SIDE ---
				H_TXT_X = 300   # Home Player Name X
				H_TXT_W = 800 # Home Player Name Width
				H_IMG_X = 1135 # Home Icon X
				H_TXT_Y = 12    # Vertical Offset
				# --- AWAY SIDE ---
				A_IMG_X = 1300 # Away Icon X
				A_TXT_X = 1392 # Away Player Name X
				A_TXT_W = 800 # Away Player Name Width
				A_TXT_Y  = 12  # Vertical Offset
				# --- ICON SIZE ---
				IMG_W  = 60    # Fixed Width
				IMG_H  = 80    # Fixed Height
				IMG_Y  = -7    # Vertical Offset
			else:
				ITEM_H = 70    # Row Height
				FONT_S = 36    # Font Size
				C_X    = 850   # Minute X Position
				T_W    = 100   # Minute Width
				T_W_Y  = 0    # Vertical Offset
				# --- HOME SIDE ---
				H_TXT_X = 10   # Home Player Name X
				H_TXT_W = 750  # Home Player Name Width
				H_IMG_X = 780  # Home Icon X
				H_TXT_Y = 0    # Vertical Offset
				# --- AWAY SIDE ---
				A_IMG_X = 970  # Away Icon X
				A_TXT_X = 1040 # Away Player Name X
				A_TXT_W = 700  # Away Player Name Width
				A_TXT_Y  = 0  # Vertical Offset
				# --- ICON SIZE ---
				IMG_W  = 60    # Fixed Width
				IMG_H  = 80    # Fixed Height
				IMG_Y  = -5    # Vertical Offset

			self["details_list"].l.setItemHeight(ITEM_H)
			self["details_list"].l.setFont(0, gFont('Regular', FONT_S))

			# Sort: Top to Bottom (Start of match to end)
			sorted_inc = sorted(inc_js['incidents'], key=lambda x: x.get('time', 0), reverse=False)
			player_cards = {}
			for inc in sorted_inc:
				if inc.get('time', 0) < 0 or inc.get('isBenchPlayer', False):
					continue
				itype = inc.get('incidentType')
				if itype not in ('goal', 'card', 'substitution'): continue
				itime = str(inc.get('time', '')) + "'"
				is_home = inc.get('isHome', True)
				text = ""
				color = 0xFFFFFF
				icon_name = ""
				if itype == 'goal':
					is_og = str(inc.get('incidentClass', '')).lower() == 'owngoal'
					is_pen = str(inc.get('incidentClass', '')).lower() == 'penalty'
					if is_og:
						text = str(inc.get('player', {}).get('name', '')) + " (OG)"
						color = 0xFF0000
						icon_name = "owngoal.png"
					else:
						p_name = str(inc.get('player', {}).get('name', 'Goal'))
						text = (p_name + " (Pen.)") if is_pen else p_name
						color = 0x00FF00
						icon_name = "goal.png"
				elif itype == 'card':
					ic_class = str(inc.get('incidentClass', '')).lower()
					p_id = inc.get('player', {}).get('id', 'unknown')
					text = str(inc.get('player', {}).get('name', ''))
					if 'yellow' in ic_class:
						player_cards[p_id] = player_cards.get(p_id, 0) + 1
						if player_cards[p_id] >= 2:
							color = 0xFF0000
							icon_name = "redcard.png"
						else:
							color = 0xFFFF00
							icon_name = "yellowcard.png"
					else:
						color = 0xFF0000
						icon_name = "redcard.png"
				elif itype == 'substitution':
					def shortName(name):
						parts = name.split()
						return "%s. %s" % (parts[0][0], parts[-1]) if len(parts) > 1 else name
					p_in = shortName(str(inc.get('playerIn', {}).get('name', '')))
					p_out = shortName(str(inc.get('playerOut', {}).get('name', '')))
					text = "%s %s / %s %s" % (p_out, title175, p_in, title176)
					color = 0xFFFFFF
					icon_name = "substitution.png"

				# --- Incident List Row Information ---
				res = [MultiContentEntryText()] # List row anchor
				if isUHD():
					res.append(MultiContentEntryText(pos=(C_X, T_W_Y), size=(T_W, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=itime)) # Match Minute
				else:
					res.append(MultiContentEntryText(pos=(C_X, T_W_Y), size=(T_W, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=itime)) # Match Minute
				
				icon_path = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/{}".format(icon_name)) # Icon Path
				png = loadPNG(icon_path) # Load Incident Icon

				if is_home:
					if png: res.append(MultiContentEntryPixmapAlphaBlend(pos=(H_IMG_X, IMG_Y), size=(IMG_W, IMG_H), png=png)) # Home Incident Icon
					res.append(MultiContentEntryText(pos=(H_TXT_X, H_TXT_Y), size=(H_TXT_W, ITEM_H), font=0, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=text, color=color)) # Home Player Name
				else:
					if png: res.append(MultiContentEntryPixmapAlphaBlend(pos=(A_IMG_X, IMG_Y), size=(IMG_W, IMG_H), png=png)) # Away Incident Icon
					res.append(MultiContentEntryText(pos=(A_TXT_X, A_TXT_Y), size=(A_TXT_W, ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=text, color=color)) # Away Player Name
				
				gList.append(res) # Add Row to List
		
		self["details_list"].setList(gList)


class MatchStatisticsScreen(Screen):
	def __init__(self, session, event_id, match_name, home_name, away_name):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_MatchStatistics
		self.event_id = event_id
		if debug_MatchStatistics: logdata("MatchStatistics", "Initializing MatchStatistics for event_id: %s, match_name: %s, home_name: %s, away_name: %s" % (event_id, match_name, home_name, away_name))
		self["title"] = Label(str(match_name) + " - " + title177)
		self["home_team"] = Label(str(home_name))
		self["away_team"] = Label(str(away_name))
		self["key_red"] = Label(_("%s") % title134)
		self["stats_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)

		self["setupActions"] = ActionMap(["FootOnsatActions", "ColorActions"], {
			"cancel": self.exitAll,
			"back": self.exitAll,
			"red": self.exitAll,
			"up": self.up,
			"down": self.down,
			"left": self.close,
			"right": self.openMedia,
		}, -1)
		
		self.onLayoutFinish.append(self.fetch_stats)

	def exitAll(self):
		self.close("exit_all")

	def openMedia(self):
		clean_title = self["title"].getText().replace(" - " + title177, "")
		home_val = self["home_team"].getText() if "home_team" in self else ""
		away_val = self["away_team"].getText() if "away_team" in self else ""
		self.session.openWithCallback(self.navCallback, MatchMediaScreen, self.event_id, clean_title, home_val, away_val)

	def navCallback(self, answer=None):
		if answer == "exit_all":
			self.close("exit_all")
		else:
			self.close()

	def up(self):
		self["stats_list"].up()

	def down(self):
		self["stats_list"].down()

	def fetch_stats(self):
		url = "https://api.sofascore.com/api/v1/event/{}/statistics".format(self.event_id)
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
			'Referer': 'https://www.sofascore.com/',
			'Origin': 'https://www.sofascore.com',
			'Accept': 'application/json',
			'X-Requested-With': 'XMLHttpRequest'
		}

		if PY3:
			d = getPage(str.encode(url), contextFactory=WebClientContextFactory(url), timeout=25, headers={k.encode(): [v.encode()] for k, v in headers.items()})
			d.addCallback(lambda raw: self.process_stats(json.loads(raw.decode('utf-8'))))
			d.addErrback(lambda _: self.process_stats(None))
		else:
			def _get():
				s = requests.Session()
				s.headers.update(headers)
				s.get('https://www.sofascore.com', timeout=10)
				r = s.get(url, timeout=25)
				return json.loads(r.content.decode('utf-8')) if r.status_code == 200 else None
			d = deferToThread(_get)
			d.addCallback(self.process_stats)
			d.addErrback(lambda _: self.process_stats(None))

	def process_stats(self, data):
		gList = []
		if isUHD():
			ITEM_H = 65   # Row Height: Increase to add space between rows
			FONT_S = 40   # Font Size: Increase to make text bigger
			W_LIST = 2462 # Total width of the list box
			W_LIST_X = 0  # Vertical Offset x 
			W_LIST_Y = 13 # Vertical Offset Y
			HOME_X = 131  # Move Home value: Higher = Right, Lower = Left
			HOME_Y = 13   # Vertical Offset
			NAME_X = 731 # Move Stat Name: Higher = Right, Lower = Left
			NAME_Y = 13   # Vertical Offset
			AWAY_X = 1930 # Move Away value: Higher = Right, Lower = Left
			AWAY_Y = 13   # Vertical Offset
			COL_W  = 400  # Width of the value boxes
			NAME_W = 1000  # Width of the middle name box
		else:
			ITEM_H = 80   # Row Height: Increase to add space between rows
			FONT_S = 36   # Font Size: Increase to make text bigger
			W_LIST = 1720 # Total width of the list box
			W_LIST_X = 0  # Vertical Offset x
			W_LIST_Y = 0  # Vertical Offset Y
			HOME_X = 10   # Move Home value: Higher = Right, Lower = Left
			HOME_Y = 0    # Vertical Offset
			NAME_X = 250  # Move Stat Name: Higher = Right, Lower = Left
			NAME_Y = 0    # Vertical Offset
			AWAY_X = 1450 # Move Away value: Higher = Right, Lower = Left
			AWAY_Y = 0    # Vertical Offset
			COL_W  = 250  # Width of the value boxes
			NAME_W = 1220 # Width of the middle name box

		self["stats_list"].l.setItemHeight(ITEM_H)
		self["stats_list"].l.setFont(0, gFont('Regular', FONT_S))

		if data and 'statistics' in data:
			for period in data['statistics']:
				if period.get('period') == 'ALL':
					for group in period.get('groups', []):
						# --- Group Header (Fixing the not-a-string error here) ---
						res = []
						res.append(MultiContentEntryText()) # Anchor
						STATS_MAP = {
						    # Group Headers
						    "Match overview":         title219,
						    "Shots":                  title220,
						    "Attack":                 title221,
						    "Passes":                 title222,
						    "Duels":                  title223,
						    "Defending":              title224,
						    "Goalkeeping":            title225,
						    # Match overview
						    "Ball possession":        title226,
						    "Expected goals":         title227,
						    "Big chances":            title228,
						    "Total shots":            title229,
						    "Goalkeeper saves":       title230,
						    "Corner kicks":           title231,
						    "Fouls":                  title232,
						    "Tackles":                title233,
						    "Free kicks":             title234,
						    "Yellow cards":           title235,
						    "Offsides":               title236,
						    "Distance covered":       title277,
						    "Number of sprints":      title278,
						    "Red cards":              title279,
						    # Shots
						    "Shots on target":        title237,
						    "Hit woodwork":           title238,
						    "Shots off target":       title239,
						    "Blocked shots":          title240,
						    "Shots inside box":       title241,
						    "Shots outside box":      title242,
						    # Attack
						    "Big chances scored":     title243,
						    "Big chances missed":     title244,
						    "Touches in penalty area":title245,
						    "Fouled in final third":  title246,
						    "Through balls":          title280,
						    # Passes
						    "Accurate passes":        title247,
						    "Throw-ins":              title248,
						    "Final third entries":    title249,
						    "Final third phase":      title250,
						    "Long balls":             title251,
						    "Crosses":                title252,
						    # Duels
						    "Duels":                  title253,
						    "Dispossessed":           title254,
						    "Ground duels":           title255,
						    "Aerial duels":           title256,
						    "Dribbles":               title257,
						    # Defending
						    "Tackles won":            title258,
						    "Total tackles":          title259,
						    "Interceptions":          title260,
						    "Recoveries":             title261,
						    "Clearances":             title262,
						    "Errors lead to a goal":  title267,
						    # Goalkeeping
						    "Total saves":            title263,
						    "Punches":                title264,
						    "Goal kicks":             title265,
						    "Goals prevented":        title272,
						    "High claims":            title273,
						    "Errors lead to a shot":  title274,
						    "Big saves":              title281,
						    "Penalty saves":          title282,
						}
						header_raw = group.get('groupName', '')
						header_text = str("-- " + STATS_MAP.get(header_raw, header_raw) + " --")
						res.append(MultiContentEntryText(pos=(W_LIST_X, W_LIST_Y), size=(W_LIST, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=header_text, color=0xffcc00))
						gList.append(res)
						
						for item in group.get('statisticsItems', []):
							res = []
							res.append(MultiContentEntryText()) # Anchor
							
							# Force all values to strings for Py2
							val_h = str(item.get('home', '0'))
							val_n = str(STATS_MAP.get(item.get('name', ''), item.get('name', '')))
							val_a = str(item.get('away', '0'))
							
							# Home
							res.append(MultiContentEntryText(pos=(HOME_X, HOME_Y), size=(COL_W, ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=val_h))
							# Name
							res.append(MultiContentEntryText(pos=(NAME_X, NAME_Y), size=(NAME_W, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=val_n, color=0xaaaaaa))
							# Away
							res.append(MultiContentEntryText(pos=(AWAY_X, AWAY_Y), size=(COL_W, ITEM_H), font=0, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=val_a))
							gList.append(res)
					break

		if not gList:
			res = []
			res.append(MultiContentEntryText()) # Anchor
			no_data_text = str(_("%s") % title178)
			res.append(MultiContentEntryText(pos=(W_LIST_X, W_LIST_Y), size=(W_LIST, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=no_data_text, color=0xff0000))
			gList.append(res)
		
		self["stats_list"].setList(gList)


class MatchMediaScreen(Screen):
	def __init__(self, session, event_id, match_name, home_name="", away_name=""):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_MatchMedia
		self.event_id = event_id
		self.home_name = home_name
		self.away_name = away_name
		if debug_MatchMedia: logdata("MatchMediaScreen", "Initializing MatchMediaScreen for event_id: %s, match_name: %s" % (event_id, match_name))
		self["title"] = Label(str(match_name) + " - " + title179)
		self["key_red"] = Label(_("%s") % title134)
		self["media_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)

		self["setupActions"] = ActionMap(["FootOnsatActions", "ColorActions"], {
			"cancel": self.exitAll, 
			"back": self.exitAll,
			"red": self.exitAll,
			"ok": self.playVideo,
			"up": self.up,
			"down": self.down,
			"left": self.openStats,
			"right": self.close,
		}, -1)
		# Check for ServiceApp/Exteplayer3 only if NOT using DreamOS 8193
		if config.plugins.FootOnSat.player.value != '8193':
			for p in plugins.getPlugins(where=PluginDescriptor.WHERE_MENU):
				if 'ServiceApp' in p.path and exists("/usr/bin/exteplayer3"):
					break
			else:
				config.plugins.FootOnSat.player.value = '4097'

		self.onLayoutFinish.append(self.fetch_media)

	def up(self):
		self["media_list"].up()

	def down(self):
		self["media_list"].down()

	def exitAll(self):
		self.close("exit_all")

	def openStats(self):
		clean_title = self["title"].getText().replace(" - " + title179, "")
		self.session.openWithCallback(self.navCallback, MatchStatisticsScreen, self.event_id, clean_title, self.home_name, self.away_name)

	def navCallback(self, answer=None):
		if answer == "exit_all":
			self.close("exit_all")
		else:
			self.close()

	def fetch_media(self):
		url = "https://api.sofascore.com/api/v1/event/{}/media".format(self.event_id)
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
			'Referer': 'https://www.sofascore.com/',
			'Origin': 'https://www.sofascore.com',
			'Accept': 'application/json',
			'X-Requested-With': 'XMLHttpRequest'
		}

		if PY3:
			d = getPage(str.encode(url), contextFactory=WebClientContextFactory(url), timeout=25, headers={k.encode(): [v.encode()] for k, v in headers.items()})
			d.addCallback(lambda raw: self.process_media(json.loads(raw.decode('utf-8'))))
			d.addErrback(lambda _: self.process_media(None))
		else:
			def _get():
				s = requests.Session()
				s.headers.update(headers)
				s.get('https://www.sofascore.com', timeout=10)
				r = s.get(url, timeout=25)
				return json.loads(r.content.decode('utf-8')) if r.status_code == 200 else None
			d = deferToThread(_get)
			d.addCallback(self.process_media)
			d.addErrback(lambda _: self.process_media(None))

	def process_media(self, data):
		gList = []
		if isUHD():
			ITEM_H = 100             # Row Height: Increase to add space between rows
			FONT_S = 50              # Font Size: Increase to make text bigger
			W_LIST = 2462            # Total width of the list box
			W_LIST_Y = 22            # Vertical Offset
			X_OFF  = 40              # Left Padding for text
			IMG_W, IMG_H = 80, 80    # info: Icon dimensions for UHD (100 is width, 100 is height)
			X_TEXT = 180             # info: Start position for text after the icon in UHD
			X_TEXT_Y = 22            # Vertical Offset
		else:
			ITEM_H = 80              # Row Height: Increase to add space between rows
			FONT_S = 36              # Font Size: Increase to make text bigger
			W_LIST = 1720            # Total width of the list box
			W_LIST_Y = 0             # Vertical Offset
			X_OFF  = 20              # Left Padding for text
			IMG_W, IMG_H = 60, 60    # info: Icon dimensions for FHD (60 is width, 60 is height)
			X_TEXT = 120             # info: Start position for text after the icon in FHD
			X_TEXT_Y = 0             # Vertical Offset

		self["media_list"].l.setItemHeight(ITEM_H)
		self["media_list"].l.setFont(0, gFont('Regular', FONT_S))
		
		path = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/")
		if isUHD():
			icon_yt = path + "youtube_iconUHD.png"
			icon_tw = path + "twitter_iconUHD.png"
			icon_vs = path + "vsports_iconUHD.png"
			icon_su = path + "superliga_iconUHD.png"
			icon_vbox7 = path + "vbox7_iconUHD.png"
			icon_sf = path + "sofascore_iconUHD.png"
		else:
			icon_yt = path + "youtube_icon.png"
			icon_tw = path + "twitter_icon.png"
			icon_vs = path + "vsports_icon.png"
			icon_su = path + "superliga_icon.png"
			icon_vbox7 = path + "vbox7_icon.png"
			icon_sf = path + "sofascore_icon.png"

		if data and 'media' in data:
			for item in data['media']:
				v_url = item.get('url', '')
				if not v_url: continue
				v_url = str(v_url)
				title = str(item.get('title', 'Video'))
				subtitle = item.get('subtitle')
				display_text = title + " (" + str(subtitle) + ")" if subtitle else title
				
				res = [v_url]
				res.append(MultiContentEntryText()) # Anchor
				
				# info: Check URL for Youtube or Twitter to assign correct icon
				icon_path = None
				if "youtube.com" in v_url.lower() or "youtu.be" in v_url.lower():
					icon_path = icon_yt
				elif "twitter.com" in v_url.lower() or "x.com" in v_url.lower():
					icon_path = icon_tw
				elif "vsports.pt" in v_url.lower():
					icon_path = icon_vs
				elif "vbox7.com" in v_url.lower():
					icon_path = icon_vbox7
				elif "sofascore.com" in v_url.lower():
					icon_path = icon_sf
				elif "superliga.dk" in v_url.lower():
					#icon_path = icon_su # Need to fix later
					continue
				elif "fifa.com" in v_url.lower():
					continue
				else:
					continue

				if icon_path and exists(icon_path):
					# info: Use LoadPixmap with size to force auto-scaling of the PNG file
					ptr = loadPNG(icon_path)
					if ptr:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(X_OFF, (ITEM_H - IMG_H)//2), size=(IMG_W, IMG_H), png=ptr))

				# info: Draw the video title text after the fixed icon position
				res.append(MultiContentEntryText(pos=(X_TEXT, X_TEXT_Y), size=(W_LIST - X_TEXT, ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_text))
				gList.append(res)

		if not gList:
			res = [None, MultiContentEntryText()]
			err_msg = str(_("%s") % title180)
			res.append(MultiContentEntryText(pos=(0, W_LIST_Y), size=(W_LIST, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=err_msg, color=0xff0000))
			gList.append(res)
		
		self["media_list"].setList(gList)

	def playVideo(self):
		cur = self["media_list"].getCurrent()
		if not cur or not cur[0]:
			return
		url = cur[0].strip()
		if debug_MatchMedia: logdata("MatchMedia", "Processing URL: %s" % str(url))
		self.play_timer_conn = None
		self.error_timer_conn = None
		url_lower = str(url).lower()
		is_youtube = "youtube.com" in url_lower or "youtu.be" in url_lower
		is_twitter = "twitter.com" in url_lower or "x.com" in url_lower
		is_vsports = "vsports.pt" in url_lower
		is_superliga = "superliga.dk" in url_lower
		is_vbox7 = "vbox7.com" in url_lower
		is_sofascore = "sofascore.com/video-player.html" in url_lower
		if is_youtube:
			if debug_MatchMedia: logdata("MatchMedia-YOUTUBE", "Start Play: %s" % url)
			pass
		if is_twitter:
			if debug_MatchMedia: logdata("MatchMedia-TWITTER", "Start Play: %s" % url)
			pass
		if is_vsports:
			if debug_MatchMedia: logdata("MatchMedia-VSPORTS", "Start Play: %s" % url)
			pass
		if is_superliga:
			if debug_MatchMedia: logdata("MatchMedia-superliga", "Start Play: %s" % url)
			pass
		if is_vbox7:
			if debug_MatchMedia: logdata("MatchMedia-vbox7", "Start Play: %s" % url)
			pass
		if is_sofascore:
			if debug_MatchMedia: logdata("MatchMedia-SOFASCORE", "Start Play: %s" % url)
			pass
		msg = _("%s") % title181
		if is_youtube:
			self.wait_dialog = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, enable_input=False)
			def safe_extract(video_url):
				try:
					v_id = video_url
					if 'watch?v=' in v_id: v_id = v_id.split('watch?v=')[-1]
					elif 'youtu.be/' in v_id: v_id = v_id.split('youtu.be/')[-1]
					if '?' in v_id: v_id = v_id.split('?')[0]
					if '&' in v_id: v_id = v_id.split('&')[0]
					ytdl = YouTubeVideoUrl()
					result = ytdl.extract(v_id)
					return str(result) if result else ""
				except Exception as e:
					err_text = str(e)
					#if debug_MatchMedia: logdata("EXTRACT_ERROR_THREAD_FUNC", err_text)
					return "ERROR:" + err_text
			deferToThread(safe_extract, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		elif is_twitter:
			self.wait_dialog = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, enable_input=False)
			deferToThread(self.extract_twitter_stream, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		elif is_vsports:
			self.wait_dialog = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, enable_input=False)
			deferToThread(self.extract_vsports_stream, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		elif is_superliga:
			self.wait_dialog = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, enable_input=False)
			deferToThread(self.extract_superliga_stream, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		elif is_vbox7:
			self.wait_dialog = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, enable_input=False)
			deferToThread(self.extract_vbox7_stream, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		elif is_sofascore:
			self.wait_dialog = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, enable_input=False)
			deferToThread(self.extract_sofascore_stream, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		else:
			#self.playAfterExtract(str(url))
			# Fallback for unsupported URLs
			if debug_MatchMedia: logdata("MatchMedia", "Unsupported URL/Video: %s" % str(url))
			msg = _("%s") % title182
			self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=10)

	def playAfterExtract(self, video_url):
		stb_model = getSTBModel()
		video_url = video_url or ""
		if hasattr(self, 'wait_dialog') and self.wait_dialog:
			self.wait_dialog.close()
		video_url_str = str(video_url)
		if "ERROR:" in video_url_str:
			err_msg = video_url_str.split("ERROR:", 1)[1].lstrip()
			lower_err = err_msg.lower()
			if debug_MatchMedia: logdata("MatchMedia", "playAfterExtract_lower: %s" % lower_err)
			if "country" in lower_err or "not available" in lower_err:
				if debug_MatchMedia: logdata("MatchMedia", "Geo-restriction error (all client retries exhausted): %s" % err_msg)
				msg = _("%s") % title183
				self.error_timer = eTimer()
				if DreamOS():
					self.error_timer_conn = self.error_timer.timeout.connect(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
				else:
					self.error_timer.callback.append(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
				self.error_timer.start(250, True)
				return
		if not video_url_str.startswith("http"):
			msg = _("%s") % title184
			self.error_timer = eTimer()
			if DreamOS():
				self.error_timer_conn = self.error_timer.timeout.connect(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
			else:
				self.error_timer.callback.append(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
			self.error_timer.start(250, True)
			return
		pure_url = video_url
		user_agent = None
		if "#http_user_agent=" in video_url:
			pure_url, user_agent = video_url.split("#http_user_agent=", 1)
			if "&Referer=" in user_agent:
				user_agent = user_agent.split("&Referer=")[0]
		is_yt = "youtube.com" in pure_url.lower() or "youtu.be" in pure_url.lower() or "googlevideo.com" in pure_url.lower()
		stype = int(config.plugins.FootOnSat.player.value)
		has_exteplayer = exists("/usr/bin/exteplayer3")
		if is_yt and config.plugins.FootOnSat.useDashMP4.value and (not has_exteplayer or stype == 4097):
			if debug_MatchMedia: logdata("MatchMedia", "Full video_url: %s" % str(video_url))
			separator = '#EXT-X-STREAM-INF:AUDIO=' if '#EXT-X-STREAM-INF:AUDIO=' in video_url else SUBURI
			if separator in video_url:
				if debug_MatchMedia: logdata("MatchMedia", "DASH: separate audio found. Starting real-time mux...")
				self.dash_fifo = None
				try:
					v_url = video_url.split(separator)[0]
					if "#http_user_agent=" in v_url: v_url = v_url.split("#http_user_agent=")[0]
					a_url = video_url.split(separator)[-1].replace('"', '').strip()
					if "#http_user_agent=" in a_url: a_url = a_url.split("#http_user_agent=")[0]
					ua = str(user_agent) if user_agent else "Mozilla/5.0"
					fifo = "/tmp/yt_dash.ts"
					try:
						if exists(fifo): os.remove(fifo)
						self.dash_fifo = fifo
					except Exception as fe:
						if debug_MatchMedia: logdata("MatchMedia", "FIFO cleanup error: %s" % str(fe))
					if self.dash_fifo:
						ffmpeg_bin = "/usr/bin/ffmpeg"
						ffmpeg_has_ssl = False
						if config.plugins.FootOnSat.playmethod.value == "1":
							try:
								proto_out = subprocess.Popen([ffmpeg_bin, '-protocols'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
								ffmpeg_has_ssl = b'https' in proto_out[0] + proto_out[1]
							except: pass
							if ffmpeg_has_ssl:
								mux_cmd = (
									'%(ff)s -y -hide_banner -loglevel error '
									'-user_agent "%(ua)s" -headers "Referer: https://www.youtube.com/\r\n" '
									'-i "%(v)s" '
									'-user_agent "%(ua)s" -headers "Referer: https://www.youtube.com/\r\n" '
									'-i "%(a)s" '
									'-c copy -f mpegts "%(fifo)s"'
								) % {'ff': ffmpeg_bin, 'ua': ua, 'v': v_url, 'a': a_url, 'fifo': fifo}
							else:
								mux_cmd = (
									'rm -f /tmp/yt_v.fifo /tmp/yt_a.fifo /tmp/yt_dash.ts; '
									'mkfifo /tmp/yt_v.fifo /tmp/yt_a.fifo; '
									'curl -k -g -L -N --user-agent "%(ua)s" -o /tmp/yt_v.fifo "%(v)s" & '
									'curl -k -g -L -N --user-agent "%(ua)s" -o /tmp/yt_a.fifo "%(a)s" & '
									'%(ff)s -y -f mov -i /tmp/yt_v.fifo -f mov -i /tmp/yt_a.fifo '
									'-map 0:v -map 1:a -c:v copy -c:a mp2 -b:a 192k -ar 48000 '
									'-fflags +genpts+nobuffer -f mpegts "%(fifo)s"; '
									'rm -f /tmp/yt_v.fifo /tmp/yt_a.fifo'
								) % {'ff': ffmpeg_bin, 'ua': ua, 'v': v_url, 'a': a_url, 'fifo': fifo}
						else:
							try: os.mkfifo(fifo)
							except: pass
							if debug_MatchMedia: logdata("MatchMedia", "STB Model detected: %s" % stb_model)
							if stb_model in ["one", "two"]:
								if debug_MatchMedia: logdata("MatchMedia", "Using DreamOS Gst-DASH Muxing")
								mux_cmd = (
									'gst-launch-1.0 -q mpegtsmux name=mux ! filesink location="%(fifo)s" '
									'souphttpsrc location="%(v)s" user-agent="com.google.android.youtube/17.31.35 (Linux; U; Android 11) gzip" ! qtdemux name=vdemux vdemux.video_0 ! h264parse ! queue ! mux. '
									'souphttpsrc location="%(a)s" user-agent="com.google.android.youtube/17.31.35 (Linux; U; Android 11) gzip" ! qtdemux name=ademux ademux.audio_0 ! aacparse ! queue ! mux.'
								) % {'v': v_url, 'a': a_url, 'fifo': fifo}
							else:
								if debug_MatchMedia: logdata("MatchMedia", "Using Standard Gst-DASH Muxing")
								mux_cmd = (
									'gst-launch-1.0 -q mpegtsmux name=mux ! filesink location="%(fifo)s" '
									'souphttpsrc location="%(v)s" user-agent="%(ua)s" ! qtdemux ! h264parse ! queue ! mux. '
									'souphttpsrc location="%(a)s" user-agent="%(ua)s" ! qtdemux ! aacparse ! queue ! mux.'
								) % {'ua': ua, 'v': v_url, 'a': a_url, 'fifo': fifo}
						if debug_MatchMedia: logdata("MatchMedia", "DASH mux cmd: %s" % mux_cmd)
						self.dash_process = subprocess.Popen(mux_cmd, shell=True, preexec_fn=os.setsid)
						if config.plugins.FootOnSat.playmethod.value == "1":
							if stb_model in ["one", "two"]:
								time.sleep(1.5)
								for i in range(250):
									if exists(fifo) and os.path.getsize(fifo) > 300000:
										break
									time.sleep(0.5)
								if exists(fifo) and os.path.getsize(fifo) < 150000:
									time.sleep(1)
								stype = 1
								if hasattr(self, 'wait_dialog') and self.wait_dialog:
									self.wait_dialog.close()
									self.wait_dialog = None
								if hasattr(self, 'error_timer') and self.error_timer:
									self.error_timer.stop()
							else:
								time.sleep(8)
						else:
							if stb_model in ["one", "two"]:
								time.sleep(3)
							for i in range(20):
								if exists(fifo): break
								time.sleep(0.05)
						pure_url = fifo
						user_agent = None
						if debug_MatchMedia: logdata("MatchMedia", "DASH mux started. Source: %s" % fifo)
					else:
						if debug_MatchMedia: logdata("MatchMedia", "DASH FIFO unavailable, video-only fallback.")
						pure_url = v_url
				except Exception as e:
					if debug_MatchMedia: logdata("MatchMedia", "DASH mux setup error: %s" % str(e))
					self.dash_fifo = None
		if pure_url.startswith("http"):
			try:
				req = compat_Request(pure_url)
				if user_agent: req.add_header("User-Agent", user_agent)
				req.add_header("Referer", "https://www.youtube.com/")
				req.add_header("Range", "bytes=0-1")
				resp = compat_urlopen(req, timeout=10)
				code = getattr(resp, "getcode", lambda: 200)()
				if code not in (200, 206): raise Exception("HTTP_%s" % code)
			except Exception as e:
				if "403" not in str(e):
					self.session.open(MessageBox, title184, MessageBox.TYPE_ERROR, timeout=10)
					return
		name = str(self["title"].getText())
		ref_str = "%d:0:1:0:0:0:0:0:0:0::%s" % (stype, compat_quote(name))
		ref = eServiceReference(ref_str)
		if user_agent:
			if DreamOS():
				# DreamOS often needs the pure URL + User-Agent separately
				ref.setPath(str(pure_url))
				ref.setData(0, str(user_agent))
			else:
				ref.setPath(str(video_url))
		else:
			ref.setPath(str(pure_url))
		ref.setName(name)
		self.play_timer = eTimer()
		if debug_MatchMedia: logdata("MatchMedia", "pure_url: %s" % str(pure_url))
		if debug_MatchMedia: logdata("MatchMedia", "SREF: %s" % ref.toString())
		if DreamOS():
			self.play_timer_conn = self.play_timer.timeout.connect(lambda: self.session.open(CustomMediaPlayer, ref, self))
		else:
			self.play_timer.callback.append(lambda: self.session.open(CustomMediaPlayer, ref, self))
		self.play_timer.start(200, True)

	def stopDashAudio(self, *args):
		if hasattr(self, 'dash_process') and self.dash_process:
			try:
				os.killpg(os.getpgid(self.dash_process.pid), signal.SIGTERM)
				if debug_MatchMedia: logdata("MatchMedia", "DASH mux process killed.")
			except:
				pass
			try:
				del self.dash_process
			except:
				pass
		fifo = getattr(self, 'dash_fifo', None)
		if fifo:
			try:
				if exists(fifo): os.remove(fifo)
				if debug_MatchMedia: logdata("MatchMedia", "DASH FIFO removed: %s" % fifo)
			except:
				pass
			self.dash_fifo = None
		# info: Clean up all temporary files and the new FIFOs
		for f in ("/tmp/yt_v.fifo", "/tmp/yt_a.fifo", "/tmp/yt_v.mp4", "/tmp/yt_a.mp4", "/tmp/a.mp4", "/tmp/yt_dash.ts"):
			if exists(f):
				try: os.remove(f)
				except: pass

	def extract_sofascore_stream(self, url):
		try:
			from urllib.parse import unquote
			if "sofascore.com/video-player.html?url=" in url:
				stream_url = unquote(url.split("url=")[1])
				return str(stream_url)
		except Exception as e:
			if debug_MatchMedia: logdata("MatchMedia", "Sofascore Error: %s" % str(e))
		return None

	def extract_superliga_stream(self, url):
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
			'Referer': 'https://superliga.dk/',
		}
		if debug_MatchMedia: logdata("MatchMedia", "Superliga: Starting extraction for %s" % url)
		r = requests.get(url, headers=headers, timeout=15, verify=False)
		if debug_MatchMedia: logdata("MatchMedia", "Superliga: Main page status: %s | Size: %s" % (r.status_code, len(r.text)))
		if r.status_code != 200: return None
		content = r.text
		event_id = None
		# Expanded patterns based on web debug fetch logs (looking for eventId=5222360)
		patterns = [
			r'eventId=(\d+)',
			r'eventId["\']?\s*[:=]\s*["\']?(\d+)',
			r'["\']match["\']\s*:\s*\{\s*["\']id["\']\s*:\s*(\d+)',
			r'["\']matchId["\']\s*:\s*(\d+)',
			r'["\']id["\']\s*:\s*(\d+)\s*,\s*["\']slug["\']\s*:\s*["\']' + url.split('/')[-1],
			r'/events/(\d+)',
			r'data-event-id=["\'](\d+)'
		]
		for pattern in patterns:
			m_ev = re.search(pattern, content)
			if m_ev:
				event_id = m_ev.group(1)
				if debug_MatchMedia: logdata("MatchMedia", "Superliga: Found EventID via pattern [%s]: %s" % (pattern, event_id))
				break
		if not event_id:
			m_id = re.search(r'["\']id["\']\s*:\s*(\d{6,10})', content)
			if m_id:
				event_id = m_id.group(1)
				if debug_MatchMedia: logdata("MatchMedia", "Superliga: Fallback Found generic ID: %s" % event_id)
		if debug_MatchMedia: logdata("MatchMedia", "Superliga: Final EventID: %s" % event_id)
		if not event_id:
			if debug_MatchMedia: logdata("MatchMedia", "Superliga: CONTENT SNIPPET: %s" % content[:1500].replace('\n', ' '))
			return None
		partner_id = "4215093"
		uiconf_id = "56081452"
		m_partner = re.search(r'partnerId["\']?\s*[:=]\s*["\']?(\d+)', content)
		if m_partner:
			partner_id = m_partner.group(1)
			if debug_MatchMedia: logdata("MatchMedia", "Superliga: Found PartnerID: %s" % partner_id)
		m_uiconf = re.search(r'uiconf_id/(\d+)', content)
		if not m_uiconf: m_uiconf = re.search(r'uiConfId["\']?\s*[:=]\s*["\']?(\d+)', content)
		if m_uiconf:
			uiconf_id = m_uiconf.group(1)
			if debug_MatchMedia: logdata("MatchMedia", "Superliga: Found UIConfID: %s" % uiconf_id)
		token = "5b6ab6f5eb84c60031bbbd24"
		api_url = "https://api.superliga.dk/highlights?appName=superligadk&access_token=%s&env=production&eventId=%s&source=kaltura" % (token, event_id)
		if debug_MatchMedia: logdata("MatchMedia", "Superliga: Calling Highlights API: %s" % api_url)
		ra = requests.get(api_url, headers=headers, timeout=10, verify=False)
		entry_id = None
		if ra.status_code == 200:
			data = ra.json()
			if debug_MatchMedia: logdata("MatchMedia", "Superliga: API Response Data: %s" % str(data)[:300])
			if isinstance(data, list) and len(data) > 0:
				entry_id = data[0].get('externalId') or data[0].get('entryId')
		if not entry_id:
			if debug_MatchMedia: logdata("MatchMedia", "Superliga: API fail/empty, scanning content for entry_id")
			m_kal = re.search(r'kaltura/(\w{1,2}_\w+)', content)
			if not m_kal: m_kal = re.search(r'entry_id["\']?\s*[:=]\s*["\']?(\w{1,2}_\w+)', content)
			if m_kal: entry_id = m_kal.group(1)
		if debug_MatchMedia: logdata("MatchMedia", "Superliga: Final EntryID: %s" % entry_id)
		if not entry_id: return None
		# Building standard HLS manifest URL which serves the .ts segments
		manifest_url = "https://cdnapisec.kaltura.com/p/%s/sp/%s00/playManifest/entryId/%s/protocol/https/format/applehttp/a.m3u8?uiConfId=%s" % (partner_id, partner_id, entry_id, uiconf_id)
		if debug_MatchMedia: logdata("MatchMedia", "Superliga: Final URL: %s" % manifest_url)
		return str(manifest_url)

	def extract_vbox7_stream(self, url):
		try:
			headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
				'Referer': 'https://www.vbox7.com/',
			}
			if debug_MatchMedia: logdata("MatchMedia", "Vbox7: Processing %s" % url)
			v_id = url.split(':')[-1].split('?')[0]
			api_url = "https://www.vbox7.com/aj/player/item/options?vid=%s" % v_id
			r = requests.get(api_url, headers=headers, timeout=10, verify=False)
			if r.status_code == 200:
				res = r.json()
				options = res.get('options', {})
				hls_api = "https://www.vbox7.com/aj/player/item/options?vid=%s&device=ios" % v_id
				rh = requests.get(hls_api, headers=headers, timeout=10, verify=False)
				if rh.status_code == 200:
					hls_res = rh.json()
					hls_url = hls_res.get('options', {}).get('src', '')
					if hls_url:
						final = hls_url.replace('\\/', '/')
						if final.startswith('//'): final = 'https:' + final
						if '.mpd' in final:
							final = final.replace('.mpd', '.m3u8')
						# Try to find separate audio track in the m3u8 manifest
						try:
							rm = requests.get(final, headers=headers, timeout=10, verify=False)
							if rm.status_code == 200:
								manifest = rm.text
								# Look for EXT-X-MEDIA audio URI
								m_audio = re.search(r'#EXT-X-MEDIA:.*?TYPE=AUDIO.*?URI="([^"]+)"', manifest, re.DOTALL)
								if m_audio:
									audio_uri = m_audio.group(1)
									base_url = final.rsplit('/', 1)[0] + '/'
									if not audio_uri.startswith('http'):
										audio_uri = base_url + audio_uri
									if debug_MatchMedia: logdata("MatchMedia", "Vbox7: Found audio track: %s" % audio_uri)
									final = final + SUBURI + audio_uri
								else:
									# Fallback: try track2 pattern from URL
									base = final.rsplit('/', 1)[0] + '/'
									v_id_part = v_id
									audio_url = base + v_id_part + '_audio.m3u8'
									# Try common vbox7 audio track naming
									for suffix in ['_track2.m3u8', '_audio.m3u8', '_2.m3u8']:
										test_url = base + v_id_part + suffix
										rt = requests.get(test_url, headers=headers, timeout=5, verify=False)
										if rt.status_code == 200:
											if debug_MatchMedia: logdata("MatchMedia", "Vbox7: Found audio fallback: %s" % test_url)
											final = final + SUBURI + test_url
											break
						except Exception as ae:
							if debug_MatchMedia: logdata("MatchMedia", "Vbox7: Audio extract error: %s" % str(ae))
						if debug_MatchMedia: logdata("MatchMedia", "Vbox7: Found Master HLS: %s" % final)
						return final
				stream = options.get('src', '')
				if stream:
					final = stream.replace('\\/', '/')
					if final.startswith('//'): final = 'https:' + final
					if debug_MatchMedia: logdata("MatchMedia", "Vbox7: Found Direct Stream: %s" % final)
					return final
			r_page = requests.get(url, headers=headers, timeout=10, verify=False)
			content = r_page.text
			m_src = re.search(r'video_src["\']?\s*[:=]\s*["\']([^"\']+)["\']', content)
			if m_src:
				final = m_src.group(1).replace('\\/', '/')
				if final.startswith('//'): final = 'https:' + final
				return final
			if debug_MatchMedia: logdata("MatchMedia", "Vbox7: No stream found")
			return None
		except Exception as e:
			if debug_MatchMedia: logdata("MatchMedia", "Vbox7 Error: %s" % str(e))
			return None

	def extract_vsports_stream(self, url):
		try:
			headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Referer': 'https://vsports.pt/'}
			r = requests.get(url, headers=headers, timeout=15, verify=False)
			if r.status_code == 200:
				content = r.content.decode('utf-8', 'ignore')
				match = re.search(r'https://vsports.pt/[^/]+/embd/([^"\'>\s?]+)', content)
				if match:
					embed_url = match.group(0)
					r_emb = requests.get(embed_url, headers=headers, timeout=15, verify=False)
					if r_emb.status_code == 200:
						emb_content = r_emb.content.decode('utf-8', 'ignore')
						sources = re.findall(r'(https?://[^"\']+\.(?:mp4|m3u8)(?:\?[^"\']+)?)', emb_content)
						if sources:
							res_tag = str(config.plugins.FootOnSat.maxResolution.value)
							res_keywords = {'37': '1080', '22': '720', '35': '480', '18': '360'}
							target = res_keywords.get(res_tag, '720')
							for s in sources:
								if target in s: return str(s)
							return str(sources[0])
			return None
		except Exception as e:
			if debug_MatchMedia: logdata("MatchMedia", "Exception: %s" % str(e))
			return None

	def extract_twitter_stream(self, url):
		try:
			import urllib3
			urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
		except: pass
		try:
			t_id = url.split('/')[-1].split('?')[0]
			api_url = "https://api.fxtwitter.com/i/status/%s" % t_id
			if debug_MatchMedia: logdata("MatchMedia", "API URL: %s" % api_url)
			headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
			r = requests.get(api_url, headers=headers, timeout=15, verify=False)
			if debug_MatchMedia: logdata("MatchMedia", "Status Code: %d" % r.status_code)
			if r.status_code == 200:
				data = r.json()
				tweet = data.get('tweet', {})
				media = tweet.get('media', {})
				videos = media.get('videos', [])
				if videos:
					res_map = {'38': 4096, '37': 1920, '22': 1280, '35': 854, '18': 640, '5': 400, '17': 176}
					target_width = res_map.get(config.plugins.FootOnSat.maxResolution.value, 1280)
					best_link = videos[0].get('url')
					current_best_diff = float('inf')
					for v in videos:
						v_url, v_width = v.get('url'), v.get('width', 0)
						if v_width <= target_width:
							diff = target_width - v_width
							if diff < current_best_diff:
								current_best_diff, best_link = diff, v_url
					if debug_MatchMedia: logdata("MatchMedia", "Stream Found: %s" % str(best_link))
					if not isinstance(best_link, str):
						best_link = best_link.encode('utf-8')
					return best_link
				else:
					if debug_MatchMedia: logdata("MatchMedia", "No videos in media")
			return None
		except Exception as e:
			if debug_MatchMedia: logdata("MatchMedia", "Exception: %s" % str(e))
			return None

	def playback_error(self, failure):
		if hasattr(self, 'wait_dialog') and self.wait_dialog:
			self.wait_dialog.close()
		if debug_MatchMedia: logdata("MatchMedia", "playback_error_raw : %s" % str(failure))
		msg = _("%s") % title184
		self.error_timer = eTimer()
		if DreamOS():
			self.error_timer_conn = self.error_timer.timeout.connect(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
		else:
			self.error_timer.callback.append(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
		self.error_timer.start(250, True)


class CustomMediaPlayer(MoviePlayer):
	def __init__(self, session, service, parent):
		MoviePlayer.__init__(self, session, service)
		self.skinName = ['CustomMediaPlayer', 'MoviePlayer']
		self.parent_screen = parent
		self.service = service
		self['actions'] = ActionMap(['ColorActions',
			'SetupActions', 'DirectionActions', 'MovieSelectionActions', 'MediaPlayerActions'],
			{
				'red': self.leavePlayer,
				'cancel': self.leavePlayer,
				'stop': self.leavePlayer
			}, -1)
		
	def leavePlayer(self):
		if debug_MatchMedia: logdata("MatchMedia", "CustomMediaPlayer: leavePlayer")
		self.close()
	
	def leavePlayerOnExit(self):
		if debug_MatchMedia: logdata("MatchMedia", "CustomMediaPlayer: leavePlayerOnExit")
		self.close()
	
	def doEofInternal(self, playing):
		if debug_MatchMedia: logdata("MatchMedia", "CustomMediaPlayer: doEofInternal")
		self.close()

	def close(self):
		if debug_MatchMedia: logdata("MatchMedia", "CustomMediaPlayer: close - cleanup")
		clist = [(_('Yes, and Close'), 'quit')]
		self.session.openWithCallback(self.callbackClose, ChoiceBox, title=_('Stop playing this movie?'), list=clist)

	def callbackClose(self, answer):
		answer = answer and answer[1]
		if debug_MatchMedia: logdata("MatchMedia", "CustomMediaPlayer: callbackClose answer=%s" % str(answer))
		if answer == 'quit':
			self.parent_screen.stopDashAudio()
			MoviePlayer.close(self)


class StandingsScreen(Screen):
	def __init__(self, session, league, url):
		self.session = session
		Screen.__init__(self, session)
		if debug_Standings: logdata("StandingsScreen_init", "Initializing StandingsScreen for league: %s, url: %s" % (league, url))
		self.league = str(league)
		self.url = str(url)
		self.league = str(league).lower()
		if self.league in ("basketball", "nba", "nfl"):
			label_text = "Ties" if self.league in ("nfl") else "Streak"
			self.skin = SKIN_standingsbasketball % label_text
		else:
			self.skin = SKIN_standings
		self["standings_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		# FIX for Python 2 eLabel: encode to UTF-8 if not Python 3
		title_text = "%s %s" % (self.league, title185)
		if not PY3:
			title_text = title_text.encode('utf-8')
		self["title"] = Label(_(title_text))
		self["key_red"] = Button(_("%s") % title186)
		self["setupActions"] = ActionMap(["OkCancelActions", "ColorActions"], {
			"ok": self.close,
			"cancel": self.close,
			"red": self.close
		}, -1)
		self.standings_data = []
		self.logo_cache = {}
		self.flags_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/")
		
		# Define standard headers for both fetching and logo downloading
		self.headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
			"Accept": "application/json, text/plain, */*",
			"Accept-Language": "en-US,en;q=0.9",
			"Accept-Encoding": "gzip, deflate, br",
			"Connection": "keep-alive",
			"Referer": "https://www.sofascore.com/",
			"Origin": "https://www.sofascore.com",
			"X-Requested-With": "XMLHttpRequest",
			"If-None-Match": 'W/"00000000000000000000000000000000-gn"',
			"Sec-Fetch-Dest": "empty",
			"Sec-Fetch-Mode": "cors",
			"Sec-Fetch-Site": "same-site", # same-site for API calls to different subdomain
			"Cache-Control": "max-age=0",
			# Optional: Sec-Ch-Ua-* headers are typically not mandatory but can be added if issues persist
			# "Sec-Ch-Ua-Mobile": "?0", 
		}
		self.headers2 = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0", # <-- New User-Agent
			"Accept-Language": "en-US,en;q=0.5",
			"Connection": "keep-alive",
			# You should set this to 'https://api.sofascore.com' or remove it entirely
			"Referer": "https://api.sofascore.com/", 
			"Cache-Control": "max-age=0",
		}
		
		# Use onShown to trigger the fetch process
		self.onShown.append(self.fetch_standings)

	def fetch_standings (self):
		# 1. Start parsing the URL to get IDs
		url_to_parse = self.url
		if not isinstance(url_to_parse, compat_str):
			url_to_parse = str(url_to_parse)

		parsed_url = compat_urlparse(url_to_parse)
		path_parts = [p for p in parsed_url.path.split('/') if p]

		tournament_id = None
		season_id = None
		
		try:
			# Tournament ID is the number at the end of the URL path (e.g., '7')
			if path_parts and path_parts[-1].isdigit():
				tournament_id = path_parts[-1]
				
			# Season ID is the number after '#id:' in the fragment (e.g., '76953')
			if parsed_url.fragment and parsed_url.fragment.startswith('id:'):
				season_id = parsed_url.fragment.split(':')[-1]
			
		except Exception as e:
			if debug_Standings: logdata("StandingsScreen", "ERROR during URL parsing: %s" % str(e))
			pass
			#trace_error()
			
		if not tournament_id or not season_id or not tournament_id.isdigit() or not season_id.isdigit():
			if debug_Standings: logdata("StandingsScreen", "CRITICAL ERROR: Failed to extract numeric IDs. T-ID:'%s', S-ID:'%s'." % (tournament_id, season_id))
			self.standings_data = []
			self.display_standings()
			return

		# 2. Construct the JSON API URL
		api_url = "https://api.sofascore.com/api/v1/unique-tournament/{}/season/{}/standings/total".format(
			tournament_id, season_id
		)
			
		if debug_Standings: logdata("StandingsScreen", "Using SofaScore API URL: %s" % api_url)
		AGENT = b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'

		# =================================================================
		# === PY3/PY2 SPLIT: Only necessary structural change to fix Py2 ===
		# =================================================================
		
		if PY3:
			try:
				sniFactory = WebClientContextFactory(api_url)
			except Exception as e:
				if debug_Standings: logdata("StandingsScreen", "Failed to create WebClientContextFactory: %s" % str(e))
				self.display_standings()
				return

			# DEBUG: Log the attempt
			if debug_Standings: logdata("StandingsScreen", "Attempting fetch (Twisted/SNI FIX) for API: %s" % api_url)

			# Fetch using Twisted's getPage
			# Add headers for robust 403 prevention (Cloudflare challenge)
			headers = {
				b'User-Agent': [AGENT],
				b'Accept': [b'application/json, text/plain, */*'],
				b'Accept-Language': [b'en-US,en;q=0.9'],
				b'Connection': [b'close'],
				b'Referer': [b'https://www.sofascore.com/'],
				b'Origin': [b'https://www.sofascore.com'],
				b'Cache-Control': [b'no-cache'],
			}

			d = getPage(
				str.encode(api_url),
				contextFactory=sniFactory,
				timeout=10,
				headers=headers
			)

		else:
			# === Python 2 (Requests/deferToThread Logic for 403 bypass) ===
			try:
				from twisted.internet.threads import deferToThread
				import requests
			except ImportError as e:
				if debug_Standings: logdata("StandingsScreen", "CRITICAL ERROR: Py2 requirements missing: %s" % str(e))
				self.display_standings()
				return None

			if debug_Standings: logdata("StandingsScreen", "Attempting fetch (Py2 Requests FIX) for API: %s" % api_url)
			
			headers2 = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
				'Referer': 'https://www.sofascore.com/',
				'Origin': 'https://www.sofascore.com',
				'Accept': 'application/json'
			}

			def _fetch_with_requests_py2():
				try:
					s = requests.Session()
					s.headers.update(headers2)
					s.get('https://www.sofascore.com')
					r = s.get(api_url, timeout=10)
					if r.status_code == 403:
						s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
						r = s.get(api_url, timeout=10)
					r.raise_for_status()
					return r.content 
				except Exception as e:
					if debug_Standings: logdata("StandingsScreen", "Python 2 Requests fetch failed: %s" % str(e))
					raise Exception("SofaScore fetch failed: %s" % str(e))

			d = deferToThread(_fetch_with_requests_py2)

		# === Wire the callbacks (Shared for both PY3 and PY2 deferred 'd') ===
		d.addCallback(self._parse_standings_data)
		d.addErrback(self._standing_error_handler, api_url)
		
	def _parse_standings_data(self, raw_json_content):
		standings = []
		api_url = locals().get('api_url', 'N/A')
		
		try:
			# Decode and parse JSON (raw_json_content is bytes from getPage)
			json_data = raw_json_content.decode('utf-8', errors='ignore')
			data = json.loads(json_data)

			if 'standings' not in data or not data['standings']:
				if debug_Standings: logdata("StandingsScreen", "No 'standings' data found in JSON response.")
				self.standings_data = []
				self.display_standings()
				return

			# 4. Extract and process standings data from JSON
			for table in data['standings']:
				
				# Handle Group/Table names (CRITICAL FIX for separation)
				if 'name' in table and table['name']:
					title = "Table %s" % table['name']
					if not PY3:
						title = title.encode('utf-8')
					standings.append(title)
				elif 'groupName' in table and table['groupName']:
					title = "Table %s" % table['groupName']
					if not PY3:
						title = title.encode('utf-8')
					standings.append(title)
		
				if 'rows' not in table:
					continue
					
				for row in table['rows']:
					team_data = row.get('team', {})
					team_name = team_data.get('name', 'Unknown Team')
					team_id = team_data.get('id')
					try:
						logo_url = "http://api.sofascore.com/api/v1/team/{}/image".format(team_id) if team_id else ""
					except Exception as e:
						logo_url = "https://api.sofascore.com/api/v1/team/{}/image".format(team_id) if team_id else ""
					# Extract all required stats directly from the 'row' dictionary
					position = str(row.get('position', 0))
					played = str(row.get('matches', 0))
					wins = str(row.get('wins', 0))
					losses = str(row.get('losses', 0))
					if self.league not in ("basketball", "nba"):
						draws = str(row.get('draws', 0)) if self.league not in ("hockey") else str(row.get('overtimeLosses', 0))
						points = str(row.get('points', 0))
						goals_scored = str(row.get('scoresFor', 0))
						goals_conceded = str(row.get('scoresAgainst', 0))
						goal_diff = str(row.get('scoreDiffFormatted', 0))
					if self.league in ("basketball", "nba", "nfl"):
						# Calculate streak
						streak_val = row.get('streak', 0)
						if isinstance(streak_val, int):
							if streak_val > 0:
								streak = "W%d" % streak_val
							elif streak_val < 0:
								streak = "L%d" % abs(streak_val)
							else:
								streak = "-"
						else:
							streak = str(streak_val) if streak_val else "-"
						if self.league in ("nfl"):
							streak = str(row.get('draws', 0))
						points_for = row.get('scoresFor', 0)
						points_against = row.get('scoresAgainst', 0)
						diff = str(points_for - points_against)
						if played and int(played) > 0:
							pct = "%.3f" % (float(wins) / float(played))
						else:
							pct = ".000"
						standings.append([
							team_name,
							position,
							played,
							wins,
							losses,
							streak,
							diff,
							pct,
							"",
							"",
							logo_url
							])
					else:
						standings.append([
							team_name,
							position,
							played,
							points,
							wins,
							draws,
							losses,
							goals_scored,
							goals_conceded,
							goal_diff,
							logo_url
							])

			self.standings_data = standings
			
			if standings:
				# Call logo download asynchronously and display when done
				deferToThread(self.check_and_download_logos).addCallback(lambda x: self.display_standings())
				return

			self.display_standings()

		except Exception as e:
			if debug_Standings: logdata("StandingsScreen", "Failed to parse JSON for API %s: %s" % (api_url, str(e)))
			#trace_error()
			self.standings_data = []
			self.display_standings()

	def _standing_error_handler(self, failure, url):
		# This handles errors from getPage (e.g., Timeout, 403, DNS errors)
		error_message = failure.getErrorMessage()
		if debug_Standings: logdata("StandingsScreen", "Twisted Fetch Error on %s: %s" % (url, error_message))
		self.standings_data = []
		self.display_standings() # Display empty standings

	def check_and_download_logos(self):
		headers = self.headers.copy() # Use headers from init
		def normalize_name(name):
			"""Smart normalization: remove punctuation, numbers, generic words, and extra spaces."""
			if not name:
				return ""
			name = name.lower()
			# Remove anything in parentheses or brackets (e.g., "(2025)", "[B]")
			name = re.sub(r"[\(\[].*?[\)\]]", "", name)
			# Remove digits
			name = re.sub(r"\d+", "", name)
			# Replace punctuation with space
			name = re.sub(r"[.,\-'/]", " ", name)
			# Remove common generic football words automatically
			generic_words = r"\b(fc|ac|sc|club|sport|cf|f c|a c|s v|team|association|athletic|united|city|real|atl[eé]tico|gmbh)\b"
			name = re.sub(generic_words, "", name)
			# Remove extra spaces
			name = ' '.join(name.split())
			return name

		def download_and_save_logo(team_name, logo_url, headers, league):
			# Check for generic "no-logo" URLs and placeholders
			if not logo_url or logo_url.endswith("/blank.gif") or 'placeholder' in logo_url or logo_url.endswith("/no-logo.gif"):
				return False

			team_filename = sanitize_team_name(team_name)

			# The final target path is ALWAYS .png (what the E2 interface expects)
			filename_png = resolveFilename(SCOPE_PLUGINS,"Extensions/FootOnSat/assets/standings/{}.png".format(team_filename))

			# Check if PNG version exists
			if exists(filename_png):
				return True

			# Determine file extension from URL (used for temp filename)
			ext = ".gif" if logo_url.lower().endswith(".gif") else (".png" if logo_url.lower().endswith(".png") else ".jpg")
			
			# Temporary file path for raw download (using .temp_raw for safety)
			temp_file = join("/tmp", "{}.temp_raw".format(team_filename))
			# Temporary path for PIL output
			final_temp_png = join("/tmp", "{}.temp_png".format(team_filename))
			
			success = False
			temp_files_to_clean = [temp_file, final_temp_png] # List all files to clean up

			# Use the proven working User-Agent (Bytes for Twisted, must be string for Requests)
			AGENT = b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
			AGENT_STR = AGENT.decode('utf-8', 'ignore')

			try:
				if PY3:
					sniFactory = WebClientContextFactory(logo_url)
					d = downloadPage(
						str.encode(logo_url), 
						temp_file,
						contextFactory=sniFactory, 
						timeout=5,
						agent=AGENT
					)
					blockingCallFromThread(reactor, lambda: d) 
				else:
					logo_headers = {
						# Headers common to both methods (must be list of strings for Twisted, single string for Requests)
						'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*;q=0.8',
						'Referer': 'https://www.sofascore.com/', # CRITICAL
						'Origin': 'https://www.sofascore.com',   # CRITICAL
					}
					# === PYTHON 2 FIX: Use Requests/deferToThread to bypass 403 ===
					#if debug_Standings: logdata("Logos", "Starting Requests download for logo: %s (PY2 FIX)" % team_name)
					
					# Use headers in Py2 format (single strings)
					py2_headers = {
						'User-Agent': AGENT_STR,
						'Accept': logo_headers['Accept'],
						'Referer': logo_headers['Referer'],
						'Origin': logo_headers['Origin'],
						'Cache-Control': 'no-cache',
					}
					
					r = requests.get(logo_url, headers=py2_headers, timeout=5, verify=False)
					r.raise_for_status()
					data = r.content
					
					# === CRITICAL FIX: Ensure it’s actually image data (not HTML 403 page) ===
					if not (data.startswith(b'\x89PNG') or data.startswith(b'\xff\xd8') or data.startswith(b'GIF')):
						if debug_Standings: logdata("Logos", "ERROR: Downloaded content for '%s' is not an image (probably 403 HTML page)." % team_name)
						return False
						
					# Save the raw file content to the temporary location
					with open(temp_file, "wb") as f:
						f.write(data)

				success = False
				if ext == ".png":
					# If already PNG, just copy the file from /tmp to the final .png path
					shutil.copyfile(temp_file, filename_png)
					if debug_Standings: logdata("Logos", "Successfully saved PNG logo for '%s'." % team_name)
					success = True
				elif PIL_AVAILABLE:
					# --- PIL CONVERSION LOGIC ---
					try:
						img = Image.open(temp_file)
						if debug_Standings: logdata("img", "Downloading logo for '%s'" % img)
						# Handle potential transparent GIF/JPG by converting to RGBA
						if img.mode not in ('RGB', 'RGBA'):
							img = img.convert('RGBA')

						img.save(filename_png, 'PNG')
						if debug_Standings: logdata("Logos", "Converted and saved %s logo for '%s' to PNG via PIL." % (ext[1:].upper(), team_name))
						success = True
					except Exception as e:
						if debug_Standings: logdata("Logos", "PIL conversion FAILED for %s: %s" % (team_name, str(e)))
						#trace_error() # Include trace for better debugging
						# Fallback to simple copy if PIL fails (e.g., corrupted file)
						shutil.copyfile(temp_file, filename_png)
						success = True # Still logged as found
				else:
					# --- NO PIL FALLBACK (Will cause display error) ---
					if debug_Standings: logdata("Logos", "WARNING: PIL not available, saving raw %s data as PNG file for '%s'." % (ext[1:].upper(), team_name))
					shutil.copyfile(temp_file, filename_png)
					success = True

				# Clean up the temporary file
				if exists(temp_file):
					os.remove(temp_file)

				return success
					
			except Exception as e:
				if debug_Standings: logdata("Logos", "Failed to download/process logo for %s: %s" % (team_name, str(e)))
				#trace_error()
				return False
			finally:
				# Ensure cleanup regardless of success/failure
				if exists(temp_file):
					os.remove(temp_file)

		if debug_Standings: logdata("Logos", "Starting check for league: %s" % self.league)

		# Ensure standings folder exists
		standings_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/")
		if not exists(standings_dir):
			try:
				os.makedirs(standings_dir)
				if debug_Standings: logdata("Logos", "Created standings folder: %s" % standings_dir)
			except Exception as e:
				if debug_Standings: logdata("Logos", "Failed to create standings folder %s: %s" % (standings_dir, str(e)))
				return

		# Get list of teams and their primary logo URLs from fetch_standings
		teams_to_process = []
		for item in self.standings_data:
			# CRITICAL FIX: The item must have 11 elements now (index 10 is the logo URL)
			if isinstance(item, list) and len(item) >= 11: 
				original_name = item[0]
				# FIX: logo_url is at index 10 (the last element)
				logo_url = item[10] 
				
				# Store both the original name (for display/saving) and the normalized name (for matching)
				standardized_name = normalize_name(original_name)
				teams_to_process.append({
					"name": standardized_name,
					"original_name": original_name,
					"url": logo_url,
					"found": False
				})

		logos_found = 0
		total_teams = len(teams_to_process)

		# -------------------------------------------------------------------
		# --- PHASE 1: DIRECT DOWNLOAD FROM SOFASCORE (PRIMARY SOURCE) ---
		# -------------------------------------------------------------------
		
		# We must perform the direct SofaScore download here to honor your request 
		# for strict priority and to fix the logical error at the start of the function.
		
		for team_info in teams_to_process:
			team_filename = sanitize_team_name(team_info["original_name"])
			filename_png = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/{}.png".format(team_filename))
			
			# Check if a PNG already exists
			if exists(filename_png):
				team_info["found"] = True
				logos_found += 1
				continue
				
			if team_info["url"]:
				absolute_url = team_info["url"]
				
				# Use the actual download function we defined above
				if download_and_save_logo(team_info["original_name"], absolute_url, headers, self.league):
					team_info["found"] = True
					logos_found += 1
		
		# -------------------------------------------------------------------
		# --- PHASE 2: WORLDFOOTBALL FALLBACK (ONLY for missing logos) ---
		# -------------------------------------------------------------------
		if logos_found < total_teams:
			primary_backup_url = log_urls.get(self.league)
			if primary_backup_url:
				if debug_Standings: logdata("Logos", "Phase 2 (Worldfootball): Scraping primary backup site (%s) for missing logos..." % primary_backup_url)
				try:
					missing_logos = any(not team["found"] for team in teams_to_process)
					if missing_logos:
						# Use general headers for HTML scrape
						html_headers = self.headers2.copy()
						html_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
						try:
							html_headers["Referer"] = "http://www.google.com/"
						except Exception as e:
							html_headers["Referer"] = "https://www.google.com/"
						html_headers["Upgrade-Insecure-Requests"] = "1"

						request = compat_Request(primary_backup_url, headers=html_headers)
						response = compat_urlopen(request, timeout=5)
						html = response.read()

						if PY3:
							html = html.decode("utf-8", errors="ignore")
						
						soup = BeautifulSoup(html, "html.parser")
						# Look for img tags
						imgs = soup.find_all("img")

						# Prepare a map from normalized scraped name to the original raw scraped name
						normalized_title_map = {}
						normalized_targets = []
						for img in imgs:
							raw_title = img.get("title") or img.get("alt")
							if raw_title:
								normalized = normalize_name(raw_title)
								# Store a unique map entry: normalized -> raw title
								if normalized not in normalized_title_map:
									normalized_title_map[normalized] = raw_title
									normalized_targets.append(normalized)

						for team_info in teams_to_process:
							if team_info["found"]:
								continue

							# Use the pre-normalized name for matching
							team_to_search = team_info["name"]

							# Fuzzy match against the normalized scraped titles (STRICT CUTOFF = 0.90)
							team_match = difflib.get_close_matches(team_to_search, normalized_targets, n=1, cutoff=0.90)
							
							if debug_Standings: logdata("Logos", "Phase 2 Fuzzy Search for: '%s' (Normalized: '%s'). Match: %s" % (team_info["original_name"], team_to_search, team_match))

							if team_match:
								normalized_matched_title = team_match[0]
								original_title = normalized_title_map.get(normalized_matched_title) # Get the raw title
								img_tag = next((img for img in imgs if (img.get("title") == original_title or img.get("alt") == original_title) and img.get("src")), None)
								
								if img_tag:
									# Worldfootball uses relative paths, so join with the base URL
									logo_src = img_tag.get("src").split("?")[0]
									logo_url = compat_urljoin(primary_backup_url, logo_src)
									
									# Use the original name for logging and saving
									if download_and_save_logo(team_info["original_name"], logo_url, headers, self.league):
										team_info["found"] = True
										logos_found += 1 # Critical counter update
										if debug_Standings: logdata("Logos", "Found logo for '%s' using match to '%s' (worldfootball)." % (team_info["original_name"], original_title))

				except Exception as e:
					if debug_Standings: logdata("Logos", "Error fetching from primary backup site %s -> %s" % (primary_backup_url, str(e)))
					pass
		
		# Final log of any still missing teams
		if debug_Standings:
			for team_info in teams_to_process:
				if not team_info["found"]:
					logdata("Logos", "MISSING FINAL logo for team: '%s'" % team_info["original_name"])

		#if debug_Standings: logdata("Logos", "Completed check_and_download_logos(), total logos found: %d" % logos_found)


	def display_standings(self):
		gList = []

		# Determine ITEM_HEIGHT based on resolution (used multiple times)
		ITEM_HEIGHT = 65 if isFHD() else 85

		self["standings_list"].l.setItemHeight(ITEM_HEIGHT)
		if isUHD():
			self["standings_list"].l.setFont(0, gFont('Regular', 32))
		else:
			self["standings_list"].l.setFont(0, gFont('Regular', 28))

		club_idx = 1  # numbering for clubs only

		for standing in self.standings_data:
			if isinstance(standing, str) and standing.startswith("Table "):
				club_idx = 1  # reset numbering for new table
				if isFHD():
					res = [ITEM_HEIGHT, MultiContentEntryText(pos=(450, 0), size=(960, ITEM_HEIGHT), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(standing))]
				else: # UHD skins
					res = [ITEM_HEIGHT, MultiContentEntryText(pos=(0, 25), size=(2428, ITEM_HEIGHT), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(standing))]
				gList.append(res)
				continue


			if self.league in ("basketball", "nba", "nfl"):
				wins = standing[3]
				losses = standing[4]
				raw_diff = standing[6]
				pct = standing[7]
				streak = standing[5]
				diff_int = int(raw_diff) if raw_diff not in (None, "", "-") else 0
				diff = "+{}".format(diff_int) if diff_int > 0 else str(diff_int)
			else:
				wins = standing[4]
				losses = standing[6]
				goals_scored = standing[7]
				goals_conceded = standing[8]
				goal_diff = standing[9]
			team = standing[0]
			position = standing[1]
			played = standing[2]
			points = standing[3]
			draws = standing[5]
			logo_url = standing[10]

			# --- LOGO SIZE AND POSITIONING ---
			if isFHD():
				LOGO_SIZE_H = 50
				LOGO_Y_POS = 8
				LOGO_X_POS = 85
				TEAM_NAME_X_POS = 160
				TEXT_Y_OFFSET = 0  # No offset needed for 1920
			else:  # 2560
				LOGO_SIZE_H = 60
				LOGO_Y_POS = int((ITEM_HEIGHT - LOGO_SIZE_H) / 2)  # Recalculate to center vertically
				LOGO_X_POS = 95
				TEAM_NAME_X_POS = 220
				TEXT_Y_OFFSET = LOGO_Y_POS  # Align text with logo vertical position

			res = [ITEM_HEIGHT]
			# Number
			if isFHD():
				res.append(MultiContentEntryText(pos=(20, 0), size=(50, ITEM_HEIGHT), font=0,
												 flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=str(club_idx)))
			else:  # 2560
				res.append(MultiContentEntryText(pos=(0, LOGO_Y_POS +13), size=(70, LOGO_SIZE_H), font=0,
												 flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=str(club_idx)))
			club_idx += 1

			# logo using file path
			flagteam_png = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/{}.png".format(sanitize_team_name(team)))
			if self.league in ("basketball", "nba", "nfl"): # This for basketball, nba and nfl option codes only
				if isFHD():
					if exists(flagteam_png):
						if PY3:
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
													png=loadPNG(flagteam_png), flags=BT_SCALE))
						else: # DreamOS
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
													png=loadPNG(flagteam_png)))
					# team name - increased width for better display
					res.append(MultiContentEntryText(pos=(TEAM_NAME_X_POS, 0), size=(400, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team or "")))
					# matches played - aligned with "Played" header
					res.append(MultiContentEntryText(pos=(553, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(played or "")))
					# wins - aligned with "Wins" header
					res.append(MultiContentEntryText(pos=(745, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(wins or "")))
					# losses - aligned with "Losses" header
					res.append(MultiContentEntryText(pos=(957, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(losses or "")))
					# Streak - aligned with "Streak" header
					res.append(MultiContentEntryText(pos=(1138, 0), size=(80, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(streak or "")))
					# Difference (DIFF) - CORRETO: +24, -6
					res.append(MultiContentEntryText(pos=(1340, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(diff or "")))
					# Win Percentage (PCT)
					res.append(MultiContentEntryText(pos=(1570, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(pct or "")))
				else: # UHD skins (2560)
					if exists(flagteam_png):
						if PY3:
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
												png=loadPNG(flagteam_png), flags=BT_SCALE))
						else: # DreamOS
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
												png=loadPNG(flagteam_png)))
					# team name - increased width for better display
					res.append(MultiContentEntryText(pos=(200, LOGO_Y_POS +13), size=(600, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team or "")))
					# matches played - aligned with "Played" header
					res.append(MultiContentEntryText(pos=(670, LOGO_Y_POS +13), size=(300, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(played or "")))
					# wins - aligned with "Wins" header
					res.append(MultiContentEntryText(pos=(970, LOGO_Y_POS +13), size=(260, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(wins or "")))
					# losses - aligned with "Losses" header
					res.append(MultiContentEntryText(pos=(1270, LOGO_Y_POS +13), size=(260, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(losses or "")))
					# Streak - aligned with "Streak" header
					res.append(MultiContentEntryText(pos=(1570, LOGO_Y_POS +13), size=(260, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(streak or "")))
					# Difference (DIFF) - CORRETO: +24, -6
					res.append(MultiContentEntryText(pos=(1870, LOGO_Y_POS +13), size=(260, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(diff or "")))
					# Win Percentage (PCT)
					res.append(MultiContentEntryText(pos=(2170, LOGO_Y_POS +13), size=(260, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(pct or "")))
			else:
				if isFHD():
					if exists(flagteam_png):
						if PY3:
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
													png=loadPNG(flagteam_png), flags=BT_SCALE))
						else: # DreamOS
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
													png=loadPNG(flagteam_png)))
					# team name - increased width for better display
					res.append(MultiContentEntryText(pos=(TEAM_NAME_X_POS, 0), size=(400, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team or "")))
					# matches played - aligned with "Played" header
					res.append(MultiContentEntryText(pos=(553, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(played or "")))
					# points - aligned with "Points" header
					res.append(MultiContentEntryText(pos=(708, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(points or "")))
					# wins - aligned with "Wins" header
					res.append(MultiContentEntryText(pos=(852, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(wins or "")))
					# draws - aligned with "Draws" header
					res.append(MultiContentEntryText(pos=(997, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(draws or "")))
					# losses - aligned with "Losses" header
					res.append(MultiContentEntryText(pos=(1152, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(losses or "")))
					# goals scored - aligned with "Goals Scored" header
					res.append(MultiContentEntryText(pos=(1342, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_scored or "")))
					# goals conceded - aligned with "Conceded" header
					res.append(MultiContentEntryText(pos=(1520, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_conceded or "")))
					# goal diff - aligned with "Difference" header
					res.append(MultiContentEntryText(pos=(1680, 0), size=(80, ITEM_HEIGHT), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goal_diff or "")))
				else: # UHD skins (2560)
					if exists(flagteam_png):
						if PY3:
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
				                                                       png=loadPNG(flagteam_png), flags=BT_SCALE))
						else: # DreamOS
							res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
				                                                       png=loadPNG(flagteam_png)))
					# team name - increased width for better display
					res.append(MultiContentEntryText(pos=(200, LOGO_Y_POS +13), size=(550, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team or "")))
					# matches played - aligned with "Played" header
					res.append(MultiContentEntryText(pos=(630, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(played or "")))
					# points - aligned with "Points" header
					res.append(MultiContentEntryText(pos=(880, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(points or "")))
					# wins - aligned with "Wins" header
					res.append(MultiContentEntryText(pos=(1120, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(wins or "")))
					# draws - aligned with "Draws" header
					res.append(MultiContentEntryText(pos=(1375, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(draws or "")))
					# losses - aligned with "Losses" header
					res.append(MultiContentEntryText(pos=(1610, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(losses or "")))
					# goals scored - aligned with "Goals Scored" header
					res.append(MultiContentEntryText(pos=(1865, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_scored or "")))
					# goals conceded - aligned with "Conceded" header
					res.append(MultiContentEntryText(pos=(2075, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_conceded or "")))
					# goal diff - aligned with "Difference" header
					res.append(MultiContentEntryText(pos=(2265, LOGO_Y_POS +13), size=(140, LOGO_SIZE_H), font=0,
											flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goal_diff or "")))
			gList.append(res)

		self["standings_list"].setList(gList)
		if not self.standings_data:
			#logdata("display_standings", "No standings data, showing MessageBox")
			self.session.openWithCallback(self.close, MessageBox, title187, MessageBox.TYPE_INFO, timeout=10)
		else:
			#logdata("display_standings", "Displaying standings, total entries: %d" % len(gList))
			pass


class FootOnSatNotif:
	def __init__(self):
		self.dialog = None

	def startNotif(self, session):
		self.dialog = session.instantiateDialog(FootOnsatNotifScreen)

FootOnSatNotifDialog = FootOnSatNotif()

class FootOnsatNotifScreen(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SKIN_FootOnsatNotif
		if debug_Notif: logdata("NotifScreen", "Initializing NotifScreen")
		self['match'] = Label()
		self['message'] = Label()
		self['compet'] = Pixmap()
		self['flag1'] = Pixmap()
		self['flag2'] = Pixmap()
		self['live'] = Pixmap()
		self.container = eConsoleAppContainer()
		self.FootOnsatTimer = eTimer()
		try:
			self.FootOnsatTimer.timeout.get().append(self.checkforNotif)
		except:
			self.FootOnsatTimer_conn = self.FootOnsatTimer.timeout.connect(self.checkforNotif)
		#self.FootOnsatTimer.start(15000)
		# CRITICAL FIX: Reduce check interval to 1 second for near-exact timing
		self.FootOnsatTimer.start(1000)
		self.onhideTimer = eTimer()
		try:
			# CRITICAL CHANGE: Handler now points to the queue processor
			self.onhideTimer.timeout.get().append(self._display_next_in_queue)
		except:
			self.onhideTimer_conn = self.onhideTimer.timeout.connect(self._display_next_in_queue)
			
		# --- ADDED STATE FOR SEQUENTIAL DISPLAY AND BUG FIX ---
		self.matches_queue = []
		self.is_displaying = False
		self.is_checking = False

	def _update_display_only(self, match, compet, team1, team2, message=None, allow_zap=True):
		if not self.instance:
			return
		
		# 1. Handle non-breaking space (Py2/3 safe)
		try:
			normalized_search_key = match.replace(u'\xa0', u' ')
		except:
			normalized_search_key = match.replace('\xa0', ' ')
			
		# 2. Collapse all sequences of whitespace to a single space, strip edges, then remove ALL spaces
		normalized_search_key = re.sub(r'\s+', ' ', normalized_search_key).strip()
		normalized_search_key = normalized_search_key.replace(' ', '') # REMOVE ALL SPACES to match the saved key
		# END FIX
		
		# Initialize zap_ref outside try block for scope
		zap_ref = None
		
		# Only perform lookup if Zap is enabled by config AND the stage allows it
		zap_enabled_by_config = config.plugins.FootOnSat.notify_zap.value in ("1", "2")
		zap_allowed = zap_enabled_by_config and allow_zap 

		if zap_allowed:
			try:
				# FIX! Use 'with' here to ensure the connection is closed
				with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
					c = conn.cursor()
					
					# Search for the fully normalized key (which has no spaces)
					c.execute("SELECT ref FROM zap_channels WHERE match = ?", (normalized_search_key,))
					row = c.fetchone()
				# 'conn.close()' is now called automatically
				
				if row and row[0]:
					zap_ref = eServiceReference(str(row[0]))
					if debug_Notif: logdata("ZAP_DEBUG", "ZAP BY REFERENCE FOUND → %s (%s)" % (zap_ref.getName(), row[0]))
				else:
					if debug_Notif: logdatalogdata("ZAP_DEBUG", "No zap ref found (Search key: '%s')" % normalized_search_key)
					pass
			except Exception as e:
				if debug_Notif: logdata("ZAP_DEBUG", "ZAP LOOKUP ERROR: %s" % str(e))
				zap_ref = None # Ensure it is None on error

		# 🔥 CORRECTED FEATURE LOGIC START
		
		if config.plugins.FootOnSat.notify_zap.value == "2":
			# Case: Zap Only mode. Must suppress notification by NOT calling _do_actual_display.
			if zap_ref:
				# Zap channel found: Execute Zap immediately with sound.
				if debug_zap: logdata("Notification", "Zap Only mode: Executing Zap to %s" % str(zap_ref))
				self._play_tone() 
				time.sleep(2.0)
				InfoBar.instance.session.nav.playService(zap_ref)
				InfoBar.instance.servicelist.addToHistory(zap_ref)
			else:
				# No Zap channel found: Do nothing. (NO ACTION, NO SOUND)
				if debug_zap: logdata("Notification", "Zap Only mode: No zap channel found, skipping.")
				pass
			
			# Notification is suppressed: Manually advance queue and RETURN
			self._display_next_in_queue()
			return # Exit to prevent calling _do_actual_display
		
		# Default path (Option "1" or Zap disabled): Proceed to display the notification
		self._do_actual_display(match, compet, team1, team2, message, zap_ref=zap_ref)

	def _do_actual_display(self, match, compet, team1, team2, message=None, zap_ref=None):
		"""Show notification popup and execute Zap AFTER a 2.0s delay if a channel is found."""
		if not self.instance:
			return

		if message:
			if debug_Notif: logdata("ZAP_DEBUG", "Message: %s" % message)
			pass

		self['match'].setText(str(match))
		if message:
			self['live'].hide()
			self['message'].setText(str(message))
		else:
			self['live'].show()
			self['message'].setText("")

		banner = FootOnSat.setCompet(compet.lower())
		self['compet'].instance.setPixmapFromFile(banner)

		flag1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/%s.png" % team1)
		flag2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/%s.png" % team2)
		default_flag = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")

		self['flag1'].instance.setPixmapFromFile(str(flag1 if fileExists(flag1) else default_flag))
		self['flag2'].instance.setPixmapFromFile(str(flag2 if fileExists(flag2) else default_flag))

		# Play sound now, tied to the notification display (Option "1")
		self._play_tone() 

		FootOnSatNotifDialog.dialog.show()
		
		# Perform the Zap and Delay HERE for option "1"
		if zap_ref:
			try:
				# 👇 DELAY HERE to let the user see/hear the notification FIRST
				time.sleep(2.0)
				InfoBar.instance.session.nav.playService(zap_ref)
				InfoBar.instance.servicelist.addToHistory(zap_ref)
				if debug_Notif: logdata("ZAP_DEBUG", "playService called — channel switching...")
			except Exception as e:
				if debug_Notif: logdata("ZAP_DEBUG", "ZAP EXECUTION ERROR: %s" % str(e))
				pass
		else:
			if debug_Notif: logdata("ZAP_DEBUG", "Zap not required.")
			pass

	def _display_next_in_queue(self):
		"""Pulls the next match from the queue, displays it, and schedules the next display or hides the dialog."""
		
		self.onhideTimer.stop() 
		
		if not self.matches_queue:
			# Queue is empty: End of sequence, hide the dialog.
			self.hideNotif() 
			return

		# Get the next match to display
		match_data = self.matches_queue.pop(0)
		allow_zap = match_data.get('allow_zap', True)

		# Display the current match info 
		self._update_display_only(
			match_data['match'], 
			match_data['compet'], 
			match_data['team1'], 
			match_data['team2'], 
			match_data['message'],
			allow_zap=allow_zap
		)
		
		COMPENSATION_MS = 3000
		notification_seconds = config.plugins.FootOnSat.notiftime.value
		notification_milliseconds = notification_seconds * 1000
		compensated_milliseconds = notification_milliseconds + COMPENSATION_MS
		if compensated_milliseconds < 1000:
			compensated_milliseconds = 1000
		if self.matches_queue:
			# Start timer with compensated value
			self.onhideTimer.start(compensated_milliseconds)
		else:
			# Start final timer with compensated value
			self.onhideTimer.start(compensated_milliseconds)

	def _play_tone(self):
		"""Plays the notification tone."""
		from .launcher import MenuFootOnSat
		tone_file = MenuFootOnSat.getToneFile()
		if exists("/usr/bin/aplay"):
			os.system('aplay "{}" &'.format(tone_file))
		elif exists("/usr/bin/gst-launch-1.0"):
			os.system('(gst-launch-1.0 -q --no-fault filesrc location="{}" ! wavparse ! audioconvert ! audioresample ! alsasink > /dev/null 2>&1 &) &'.format(tone_file))
		else:
			if debug_Notif: logdata("FootOnSatNotif", "No supported sound player found (aplay/gst-launch).")
			pass

	def _start_sequential_display(self):
		"""Starts the sequential display process if not already running."""
		if self.is_displaying:
			return

		self.is_displaying = True
		# Sound logic has been MOVED to _play_tone() and is called when action is confirmed.
			
		# Start the sequential timer to immediately process the first item
		self.onhideTimer.start(10)

	def checkforNotif(self):
		
		# --- CRITICAL FIX: Re-entry Lock ---
		if self.is_checking:
			return
		self.is_checking = True

		try:
			if fileExists(join(PLUGINPATH, "db/footonsat.db")):
				self.deloldRecords()
				with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
					cur = conn.cursor()
					rows = cur.execute("select * from LIVE_NOTIF")
					rows = rows.fetchall()
					now = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), "%Y-%m-%d %H:%M")
					
					# Get the user's notification choice ONCE per timer tick
					user_choice = config.plugins.FootOnSat.notify.value
					
					if len(rows) > 0:
						for row in rows:
							match_name = row[0]
							first_notif_str = row[5]
							first_notif_time = datetime.strptime(first_notif_str, "%H:%M - %Y-%m-%d")
							match_time_obj = datetime.strptime(row[2], "%H:%M - %Y-%m-%d")

							# --- Check if the current scheduled reminder time is NOW ---
							if now == first_notif_time:
								
								time_diff_minutes = int((match_time_obj - first_notif_time).total_seconds() / 60)
								
								if time_diff_minutes == 30:
									# --- Stage 1: 30 Minute Reminder ---
									
									# 1a. Trigger Notification if option includes 30 min (1, 4, 6, 7)
									if user_choice in ("1", "4", "6", "7"):
										# Zap NOT allowed here
										self.notify(match_name.strip(), row[1], row[3], row[4], row[8], allow_zap=False)
									
									# 1b. Determine Next Notification Time & Message
									if user_choice in ("1", "3", "5", "7"):
										# Next notification should be 15 min
										message_next = title148 if PY3 else title148.decode('utf-8')
										notif_next_time = (match_time_obj - timedelta(minutes=15)).strftime("%H:%M - %Y-%m-%d")
									elif user_choice in ("2", "6"):
										# Next notification should be start time
										message_next = "%s" % title188
										notif_next_time = match_time_obj.strftime("%H:%M - %Y-%m-%d")
									else:
										# No more notifications required for this choice (e.g., choice 4: 30 min only)
										message_next = "%s" % title189
										# Set next time to 1 minute after match start for guaranteed cleanup
										notif_next_time = (match_time_obj + timedelta(minutes=1)).strftime("%H:%M - %Y-%m-%d")
									
									# 1c. Update Database for next stage
									cur.execute("UPDATE LIVE_NOTIF set FIRST_NOTIF = ?, MESSAGE = ? WHERE MATCH = ?", (notif_next_time, message_next, match_name,))
									#if debug_Notif: logdata("FootOnSatNotif", "TRIGGER: 30-min Notif for %s. Next: %s" % (match_name, message_next))
									continue

								elif time_diff_minutes == 15:
									# --- Stage 2: 15 Minute Reminder ---
									
									# 2a. Trigger Notification if option includes 15 min (1, 3, 5, 7)
									if user_choice in ("1", "3", "5", "7"):
										# Zap NOT allowed here
										self.notify(match_name.strip(), row[1], row[3], row[4], row[8], allow_zap=False)
									
									# 2b. Determine Next Notification Time & Message
									if user_choice in ("1", "2", "5", "6"):
										# Next notification should be start time
										message_next = title188 if PY3 else title188.decode('utf-8')
										notif_next_time = match_time_obj.strftime("%H:%M - %Y-%m-%d")
									else:
										# No more notifications required for this choice (e.g., choice 3, 7)
										message_next = title189 if PY3 else title188.decode('utf-8')
										# Set next time to 1 minute after match start for guaranteed cleanup
										notif_next_time = (match_time_obj + timedelta(minutes=1)).strftime("%H:%M - %Y-%m-%d")
										
									# 2c. Update Database for next stage
									cur.execute("UPDATE LIVE_NOTIF set FIRST_NOTIF = ?, MESSAGE = ? WHERE MATCH = ?", (notif_next_time, message_next, match_name,))
									#if debug_Notif: logdata("FootOnSatNotif", "TRIGGER: 15-min Notif for %s. Next: %s" % (match_name, message_next))
									continue

								elif time_diff_minutes <= 1:
									# --- Stage 3: Match Start Notification ---
									
									# 3a. Trigger Notification if option includes Start (1, 2, 5, 6)
									if user_choice in ("1", "2", "5", "6"):
										# Zap IS allowed here
										self.notify(match_name.strip(), row[1], row[3], row[4], allow_zap=True)
										if debug_Notif: logdata("FootOnSatNotif", "TRIGGER: Match Start Notif and DB delete for match: %s" % match_name)
									else:
										# Log deletion without triggering final notification
										if debug_Notif: logdata("FootOnSatNotif", "CLEANUP: Deleting record after final stage for match: %s (No Start Notif)" % match_name)
										pass
										
									# 3b. Delete the record regardless of the notification choice
									cur.execute("DELETE FROM LIVE_NOTIF WHERE MATCH = ?", (match_name,))
									continue
					conn.commit()

		except Exception as e:
			if debug_Notif: logdata("FootOnSatNotif", "ERROR in checkforNotif: %s" % str(e))
			pass
		
		finally:
			if 'gc' in sys.modules and sys.version_info >= (3, 14):  # Checks if the 'gc' (Garbage Collector) module is available and loaded.
				gc.collect()         # Forces immediate cleanup of unreferenced objects and file handles.
			self.is_checking = False # Reset the lock ensures it can run again later

	def deloldRecords(self):
		if not fileExists(join(PLUGINPATH, "db/footonsat.db")):
			return
			
		with connect(join(PLUGINPATH, "db/footonsat.db")) as conn:
			cur = conn.cursor()
			# row[0]=MATCH, row[1]=COMPET, row[2]=DATE
			rows = cur.execute("select * from LIVE_NOTIF")
			rows = rows.fetchall()
			
			# Note: All necessary modules (datetime, timedelta, re) are available globally
			now = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), "%Y-%m-%d %H:%M") 
			if len(rows) > 0:
				for row in rows:
					match_name = row[0] 
					compet_name = row[1] # Reliable field 
					date_string = row[2] # Reliable field
					try:
						# row[2] format: "HH:MM - YYYY-MM-DD"
						record_date = datetime.strptime(date_string, "%H:%M - %Y-%m-%d")
						cleanup_time = record_date + timedelta(minutes=1)
						
						if now > cleanup_time:
							
							# 1. Prepare the key for the ZAP_CHANNELS table (fully cleaned key)
							# This uses the same logic used during the save/lookup
							normalized_zap_key = match_name.replace(u'\xa0', u' ')
							normalized_zap_key = re.sub(r'\s+', ' ', normalized_zap_key).strip()
							normalized_zap_key = normalized_zap_key.replace(' ', '')
							
							# 2. CRITICAL FIX: Delete from LIVE_NOTIF using a reliable composite key (COMPET and DATE).
							# This bypasses the unreliable MATCH primary key string lookup and guarantees deletion.
							cur.execute("DELETE FROM LIVE_NOTIF WHERE COMPET = ? AND DATE = ?", (compet_name, date_string,))
							
							# 3. Delete from zap_channels using the cleaned key
							cur.execute("DELETE FROM zap_channels WHERE match = ?", (normalized_zap_key,))
							
							if debug_Notif: logdata("FootOnSatNotif", "CLEANUP SUCCESSFUL: Deleted LIVE_NOTIF and zap_channels for match: %s" % match_name)

					except Exception as e:
						if debug_Notif: logdata("FootOnSatNotif", "Error during record cleanup (%s): %s" % (date_string, str(e)))
						pass
			conn.commit()

	def notify(self, match, compet, team1, team2, message=None, allow_zap=True):
		"""
		[USER REQUESTED CHANGE] Now queues the notification and starts a sequential display timer.
		It respects the single-call nature of checkforNotif's loop but delivers the output sequentially.
		"""
		if self.instance and FootOnSatNotifDialog.dialog is not None:
			# 1. Package the match details
			match_data = {
				'match': match.strip(), 
				'compet': compet, 
				'team1': team1, 
				'team2': team2, 
				'message': message,
				'allow_zap': allow_zap,
			}
			
			# 2. Add to queue
			self.matches_queue.append(match_data)

			# 3. Start the sequential display process if it's not already running
			self._start_sequential_display()

	def hideNotif(self):
		"""Standard hide function used by the queue processor."""
		self.is_displaying = False
		FootOnSatNotifDialog.dialog.hide()
