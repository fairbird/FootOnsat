# -*- coding: utf-8 -*-
import os, io, re, gc, sys, json, math, codecs, random, time, shutil, difflib, requests, subprocess, signal
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

### images path
OPENBH="/usr/lib/enigma2/python/Screens/BpBlue.py"
OPENBH2="/usr/lib/enigma2/python/Screens/BpBlue.pyc"
OPENVIX="/usr/lib/enigma2/python/Plugins/SystemPlugins/ViX"

try:
	from urllib.parse import urlparse, urljoin
except ImportError:
	from urlparse import urlparse, urljoin

# Check for PIL availability first, and import if found
try:
	from PIL import Image
	PIL_AVAILABLE = True
except ImportError:
	PIL_AVAILABLE = False
	# Log a warning if PIL is not available, as conversion will fail
	logdata("Logos", "WARNING: PIL/Pillow library not found. Non-PNG logo conversion will fail.")

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

DB_PATH = '/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/db/footonsat.db'

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
}

SPORTS = {
	"basketball", "nba", "hockey", "nfl"
}
FOOTBALL = {
	"championsleague", "europaleague", "ConferenceLeague", "premierleague",
	"laliga", "laliga2", "championship", "seriea", "ligue1", "eredivisie", "saudiarabia",
	"bundesliga", "bundesliga2", "belgianpro", "superLig", "liganos", "afcchampions", "afcchampionstwo"
}

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
		domain = urlparse(url).netloc
		self.hostname = domain
	
	def getContext(self, hostname=None, port=None):
		ctx = ClientContextFactory.getContext(self)
		if self.hostname and ClientTLSOptions is not None:
			ClientTLSOptions(self.hostname, ctx)
		return ctx


class FootOnSat(Screen):
	def __init__(self, session, link, *args):
		#logdata("FootOnSat-INIT", "Plugin initialization started.")
		self.session = session
		Screen.__init__(self, session)
		self.MENUTEXT = "Press Menu to select zap channel"
		self.execing = False # FIX: Prevents AttributeError in base class's close() method
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
		self.link = link
		self["counter"] = Label()
		self["channel"] = Label()
		self["sat"] = Label()
		self["freq"] = Label()
		self["enc"] = Label()
		self["menu"] = Label()
		self["menu2"] = Label()
		self["key_red"] = Button(_("Ignore Competition"))
		self["key_yellow"] = Button(_("Reset Ignore List"))
		self["key_blue"] = Button(_("Scan"))
		self["key_green"] = Button(_("Standings Table"))
		self["key_red"].hide()
		self["key_yellow"].hide()
		self["key_blue"].hide()
		self["key_green"].hide()
		self["list1"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self["list2"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.selectedList = self["list1"]
		self.canScan = False
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
					self["menu"].setText(self.MENUTEXT)
					key = re.sub(r'\s+', '', match)
					if not PY3:
						key = key.decode('utf-8') if isinstance(key, str) else key
					try:
						with connect(DB_PATH) as conn: # <-- FIX: Use 'with' statement for guaranteed closing
							c = conn.cursor()
							c.execute("SELECT ref FROM zap_channels WHERE match = ?", (key,))
							z = c.fetchone()
						if z:
							service_ref_string = z[0]
							#logdata("ZAP_DEBUG", "Raw zap ref from DB: '%s' (type: %s)" % (service_ref_string, type(service_ref_string)))
							if not PY3 and isinstance(service_ref_string, unicode):
								service_ref_string = service_ref_string.encode('utf-8', 'ignore')
							service_ref = eServiceReference(service_ref_string)
							info = eServiceCenter.getInstance().info(service_ref)
							channel_name = info.getName(service_ref) if info else ""
							#logdata("ZAP_DEBUG", "Fetched channel name: '%s'" % channel_name)
							if channel_name:
								self["menu2"].setText("Will be Zap to >> " + channel_name)
							else:
								self["menu2"].setText("")
						else:
							#logdata("ZAP_DEBUG", "No zap ref found for match → '%s'" % key)
							self["menu2"].setText("")
					except Exception as e:
						#logdata("ZAP_DEBUG", "Error fetching zap ref: %s" % str(e))
						self["menu2"].setText("")
				else:
					self["menu"].setText("")
					self["menu2"].setText("")
			else:
				self["menu"].setText("")
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
				if clean_status == 'CANCELED': # Using the exact clean status 'HALFTIME' from the scraper logic
					status_text = "Canceled"
					display_prefix = "Status: "
				elif clean_status == 'FINISHED':
					status_text = "Finished"
					display_prefix = "Status: "
				elif clean_status == 'FT':
					status_text = "Full Time"
					display_prefix = "Status: "
				elif clean_status == 'AET':
					status_text = "After Extra Time"
					display_prefix = "Status: "
				elif clean_status == 'PEN':
					status_text = "Penalties"
					display_prefix = "Status: "
				elif clean_status == 'HALFTIME': # Using the exact clean status 'HALFTIME' from the scraper logic
					status_text = "Half Time"
					display_prefix = "Live: " # Typically, Half Time is still considered a "Live" state
				elif clean_status.isdigit() or re.search(r'^\d+[\'+]*\+?\d*$', clean_status):
					# Covers minutes like '51', '77', '90+', etc.
					status_text = "%s min" % display_status 
					display_prefix = "Live: " # Prefix for running matches
				else:
					# Catch-all for "LIVE", "POSTPONED", "CANCELLED", etc.
					status_text = display_status
					display_prefix = "Live: "
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
				if self.link != "live" and self.link != "end":
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
					# If score or status exists, display the dynamic status/time (e.g., "Live: 70 min" or "Status: FT")
					if isUHD():
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(430, 120), size=(400, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(1000, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
					else:
						if self.link in FOOTBALL:
							res.append(MultiContentEntryText(pos=(320, 120), size=(240, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=LIVECOLORE))
				else:
					# Otherwise, display the scheduled Kick-off time
					if isUHD():
						if self.link in (SPORTS | FOOTBALL):
							res.append(MultiContentEntryText(pos=(430, 120), size=(1000, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(1000, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
					else:
						if self.link in (SPORTS | FOOTBALL):
							res.append(MultiContentEntryText(pos=(320, 120), size=(500, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
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
			if self.link in ["today"]:
				self['key_red'].show()
				self['key_yellow'].show()
				self['key_green'].hide()
			elif self.link in json_urls:
				self['key_red'].hide()
				self['key_yellow'].hide()
				self['key_green'].show()
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
				no_schedules_text = _('No Live matches at this time')
			elif self.link == "end":
				no_schedules_text = _('No Finished matches at this time')
			else:
				no_schedules_text = _('No schedules in this section at this time')
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
				size=(850 if isUHD() else 660, 36),
				font=0, 
				flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, 
				text=no_schedules_text
			))
			gList.append(res)
			# Set the list
			self["list1"].setList(gList)
			# Clear all auxiliary information and hide buttons
			self['key_red'].hide()
			self['key_yellow'].hide()
			self['key_blue'].hide()
			if self.link in ["today", "live", "end"]:
				self['key_green'].hide()
			else:
				self['key_green'].show()
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
					self["menu"].setText(self.MENUTEXT)
					key = re.sub(r'\s+', '', match)
					if not PY3:
						key = key.decode('utf-8') if isinstance(key, str) else key
					try:
						with connect(DB_PATH) as conn: # <-- FIX: Use 'with' statement for guaranteed closing
							c = conn.cursor()
							c.execute("SELECT ref FROM zap_channels WHERE match = ?", (key,))
							z = c.fetchone()
						if z:
							service_ref_string = z[0]
							#logdata("ZAP_DEBUG", "Raw zap ref from DB: '%s' (type: %s)" % (service_ref_string, type(service_ref_string)))
							if not PY3 and isinstance(service_ref_string, unicode):
								service_ref_string = service_ref_string.encode('utf-8', 'ignore')
							service_ref = eServiceReference(service_ref_string)
							info = eServiceCenter.getInstance().info(service_ref)
							channel_name = info.getName(service_ref) if info else ""
							#logdata("ZAP_DEBUG", "Fetched channel name: '%s'" % channel_name)
							if channel_name:
								self["menu2"].setText("Will be Zap to >> " + channel_name)
							else:
								self["menu2"].setText("")
						else:
							#logdata("ZAP_DEBUG", "No zap ref found for match → '%s'" % key)
							self["menu2"].setText("")
					except Exception as e:
						#logdata("ZAP_DEBUG", "Error fetching zap ref: %s" % str(e))
						self["menu2"].setText("")
				else:
					self["menu"].setText("")
					self["menu2"].setText("")
			else:
				self["menu"].setText("")
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
			with connect(DB_PATH) as conn:
				cur = conn.cursor()
				cur.execute('CREATE TABLE IF NOT EXISTS LIVE_NOTIF (MATCH TEXT primary key , COMPET TEXT , DATE TEXT , TEAM1_FLAG TEXT , TEAM2_FLAG TEXT , FIRST_NOTIF TEXT , FIRST_NOTIF_STATUS TEXT , LIVE_NOTIF_STATUS TEXT,MESSAGE TEXT)')
		except DatabaseError:
			# If the file is corrupted, delete it and try again.
			if exists(DB_PATH):
				os.remove(DB_PATH)
			with connect(DB_PATH) as conn:
				cur = conn.cursor()
				cur.execute('CREATE TABLE IF NOT EXISTS LIVE_NOTIF (MATCH TEXT primary key , COMPET TEXT , DATE TEXT , TEAM1_FLAG TEXT , TEAM2_FLAG TEXT , FIRST_NOTIF TEXT , FIRST_NOTIF_STATUS TEXT , LIVE_NOTIF_STATUS TEXT,MESSAGE TEXT)')

	def menu(self):
		if self.link != "live" and self.link != "end":
			if self.selectedList != self["list1"] or len(self.matches) == 0:
				return

			index = self['list1'].getSelectionIndex()
			match = self.matches[index][0] if PY3 else self.matches[index][0].decode('utf-8')

			if not self.checkIfexist(match):
				self.session.open(MessageBox,
					_("Please press OK on the match first to enable notification!"),
					MessageBox.TYPE_INFO, timeout=6)
				return

			self.current_selected_match = match

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

			self.session.openWithCallback(self.channelSelected, sel_class, _("Select Notification Channel"))

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

		logdata("ZAP_DEBUG", "SAVING ZAP REF → '%s' → %s (%s)" % (normalized_match, channel_name, ref_string))

		try:
			with connect(DB_PATH) as conn: # <-- FIX: Use 'with' for transaction safety and guaranteed close
				c = conn.cursor()
				c.execute('CREATE TABLE IF NOT EXISTS zap_channels (match TEXT primary key, ref TEXT)''')
				# Insert using the fully normalized key (which has no spaces)
				c.execute("INSERT OR REPLACE INTO zap_channels (match, ref) VALUES (?, ?)", (normalized_match, ref_string))
				# conn.commit() is implicitly called if the 'with' block exits without error
			logdata("ZAP_DEBUG", "ZAP REF SAVED SUCCESSFULLY → %s" % ref_string)
		except Exception as e:
			logdata("ZAP_DEBUG", "SAVE ERROR: %s" % str(e))

		self.iniMenu()

		self.session.open(MessageBox,
			_("Notification channel saved!\n\n") +
			_("Match: ") + exact_match + "\n" +
			_("Channel: ") + channel_name + "\n\n" +
			_("Receiver will zap to this channel when notification appears."),
			MessageBox.TYPE_INFO, timeout=10)

	def ok(self):
		if self.selectedList != self["list1"] or len(self.matches) == 0:
			return

		index = self['list1'].getSelectionIndex()
		current_match = self.matches[index]

		if (self.link == "live" or self.link == "end" or self.link in FOOTBALL) and len(current_match) > 8 and current_match[8]:
			current_match = self.matches[index]
			if len(current_match) > 8 and current_match[8]:
				event_id = current_match[8]
				
				# match[0] usually contains "Team A vs Team B"
				match_str = current_match[0]
				parts = re.split(r'\s+v[s]?\s+', match_str, 1, flags=re.IGNORECASE)
				home_full = parts[0].strip() if len(parts) > 1 else "Home"
				away_full = parts[1].strip() if len(parts) > 1 else "Away"

				# Open the screen with ALL parameters
				self.session.open(MatchDetailsScreen, 
					event_id, 
					current_match[2], # Competition (Title)
					home_full,        # Full Name (Bodo Glimt)
					away_full,        # Full Name (Diosgyor)
					current_match[3], # Country (Norway)
					current_match[4]) # Country (Hungary)
			else:
				self.session.open(MessageBox, _("Please wait a few seconds to get live data..."), MessageBox.TYPE_INFO, timeout=3)
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
			with connect(DB_PATH) as conn:
				cur = conn.cursor()
				cur.execute("CREATE TABLE IF NOT EXISTS zap_channels (match TEXT primary key, ref TEXT)")
				if self.checkIfexist(match):
					cur.execute("DELETE FROM LIVE_NOTIF WHERE MATCH = ?", (match,))
					cur.execute("DELETE FROM zap_channels WHERE match = ?", (re.sub(r'\s+', '', match),))
				else:
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
			message = "Kick-off in 30 minutes"
			return [first_notif_str, message]
		# 2. 15-minute reminder
		notif_15min_time = dt_obj - timedelta(minutes=15)
		if notif_15min_time > now:
			first_notif_str = notif_15min_time.strftime("%H:%M - %Y-%m-%d")
			message = "Kick-off in 15 minutes"
			return [first_notif_str, message]
		# 3. Match Start time reminder
		if dt_obj > now:
			first_notif_str = dt_obj.strftime("%H:%M - %Y-%m-%d")
			message = "Kick-off in 1 minute"
			return [first_notif_str, message]
		# 4. Fallback: Match already started or passed (should be immediately deleted by cleanup)
		first_notif_str = dt_obj.strftime("%H:%M - %Y-%m-%d")
		message = "Match has started" 
		return [first_notif_str, message]

	def sameDate(self, dt):
		with connect(DB_PATH) as conn:
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
		with connect(DB_PATH) as conn:
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
			with connect(DB_PATH) as conn:
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
		#logdata("FootOnSat-API", "Starting callAPI to fetch main schedule: %s" % self.link)
		url_link = "today" if self.link in ["live", "end"] else self.link
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
			self.session.openWithCallback(self.exit, MessageBox, _('An Unexpected HTTP Error Occurred During The API Request !!'), MessageBox.TYPE_ERROR, timeout=10)

	def fetch_live_results(self):
		# Define the fixed time windows
		LIVE_DURATION = timedelta(hours=4) # 4 hours limit for finished matches
		TIME_WINDOW = timedelta(hours=4) # Generous fuzzy matching time tolerance
		
		live_start_time = time.time()
		#logdata("FootOnSat-LIVESCORE", "fetch_live_results initiated.")
		
		# === URL Setup ===
		today_iso = date.today().isoformat()
		url1 = 'https://api.sofascore.com/api/v1/sport/football/scheduled-events/{0}/'.format(today_iso)
		url2 = 'https://api.sofascore.com/api/v1/sport/football/scheduled-events/{0}/inverse'.format(today_iso)

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

		#logdata("FootOnSat-LIVESCORE", "Sending request to SofaScore API.")

		# === SMART DYNAMIC FETCH ===
		# On Saturday/Sunday → url2 = 30 MB = DEATH
		# So we check day: if weekend → SKIP url2 completely
		weekday = date.today().weekday()  # 5 = Saturday, 6 = Sunday
		is_weekend = weekday >= 5
		if config.plugins.FootOnSat.extrafetch.value:
			fetch_url2 = True  # Always fetch url2, optimized with timeout for large responses
		else:
			fetch_url2 = not is_weekend  # ONLY try url2 on Mon–Fri

		# === Twisted HTTP Request Handling (with Py3 compatibility) ===
		deferred_list = []
		if PY3:
			try:
				sniFactory = WebClientContextFactory()
			except Exception as e:
				logdata("fetch_live_results", "Failed to create WebClientContextFactory: %s" % str(e))
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
			d1 = getPage(str.encode(url1), contextFactory=sniFactory, timeout=35, headers=twisted_live_headers)
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
						return getPage(str.encode(url2), contextFactory=sniFactory, timeout=35, headers=headers2)
					except:
						return defer.succeed(None)
				d2 = safe_url2()
				deferred_list.append(d2)
			else:
				# Weekend: inject None so gatherResults keeps order
				deferred_list.append(defer.succeed(None))

			d = defer.gatherResults(deferred_list, consumeErrors=True)

			def process_results(results):
				raw1, raw2 = results

				# Log url1
				#if isinstance(raw1, Failure):
				#	logdata("fetch_live_results", "DEBUG URL1 FAILED: %s" % raw1.getErrorMessage())
				#else:
				#	logdata("fetch_live_results", "DEBUG URL1 OK (Bytes: %d)" % len(raw1))

				# Log url2
				#if not fetch_url2:
				#	logdata("fetch_live_results", "DEBUG URL2 SKIPPED (weekend protection active)")
				#elif raw2 is None:
				#	logdata("fetch_live_results", "DEBUG URL2 SKIPPED (setup failed)")
				#elif isinstance(raw2, Failure):
				#	logdata("fetch_live_results", "DEBUG URL2 FAILED → SKIPPED SAFELY")
				#else:
				#	logdata("fetch_live_results", "DEBUG URL2 OK (Bytes: %d) → using extra data" % len(raw2))

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
			# PY2 version — same logic
			def _fetch_smart():
				results = []
				# url1 always
				try:
					r = requests.get(url1, headers=headers2, timeout=35)
					r.raise_for_status()
					results.append(r.content)
					#logdata("fetch_live_results", "DEBUG URL1 (Py2) OK (%d KB)" % (len(r.content)//1024))
				except Exception as e:
					logdata("fetch_live_results", "DEBUG URL1 (Py2) FAILED: %s" % str(e))
					results.append(None)

				# url2 only if safe
				if fetch_url2:
					try:
						h2 = headers2.copy()
						h2['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/129.0 Safari/537.36'
						r2 = requests.get(url2, headers=h2, timeout=35)
						r2.raise_for_status()
						results.append(r2.content)
						#logdata("fetch_live_results", "DEBUG URL2 (Py2) OK (%d MB) → extra data" % (len(r2.content)//1024//1024))
					except Exception as e:
						logdata("fetch_live_results", "DEBUG URL2 (Py2) FAILED → SKIPPED")
						results.append(None)
				else:
					#logdata("fetch_live_results", "DEBUG URL2 (Py2) SKIPPED (weekend mode)")
					results.append(None)

				valid = [r for r in results if r is not None]
				return valid or [b'{"events":[]}']

			d = deferToThread(_fetch_smart)
		
		# === _process_response (Twisted Callback from network fetch) ===
		def _process_response(raw_list): # <--- Argument changed from 'raw' to 'raw_list'
			process_start = time.time()
			#logdata("FootOnSat-LIVESCORE", "Received SofaScore response. Starting processing.")
			all_events = []
			# Decode and JSON Load
			for idx, raw in enumerate(raw_list):
				if raw is None: # Skip if fetch failed (non-PY3 path)
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
#						logdata("FootOnSat-DEBUG", "Saved PRETTY-PRINTED SofaScore EVENTS to %s" % sofa_debug_path)
#					except Exception as e:
#						logdata("FootOnSat-DEBUG-ERROR", "Failed to save SofaScore JSON: %s" % str(e))
					# === END DEBUG ===
					events = data.get('events', [])
					all_events.extend(events)
				except ValueError as e:
					# Log the actual JSON parsing error
					logdata("fetch_live_results", "JSON parse error (ValueError): %s" % str(e))
					# Log the beginning of the raw data that caused the crash (first 256 characters)
					logdata("fetch_live_results", "Corrupt Data Snippet: %s..." % data_str[:256].replace('\n', ' '))
					continue # Continue to the next response in the list
				except Exception as e:
					# Log any other unexpected decode/general error
					logdata("fetch_live_results", "Decode/General error: %s" % str(e))
					continue # Continue to the next response in the list

			if not all_events:
				self.matches = [list(m) for m in self.matches]
				try:
					self.iniMenu()
				except Exception as e:
					pass
				return

			events = all_events
			gc.collect() # Force garbage collection to free memory after processing large JSON data

			# === STEP 1: EVENT BUILDING & STRICT FILTERING (Main thread) ===
			now = datetime.now()
			now_adj = now - timedelta(minutes=3)
			
			live_matches = []
			build_start = time.time()
			for ev in events:
				try:
					try:
						home_team = ev.get('homeTeam') or {}
						away_team = ev.get('awayTeam') or {}
						home = compat_str(home_team.get('name', 'Unknown Home'))
						away = compat_str(away_team.get('name', 'Unknown Away'))
						if home == 'Unknown Home' or away == 'Unknown Away':
							continue
					except Exception as e:
						logdata("FootOnSat-Sofa-ERROR", "Team name parse error: %s" % str(e))
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
							status = 'PEN'
						elif descr.lower() in ['half time', 'halftime']:
							status = 'HALFTIME'
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
							status = 'CANCELED'
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
					logdata("FootOnSat-Sofa-ERROR", "Error building live_matches for an event: %s" % str(e))
					continue
			
			#logdata("FootOnSat-PERF", "LIVESCORE: Data extraction/filtering completed on Main Thread in %.3f s." % (time.time() - build_start))

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
				#logdata("FootOnSat-PERF", "LIVESCORE: Fuzzy Matching started on background thread.")
				
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

							#logdata("FuzzyDebug","COMPARE | SCHED: '%s' vs '%s' | LIVE: '%s' vs '%s'" % (
							#	l_t1_clean, l_t2_clean,
							#	s_t1_clean, s_t2_clean))

							sim1 = SequenceMatcher(None, l_t1_clean, s_t1_clean).ratio()
							sim2 = SequenceMatcher(None, l_t2_clean, s_t2_clean).ratio()
							avg_straight = (sim1 + sim2) / 2.0

							sim1s = SequenceMatcher(None, l_t1_clean, s_t2_clean).ratio()
							sim2s = SequenceMatcher(None, l_t2_clean, s_t1_clean).ratio()
							avg_swap = (sim1s + sim2s) / 2.0

							cur_sim = max(avg_straight, avg_swap)
							#logdata("FuzzyDebug", "Match '%s': sim=%.2f (straight=%.2f, swap=%.2f)" % (local_name, cur_sim, avg_straight, avg_swap))

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

				#logdata("FootOnSat-PERF", "LIVESCORE: Ultra-Optimized Fuzzy Matching finished in %.3f s." % (time.time() - match_perf_start))
				return matches_list

			def _matching_complete(updated_matches_list):
				cache_file, terminated_cache, changed, final_list = "/tmp/terminated_matches.json", [], False, []
				try:
					if exists(cache_file):
						with open(cache_file, 'r') as f: terminated_cache = json.load(f)
				except: pass
				for m in updated_matches_list:
					m_name, m_status = str(m[0]), str(m[7]).upper()
					is_term = any(x in m_status for x in ['FINISHED', 'CANCELED', 'POSTPONED'])
					in_cache = m_name in terminated_cache
					if getattr(self, 'link', None) == "live":
						if is_term and not in_cache:
							terminated_cache.append(m_name)
							changed = True
						if is_term or in_cache: continue
					elif getattr(self, 'link', None) == "end":
						if not (is_term or in_cache):
							continue
					elif getattr(self, 'link', None) not in ["live", "end", "today"]:
						pass
					final_list.append(m)
				self.matches = final_list
				if changed and self.link == "live":
					try:
						with open(cache_file, 'w') as f: json.dump(terminated_cache, f, ensure_ascii=False)
					except: pass
				try: self.iniMenu()
				except: pass
				#logdata("FootOnSat-PERF", "LIVESCORE: Final UI updated with scores. Total processing time: %.3f s." % (time.time() - process_start))

			d_match = deferToThread(_do_fuzzy_matching, matches_list, live_matches, now_adj)
			d_match.addCallback(_matching_complete)
			d_match.addErrback(lambda f: logdata("FootOnSat-Sofa-ERROR", "Fuzzy matching thread failed: %s" % f.getErrorMessage()))

		def _error(failure):
			logdata("FootOnSat-Sofa-ERROR", "Twisted Request failed: %s" % failure.getErrorMessage())

		d.addCallback(_process_response)
		d.addErrback(_error)
		
		#logdata("FootOnSat-PERF", "LIVESCORE: Network request fired. Time elapsed until non-blocking request: %.3f s." % (time.time() - live_start_time))

	def getData(self, data):
		list = []
		try:
			self.js = json.loads(data)
#			data_str = data.decode('utf-8', 'ignore')
#			self.js = json.loads(data_str) # Use the decoded string
		except Exception as e:
			self.session.openWithCallback(self.exit, MessageBox, _('Invalid API data! Check logs.'), MessageBox.TYPE_ERROR, timeout=10)
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

		cache_file = "/tmp/terminated_matches.json"
		terminated_cache = []
		cache_changed = False
		try:
			if exists(cache_file):
				with open(cache_file, 'r') as f: terminated_cache = json.load(f)
		except: pass

		ignored_competitions = []
		try:
			ignored_competitions = self.manageIgnoreFile()
		except Exception as e:
			#logdata("getData", "Failed to load ignored competitions: " + str(e))
			pass

		now = datetime.now()
		# 1. UPDATED: Consider matches live for 2 hours
		try:
			# Check the configuration value for the "finished" duration
			if config.plugins.FootOnSat.finished.value == "3":
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

		if self.js.get('footonsat') or self.link in ["live", "end"]:
			target_data = self.js.get('footonsat', [])
			for match in target_data:
				try:
					compet = str(match['compet']).strip()
					for suffix in [' - Week ', ' - Matchday ', ' - Round ']:
						if suffix in compet:
							compet = compet.split(suffix)[0].strip()

					if compet not in ignored_competitions or self.link not in ["today", "live", "end"]:
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
						is_really_finished = now > (match_date_adjusted + timedelta(minutes=150))
						is_terminated = any(x in str(match_status).upper() for x in ['FINISHED', 'CANCELED', 'POSTPONED'])
						in_cache = match_name in terminated_cache
						if getattr(self, 'link', None) == "live":
							if is_really_finished and in_cache:
								terminated_cache.remove(match_name)
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
					#else:
						#logdata("getData", "Ignored competition: " + str(match['match']) + ", Compet: " + compet)
				except KeyError:
					#logdata("getData-error", "KeyError on match: " + str(match))
					pass

			self.matches = list

			if cache_changed:
				try:
					with open(cache_file, 'w') as f: json.dump(terminated_cache, f, ensure_ascii=False)
				except: pass

			#logdata("DEBUG_VALUE", "Value is: %s | Link is: %s" % (str(config.plugins.FootOnSat.livescore.value), str(self.link)))
			# Only fetch live results for live/finished matches if livescore is set to "3"					
			if config.plugins.FootOnSat.livescore.value == "2":
				# Added 'and self.link != "today"' to block scores for the today section
				if config.plugins.FootOnSat.livescoresections.value == "1" and self.link != "today":
					self.fetch_live_results()
				elif config.plugins.FootOnSat.livescoresections.value == "2":
					# Logic: If setting is 'Specific Section', use it for 'live'
					if self.link == "live" or self.link == "end":
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
		if self.link in json_urls:
			self.session.open(StandingsScreen, self.link, json_urls[self.link])

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
				logdata("scan_exception", "Failed to parse freq '{}': {}".format(freq, e))
			symbolrate = self.channelData[index][2].split(' ')[2]
			pos = self.channelData[index][1].split(' ')[-1].replace('°', ' ').split(' ')
			sat = self.getSat(pos)
			fec = self.channelData[index][2].split(' ')[-1]
			polarization = 'V' if 'V' in self.channelData[index][2] else 'H'

			if len(nimList) == 0:
				self.session.open(MessageBox, _('Satellite frontend Not found!'), MessageBox.TYPE_ERROR, timeout=10)
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
				self.session.open(MessageBox, 'Satfinder Is not compatible with this image', MessageBox.TYPE_ERROR, timeout=10)
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
		self.close()

	def manageIgnoreFile(self, compet=None, reset=False, remove=None):
		# logdata("manageIgnoreFile", "Called with compet={}, reset={}, remove={}".format(compet, reset, remove))
		# Create ignore directory if it doesn't exist
		from .launcher import get_ignore_paths
		ignore_dir, ignore_file = get_ignore_paths()
		if not exists(ignore_dir):
			try:
				os.makedirs(ignore_dir, 0o755)
				# logdata("manageIgnoreFile", "Created ignore directory: " + ignore_dir)
			except Exception as e:
				logdata("manageIgnoreFile", "Failed to create ignore dir: " + str(e))
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
				# logdata("manageIgnoreFile", "Reset ignore-match.json to empty")
				return []
			except Exception as e:
				logdata("manageIgnoreFile", "Failed to reset ignore file: " + str(e))
				return []
		# Load or initialize ignored competitions
		ignored = []
		if exists(ignore_file):
			try:
				with fopen(ignore_file, 'r') as f:
					data = json.load(f)
					ignored = data.get("ignored_competitions", [])
				# logdata("manageIgnoreFile", "Loaded ignored competitions: " + str(ignored))
			except Exception as e:
				logdata("manageIgnoreFile", "Failed to read ignore file: " + str(e))
				# Create empty file if reading fails
				try:
					with fopen(ignore_file, 'w') as f:
						json.dump({"ignored_competitions": []}, f)
					# logdata("manageIgnoreFile", "Created empty ignore-match.json after read failure")
				except Exception as e:
					logdata("manageIgnoreFile", "Failed to create ignore file: " + str(e))
					return []
		else:
			try:
				with fopen(ignore_file, 'w') as f:
					json.dump({"ignored_competitions": []}, f)
				# logdata("manageIgnoreFile", "Created empty ignore-match.json")
			except Exception as e:
				logdata("manageIgnoreFile", "Failed to create ignore file: " + str(e))
				return []
		# Remove competition if provided
		if remove:
			try:
				compet_str = str(remove).strip()
			except UnicodeEncodeError:
				compet_str = unicode(remove).encode('utf-8').strip()  # Python 2 compatibility
			# logdata("manageIgnoreFile", "Attempting to remove compet: " + (compet_str if compet_str else "None"))
			if compet_str in ignored:
				ignored.remove(compet_str)
				try:
					with fopen(ignore_file, 'w') as f:
						json.dump({"ignored_competitions": ignored}, f)
					# logdata("manageIgnoreFile", "Removed competition: " + compet_str + ", New list: " + str(ignored))
				except Exception as e:
					logdata("manageIgnoreFile", "Failed to update ignore file after removing " + compet_str + ": " + str(e))
					return ignored
			#else:
				#logdata("manageIgnoreFile", "Competition not removed: " + (compet_str if compet_str else "None") + " (not in ignore list)")
			return ignored
		# Add competition if provided
		if compet:
			try:
				compet_str = str(compet).strip()
			except UnicodeEncodeError:
				compet_str = unicode(compet).encode('utf-8').strip()  # Python 2 compatibility
			# logdata("manageIgnoreFile", "Received compet: " + (compet_str if compet_str else "None"))
			if compet_str and compet_str not in ignored:
				ignored.append(compet_str)
				try:
					with fopen(ignore_file, 'w') as f:
						json.dump({"ignored_competitions": ignored}, f)
					# logdata("manageIgnoreFile", "Added competition to ignore: " + compet_str + ", New list: " + str(ignored))
					return ignored
				except Exception as e:
					logdata("manageIgnoreFile", "Failed to update ignore file with " + compet_str + ": " + str(e))
					return ignored
			#else:
			#	logdata("manageIgnoreFile", "Competition not added: " + (compet_str if compet_str else "None") + " (already ignored or empty)")
		return ignored

	def selectCompetitionToRemove(self, selected):
		if not selected or not selected[1]:
			self.session.open(MessageBox, _('No competition selected to remove'), MessageBox.TYPE_INFO, timeout=5)
			return
		compet = selected[1]
		# logdata("selectCompetitionToRemove", "Removing competition: " + compet)
		self.manageIgnoreFile(remove=compet)
		self.session.open(MessageBox, _('Competition "%s" removed from ignore list') % compet, MessageBox.TYPE_INFO, timeout=5)
		# Refresh the match list to include removed competition's matches
		self.matches = []
		self["list1"].setList([])
		self.callAPI()

	def keyRed(self):
		from .launcher import get_ignore_paths
		ignore_dir_path, ignore_file_path = get_ignore_paths()
		
		if self.link == "today" and self.selectedList == self["list1"] and len(self.matches) > 0:
			try:
				index = self['list1'].getSelectionIndex()
				compet = str(self.matches[index][2]).strip()
				# Remove week/round/matchday suffixes
				for suffix in [' - Week ', ' - Matchday ', ' - Round ']:
					if suffix in compet:
						compet = compet.split(suffix)[0].strip()
				
				if not compet:
					self.session.open(MessageBox, _('No valid competition selected!'), MessageBox.TYPE_ERROR, timeout=5)
					return
				
				# Load current ignored competitions
				ignored_before = self.manageIgnoreFile()
				# Add selected competition to ignore list
				self.manageIgnoreFile(compet=compet)
				ignored_after = self.manageIgnoreFile()
				
				if compet in ignored_after and compet not in ignored_before:
					# Use the variable containing only the file path string
					path_info = ignore_file_path
					msg = _('Competition "%s" added to ignore list.\n\nSave file on "%s"') % (compet, path_info)
					self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=5)
				#else:
				#	logdata("keyRed", "Competition " + compet + " not added (already ignored or failed)")
				
				# Refresh the match list to exclude ignored competitions
				self.matches = []
				self["list1"].setList([])
				self.callAPI()
			except Exception as e:
				logdata("keyRed", "Error ignoring competition: " + str(e))
				self.session.open(MessageBox, _('Error ignoring competition!'), MessageBox.TYPE_ERROR, timeout=5)

	def keyYellow(self):
		if self.link == "today":
			try:
				ignored_list = self.manageIgnoreFile()
				if not ignored_list:
					self.session.open(MessageBox, _('No competitions in the ignore list'), MessageBox.TYPE_INFO, timeout=5)
					return
				# logdata("keyYellow", "Ignored competitions: " + str(ignored_list))
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
							# logdata("keyYellow", "Error converting competition to byte string: " + str(e))
							comp_str = str(comp) # Fallback
					list.append((comp_str, comp_str))
				# If the list is empty after processing, stop
				if not list:
					self.session.open(MessageBox, _('Error processing ignore list items!'), MessageBox.TYPE_ERROR, timeout=5)
					return
				self.session.openWithCallback(self.selectCompetitionToRemove, ChoiceBox, _('Select the competition to remove from list'), list)
			except Exception as e:
				# logdata("keyYellow", "Error selecting competition to remove: " + str(e))
				# This addresses the original error which likely occurred here due to string conversion failure
				self.session.open(MessageBox, _('Error accessing ignore list!'), MessageBox.TYPE_ERROR, timeout=5)


class MatchDetailsScreen(Screen):
	def __init__(self, session, event_id, match_name, home_full, away_full, home_country, away_country):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_MatchDetails
		self.event_id = str(event_id)
		self["title"] = Label(str(match_name) + " - Details")
		self["home_name_big"] = Label(str(home_full))
		self["away_name_big"] = Label(str(away_full))
		self["home_team"] = Pixmap()
		self["away_team"] = Pixmap()
		self["score"] = Label("- : -")
		self["status"] = Label(_("Loading..."))
		self["key_red"] = Label(_("Close"))
		
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
			h_pos, a_pos = (750, 680), (2790, 680)
			# info: Set specific big size for UHD (Width, Height)
			flag_size = eSize(200, 100)
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
		self.session.openWithCallback(self.navCallback, MatchMediaScreen, self.event_id, self["title"].getText().replace(" - Details", ""))

	def openStats(self):
		self.session.openWithCallback(self.navCallback, MatchStatisticsScreen, self.event_id, self["title"].getText().replace(" - Details", ""), self["home_name_big"].getText(), self["away_name_big"].getText())

	def navCallback(self, answer=None):
		if answer == "exit_all":
			self.close()

	def up(self):
		self["details_list"].up()

	def down(self):
		self["details_list"].down()

	def fetch_details(self):
		if sys.version_info[:2] == (3, 9): # Python 3.9
			def _get_data(eid):
				try:
					urls = ["https://api.sofascore.com/api/v1/event/{}/incidents".format(eid),
							"https://api.sofascore.com/api/v1/event/{}".format(eid)]
					sni = WebClientContextFactory()
					hdrs = {b'User-Agent':[b'Mozilla/5.0 (X11; Linux x86_64)'],
							b'Connection':[b'close'],
							b'Accept':[b'application/json, text/plain, */*'],
							b'Referer':[b'https://www.sofascore.com/'],
							b'Origin':[b'https://www.sofascore.com'],
							b'Cache-Control':[b'no-cache']}
					from twisted.internet import defer
					return defer.gatherResults([getPage(str.encode(u), contextFactory=sni, timeout=25, headers=hdrs) for u in urls])
				except Exception as e:
					logdata("MatchDetails", "Exception: %s" % str(e))
					return None, None
			def _done(raw):
				try:
					return [json.loads(r.decode() if r else b'{}') for r in raw]
				except Exception as e:
					logdata("MatchDetails", "Exception: %s" % str(e))
					return None, None

			d = deferToThread(_get_data, self.event_id)
			d.addCallback(lambda r: r.addCallback(_done))
			d.addCallbacks(self.process_data, lambda _: self.process_data(None))
		else:  # Python 2 and other 3.x without 3.9
			def _get_data(eid):
				headers = {'User-Agent': 'Mozilla/5.0'}
				try:
					url_i = "https://api.sofascore.com/api/v1/event/{}/incidents".format(eid)
					url_e = "https://api.sofascore.com/api/v1/event/{}".format(eid)
					res_i = requests.get(url_i, headers=headers, timeout=10).json()
					res_e = requests.get(url_e, headers=headers, timeout=10).json()
					return res_i, res_e
				except:
					return None, None
			d = deferToThread(_get_data, self.event_id)
			d.addCallback(self.process_data)

	def process_data(self, data):
		inc_js, ev_js = data
		if ev_js and 'event' in ev_js:
			ev = ev_js['event']
			h = ev.get('homeScore', {}).get('current', 0)
			a = ev.get('awayScore', {}).get('current', 0)
			self["score"].setText(str(h) + " - " + str(a))
			self["status"].setText(str(ev.get('status', {}).get('description', '')))

		gList = []
		if inc_js and 'incidents' in inc_js:
			if isUHD():
				ITEM_H = 120   # Row Height
				FONT_S = 50    # Font Size
				C_X    = 1620  # Minute X Position
				T_W    = 200   # Minute Width
				H_TXT_X = 40   # Home Player Name X
				H_TXT_W = 1450 # Home Player Name Width
				H_IMG_X = 1530 # Home Icon X
				A_IMG_X = 1850 # Away Icon X
				A_TXT_X = 1930 # Away Player Name X
				A_TXT_W = 1450 # Away Player Name Width
				IMG_W  = 60    # Fixed Width
				IMG_H  = 80    # Fixed Height
				IMG_Y  = 20    # Vertical Offset
			else:
				ITEM_H = 70    # Row Height
				FONT_S = 36    # Font Size
				C_X    = 850   # Minute X Position
				T_W    = 100   # Minute Width
				H_TXT_X = 10   # Home Player Name X
				H_TXT_W = 750  # Home Player Name Width
				H_IMG_X = 780  # Home Icon X
				A_IMG_X = 970  # Away Icon X
				A_TXT_X = 1040 # Away Player Name X
				A_TXT_W = 700  # Away Player Name Width
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
					if is_og:
						text = str(inc.get('player', {}).get('name', 'Own Goal')) + " (OG)"
						color = 0xFF0000
						icon_name = "owngoal.png"
					else:
						text = str(inc.get('player', {}).get('name', 'Goal'))
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
					text = str(inc.get('playerIn', {}).get('name', ''))
					color = 0xAAAAAA
					icon_name = "substitution.png"

				# --- Incident List Row Information ---
				res = [MultiContentEntryText()] # List row anchor
				res.append(MultiContentEntryText(pos=(C_X, 0), size=(T_W, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=itime)) # Match Minute
				
				icon_path = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/{}".format(icon_name)) # Icon Path
				png = loadPNG(icon_path) # Load Incident Icon

				if is_home:
					if png: res.append(MultiContentEntryPixmapAlphaBlend(pos=(H_IMG_X, IMG_Y), size=(IMG_W, IMG_H), png=png)) # Home Incident Icon
					res.append(MultiContentEntryText(pos=(H_TXT_X, 0), size=(H_TXT_W, ITEM_H), font=0, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=text, color=color)) # Home Player Name
				else:
					if png: res.append(MultiContentEntryPixmapAlphaBlend(pos=(A_IMG_X, IMG_Y), size=(IMG_W, IMG_H), png=png)) # Away Incident Icon
					res.append(MultiContentEntryText(pos=(A_TXT_X, 0), size=(A_TXT_W, ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=text, color=color)) # Away Player Name
				
				gList.append(res) # Add Row to List
		
		self["details_list"].setList(gList)


class MatchStatisticsScreen(Screen):
	def __init__(self, session, event_id, match_name, home_name, away_name):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_MatchStatistics
		self.event_id = event_id
		self["title"] = Label(str(match_name) + " - Statistics")
		self["home_team"] = Label(str(home_name))
		self["away_team"] = Label(str(away_name))
		self["key_red"] = Label(_("Close"))
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
		clean_title = self["title"].getText().replace(" - Statistics", "")
		self.session.openWithCallback(self.navCallback, MatchMediaScreen, self.event_id, clean_title)

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
		if sys.version_info[:2] == (3, 9):
			def _get_stats(eid):
				try:
					url = "https://api.sofascore.com/api/v1/event/{}/statistics".format(eid)
					sni = WebClientContextFactory()
					hdrs = {
						b'User-Agent': [b'Mozilla/5.0 (X11; Linux x86_64)'],
						b'Connection': [b'close'],
						b'Accept': [b'application/json, text/plain, */*'],
						b'Referer': [b'https://www.sofascore.com/'],
						b'Origin': [b'https://www.sofascore.com'],
					}
					return getPage(str.encode(url), contextFactory=sni, timeout=25, headers=hdrs)
				except Exception as e:
					logdata("MatchStats", "Exception: %s" % str(e))
					return None
			def _done(raw):
				try:
					return json.loads(raw.decode()) if raw else None
				except:
					return None
			d = _get_stats(self.event_id)
			d.addCallback(_done)
			d.addCallbacks(self.process_stats, lambda _: self.process_stats(None))
		else:
			def _get_stats(eid):
				headers = {'User-Agent': 'Mozilla/5.0'}
				try:
					url = "https://api.sofascore.com/api/v1/event/{}/statistics".format(eid)
					return requests.get(url, headers=headers, timeout=10).json()
				except:
					return None
			d = deferToThread(_get_stats, self.event_id)
			d.addCallback(self.process_stats)

	def process_stats(self, data):
		gList = []
		if isUHD():
			ITEM_H = 120  # Row Height: Increase to add space between rows
			FONT_S = 52   # Font Size: Increase to make text bigger
			W_LIST = 3440 # Total width of the list box
			HOME_X = 20   # Move Home value: Higher = Right, Lower = Left
			NAME_X = 400  # Move Stat Name: Higher = Right, Lower = Left
			AWAY_X = 3000 # Move Away value: Higher = Right, Lower = Left
			COL_W  = 400  # Width of the value boxes
			NAME_W = 2640 # Width of the middle name box
		else:
			ITEM_H = 80   # Row Height: Increase to add space between rows
			FONT_S = 36   # Font Size: Increase to make text bigger
			W_LIST = 1720 # Total width of the list box
			HOME_X = 10   # Move Home value: Higher = Right, Lower = Left
			NAME_X = 250  # Move Stat Name: Higher = Right, Lower = Left
			AWAY_X = 1450 # Move Away value: Higher = Right, Lower = Left
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
						# Force header to string for Py2
						header_raw = group.get('groupName', '')
						header_text = str("-- " + header_raw + " --") 
						res.append(MultiContentEntryText(pos=(0, 0), size=(W_LIST, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=header_text, color=0xffcc00))
						gList.append(res)
						
						for item in group.get('statisticsItems', []):
							res = []
							res.append(MultiContentEntryText()) # Anchor
							
							# Force all values to strings for Py2
							val_h = str(item.get('home', '0'))
							val_n = str(item.get('name', ''))
							val_a = str(item.get('away', '0'))
							
							# Home
							res.append(MultiContentEntryText(pos=(HOME_X, 0), size=(COL_W, ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=val_h))
							# Name
							res.append(MultiContentEntryText(pos=(NAME_X, 0), size=(NAME_W, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=val_n, color=0xaaaaaa))
							# Away
							res.append(MultiContentEntryText(pos=(AWAY_X, 0), size=(COL_W, ITEM_H), font=0, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=val_a))
							gList.append(res)
					break

		if not gList:
			res = []
			res.append(MultiContentEntryText()) # Anchor
			no_data_text = str(_("No statistics information available"))
			res.append(MultiContentEntryText(pos=(0, 0), size=(W_LIST, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=no_data_text, color=0xff0000))
			gList.append(res)
		
		self["stats_list"].setList(gList)


class MatchMediaScreen(Screen):
	def __init__(self, session, event_id, match_name):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_MatchMedia
		self.event_id = event_id

		self["title"] = Label(str(match_name) + " - Media")
		self["key_red"] = Label(_("Close"))
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
		clean_title = self["title"].getText().replace(" - Media", "")
		self.session.openWithCallback(self.navCallback, MatchStatisticsScreen, self.event_id, clean_title, "", "")

	def navCallback(self, answer=None):
		if answer == "exit_all":
			self.close("exit_all")
		else:
			self.close()

	def fetch_media(self):
		if sys.version_info[:2] == (3, 9):
			def _get_media(eid):
				try:
					url = "https://api.sofascore.com/api/v1/event/{}/media".format(eid)
					sni = WebClientContextFactory()
					hdrs = {
						b'User-Agent': [b'Mozilla/5.0 (X11; Linux x86_64)'],
						b'Connection': [b'close'],
						b'Accept': [b'application/json, text/plain, */*'],
						b'Referer': [b'https://www.sofascore.com/'],
						b'Origin': [b'https://www.sofascore.com'],
					}
					return getPage(str.encode(url), contextFactory=sni, timeout=25, headers=hdrs)
				except Exception as e:
					logdata("MatchMedia", "Exception: %s" % str(e))
					return None
			def _done(raw):
				try:
					return json.loads(raw.decode()) if raw else None
				except:
					return None
			d = _get_media(self.event_id)
			d.addCallback(_done)
			d.addCallbacks(self.process_media, lambda _: self.process_media(None))
		else:
			def _get_media(eid):
				headers = {'User-Agent': 'Mozilla/5.0'}
				try:
					url = "https://api.sofascore.com/api/v1/event/{}/media".format(eid)
					return requests.get(url, headers=headers, timeout=10).json()
				except:
					return None
			d = deferToThread(_get_media, self.event_id)
			d.addCallback(self.process_media)

	def process_media(self, data):
		gList = []
		if isUHD():
			ITEM_H = 120             # Row Height: Increase to add space between rows
			FONT_S = 52              # Font Size: Increase to make text bigger
			W_LIST = 3440            # Total width of the list box
			X_OFF  = 40              # Left Padding for text
			IMG_W, IMG_H = 100, 100   # info: Icon dimensions for UHD (100 is width, 100 is height)
			X_TEXT = 180             # info: Start position for text after the icon in UHD
		else:
			ITEM_H = 80              # Row Height: Increase to add space between rows
			FONT_S = 36              # Font Size: Increase to make text bigger
			W_LIST = 1720            # Total width of the list box
			X_OFF  = 20              # Left Padding for text
			IMG_W, IMG_H = 60, 60    # info: Icon dimensions for FHD (60 is width, 60 is height)
			X_TEXT = 120             # info: Start position for text after the icon in FHD

		self["media_list"].l.setItemHeight(ITEM_H)
		self["media_list"].l.setFont(0, gFont('Regular', FONT_S))
		
		path = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/")
		if isUHD():
			icon_yt = path + "youtube_iconUHD.png"
			icon_tw = path + "twitter_iconUHD.png"
		else:
			icon_yt = path + "youtube_icon.png"
			icon_tw = path + "twitter_icon.png"

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

				if icon_path and exists(icon_path):
					# info: Use LoadPixmap with size to force auto-scaling of the PNG file
					ptr = loadPNG(icon_path)
					if ptr:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(X_OFF, (ITEM_H - IMG_H)//2), size=(IMG_W, IMG_H), png=ptr))

				# info: Draw the video title text after the fixed icon position
				res.append(MultiContentEntryText(pos=(X_TEXT, 0), size=(W_LIST - X_TEXT, ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_text))
				gList.append(res)

		if not gList:
			res = [None, MultiContentEntryText()]
			err_msg = str(_("No media available"))
			res.append(MultiContentEntryText(pos=(0, 0), size=(W_LIST, ITEM_H), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=err_msg, color=0xff0000))
			gList.append(res)
		
		self["media_list"].setList(gList)

	def playVideo(self):
		cur = self["media_list"].getCurrent()
		if not cur or not cur[0]:
			return
		url = cur[0].strip()
		#logdata("Processing URL", str(url))
		self.play_timer_conn = None
		self.error_timer_conn = None
		is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()
		is_twitter = "twitter.com" in url.lower() or "x.com" in url.lower()
		if is_youtube:
			self.wait_dialog = self.session.open(MessageBox, _("Please wait while extracting video stream..."), MessageBox.TYPE_INFO, enable_input=False)
			from twisted.internet.threads import deferToThread
			def safe_extract(video_url):
				try:
					v_id = video_url
					if 'watch?v=' in v_id: v_id = v_id.split('watch?v=')[-1]
					elif 'youtu.be/' in v_id: v_id = v_id.split('youtu.be/')[-1]
					if '&' in v_id: v_id = v_id.split('&')[0]
					ytdl = YouTubeVideoUrl()
					result = ytdl.extract(v_id)
					return str(result) if result else ""
				except Exception as e:
					err_text = str(e)
					#logdata("EXTRACT_ERROR_THREAD_FUNC", err_text)
					return "ERROR:" + err_text
			deferToThread(safe_extract, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		elif is_twitter:
			self.wait_dialog = self.session.open(MessageBox, _("Please wait while extracting video stream..."), MessageBox.TYPE_INFO, enable_input=False)
			from twisted.internet.threads import deferToThread
			deferToThread(self.extract_twitter_stream, url).addCallback(self.playAfterExtract).addErrback(self.playback_error)
		else:
			self.playAfterExtract(str(url))

	def playAfterExtract(self, video_url):
		video_url = video_url or ""
		if hasattr(self, 'wait_dialog') and self.wait_dialog:
			self.wait_dialog.close()
		video_url_str = str(video_url)
		if "ERROR:" in video_url_str:
			err_msg = video_url_str.split("ERROR:", 1)[1].lstrip()
			lower_err = err_msg.lower()
			#logdata("playAfterExtract_lower", lower_err)
			if "country" in lower_err or "available" in lower_err:
				msg = _("This video is not available in your country or is private.")
				self.error_timer = eTimer()
				if DreamOS():
					self.error_timer_conn = self.error_timer.timeout.connect(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
				else:
					self.error_timer.callback.append(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
				self.error_timer.start(250, True)
				return
		if not video_url_str.startswith("http"):
			msg = _("Failed to extract video stream or link is broken.")
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
		#logdata("DASH_DEBUG", "is_yt: %s | has_exteplayer: %s | UseDash: %s" % (str(is_yt), str(has_exteplayer), str(config.plugins.FootOnSat.useDashMP4.value)))
		if is_yt and config.plugins.FootOnSat.useDashMP4.value and (not has_exteplayer or stype == 4097):
			#logdata("DASH_START", "Entering DASH logic...")
			#logdata("DASH_DEBUG_URL", "Full video_url: %s" % str(video_url))
			separator = '#EXT-X-STREAM-INF:AUDIO=' if '#EXT-X-STREAM-INF:AUDIO=' in video_url else SUBURI
			if separator in video_url:
				#logdata("DASH_READY", "Audio stream found via %s. Preparing download..." % separator)
				try:
					v_url = pure_url
					a_url = video_url.split(separator)[-1].replace('"', '').strip()
					if "#http_user_agent=" in a_url: a_url = a_url.split("#http_user_agent=")[0]
					a_tmp = "/tmp/a.mp4"
					ua = str(user_agent) if user_agent else "Mozilla/5.0"
					down_a = 'wget --no-check-certificate -U "%s" -O %s "%s"' % (ua, a_tmp, a_url)
					#logdata("DASH_DL", "Downloading audio: %s" % down_a)
					gst_cmd = "gst-launch-1.0 filesrc location=%s ! decodebin ! audioconvert ! audioresample ! alsasink" % a_tmp
					self.dash_process = subprocess.Popen('%s && %s' % (down_a, gst_cmd), shell=True, preexec_fn=os.setsid)
					#logdata("DASH_GST", "Audio download and background playback started.")
				except Exception as e:
					logdata("DASH_FATAL", "Error: %s" % str(e))
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
				self.session.open(MessageBox, _("Failed to extract video stream or link is broken."), MessageBox.TYPE_ERROR, timeout=10)
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
		if DreamOS():
			self.play_timer_conn = self.play_timer.timeout.connect(lambda: self.session.openWithCallback(self.stopDashAudio, MoviePlayer, ref))
		else:
			self.play_timer.callback.append(lambda: self.session.openWithCallback(self.stopDashAudio, MoviePlayer, ref))
		self.play_timer.start(200, True)

	def stopDashAudio(self, *args):
		if hasattr(self, 'dash_process') and self.dash_process:
			try:
				os.killpg(os.getpgid(self.dash_process.pid), signal.SIGTERM)
				#logdata("DASH_STOP", "Audio process killed.")
				del self.dash_process
				if exists("/tmp/a.mp4"): os.remove("/tmp/a.mp4")
			except:
				pass

	def extract_twitter_stream(self, url):
		try:
			import urllib3
			urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
		except: pass
		try:
			t_id = url.split('/')[-1].split('?')[0]
			api_url = "https://api.fxtwitter.com/i/status/%s" % t_id
			headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
			r = requests.get(api_url, headers=headers, timeout=15, verify=False)
			if r.status_code == 200:
				data = r.json()
				tweet = data.get('tweet', {})
				media = tweet.get('media', {})
				videos = media.get('videos', [])
				if videos:
					video_url = videos[0].get('url')
					if not isinstance(video_url, str):
						video_url = video_url.encode('utf-8')
					return video_url
			return None
		except Exception as e:
			logdata("Twitter Exception", str(e))
			return None

	def playback_error(self, failure):
		if hasattr(self, 'wait_dialog') and self.wait_dialog:
			self.wait_dialog.close()
		logdata("playback_error_raw", str(failure))
		msg = _("Failed to extract video stream or link is broken.")
		self.error_timer = eTimer()
		if DreamOS():
			self.error_timer_conn = self.error_timer.timeout.connect(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
		else:
			self.error_timer.callback.append(lambda: self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout=10))
		self.error_timer.start(250, True)


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

		logdata("ZAP_DEBUG", "=== NOTIFICATION START ===")
		logdata("ZAP_DEBUG", "Match: '%s'" % match)
		
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
				with connect(DB_PATH) as conn:
					c = conn.cursor()
					
					# Search for the fully normalized key (which has no spaces)
					c.execute("SELECT ref FROM zap_channels WHERE match = ?", (normalized_search_key,))
					row = c.fetchone()
				# 'conn.close()' is now called automatically
				
				if row and row[0]:
					from enigma import eServiceReference
					zap_ref = eServiceReference(str(row[0]))
					logdata("ZAP_DEBUG", "ZAP BY REFERENCE FOUND → %s (%s)" % (zap_ref.getName(), row[0]))
				else:
					logdata("ZAP_DEBUG", "No zap ref found (Search key: '%s')" % normalized_search_key)
					
			except Exception as e:
				logdata("ZAP_DEBUG", "ZAP LOOKUP ERROR: %s" % str(e))
				zap_ref = None # Ensure it is None on error

		# 🔥 CORRECTED FEATURE LOGIC START
		
		if config.plugins.FootOnSat.notify_zap.value == "2":
			# Case: Zap Only mode. Must suppress notification by NOT calling _do_actual_display.
			if zap_ref:
				# Zap channel found: Execute Zap immediately with sound.
				self._play_tone() 
				time.sleep(2.0)
				InfoBar.instance.session.nav.playService(zap_ref)
				InfoBar.instance.servicelist.addToHistory(zap_ref)
				logdata("ZAP_DEBUG", "playService called — channel switching...")
			else:
				# No Zap channel found: Do nothing. (NO ACTION, NO SOUND)
				logdata("ZAP_DEBUG", "Zap only mode (Option 2) selected. No Zap channel found, skipping notification and zap.")
			
			# Notification is suppressed: Manually advance queue and RETURN
			self._display_next_in_queue()
			logdata("ZAP_DEBUG", "=== NOTIFICATION END ===\n")
			return # Exit to prevent calling _do_actual_display
		
		# Default path (Option "1" or Zap disabled): Proceed to display the notification
		self._do_actual_display(match, compet, team1, team2, message, zap_ref=zap_ref)

	def _do_actual_display(self, match, compet, team1, team2, message=None, zap_ref=None):
		"""Show notification popup and execute Zap AFTER a 2.0s delay if a channel is found."""
		if not self.instance:
			logdata("ZAP_DEBUG", "Cannot show popup – no instance")
			return

		logdata("ZAP_DEBUG", "SHOWING NOTIFICATION POPUP: %s" % match)
		if message:
			logdata("ZAP_DEBUG", "Message: %s" % message)

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

		# 🔥 Play sound now, tied to the notification display (Option "1")
		self._play_tone() 

		FootOnSatNotifDialog.dialog.show()
		logdata("ZAP_DEBUG", "NOTIFICATION POPUP IS NOW VISIBLE")
		
		# 🔥 Perform the Zap and Delay HERE for option "1"
		if zap_ref:
			try:
				# 👇 DELAY HERE to let the user see/hear the notification FIRST
				time.sleep(2.0)
				logdata("ZAP_DEBUG", "Delay finished, executing Zap.")
				InfoBar.instance.session.nav.playService(zap_ref)
				InfoBar.instance.servicelist.addToHistory(zap_ref)
				logdata("ZAP_DEBUG", "playService called — channel switching...")

			except Exception as e:
				logdata("ZAP_DEBUG", "ZAP EXECUTION ERROR: %s" % str(e))
		else:
			logdata("ZAP_DEBUG", "Zap not required.")

		logdata("ZAP_DEBUG", "=== NOTIFICATION END ===\n")

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
			logdata("FootOnSatNotif", "No supported sound player found (aplay/gst-launch).")

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
			if fileExists(DB_PATH):
				self.deloldRecords()
				with connect(DB_PATH) as conn:
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
										message_next = "Kick-off in 15 minutes"
										notif_next_time = (match_time_obj - timedelta(minutes=15)).strftime("%H:%M - %Y-%m-%d")
									elif user_choice in ("2", "6"):
										# Next notification should be start time
										message_next = "Kick-off is NOW"
										notif_next_time = match_time_obj.strftime("%H:%M - %Y-%m-%d")
									else:
										# No more notifications required for this choice (e.g., choice 4: 30 min only)
										message_next = "Notifications Done"
										# Set next time to 1 minute after match start for guaranteed cleanup
										notif_next_time = (match_time_obj + timedelta(minutes=1)).strftime("%H:%M - %Y-%m-%d")
									
									# 1c. Update Database for next stage
									cur.execute("UPDATE LIVE_NOTIF set FIRST_NOTIF = ?, MESSAGE = ? WHERE MATCH = ?", (notif_next_time, message_next, match_name,))
									#logdata("FootOnSatNotif", "TRIGGER: 30-min Notif for %s. Next: %s" % (match_name, message_next))
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
										message_next = "Kick-off is NOW"
										notif_next_time = match_time_obj.strftime("%H:%M - %Y-%m-%d")
									else:
										# No more notifications required for this choice (e.g., choice 3, 7)
										message_next = "Notifications Done"
										# Set next time to 1 minute after match start for guaranteed cleanup
										notif_next_time = (match_time_obj + timedelta(minutes=1)).strftime("%H:%M - %Y-%m-%d")
										
									# 2c. Update Database for next stage
									cur.execute("UPDATE LIVE_NOTIF set FIRST_NOTIF = ?, MESSAGE = ? WHERE MATCH = ?", (notif_next_time, message_next, match_name,))
									#logdata("FootOnSatNotif", "TRIGGER: 15-min Notif for %s. Next: %s" % (match_name, message_next))
									continue

								elif time_diff_minutes <= 1:
									# --- Stage 3: Match Start Notification ---
									
									# 3a. Trigger Notification if option includes Start (1, 2, 5, 6)
									if user_choice in ("1", "2", "5", "6"):
										# Zap IS allowed here
										self.notify(match_name.strip(), row[1], row[3], row[4], allow_zap=True)
										#logdata("FootOnSatNotif", "TRIGGER: Match Start Notif and DB delete for match: %s" % match_name)
									else:
										# Log deletion without triggering final notification
										#logdata("FootOnSatNotif", "CLEANUP: Deleting record after final stage for match: %s (No Start Notif)" % match_name)
										pass
										
									# 3b. Delete the record regardless of the notification choice
									cur.execute("DELETE FROM LIVE_NOTIF WHERE MATCH = ?", (match_name,))
									continue
					conn.commit()

		except Exception as e:
			logdata("FootOnSatNotif", "ERROR in checkforNotif: %s" % str(e))
		
		finally:
			if 'gc' in sys.modules and sys.version_info >= (3, 14):  # Checks if the 'gc' (Garbage Collector) module is available and loaded.
				gc.collect()         # Forces immediate cleanup of unreferenced objects and file handles.
			self.is_checking = False # Reset the lock ensures it can run again later

	def deloldRecords(self):
		if not fileExists(DB_PATH):
			return
			
		with connect(DB_PATH) as conn:
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
							
							logdata("FootOnSatNotif", "CLEANUP SUCCESSFUL: Deleted LIVE_NOTIF and zap_channels for match: %s" % match_name)

					except Exception as e:
						logdata("FootOnSatNotif", "Error during record cleanup (%s): %s" % (date_string, str(e)))
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


class StandingsScreen(Screen):
	def __init__(self, session, league, url):
		self.session = session
		Screen.__init__(self, session)
		#logdata("StandingsScreen_init", "Initializing StandingsScreen for league: %s, url: %s" % (league, url))
		self.league = str(league)
		print("self.league: %s" % self.league)
		self.url = str(url)
		self.league = str(league).lower()
		if self.league in ("basketball", "nba", "nfl"):
			label_text = "Ties" if self.league in ("nfl") else "Streak"
			self.skin = SKIN_standingsbasketball % label_text
		else:
			self.skin = SKIN_standings
		self["standings_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		# FIX for Python 2 eLabel: encode to UTF-8 if not Python 3
		title_text = "%s Standings" % self.league
		if not PY3:
			title_text = title_text.encode('utf-8')
		self["title"] = Label(_(title_text))
		self["key_red"] = Button(_("To Close Press Ok or Exit"))
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

	def fetch_standings(self):
		# 1. Start parsing the URL to get IDs
		url_to_parse = self.url
		if not isinstance(url_to_parse, compat_str):
			url_to_parse = str(url_to_parse)

		parsed_url = urlparse(url_to_parse)
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
			logdata("StandingsScreen", "ERROR during URL parsing: %s" % str(e))
			#trace_error()
			
		if not tournament_id or not season_id or not tournament_id.isdigit() or not season_id.isdigit():
			#logdata("StandingsScreen", "CRITICAL ERROR: Failed to extract numeric IDs. T-ID:'%s', S-ID:'%s'." % (tournament_id, season_id))
			self.standings_data = []
			self.display_standings()
			return

		# 2. Construct the JSON API URL
		try:
			api_url = "http://api.sofascore.com/api/v1/unique-tournament/{}/season/{}/standings/total".format(
				tournament_id, season_id
			)
		except Exception as e:
			api_url = "https://api.sofascore.com/api/v1/unique-tournament/{}/season/{}/standings/total".format(
				tournament_id, season_id
			)
			
		#logdata("StandingsScreen", "Using SofaScore API URL: %s" % api_url)
		AGENT = b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'

		# =================================================================
		# === PY3/PY2 SPLIT: Only necessary structural change to fix Py2 ===
		# =================================================================
		
		if PY3:
			try:
				sniFactory = WebClientContextFactory(api_url)
			except Exception as e:
				#logdata("StandingsScreen", "Failed to create WebClientContextFactory: %s" % str(e))
				self.display_standings()
				return

			# DEBUG: Log the attempt
			#logdata("StandingsScreen", "Attempting fetch (Twisted/SNI FIX) for API: %s" % api_url)

			# Fetch using Twisted's getPage
			# Add headers for robust 403 prevention on older Twisted versions
			headers = {
				'Connection': ['close'],
				'Accept': ['application/json, text/plain, */*']
			}

			d = getPage(
				str.encode(api_url), 
				contextFactory=sniFactory, 
				timeout=10, 
				agent=AGENT 
			)

		else:
			# === Python 2 (Requests/deferToThread Logic for 403 bypass) ===
			try:
				# Imports are placed here to ensure they only happen in Py2 environment
				from twisted.internet.threads import deferToThread
				import requests
				import random
			except ImportError as e:
				#logdata("StandingsScreen", "CRITICAL ERROR: Python 2 requires 'requests' and 'deferToThread': %s" % str(e))
				self.display_standings()
				return None

			#logdata("StandingsScreen", "Attempting fetch (Py2 Requests FIX) for API: %s" % api_url)
			
			# --- Headers/UA for Py2 consistency/403 bypass ---
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

			def _fetch_with_requests_py2():
				try:
					r = requests.get(api_url, headers=headers2, timeout=10)
					r.raise_for_status()
					# Twisted expects a deferred result, which is the raw content
					return r.content 
				except Exception as e:
					#logdata("StandingsScreen", "Python 2 Requests fetch failed: %s" % str(e))
					# Raise to trigger the deferred errback
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
			#logdata("StandingsScreen", "JSON data fetched and parsed successfully.")

			if 'standings' not in data or not data['standings']:
				#logdata("StandingsScreen", "No 'standings' data found in JSON response.")
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
			logdata("StandingsScreen", "Failed to parse JSON for API %s: %s" % (api_url, str(e)))
			#trace_error()
			self.standings_data = []
			self.display_standings()

	def _standing_error_handler(self, failure, url):
		# This handles errors from getPage (e.g., Timeout, 403, DNS errors)
		error_message = failure.getErrorMessage()
		#logdata("StandingsScreen", "Twisted Fetch Error on %s: %s" % (url, error_message))
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
					#logdata("Logos", "Starting Requests download for logo: %s (PY2 FIX)" % team_name)
					
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
						#logdata("Logos", "ERROR: Downloaded content for '%s' is not an image (probably 403 HTML page)." % team_name)
						return False
						
					# Save the raw file content to the temporary location
					with open(temp_file, "wb") as f:
						f.write(data)

				success = False
				if ext == ".png":
					# If already PNG, just copy the file from /tmp to the final .png path
					shutil.copyfile(temp_file, filename_png)
					#logdata("Logos", "Successfully saved PNG logo for '%s'." % team_name)
					success = True
				elif PIL_AVAILABLE:
					# --- PIL CONVERSION LOGIC ---
					try:
						img = Image.open(temp_file)
						#logdata("img", "Downloading logo for '%s'" % img)
						# Handle potential transparent GIF/JPG by converting to RGBA
						if img.mode not in ('RGB', 'RGBA'):
							img = img.convert('RGBA')

						img.save(filename_png, 'PNG')
						#logdata("Logos", "Converted and saved %s logo for '%s' to PNG via PIL." % (ext[1:].upper(), team_name))
						success = True
					except Exception as e:
						logdata("Logos", "PIL conversion FAILED for %s: %s" % (team_name, str(e)))
						#trace_error() # Include trace for better debugging
						# Fallback to simple copy if PIL fails (e.g., corrupted file)
						shutil.copyfile(temp_file, filename_png)
						success = True # Still logged as found
				else:
					# --- NO PIL FALLBACK (Will cause display error) ---
					#logdata("Logos", "WARNING: PIL not available, saving raw %s data as PNG file for '%s'." % (ext[1:].upper(), team_name))
					shutil.copyfile(temp_file, filename_png)
					success = True

				# Clean up the temporary file
				if exists(temp_file):
					os.remove(temp_file)

				return success
					
			except Exception as e:
				logdata("Logos", "Failed to download/process logo for %s: %s" % (team_name, str(e)))
				#trace_error()
				return False
			finally:
				# Ensure cleanup regardless of success/failure
				if exists(temp_file):
					os.remove(temp_file)
		#logdata("Logos", "Starting check for league: %s" % self.league)

		# Ensure standings folder exists
		standings_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/")
		if not exists(standings_dir):
			try:
				os.makedirs(standings_dir)
				#logdata("Logos", "Created standings folder: %s" % standings_dir)
			except Exception as e:
				#logdata("Logos", "Failed to create standings folder %s: %s" % (standings_dir, str(e)))
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
				#logdata("Logos", "Phase 2 (Worldfootball): Scraping primary backup site (%s) for missing logos..." % primary_backup_url)
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
							
							#logdata("Logos", "Phase 2 Fuzzy Search for: '%s' (Normalized: '%s'). Match: %s" % (team_info["original_name"], team_to_search, team_match))

							if team_match:
								normalized_matched_title = team_match[0]
								original_title = normalized_title_map.get(normalized_matched_title) # Get the raw title
								img_tag = next((img for img in imgs if (img.get("title") == original_title or img.get("alt") == original_title) and img.get("src")), None)
								
								if img_tag:
									# Worldfootball uses relative paths, so join with the base URL
									logo_src = img_tag.get("src").split("?")[0]
									logo_url = urljoin(primary_backup_url, logo_src)
									
									# Use the original name for logging and saving
									if download_and_save_logo(team_info["original_name"], logo_url, headers, self.league):
										team_info["found"] = True
										logos_found += 1 # Critical counter update
										#logdata("Logos", "Found logo for '%s' using match to '%s' (worldfootball)." % (team_info["original_name"], original_title))

				except Exception as e:
					#logdata("Logos", "Error fetching from primary backup site %s -> %s" % (primary_backup_url, str(e)))
					pass
		
		# Final log of any still missing teams
		for team_info in teams_to_process:
			if not team_info["found"]:
				logdata("Logos", "MISSING FINAL logo for team: '%s'" % team_info["original_name"])

		#logdata("Logos", "Completed check_and_download_logos(), total logos found: %d" % logos_found)


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
			self.session.openWithCallback(self.close, MessageBox, _('No standings available for this league.'), MessageBox.TYPE_INFO, timeout=10)
		else:
			#logdata("display_standings", "Displaying standings, total entries: %d" % len(gList))
			pass
