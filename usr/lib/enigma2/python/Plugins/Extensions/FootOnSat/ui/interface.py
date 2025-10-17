# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import math
import codecs
import random
import time
import shutil
import traceback
import threading
import difflib
from time import strftime
from sqlite3 import connect
from bs4 import BeautifulSoup
from unicodedata import normalize
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from enigma import eTimer, gRGB, loadPNG, gPixmapPtr, RT_WRAP, ePoint, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont, getDesktop, eConsoleAppContainer
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaTest, MultiContentEntryPixmapAlphaBlend
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Button import Button
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
from Tools.LoadPixmap import LoadPixmap
from twisted.web.client import getPage, downloadPage
from twisted.internet.ssl import ClientContextFactory
from twisted.internet._sslverify import ClientTLSOptions
from .compat import PY3, compat_urlopen, compat_HTTPError, compat_URLError, compat_Request, compat_str

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
	from urllib.parse import urlparse, urljoin
except ImportError:
	from urlparse import urlparse, urljoin # Python 2 compatibility

reswidth = getDesktop(0).size().width()

ignore_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/ignore")
ignore_file = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/ignore/ignore-match.json")
DB_PATH = '/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/db/footonsat.db'

## url for Standings table
json_urls = {
	# Champions league
	"championsleague": "https://www.fctables.com/championsleague/",
	# Europa league
	"europaleague": "https://www.fctables.com/europaleague/",
	# Conference league
	"ConferenceLeague": "https://www.fctables.com/europa-conference-league/",

	# England league
	"premierleague": "https://www.fctables.com/england/premier-league/",
	# champion ship league
	"championship": "https://www.fctables.com/england/championship/",
	# Italy league
	"seriea": "https://www.skysports.com/serie-a-table",
	#"seriea": "https://www.fctables.com/italy/serie-a/",
	# France league
	"ligue1": "https://www.fctables.com/france/ligue-1/",
	# Spain league 1 + 2
	"laliga": "https://www.fctables.com/spain/liga-bbva/",
	"laliga2": "https://www.fctables.com/spain/liga-adelante/",
	# Germany league
	"bundesliga": "https://www.fctables.com/germany/1-bundesliga/",
	# Portugal league
	"liganos": "https://www.fctables.com/portugal/liga-zon-sagres/",
	# Belgium league
	"belgianpro": "https://www.fctables.com/belgium/jupiler-league/",
	# Turkey league
	"superLig": "https://www.fctables.com/turkey/super-lig/",
	# Netherlands league
	"eredivisie": "https://www.fctables.com/netherlands/eredivisie/",

	# Saudi Arabia league
	"saudiarabia": "https://www.fctables.com/saudi-arabia/1-division/",
	# Asia Champions league
	"afcchampions": "https://www.fctables.com/afcchampionsleague/",
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
	# Germany league
	"bundesliga": "https://www.worldfootball.net/competition/bundesliga/",
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
	# Asia Champions league
	"afcchampions": "https://www.worldfootball.net/competition/afc-champions-league-elite/",
}

def logdata(label_name = "", data = None):
	try:
		data=str(data)
		fp = open("/tmp/FootOnSat.log", "a")
		fp.write( str(label_name) + " : " + data+"\n")
		fp.close()
	except:
		trace_error()    
		pass

def trace_error():
	try:
		traceback.print_exc(file=sys.stdout)
		traceback.print_exc(file=open("/tmp/FootOnSat.log", "a"))
	except:
		pass

def DreamOS():
	if os.path.exists('/var/lib/dpkg/status'):
		return True
	return False

def readFromFile(filename):
	_file = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/{}".format(filename))
	with open(_file, 'r') as f:
		return f.read()

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


class WebClientContextFactory(ClientContextFactory):
	def __init__(self, url=None):
		domain = urlparse(url).netloc
		self.hostname = domain

	def getContext(self, hostname=None, port=None):
		ctx = ClientContextFactory.getContext(self)
		if self.hostname and ClientTLSOptions is not None: # workaround for TLS SNI
			ClientTLSOptions(self.hostname, ctx)
		return ctx


class FootOnSat(Screen):
	def __init__(self, session, link, *args):
		self.session = session
		Screen.__init__(self, session)
		if reswidth == 1920:
			skin = "assets/skin/FHD/interface.xml"
		elif reswidth >= 2560:
			skin = "assets/skin/UHD/interface.xml"
		else:
			skin = "assets/skin/FHD/interface.xml"
		self.skin = readFromFile(skin)
		self["setupActions"] = ActionMap(["FootOnsatActions", "ColorActions"],
		{
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
		self.items_per_page = 5 if reswidth >= 2560 else 4
		self.create_table()
		self.callAPI()

	def onWindowShow(self):
		self["list1"].onSelectionChanged.append(self.getChannels)
		self.enablelist1()
		self.disablelist2()
		self.iniMenu()

	def iniMenu(self):
		if len(self.matches) > 0:
			res = []
			gList = []
			self["list1"].l.setItemHeight(175)
			if reswidth >= 2560:
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
				if clean_status == 'FINISHED': # <-- NEW: Check for the status returned by the scraper
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
				banner = FootOnSat.setCompet(str(compet).lower())
				match_date = self.getTime(match_date)
				if not fileExists(flagTeam1):
					flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
				if not fileExists(flagTeam2):
					flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
				if not fileExists(teamlog1):
					teamlog1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/default.png")
				if not fileExists(teamlog2):
					teamlog2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/teamlog/default.png")
				if self.checkIfexist(match):
					notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_on.png")
				else:
					notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_off.png")
				# Initialize list entry
				res.append(MultiContentEntryText())
				# Team 1 flag/logteam
				if self.link == "basketball":
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(70, 5), size=(160, 160), png=loadPNG(teamlog1)))
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(212, 70), size=(40, 30), png=loadPNG(flagTeam1)))
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(420, 70), size=(40, 30), png=loadPNG(flagTeam1)))
				# Score team 1
				if self.link != "basketball":
					if reswidth >= 2560:
						res.append(MultiContentEntryText(pos=(500, 69), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=0xFF0000))
					else:
						res.append(MultiContentEntryText(pos=(482, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=0xFF0000))
				 # Team 2 flag/logteam
				if reswidth >= 2560:
					if self.link == "basketball":
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1440, 5), size=(160, 160), png=loadPNG(teamlog2)))
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1550, 70), size=(40, 30), png=loadPNG(flagTeam2)))
					else:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1550, 70), size=(40, 30), png=loadPNG(flagTeam2)))
				else:
					if self.link == "basketball":
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1030, 10), size=(160, 160), png=loadPNG(teamlog2)))
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1012, 70), size=(40, 30), png=loadPNG(flagTeam2)))
					else:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(1142, 70), size=(40, 30), png=loadPNG(flagTeam2)))
				# Score team 2
				if self.link != "basketball":
					if reswidth >= 2560:
						res.append(MultiContentEntryText(pos=(1490, 69), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=0xFF0000))
					else:
						res.append(MultiContentEntryText(pos=(1092, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=0xFF0000))
				# Competition banner
				if not self.link == "basketball":
					try:
						res.append(MultiContentEntryPixmapAlphaTest(pos=(65, 6), size=(320, 163), png=loadPNG(banner), flags=BT_SCALE))
					except TypeError:
						res.append(MultiContentEntryPixmapAlphaTest(pos=(65, 6), size=(320, 163), png=loadPNG(banner)))
				# Notification icon
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(-20, 63), size=(70, 50), png=loadPNG(notif)))
				# Match name
				if reswidth >= 2560:
					if self.link == "basketball":
						res.append(MultiContentEntryText(pos=(390, 69), size=(1000, 40), font=0, flags=RT_HALIGN_LEFT | RT_HALIGN_CENTER, text=str(match)))
					else:
						res.append(MultiContentEntryText(pos=(550, 69), size=(900, 40), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(match)))
				else:
					if self.link == "basketball":
						res.append(MultiContentEntryText(pos=(390, 66), size=(500, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(match)))
					else:
						res.append(MultiContentEntryText(pos=(500, 66), size=(570, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(match)))
				# status_text + match_status
				if (team1_score != "" or match_status != "") and self.link != "basketball":
					# If score or status exists, display the dynamic status/time (e.g., "Live: 70 min" or "Status: FT")
					if reswidth >= 2560:
						res.append(MultiContentEntryText(pos=(420, 120), size=(1000, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=0xFF0000))
					else:
						res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_prefix + "%s" % status_text), color=0xFF0000))
				else:
					# Otherwise, display the scheduled Kick-off time
					if reswidth >= 2560:
						if self.link == "basketball":
							res.append(MultiContentEntryText(pos=(430, 120), size=(1000, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(1000, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
					else:
						if self.link == "basketball":
							res.append(MultiContentEntryText(pos=(430, 120), size=(500, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
						else:
							res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
				# Competition name
				if reswidth >= 2560:
					if self.link == "basketball":
						res.append(MultiContentEntryText(pos=(430, 15), size=(1000, 40), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
					else:
						res.append(MultiContentEntryText(pos=(420, 15), size=(1000, 40), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
				else:
					if self.link == "basketball":
						res.append(MultiContentEntryText(pos=(430, 15), size=(500, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
					else:
						res.append(MultiContentEntryText(pos=(420, 15), size=(785, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
				gList.append(res)
				res = []
			self["list1"].setList(gList)
			if self.link in ["today", "basketball"]:
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
			self.session.openWithCallback(self.exit, MessageBox, _('No schedules in this section at this time'), MessageBox.TYPE_INFO, timeout=10)

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
		elif self.selectedList == self["list1"]:
			self.exit()

	def right(self):
		if self.selectedList.getCurrent():
			self.selectedList = self["list2"]
			self.enablelist2()
			self.updateChannelData()

	def listDOWN(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveDown)
		if self.selectedList == self["list1"]:
			self.disablelist2()
			self.updateCounter()
			self.resetChannelinfo()
		if self.selectedList == self["list2"]:
			self.updateChannelData()

	def listUP(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveUp)
		if self.selectedList == self["list1"]:
			self.disablelist2()
			self.updateCounter()
			self.resetChannelinfo()
		if self.selectedList == self["list2"]:
			self.updateChannelData()

	def create_table(self):
		with connect(DB_PATH) as conn:
			cur = conn.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS LIVE_NOTIF (MATCH TEXT primary key , COMPET TEXT , DATE TEXT , TEAM1_FLAG TEXT , TEAM2_FLAG TEXT , FIRST_NOTIF TEXT , FIRST_NOTIF_STATUS TEXT , LIVE_NOTIF_STATUS TEXT,MESSAGE TEXT)')

	def ok(self):
		if self.selectedList == self["list1"] and len(self.matches) > 0:
			index = self['list1'].getSelectionIndex()
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

			# Only allow selection/unselection for future matches
			if datetime.strptime(match_date, "%H:%M - %Y-%m-%d") > datetime.now():
				if self.checkIfexist(match):
					# --- UNSELECT ACTION --- (Match is already in the DB)
					with connect(DB_PATH) as conn:
						cur = conn.cursor()
						cur.execute("DELETE FROM LIVE_NOTIF WHERE MATCH = ?", (match,))
					# Re-enable the log line for clarity on unselect
					#logdata("FootOnSatNotif", "UNSELECT: Deleted notification for match: %s" % match) 
				else:
					# --- SELECT ACTION --- (Match is NOT in the DB)
					
					# NOTE: Removed the 'if not self.sameDate(match_date):' check 
					#       to allow multiple matches at the same time.
					
					with connect(DB_PATH) as conn:
						cur = conn.cursor()
						first_notif, message = self.setFirstNotifTime(match_date)
						
						# Use "Waiting" for both status fields as per current schema, 
						# relying on FIRST_NOTIF time for sequential updates.
						cur.execute("INSERT INTO LIVE_NOTIF(MATCH,COMPET,DATE,TEAM1_FLAG,TEAM2_FLAG,FIRST_NOTIF,FIRST_NOTIF_STATUS,LIVE_NOTIF_STATUS,MESSAGE) values (?,?,?,?,?,?,?,?,?)", (
							match, compet, match_date, flag1, flag2, first_notif, "Waiting", "Waiting", message,))
						
						# Re-enable the log line for clarity on select
						#logdata("FootOnSatNotif", "SELECT: Inserted notification for match: %s. Notif time: %s" % (match, first_notif))
			
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
			match = match
		else:
			match = match.decode('utf-8')
		with connect(DB_PATH) as conn:
			cur = conn.cursor()
			cur.execute("SELECT MATCH FROM LIVE_NOTIF WHERE MATCH = ?", (match,))
			data = cur.fetchone()
			if data is None:
				return False
			else:
				return True

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
		url = 'https://raw.githubusercontent.com/fairbird/footonsat-api/main/{}.json'.format(self.link)
		sniFactory = WebClientContextFactory(url)
		getPage(str.encode(url), contextFactory=sniFactory).addCallback(self.getData).addErrback(self.error)

	def error(self, error=None):
		if error:
			self.session.openWithCallback(self.exit, MessageBox, _('An Unexpected HTTP Error Occurred During The API Request !!'), MessageBox.TYPE_ERROR, timeout=10)

	def fetch_live_results(self):
		"""
		Fetch and parse live results from Flashscore.com (mobile) using a resilient 
		parsing strategy for the br-separated, non-table HTML structure provided.
		"""
		
		# NOTE: This code assumes necessary imports (like re, datetime, BeautifulSoup, etc.) are available.
		url = "https://m.flashscore.com/" 
		#logdata("FootOnSat-LiveFetch", "Starting fetch: %s" % url)
		
		# Using the base URL as confirmed in your HTML sample
		headers = {
			"User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Mobile Safari/537.36",
			"Accept-Language": "en-US,en;q=0.9",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
		}
		
		html = None
		# --- Network Fetch ---
		try:
			request = compat_Request(url, headers=headers)
			response = compat_urlopen(request, timeout=5)  
			raw_html_content = response.read()
			
			if PY3:
				html = raw_html_content.decode('utf-8', errors="ignore")
			else:
				html = compat_str(raw_html_content)
			
			#logdata("FootOnSat-LiveFetch", "Fetched HTML length: %d" % len(html))
		except Exception as e:
			#logdata("FootOnSat-LiveFetch-ERROR", "Failed to fetch %s: %s" % (url, str(e)))
			return
		
		if not html:
			return

		# <<< CRITICAL SPEED OPTIMIZATION: Extract only the data block >>>
		# Look for the block containing match results
		match_block = re.search(r'<div id="score-data">(.*?)</div><p class="advert-bottom', html, re.DOTALL)
		
		if match_block:
			html_to_parse = match_block.group(1)
			#logdata("FootOnSat-LiveFetch-OPT", "Parsing small block (length: %d)" % len(html_to_parse))
		else:
			html_to_parse = html
			#logdata("FootOnSat-LiveFetch-OPT", "WARNING: Data block not found, parsing full page (slow fallback).")
			
		soup = BeautifulSoup(html_to_parse, "html.parser")
		matches_data = []
		
		# --- Data Extraction (Targeting the <a> tag with score and its siblings) ---
		# The structure is: <span>Time/Status</span>Team1 - Team2 <a class="fin/sched/live">Score</a><br />
		for score_link in soup.find_all("a", class_=re.compile(r'(fin|live|sched)')):
			try:
				# 1. Extract Score and Base Status
				score_text = score_link.get_text(strip=True)
				score_class = score_link.get('class', [''])[0] 
				
				# Check for scheduled or unplayed scores
				if score_text == "-:-":
					continue
				
				# Extract the team string (e.g., "Equatorial Guinea - Liberia")
				# This text node is a preceding sibling of the score_link <a>
				team_string = score_link.previous_sibling
				if team_string and isinstance(team_string, compat_str):
					team_string = team_string.strip()
				else:
					# Fallback for complex structure with images/other elements
					continue

				# 2. Extract Status/Time
				# The status is in a span tag or a text node before the team string.
				status_span = score_link.find_previous_sibling("span")
				scraped_status = ""
				
				if status_span and status_span.get('class', [''])[0] == 'live':
					scraped_status = status_span.get_text(strip=True)
				elif status_span: 
					# Use the text of the span element that contains the scheduled time (for live matches it will be minute)
					scraped_status = status_span.get_text(strip=True)

				# 3. Status Normalization (The Fix)
				match_status = scraped_status.strip().upper() if scraped_status else ''
				
				# A. FINISHED matches: Check the link class or known text status
				if score_class == 'fin' or match_status in ('FT', 'AET', 'PEN'):
					match_status = 'FINISHED'
				# B. HALFTIME matches: Check for HT status
				elif match_status == 'HALF TIME': # Based on the HTML: <span class="live">Half Time</span>
					match_status = 'HALFTIME'
				# C. LIVE minute matches: Preserve the minute number
				elif re.match(r'^\d{1,3}[\'+]*\+?\d*$', match_status):
					# This preserves minutes like '51', '77', '90+' etc.
					pass 
				# D. Any other non-recognized status, defaults to LIVE if score link is "live"
				elif score_class == 'live':
					match_status = 'LIVE'
				else:
					# For scheduled/unknown types that weren't captured by 'fin' class
					continue 

				# 4. Extract Teams and Scores
				teams = re.split(r'\s*-\s*', team_string)
				if len(teams) != 2:
					# Try to strip out noise before splitting (e.g., the red card images)
					team_string_clean = re.sub(r'<img[^>]*>', '', team_string)
					teams = re.split(r'\s*-\s*', team_string_clean)
					if len(teams) != 2:
						#logdata("FootOnSat-Scrape-WARN", "Failed to parse teams from: '%s'" % team_string)
						continue
						
				team1, team2 = [t.strip() for t in teams]
				
				# Strip score from noise like red card images or extra text near the score
				score_text_clean = re.sub(r'[^0-9:]', '', score_text)
				if ":" not in score_text_clean:
					continue
					
				team1_score, team2_score = score_text_clean.split(":")
				match_name = "%s vs %s" % (team1, team2)
				
				matches_data.append({
					"match_name": match_name,
					"team1_score": team1_score.strip(),
					"team2_score": team2_score.strip(),
					"team1": team1,  
					"team2": team2,  
					"match_status": match_status 
				})
				#logdata("FootOnSat-Scrape", "Scraped Live: %s (%s:%s) Status: %s" % (match_name, team1_score, team2_score, match_status))
			except Exception as e:
				#logdata("FootOnSat-Scrape-ERROR", "Error processing scraped match: %s" % str(e))
				continue
		
		# --- Match Assignment Logic ---
		matches_list = [list(match) for match in self.matches]
		
		now = datetime.now()
		TIME_OFFSET = timedelta(minutes=3) 
		now_adjusted = now - TIME_OFFSET
		#logdata("FootOnSat-Time-Adjust", "Local time adjusted by %s seconds for sync." % TIME_OFFSET.total_seconds())
		
		# --- Debugging Name Cleaning Helper (Acronym Focus) ---
		def _clean_name(name, source=""):
			# Log the raw input name
			#logdata("FootOnSatNotif", "DEBUG CLEAN START: Source='%s', Raw Name='%s'" % (source, name))
			
			# Normalization and Python 2/3 handling (unchanged for safety)
			if not PY3 and isinstance(name, str):
				name = name.decode('ascii', 'ignore')
			
			try:
				if PY3:
					name = normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
				else:
					name = normalize('NFKD', name.decode('utf-8')).encode('ascii', 'ignore')
			except: 
				pass 
				
			name = name.strip().lower()

			# Handle dotted abbreviations (e.g., U.A.E. -> uae, U.S.A. -> usa)
			name = re.sub(r'\b([a-z])\.([a-z])(?:\.([a-z]))*\.?\b', lambda m: ''.join(c for c in m.group(0) if c.isalpha()), name)
			if 'uae' in name:
				name = name.replace('uae', 'united arab emirates')
			# CRITICAL ADDITION: Add the words from the full name that MUST be ignored
			NOISE_PATTERN = r'\b(reserves?|club|team|squad|sport|athletic|calcio|foot|junior|senior|amateur|ii|b|of|the|and|a|utd|atl|fc|cf|as|ac|republic|federal|states|city|borough|county|national|squadra|selec|internacional)\b'
			name = re.sub(NOISE_PATTERN, ' ', name, flags=re.IGNORECASE)

			name = re.sub(r'\sw\s*$', ' ', name)
			name = re.sub(r'\sw\s', ' ', name)
			
			# Aggressively remove all non-alphanumeric characters (dots/hyphens are now gone)
			name = re.sub(r'[^a-z0-9]+', ' ', name)
			
			# Collapse multiple spaces into a single space
			name = re.sub(r'\s+', ' ', name) 
			
			final_cleaned_name = name.strip()
			
			# Log the final cleaned output name
			#logdata("FootOnSatNotif", "DEBUG CLEAN END: Cleaned Name='%s'" % final_cleaned_name)
			
			return final_cleaned_name
		# -----------------------------------------------------------------------
		SIMILARITY_THRESHOLD = 0.50  # Change from 0.60 to 0.50

		for match in matches_list:
			match_name_full = match[0]
			try:
				# Assuming match[1] is the time string "HH:MM - YYYY-MM-DD"
				match_date = datetime.strptime(match[1], "%H:%M - %Y-%m-%d")
			except ValueError:
				match_date = now_adjusted 
				
			# CRITICAL CHECK: Check if match is finished based on scraped data 
			is_finished = False
			local_teams_temp = re.split(r'\s+vs\s+|\s+-\s+', match_name_full)
			
			if len(local_teams_temp) == 2:
				local_t1_norm_simple = _clean_name(local_teams_temp[0])
				local_t2_norm_simple = _clean_name(local_teams_temp[1])
				
				for live_match in matches_data:
					if live_match["match_status"] == 'FINISHED':
						live_t1_norm_simple = _clean_name(live_match["team1"])
						live_t2_norm_simple = _clean_name(live_match["team2"])
						
						# Direct match OR swapped match
						if ((local_t1_norm_simple == live_t1_norm_simple and local_t2_norm_simple == live_t2_norm_simple) or
							(local_t1_norm_simple == live_t2_norm_simple and local_t2_norm_simple == live_t1_norm_simple)):
							is_finished = True
							break
						
			if match_date <= now_adjusted or is_finished:
				# Proceed with score matching
				local_teams = re.split(r'\s+vs\s+|\s+-\s+', match_name_full)
				if len(local_teams) != 2:
					continue
					
				local_t1_norm = _clean_name(local_teams[0])
				local_t2_norm = _clean_name(local_teams[1])
				
				found = False
				best_similarity = 0.0
				best_live_match = None
				
				for live_match in matches_data:
					live_t1_norm = _clean_name(live_match["team1"])
					live_t2_norm = _clean_name(live_match["team2"])
					
					# Calculate similarity for both straight and swapped orders
					sim_t1_straight = SequenceMatcher(None, local_t1_norm, live_t1_norm).ratio()
					sim_t2_straight = SequenceMatcher(None, local_t2_norm, live_t2_norm).ratio()
					avg_sim_straight = (sim_t1_straight + sim_t2_straight) / 2
					
					sim_t1_swap = SequenceMatcher(None, local_t1_norm, live_t2_norm).ratio()
					sim_t2_swap = SequenceMatcher(None, local_t2_norm, live_t1_norm).ratio()
					avg_sim_swap = (sim_t1_swap + sim_t2_swap) / 2
					
					current_similarity = max(avg_sim_straight, avg_sim_swap)
						
					if current_similarity > best_similarity:
						best_similarity = current_similarity
						
						# Decide which order to use for score assignment
						if avg_sim_straight >= avg_sim_swap:
							# Use straight order (Team 1 -> live Team 1, Team 2 -> live Team 2)
							best_live_match = {
								"team1_score": live_match["team1_score"],
								"team2_score": live_match["team2_score"],
								"match_status": live_match["match_status"]
							}
						else:
							# Use swapped order (Team 1 -> live Team 2, Team 2 -> live Team 1)
							best_live_match = {
								"team1_score": live_match["team2_score"],
								"team2_score": live_match["team1_score"],
								"match_status": live_match["match_status"]
							}

				if best_similarity >= SIMILARITY_THRESHOLD and best_live_match:
					# --- 1. ASSIGNMENT BLOCK (SUCCESS) ---
					if config.plugins.FootOnSat.livescore.value == "3":
						match[5] = compat_str(best_live_match["team1_score"]).strip()
						match[6] = compat_str(best_live_match["team2_score"]).strip()
						match[7] = compat_str(best_live_match["match_status"]).strip()  
					else:
						match[5] = ""
						match[6] = ""
						match[7] = ""
					found = True
					# NEW DEBUG LOG FOR SUCCESSFUL ASSIGNMENT (NOTIF OFF)
					#logdata("FootOnSat-Notify-SUCCESS", "Assigned Score to %s (Sim: %.3f): %s-%s, Status: %s" % (match_name_full, best_similarity, match[5], match[6], match[7]))
					
				if match_date <= now + timedelta(hours=2): 
					# --- 2. RESET BLOCK (NOT FOUND, IN 2-HOUR WINDOW) ---
					if not found:
						match[5] = ""
						match[6] = ""
						match[7] = ""
						# NEW DEBUG LOG FOR RESET (NOTIF ON)
						#logdata("FootOnSat-Notify-RESET", "Reset status for upcoming match %s. Eligible for notification." % match_name_full)
				else:
					# --- 3. CLEANUP BLOCK (TOO OLD OR FAR FUTURE) ---
					if match_date < now_adjusted:
						# Match has passed the time/tracking window 
						match[5] = ""
						match[6] = ""
						match[7] = ""  
						# NEW DEBUG LOG FOR CLEANUP
						#logdata("FootOnSat-Notify-CLEANUP", "Clearing old match data for %s" % match_name_full)
					# else: Match is far in the FUTURE, scores remain empty.
					
			else:
				# Match has not started yet (far in the future)
				match[5] = ""
				match[6] = ""
				match[7] = ""  
				
		self.matches = matches_list

	def getData(self, data):
		list = []
		try:
			self.js = json.loads(data)
		except Exception as e:
			self.session.openWithCallback(self.exit, MessageBox, _('Invalid API data! Check logs.'), MessageBox.TYPE_ERROR, timeout=10)
			return

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
			if config.plugins.FootOnSat.finished.value == "2": 
				HOUR = 2
			else:
				# Default to 3 hours if option is not '2'
				HOUR = 5
		except AttributeError:
			# Fallback in case the config element is missing or not properly initialized
			HOUR = 2

		# Define the duration for how long a match is considered 'live' or recent
		LIVE_DURATION = timedelta(hours=HOUR) 
		#logdata("FootOnSat-Duration", "Set live duration to %d hours." % HOUR)
		
		# ... (rest of the fetching and parsing logic) ...

		if self.js['footonsat'] != []:
			for match in self.js['footonsat']:
				try:
					compet = str(match['compet']).strip()
					for suffix in [' - Week ', ' - Matchday ', ' - Round ']:
						if suffix in compet:
							compet = compet.split(suffix)[0].strip()

					if compet not in ignored_competitions:
						match_date = datetime.strptime(match['date'] + ' ' + match['time'], '%Y-%m-%d %H:%M')
						match_date_adjusted = datetime.strptime(self.getTime(match['time'] + ' - ' + match['date']), '%H:%M - %Y-%m-%d')

						is_upcoming = match_date_adjusted > now
						is_live = now >= match_date_adjusted and now <= match_date_adjusted + LIVE_DURATION

						# 2. UPDATED: Initialize scores/status from JSON for all live/past matches
						team1_score = str(match.get('score1', "")).strip()
						team2_score = str(match.get('score2', "")).strip()
						match_status = "" # This will be overwritten by fetch_live_results if needed

						append_match = False

						if is_upcoming:
							append_match = True
							team1_score = "" # Clear initial scores for upcoming matches
							team2_score = ""
						elif is_live:
							if config.plugins.FootOnSat.livescore.value in ["2", "3"]:
								append_match = True
							# If config.livescore.value is NOT "3", scores are cleared later if needed, but we keep them here for the upcoming live score fetch.
						else:
							# Skip past matches outside the LIVE_DURATION window
							pass

						if append_match:
							list.append([str(match['match']),
										 str(match['time']) + ' - ' + str(match['date']),
										 str(match['compet']),
										 str(match['flags']['team1']),
										 str(match['flags']['team2']),
										 team1_score,
										 team2_score,
										 match_status])
					else:
						logdata("getData", "Ignored competition: " + str(match['match']) + ", Compet: " + compet)
				except KeyError:
					#logdata("getData-error", "KeyError on match: " + str(match))
					pass

			self.matches = list

			# Only fetch live results for live/finished matches if livescore is set to "3"
			if config.plugins.FootOnSat.livescore.value == "3":
				if config.plugins.FootOnSat.livescoresections.value == "1":
					self.fetch_live_results()
				elif config.plugins.FootOnSat.livescoresections.value == "2":
					if self.link == "today":
						self.fetch_live_results()

			self.onWindowShow()
		else:
			self.session.openWithCallback(self.exit, MessageBox, _('No schedules in this section at this time'), MessageBox.TYPE_ERROR, timeout=10)
		
	def getChannels(self):
		list = []
		res = []
		gList = []
		self["list2"].l.setItemHeight(50)
		if reswidth >= 2560:
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
		if not os.path.exists(ignore_dir):
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
			import io
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
		if os.path.exists(ignore_file):
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
			else:
				logdata("manageIgnoreFile", "Competition not removed: " + (compet_str if compet_str else "None") + " (not in ignore list)")
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
			else:
				logdata("manageIgnoreFile", "Competition not added: " + (compet_str if compet_str else "None") + " (already ignored or empty)")
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
		if self.link == "today" and self.selectedList == self["list1"] and len(self.matches) > 0:
			try:
				index = self['list1'].getSelectionIndex()
				# logdata("keyRed", "Selected match tuple: " + str(self.matches[index]))
				compet = str(self.matches[index][2]).strip()
				# Remove week/round/matchday suffixes
				for suffix in [' - Week ', ' - Matchday ', ' - Round ']:
					if suffix in compet:
						compet = compet.split(suffix)[0].strip()
				# logdata("keyRed", "Attempting to ignore competition: " + (compet if compet else "None"))
				if not compet:
					# logdata("keyRed", "Competition is empty or invalid")
					self.session.open(MessageBox, _('No valid competition selected!'), MessageBox.TYPE_ERROR, timeout=5)
					return
				# Load current ignored competitions
				ignored_before = self.manageIgnoreFile()
				# Add selected competition to ignore list
				self.manageIgnoreFile(compet=compet)
				ignored_after = self.manageIgnoreFile()
				if compet in ignored_after and compet not in ignored_before:
					self.session.open(MessageBox, _('Competition "%s" added to ignore list') % compet, MessageBox.TYPE_INFO, timeout=5)
				else:
					logdata("keyRed", "Competition " + compet + " not added (already ignored or failed)")
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

# Note: All necessary imports and mocks (like DB_PATH, logdata, time, timedelta, connect, config, etc.) are assumed to be present above this class definition.

class FootOnSatNotif:
	def __init__(self):
		self.dialog = None

	def startNotif(self, session):
		self.dialog = session.instantiateDialog(FootOnsatNotifScreen)

FootOnSatNotifDialog = FootOnSatNotif()

class FootOnsatNotifScreen(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		if reswidth == 1920:
			skin = "assets/skin/FHD/FootOnsatNotif.xml"
		elif reswidth >= 2560:
			skin = "assets/skin/UHD/FootOnsatNotif.xml"
		else:
			skin = "assets/skin/FHD/FootOnsatNotif.xml"
		self.skin = readFromFile(skin)
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
		self.FootOnsatTimer.start(15000)
		self.onhideTimer = eTimer()
		try:
			# CRITICAL CHANGE: Handler now points to the queue processor
			self.onhideTimer.timeout.get().append(self._display_next_in_queue)
		except:
			self.onhideTimer_conn = self.onhideTimer.timeout.connect(self._display_next_in_queue)
			
		# --- ADDED STATE FOR SEQUENTIAL DISPLAY AND BUG FIX ---
		self.matches_queue = []
		self.is_displaying = False
		self.is_checking = False # CRITICAL Re-entry Lock for checkforNotif

	def _update_display_only(self, match, compet, team1, team2, message=None):
		"""Helper to update the screen elements only."""
		if self.instance:
			if FootOnSatNotifDialog.dialog is not None:
				self['match'].setText(_(str(match)))
				if message:
					self['live'].hide()
					self['message'].setText(str(message))
				else:
					self['live'].show()
					self['message'].setText("")
				banner = FootOnSat.setCompet(compet.lower())
				self['compet'].instance.setPixmapFromFile(banner)
				flag1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team1))
				flag2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team2))
				if not fileExists(flag1):
					flag1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
				if not fileExists(flag2):
					flag2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
				self['flag1'].instance.setPixmapFromFile(flag1)
				self['flag2'].instance.setPixmapFromFile(flag2)
				FootOnSatNotifDialog.dialog.show()

	def _display_next_in_queue(self):
		"""Pulls the next match from the queue, displays it, and schedules the next display or hides the dialog."""
		
		self.onhideTimer.stop() 
		
		if not self.matches_queue:
			# Queue is empty: End of sequence, hide the dialog.
			self.hideNotif() 
			return

		# Get the next match to display
		match_data = self.matches_queue.pop(0)
		
		# Display the current match info 
		self._update_display_only(
			match_data['match'], 
			match_data['compet'], 
			match_data['team1'], 
			match_data['team2'], 
			match_data['message']
		)
		
		# Schedule the next display or hide 
		if self.matches_queue:
			# CRITICAL CHANGE: 5-second delay between matches (5000ms)
			self.onhideTimer.start(5000) 
		else:
			# 6 seconds before final hide (original time)
			self.onhideTimer.start(6000) 
			
	def _start_sequential_display(self):
		"""Starts the sequential display process if not already running."""
		if self.is_displaying:
			return
			
		self.is_displaying = True
		# Play sound once per batch (assuming first time notify is called is start of batch)
		try:
			if os.path.exists("/usr/bin/aplay"):
				os.system('aplay /usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/sound/notif1.wav &')
			else:
				os.system('ffmpeg -hide_banner -loglevel quiet -i "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/sound/notif1.wav" -filter:a "volume=1.0" -f alsa default &')
		except Exception as e:
			logdata("FootOnSatNotif", "Sound play error: %s" % e)
		
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
										self.notify(match_name.strip(), row[1], row[3], row[4], row[8])
									
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
										self.notify(match_name.strip(), row[1], row[3], row[4], row[8])
									
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
										# Trigger the start notification (no message)
										self.notify(match_name.strip(), row[1], row[3], row[4])
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
			self.is_checking = False # Reset the lock ensures it can run again later

	def deloldRecords(self):
		with connect(DB_PATH) as conn:
			cur = conn.cursor()
			# Select all columns to get the match name (row[0]) and date (row[2]) for logging
			rows = cur.execute("select * from LIVE_NOTIF")
			rows = rows.fetchall()
			# Note: today is only checked for Date comparison, not time.
			today = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), "%Y-%m-%d %H:%M") 
			if len(rows) > 0:
				for row in rows:
					# row[2] is the DATE field
					record_date = datetime.strptime(row[2], "%H:%M - %Y-%m-%d")
					cleanup_time = record_date + timedelta(minutes=1) # Cleanup 1 minute after match time
					
					if today > cleanup_time:
						 cur.execute("DELETE FROM LIVE_NOTIF WHERE DATE = ?", (row[2],))
			conn.commit()

	def notify(self, match, compet, team1, team2, message=None):
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
		if reswidth == 1920:
			skin = "assets/skin/FHD/standings.xml"
		elif reswidth >= 2560:
			skin = "assets/skin/UHD/standings.xml"
		else:
			skin = "assets/skin/FHD/standings.xml"
		self.skin = readFromFile(skin)
		self.league = str(league)
		self.url = str(url)
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
		self.onShown.append(self.fetch_standings)

	def fetch_standings(self):
		#logdata("fetch_standings", "Fetching standings for league: %s" % self.league)
		url = self.url
		# Using the aggressive headers provided by the user, but REMOVING Accept-Encoding 
		# to ensure we get uncompressed data for easier debugging and parsing.
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
			"Accept-Language": "en-US,en;q=0.5",
			# "Accept-Encoding": "gzip, deflate, br", <-- Removed this line
			"Connection": "keep-alive",
			"Referer": "https://www.google.com/", 
			"Upgrade-Insecure-Requests": "1",
			"Sec-Fetch-Dest": "document",
			"Sec-Fetch-Mode": "navigate",
			"Sec-Fetch-Site": "cross-site",
			"Cache-Control": "max-age=0",
			"Cookie": "fcfc_cookie=1; time_zone=Europe/London;", 
		}
		html = None
		
		# Use compat_Request and compat_urlopen (replacing requests.get)
		try:
			request = compat_Request(url, headers=headers)
			response = compat_urlopen(request, timeout=20)
			
			raw_html_content = response.read()
			
			if PY3:
				html = raw_html_content.decode('utf-8', errors="ignore")
			else:
				html = str(raw_html_content) 

			logdata("fetch_standings", "HTML fetched, length: %d" % len(html))
			# Save HTML for manual inspection
			# with open("/tmp/standings_%s.html" % self.league, "w") as f:
			#     f.write(html)
			# logdata("fetch_standings", "HTML saved to /tmp/standings_%s.html for inspection" % self.league)

			soup = BeautifulSoup(html, "html.parser")
			standings = []
			tables = []

			if self.league == "seriea":
				#logdata("fetch_standings", "Processing Serie A standings from Sky Sports")
				table = soup.find("table")
				if not table:
					#logdata("fetch_standings", "No table found for Serie A")
					self.standings_data = []
					self.display_standings()
					return
				rows = table.find_all("tr")[1:]  # Skip header row
				#logdata("fetch_standings", "Found %d rows for Serie A" % len(rows))
				for row_idx, row in enumerate(rows):
					cells = row.find_all("td")
					if len(cells) < 9:
						#logdata("fetch_standings", "Skipping row %d with insufficient columns: %d" % (row_idx, len(cells)))
						continue
					position = cells[0].get_text(strip=True) if cells[0].get_text(strip=True).isdigit() else "0"
					team = cells[1].get_text(strip=True)
					played = cells[2].get_text(strip=True) if cells[2].get_text(strip=True).isdigit() else "0"
					wins = cells[3].get_text(strip=True) if cells[3].get_text(strip=True).isdigit() else "0"
					draws = cells[4].get_text(strip=True) if cells[4].get_text(strip=True).isdigit() else "0"
					losses = cells[5].get_text(strip=True) if cells[5].get_text(strip=True).isdigit() else "0"
					goals_scored = cells[6].get_text(strip=True) if cells[6].get_text(strip=True).isdigit() else "0"
					goals_conceded = cells[7].get_text(strip=True) if cells[7].get_text(strip=True).isdigit() else "0"

					goal_diff_text = cells[8].get_text(strip=True) if len(cells) > 8 else "0"
					# Serie A: Skysports may include + and - in table, preserve them
					if goal_diff_text.startswith('+') or goal_diff_text.startswith('-'):
						goal_diff = goal_diff_text
					elif goal_diff_text.lstrip('-+').isdigit():
						goal_diff_value = int(goal_diff_text.lstrip('-+'))
						goal_diff = "+" + str(goal_diff_value) if goal_diff_value > 0 else str(goal_diff_value)
					else:
						goal_diff = "0"
					#logdata("fetch_standings_goal_diff", "SerieA Row %d: raw='%s', parsed='%s'" % (row_idx, goal_diff_text, goal_diff))

					points = cells[9].get_text(strip=True) if len(cells) > 9 and cells[9].get_text(strip=True).isdigit() else "0"
					logo_url = ""
					img = cells[1].find("img")
					if img and img.get("src"):
						logo_url = img.get("src").split("?")[0]
					if not team:
						#logdata("fetch_standings", "Skipping row %d with empty team name" % row_idx)
						continue
					#logdata("fetch_standings_row", "Serie A Row %d Extracted: team=%s, position=%s, played=%s, points=%s, wins=%s, draws=%s, losses=%s, goals_scored=%s, goals_conceded=%s, goal_diff=%s, logo_url=%s" % (
					#    row_idx, team, position, played, points, wins, draws, losses, goals_scored, goals_conceded, goal_diff, logo_url))
					standings.append([
						str(team),
						str(position),
						str(played),
						str(points),
						str(wins),
						str(draws),
						str(losses),
						str(goals_scored),
						str(goals_conceded),
						str(goal_diff),
						str(logo_url)
					])
			else:
				for t in soup.find_all("table"):
					rows = t.find_all("tr")
					if len(rows) > 1 and any(len(row.find_all("td")) > 2 and any(cell.get_text(strip=True) not in ["", "#"] for cell in row.find_all("td")) for row in rows[1:]):
						tables.append(t)
				if not tables:
					#logdata("fetch_standings", "No valid standings tables found for %s" % self.league)
					self.standings_data = []
					self.display_standings()
					return
				#logdata("fetch_standings", "Found %d potential tables for %s" % (len(tables), self.league))
				table_limit = 2 if self.league == "afcchampions" else 1
				tables_to_process = tables[:table_limit]
				if self.league == "afcchampions" and table_limit == 2:
					tables_to_process.reverse()
					t_display_idx = 2
				else:
					t_display_idx = 1
				for t_idx, table in enumerate(tables_to_process, 0):
					#logdata("fetch_standings", "Processing Table %d for %s" % (t_display_idx, self.league))
					if self.league == "afcchampions":
						standings.append("Table %d" % t_display_idx)
						t_display_idx -= 1
					rows = table.find_all("tr")[1:]
					for row in rows:
						cells = row.find_all("td")
						if len(cells) < 2:
							#logdata("fetch_standings", "Skipping row with insufficient columns: %d" % len(cells))
							continue
						team = ""
						logo_url = ""
						position = "0"
						played = "0"
						points = "0"
						wins = "0"
						draws = "0"
						losses = "0"
						goals_scored = "0"
						goals_conceded = "0"
						goal_diff = "0"
						for idx, cell in enumerate(cells):
							class_name = cell.get("class", []) or []
							cell_text = cell.get_text(strip=True) or ""
							#logdata("fetch_standings_cell", "Table %d, Cell %d class: %s, value: %s" % (t_idx, idx, class_name, cell_text))
							if idx == 0:
								position = cell_text if cell_text.isdigit() else "0"
							elif "tl" in class_name or (idx == 1 and not team and cell_text):
								team_link = cell.find("a")
								team = team_link.get_text(strip=True) if team_link else cell_text
								img = cell.find("img")
								logo_url = img.get("src").split("?")[0] if img and img.get("src") else ""
							elif "table_games" in class_name or (idx == 2 and cell_text.isdigit()):
								played = cell_text if cell_text.isdigit() else "0"
							elif "points" in class_name or (idx == 3 and cell_text.isdigit()):
								points = cell_text if cell_text.isdigit() else "0"
							elif "wins" in class_name or (idx == 4 and cell_text.isdigit()):
								wins = cell_text if cell_text.isdigit() else "0"
							elif "draws" in class_name or (idx == 5 and cell_text.isdigit()):
								draws = cell_text if cell_text.isdigit() else "0"
							elif "defeits" in class_name or (idx == 6 and cell_text.isdigit()):
								losses = cell_text if cell_text.isdigit() else "0"
							elif "goals" in class_name and "goals_d" not in class_name or (idx == 7 and cell_text.isdigit()):
								goals_scored = cell_text if cell_text.isdigit() else "0"
							elif "goals_d" in class_name or (idx == 8 and cell_text.isdigit()):
								goals_conceded = cell_text if cell_text.isdigit() else "0"
							elif cell_text.lstrip('-').isdigit():
								# fctables.com only has - for negative, no + for positive
								if cell_text.startswith('-'):
									goal_diff = cell_text
								else:
									goal_diff = "+" + cell_text if cell_text.isdigit() else "0"
								#logdata("fetch_standings_goal_diff", "Other leagues: raw='%s', parsed='%s'" % (cell_text, goal_diff))
						if not team:
							#logdata("fetch_standings", "Skipping row with empty team name: %s" % [cell.get_text(strip=True) for cell in cells])
							continue
						#logdata("fetch_standings_row", "Table %d, Extracted: team=%s, position=%s, played=%s, points=%s, wins=%s, draws=%s, losses=%s, goals_scored=%s, goals_conceded=%s, goal_diff=%s, logo_url=%s" % (
						#    t_idx, team, position, played, points, wins, draws, losses, goals_scored, goals_conceded, goal_diff, logo_url))
						if team == "Sintra Football": team = "Estrela Amadora"
						if team == "Chengdu Qianbao FC": team = "Chengdu Rongcheng"
						if team == "Artsakh": team = "RC Strasbourg"
						if team == "Al Suqoor": team = "NEOM SC"
						if team == "Al Hazm": team = "Al Hazem"
						standings.append([
							str(team),
							str(position),
							str(played),
							str(points),
							str(wins),
							str(draws),
							str(losses),
							str(goals_scored),
							str(goals_conceded),
							str(goal_diff),
							str(logo_url)
						])
			self.standings_data = standings
			#logdata("fetch_standings", "Total teams fetched: %d" % len([x for x in standings if not isinstance(x, str)]))
			if standings:
				try:
					self.check_and_download_logos()
				except Exception as e:
					#logdata("fetch_standings_error", "Error in check_and_download_logos: %s" % str(e))
					pass
			self.display_standings()
		except (compat_HTTPError, compat_URLError, Exception) as e:
			#logdata("fetch_standings_error", "Failed to fetch standings for URL %s: %s" % (url, str(e)))
			self.standings_data = []
			self.display_standings()

	def check_and_download_logos(self):
		# NEW SMART/GENERAL NORMALIZATION FUNCTION
		def normalize_name(name):
			"""Aggressively cleans up team names for robust fuzzy matching."""
			if not name:
				return ""
			name = name.lower()
			# Remove common legal suffixes and punctuation that interfere with fuzzy matching
			replacements = {
				' f.c.': '', ' fc': '', ' a.c.': '', ' ac': '', ' s.v.': '', ' sv': '',
				' association': '', ' club': '', ' sport': '', ' athletic': '',
				' united': '', ' city': '', ' real': '', ' atlético': '',
				' gmbh': '', ' & co. kg': '', 'gmbh & co. kg': '',
				'.': '', ',': '', '-': ' '
			}
			for old, new in replacements.items():
				name = name.replace(old, new)
			# Clean up extra spaces
			return ' '.join(name.split())

	def check_and_download_logos(self):
		# NOTE: This function assumes the 're' module is imported globally 
		# or available in the environment scope for the regex-based name cleanup.

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
			filename_png = resolveFilename(SCOPE_PLUGINS,
										 "Extensions/FootOnSat/assets/standings/{}.png".format(team_filename))

			# Check if PNG version exists
			if os.path.exists(filename_png):
				return True 

			#logdata("Logos", "Downloading logo for '%s' from: %s" % (team_name, logo_url))

			# Determine file extension from URL (used for temp filename)
			ext = ".gif" if logo_url.lower().endswith(".gif") else (".png" if logo_url.lower().endswith(".png") else ".jpg")
			
			# Temporary file path (using the actual downloaded extension)
			temp_file = os.path.join("/tmp", "{}{}".format(team_filename, ext))

			try:
				# --- The network request uses the fixed 'headers' ---
				req = compat_Request(logo_url, headers=headers)
				resp = compat_urlopen(req, timeout=10)
				
				# Save the raw file content to the temporary location
				with open(temp_file, "wb") as f:
					f.write(resp.read())
				
				
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
						
						# Handle potential transparent GIF/JPG by converting to RGBA
						if img.mode not in ('RGB', 'RGBA'):
							img = img.convert('RGBA')

						img.save(filename_png, 'PNG')
						#logdata("Logos", "Converted and saved %s logo for '%s' to PNG via PIL." % (ext[1:].upper(), team_name))
						success = True
					except Exception as e:
						#logdata("Logos", "PIL conversion FAILED for %s: %s" % (team_name, str(e)))
						trace_error() # Include trace for better debugging
						# Fallback to simple copy if PIL fails (e.g., corrupted file)
						shutil.copyfile(temp_file, filename_png)
						success = True # Still logged as found
				else:
					# --- NO PIL FALLBACK (Will cause display error) ---
					#logdata("Logos", "WARNING: PIL not available, saving raw %s data as PNG file for '%s'." % (ext[1:].upper(), team_name))
					shutil.copyfile(temp_file, filename_png)
					success = True

				# Clean up the temporary file
				if os.path.exists(temp_file):
					os.remove(temp_file) 

				return success
					
			except Exception as e:
				#logdata("Logos", "Failed to download/process logo for %s: %s" % (team_name, str(e)))
				trace_error()
				return False
			finally:
				# Ensure cleanup regardless of success/failure
				if os.path.exists(temp_file):
					os.remove(temp_file) 
		# ---------------------------------------------------
		
		# --- Robust Headers provided by user to fix 403 Forbidden error ---
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
			"Accept-Language": "en-US,en;q=0.5",
			"Connection": "keep-alive",
			"Referer": "https://www.google.com/", 
			"Upgrade-Insecure-Requests": "1",
			"Sec-Fetch-Dest": "document",
			"Sec-Fetch-Mode": "navigate",
			"Sec-Fetch-Site": "cross-site",
			"Cache-Control": "max-age=0",
			"Cookie": "fcfc_cookie=1; time_zone=Europe/London;", 
		}
		# -------------------------------------------------------------------

		#logdata("Logos", "Starting check for league: %s" % self.league)

		# Ensure standings folder exists
		standings_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/")
		if not os.path.exists(standings_dir):
			try:
				os.makedirs(standings_dir)
				#logdata("Logos", "Created standings folder: %s" % standings_dir)
			except Exception as e:
				#logdata("Logos", "Failed to create standings folder %s: %s" % (standings_dir, str(e)))
				return

		# Get list of teams and their primary logo URLs from fetch_standings
		teams_to_process = []
		for item in self.standings_data:
			if isinstance(item, list) and len(item) > 10:
				original_name = item[0]
				# Store both the original name (for display/saving) and the normalized name (for matching)
				standardized_name = normalize_name(original_name)
				teams_to_process.append({
					"name": standardized_name, 
					"original_name": original_name, 
					"url": item[10], 
					"found": False
				})

		logos_found = 0
		total_teams = len(teams_to_process) 

		# --- Phase 1: Use Logo URL scraped in fetch_standings (Primary Source) ---
		#logdata("Logos", "Phase 1: Attempting download using scraped logo URLs...")
		for team_info in teams_to_process:
			team_filename = sanitize_team_name(team_info["original_name"])
			filename_png = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/{}.png".format(team_filename))
			
			# Check if a PNG already exists
			if os.path.exists(filename_png):
				team_info["found"] = True
				logos_found += 1
				continue
				
			if team_info["url"]:
				# Ensure the logo URL is absolute for correct downloading
				absolute_url = urljoin(self.url, team_info["url"])
				
				# Pass the original_name for correct logging/saving
				if download_and_save_logo(team_info["original_name"], absolute_url, headers, self.league):
					team_info["found"] = True
					logos_found += 1
		
		# --- Check for early exit for speed improvement ---
		if logos_found >= total_teams:
			pass
			#logdata("Logos", "All logos found in Phase 1. Skipping Phase 2 and 3 for efficiency.")
		else:
			
			# --- Phase 2 (Primary Backup): Use Worldfootball.net (log_urls) for Missing Logos ---
			primary_backup_url = log_urls.get(self.league)
			if primary_backup_url:
				#logdata("Logos", "Phase 2 (Worldfootball): Scraping primary backup site (%s) for missing logos..." % primary_backup_url)
				try:
					missing_logos = any(not team["found"] for team in teams_to_process)
					if missing_logos:
						request = compat_Request(primary_backup_url, headers=headers)
						response = compat_urlopen(request, timeout=20)
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

					if logos_found >= total_teams:
						pass
						#logdata("Logos", "All logos found after Phase 2. Skipping Phase 3 for efficiency.")
					else:

						# --- Phase 3 (Secondary Backup): Use fctables.com (json_urls) for Remaining Missing Logos ---
						secondary_backup_url = json_urls.get(self.league)
						if secondary_backup_url:
							#logdata("Logos", "Phase 3 (fctables): Scraping secondary backup site (%s) for remaining missing logos..." % secondary_backup_url)
							try:
								missing_logos = any(not team["found"] for team in teams_to_process)
								if missing_logos:
									request = compat_Request(secondary_backup_url, headers=headers)
									response = compat_urlopen(request, timeout=20)
									html = response.read()

									if PY3:
										html = html.decode("utf-8", errors="ignore")
									
									soup = BeautifulSoup(html, "html.parser")
									imgs = soup.find_all("img")

									# Prepare map for Phase 3 matching
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

										team_to_search = team_info["name"]
										
										# Fuzzy match against the normalized scraped titles (STRICT CUTOFF = 0.90)
										match = difflib.get_close_matches(team_to_search, normalized_targets, n=1, cutoff=0.90)
										
										#logdata("Logos", "Phase 3 Fuzzy Search for: '%s' (Normalized: '%s'). Match: %s" % (team_info["original_name"], team_to_search, match))

										if match:
											normalized_matched_title = match[0]
											original_title = normalized_title_map.get(normalized_matched_title) # Get the raw title
											img_tag = next((img for img in imgs if (img.get("title") == original_title or img.get("alt") == original_title) and img.get("src")), None)
											
											if img_tag:
												logo_src = img_tag.get("src").split("?")[0]
												logo_url = urljoin(secondary_backup_url, logo_src) 

												# Use the original name for logging and saving
												if download_and_save_logo(team_info["original_name"], logo_url, headers, self.league):
													team_info["found"] = True
													logos_found += 1 # Critical counter update
													#logdata("Logos", "Found logo for '%s' using match to '%s' (fctables)." % (team_info["original_name"], original_title))
													
							except Exception as e:
								#logdata("Logos", "Error fetching from secondary backup site %s -> %s" % (secondary_backup_url, str(e)))
								pass


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
		ITEM_HEIGHT = 65 if reswidth == 1920 else 85

		self["standings_list"].l.setItemHeight(ITEM_HEIGHT)
		if reswidth >= 2560:
			self["standings_list"].l.setFont(0, gFont('Regular', 32))
		else:
			self["standings_list"].l.setFont(0, gFont('Regular', 28))

		club_idx = 1  # numbering for clubs only

		for standing in self.standings_data:
			if isinstance(standing, str) and standing.startswith("Table "):
				club_idx = 1  # reset numbering for new table
				if reswidth == 1920:
					res = [ITEM_HEIGHT, MultiContentEntryText(pos=(450, 0), size=(960, ITEM_HEIGHT), font=0,
													   flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(standing))]
				else: # UHD skins
					res = [ITEM_HEIGHT, MultiContentEntryText(pos=(900, 0), size=(1920, ITEM_HEIGHT), font=0,
													   flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(standing))]
				gList.append(res)
				continue

			team = standing[0]
			position = standing[1]
			played = standing[2]
			points = standing[3]
			wins = standing[4]
			draws = standing[5]
			losses = standing[6]
			goals_scored = standing[7]
			goals_conceded = standing[8]
			goal_diff = standing[9]
			logo_url = standing[10]

			# --- LOGO SIZE AND POSITIONING ---
			if reswidth == 1920:
				LOGO_SIZE_H = 50
				LOGO_Y_POS = 8
				LOGO_X_POS = 95
				TEAM_NAME_X_POS = 160
				TEXT_Y_OFFSET = 0  # No offset needed for 1920
			else:  # 2560
				LOGO_SIZE_H = 45  # Reduced from 55 to 45
				LOGO_Y_POS = int((ITEM_HEIGHT - LOGO_SIZE_H) / 2)  # Recalculate to center vertically
				LOGO_X_POS = 130
				TEAM_NAME_X_POS = 220
				TEXT_Y_OFFSET = LOGO_Y_POS  # Align text with logo vertical position

			res = [ITEM_HEIGHT]
			# number
			# Number
			if reswidth == 1920:
				res.append(MultiContentEntryText(pos=(20, 0), size=(50, ITEM_HEIGHT), font=0,
												 flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=str(club_idx)))
			else:  # 2560
				res.append(MultiContentEntryText(pos=(30, LOGO_Y_POS), size=(70, LOGO_SIZE_H), font=0,
												 flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=str(club_idx)))
			club_idx += 1

			# logo using file path
			flagteam_png = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/{}.png".format(sanitize_team_name(team)))
			if reswidth == 1920:
				if os.path.exists(flagteam_png):
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
				if os.path.exists(flagteam_png):
					if PY3:
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
																   png=loadPNG(flagteam_png), flags=BT_SCALE))
					else: # DreamOS
						res.append(MultiContentEntryPixmapAlphaBlend(pos=(LOGO_X_POS, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
																   png=loadPNG(flagteam_png)))
				# team name - increased width for better display
				res.append(MultiContentEntryText(pos=(230, LOGO_Y_POS), size=(550, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team or "")))
				# matches played - aligned with "Played" header
				res.append(MultiContentEntryText(pos=(660, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(played or "")))
				# points - aligned with "Points" header
				res.append(MultiContentEntryText(pos=(905, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(points or "")))
				# wins - aligned with "Wins" header
				res.append(MultiContentEntryText(pos=(1150, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(wins or "")))
				# draws - aligned with "Draws" header
				res.append(MultiContentEntryText(pos=(1405, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(draws or "")))
				# losses - aligned with "Losses" header
				res.append(MultiContentEntryText(pos=(1640, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(losses or "")))
				# goals scored - aligned with "Goals Scored" header
				res.append(MultiContentEntryText(pos=(1870, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_scored or "")))
				# goals conceded - aligned with "Conceded" header
				res.append(MultiContentEntryText(pos=(2080, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_conceded or "")))
				# goal diff - aligned with "Difference" header
				res.append(MultiContentEntryText(pos=(2260, LOGO_Y_POS), size=(140, LOGO_SIZE_H), font=0,
												 flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goal_diff or "")))
			gList.append(res)

		self["standings_list"].setList(gList)
		if not self.standings_data:
			#logdata("display_standings", "No standings data, showing MessageBox")
			self.session.openWithCallback(self.close, MessageBox, _('No standings available for this league.'), MessageBox.TYPE_INFO, timeout=10)
		else:
			#logdata("display_standings", "Displaying standings, total entries: %d" % len(gList))
			pass
