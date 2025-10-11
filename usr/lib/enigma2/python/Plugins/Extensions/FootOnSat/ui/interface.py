# -*- coding: utf-8 -*-
import os
import sys
import json
import math
import codecs
import random
import traceback
import re
import threading
import difflib
from PIL import Image
from unicodedata import normalize
from time import strftime
from sqlite3 import connect
from bs4 import BeautifulSoup
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
from .compat import PY3, compat_urlopen, compat_HTTPError, compat_URLError, compat_Request

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
    "premierleague": "https://www.fctables.com/england/premier-league/",
    "championsleague": "https://www.fctables.com/championsleague/",
    "europaleague": "https://www.fctables.com/europaleague/",
    "ConferenceLeague": "https://www.fctables.com/europa-conference-league/",
    "seriea": "https://www.skysports.com/serie-a-table",
#    "seriea": "https://www.fctables.com/italy/serie-a/",
    "ligue1": "https://www.fctables.com/france/ligue-1/",
    "laliga": "https://www.fctables.com/spain/liga-bbva/",
    "laliga2": "https://www.fctables.com/spain/liga-adelante/",
    "bundesliga": "https://www.fctables.com/germany/1-bundesliga/",
    "championship": "https://www.fctables.com/england/championship/",
    "liganos": "https://www.fctables.com/portugal/liga-zon-sagres/",
    "superLig": "https://www.fctables.com/turkey/super-lig/",
    "saudiarabia": "https://www.fctables.com/saudi-arabia/1-division/",
    "afcchampions": "https://www.fctables.com/afcchampionsleague/",
}

# use thess url download missing log of team (Extra code)
log_urls = {
    "premierleague": "https://www.worldfootball.net/competition/eng-premier-league/",
    "championsleague": "https://www.worldfootball.net/competition/champions-league/",
    "europaleague": "https://www.worldfootball.net/competition/europa-league/",
    "ConferenceLeague": "https://www.worldfootball.net/competition/conference-league/",
    "seriea": "https://www.worldfootball.net/competition/ita-serie-a/",
    "ligue1": "https://www.worldfootball.net/competition/fra-ligue-1/",
    "laliga": "https://www.worldfootball.net/competition/esp-primera-division/",
    "bundesliga": "https://www.worldfootball.net/competition/bundesliga/",
    "laliga2": "https://www.worldfootball.net/competition/esp-segunda-division/",
    "championship": "https://www.worldfootball.net/competition/eng-championship/",
    "liganos": "https://www.worldfootball.net/competition/por-primeira-liga/",
    "superLig": "https://www.worldfootball.net/competition/tur-sueperlig/",
    "saudiarabia": "https://www.worldfootball.net/competition/ksa-saudi-pro-league/",
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
        elif reswidth == 2560:
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
            if reswidth == 2560:
                self["list1"].l.setFont(0, gFont('Regular', 36))
            else:
                self["list1"].l.setFont(0, gFont('Regular', 28))
            for i in range(0, len(self.matches)):
                match = self.matches[i][0]
                match_date = self.matches[i][1]
                compet = self.matches[i][2]
                team1 = self.matches[i][3]
                team2 = self.matches[i][4]
                team1_score = self.matches[i][5]  # Team1 score
                team2_score = self.matches[i][6]  # Team2 score
                flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team1))
                flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/{}.png".format(team2))
                banner = FootOnSat.setCompet(str(compet).lower())
                match_date = self.getTime(match_date)
                if not fileExists(flagTeam1):
                    flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
                if not fileExists(flagTeam2):
                    flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
                if self.checkIfexist(match):
                    notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_on.png")
                else:
                    notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_off.png")
                # Initialize list entry
                res.append(MultiContentEntryText())
                # Team 1 flag
                res.append(MultiContentEntryPixmapAlphaBlend(pos=(420, 69), size=(40, 30), png=loadPNG(flagTeam1)))
                # Score team 1
                res.append(MultiContentEntryText(pos=(482, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=0xFF0000))
                # Team 2 flag
                if reswidth == 2560:
                    res.append(MultiContentEntryPixmapAlphaBlend(pos=(1190, 69), size=(40, 30), png=loadPNG(flagTeam2)))
                else:
                    res.append(MultiContentEntryPixmapAlphaBlend(pos=(1142, 69), size=(40, 30), png=loadPNG(flagTeam2)))
                # Score team 2
                res.append(MultiContentEntryText(pos=(1092, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=0xFF0000))
                # Competition banner
                try:
                    res.append(MultiContentEntryPixmapAlphaTest(pos=(65, 6), size=(320, 163), png=loadPNG(banner), flags=BT_SCALE))
                except TypeError:
                    res.append(MultiContentEntryPixmapAlphaTest(pos=(65, 6), size=(320, 163), png=loadPNG(banner)))
                # Notification icon
                res.append(MultiContentEntryPixmapAlphaBlend(pos=(-20, 63), size=(70, 50), png=loadPNG(notif)))
                # Match name
                res.append(MultiContentEntryText(pos=(500, 66), size=(570, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(match)))
                # Kick-off time
                res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str("Kick-off : %s" % match_date)))
                # Competition name
                res.append(MultiContentEntryText(pos=(420, 15), size=(785, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
                gList.append(res)
                res = []
            self["list1"].setList(gList)
            if self.link == "today":
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
            items_per_page = 4
            total_pages = int(math.ceil(float(len(self.matches)) / items_per_page))
            current_page = int(math.ceil((current_index + 1) / float(items_per_page)))
            if current_page < total_pages:
                new_index = min(current_page * items_per_page, len(self.matches) - 1)
                self["list1"].instance.moveSelectionTo(new_index)
                self.updateCounter()
                self.resetChannelinfo()

    def backward(self):
        if len(self.matches) > 0:
            current_index = self["list1"].getSelectionIndex()
            items_per_page = 4
            current_page = int(math.ceil((current_index + 1) / float(items_per_page)))
            if current_page > 1:
                new_index = max((current_page - 2) * items_per_page, 0)
                self["list1"].instance.moveSelectionTo(new_index)
                self.updateCounter()
                self.resetChannelinfo()

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

            if datetime.strptime(match_date, "%H:%M - %Y-%m-%d") > datetime.now():
                if self.checkIfexist(match):
                    with connect(DB_PATH) as conn:
                        cur = conn.cursor()
                        cur.execute("DELETE FROM LIVE_NOTIF WHERE MATCH = ?", (match,))
                else:
                    if not self.sameDate(match_date):
                        with connect(DB_PATH) as conn:
                            cur = conn.cursor()
                            first_notif, message = self.setFirstNotifTime(match_date)
                            cur.execute("INSERT INTO LIVE_NOTIF(MATCH,COMPET,DATE,TEAM1_FLAG,TEAM2_FLAG,FIRST_NOTIF,FIRST_NOTIF_STATUS,LIVE_NOTIF_STATUS,MESSAGE) values (?,?,?,?,?,?,?,?,?)", (
                                match, compet, match_date, flag1, flag2, first_notif, "Waiting", "Waiting", message,))
                self.iniMenu()

    def setFirstNotifTime(self, dt):
        dt_obj = datetime.strptime(dt, "%H:%M - %Y-%m-%d")
        now = datetime.now()
        duration = dt_obj - now
        duration_in_s = duration.total_seconds()
        minutes = divmod(duration_in_s, 60)[0]
        if minutes < 30:
            first_notif = (dt_obj - timedelta(minutes=minutes / 2)).strftime("%H:%M - %Y-%m-%d")
            message = "Kick-off in {} minutes".format(int(minutes / 2))
        else:
            first_notif = (dt_obj - timedelta(minutes=30)).strftime("%H:%M - %Y-%m-%d")
            message = "Kick-off in 30 minutes"
        return [first_notif, message]

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

    def updateCounter(self):
        if len(self.matches) > 0:
            index = self['list1'].getSelectionIndex()
            total_pages = int(math.ceil(float(len(self.matches)) / 4))
            current_page = int(math.ceil((index) // 4)) +1
            self["counter"].setText("{}/{}".format(current_page, total_pages))

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
        """Fetch and parse live and finished match results from Flashscore.com (mobile)"""
        url = "https://m.flashscore.com/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        try:
            request = compat_Request(url, headers=headers)
            response = compat_urlopen(request, timeout=6)
            html = response.read()
            if PY3:
                html = html.decode('utf-8', errors='ignore')
            else:
                html = str(html)
            #logdata("fetch_live_results_raw", "Fetched HTML from %s, length: %d" % (url, len(html)))
        except (compat_HTTPError, compat_URLError) as e:
            #logdata("fetch_live_results_error", "Failed to fetch %s: %s" % (url, str(e)))
            return

        soup = BeautifulSoup(html, "html.parser")
        matches_data = []
        now = datetime.now()

        for a_tag in soup.find_all("a", class_=lambda x: x is None or "live" in str(x)):
            try:
                score_text = a_tag.get_text(strip=True).encode('ascii', 'ignore').decode('ascii') if not PY3 else a_tag.get_text(strip=True)
                if not re.match(r'^\d+:\d+$', score_text):
                    continue

                parent_div = a_tag.find_parent("div")
                if not parent_div:
                    continue

                team_spans = parent_div.find_all("span", class_="team_name_span")
                if len(team_spans) == 2:
                    teams = [t.get_text(strip=True).encode('ascii', 'ignore').decode('ascii') if not PY3 else t.get_text(strip=True) for t in team_spans]
                else:
                    previous_text = a_tag.find_previous(text=True)
                    if not previous_text or " - " not in previous_text:
                        continue
                    previous_text = previous_text.encode('ascii', 'ignore').decode('ascii') if not PY3 else previous_text
                    teams = [t.strip() for t in previous_text.split(" - ")]

                if len(teams) != 2:
                    continue

                team1, team2 = teams
                team1_score, team2_score = score_text.split(":")
                match_name = "%s vs %s" % (team1, team2)

                matches_data.append({
                    "match_name": match_name,
                    "team1_score": team1_score.strip(),
                    "team2_score": team2_score.strip()
                })
                #logdata("fetch_live_results_raw", "Scraped match: %s (%s:%s)" % (match_name, team1_score, team2_score))
            except Exception as e:
                #logdata("fetch_live_results_error", "Error processing match: %s" % str(e))
                continue

        matches_list = [list(match) for match in self.matches]

        def normalize_name(name):
            if not PY3 and isinstance(name, str):
                name = name.decode('ascii', 'ignore')
            name = name.strip().lower()
            name = normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii') if not PY3 else normalize('NFKD', name)
            name = name.replace("psg", "paris st germain")
            name = name.replace(" paris sg", " paris st germain")
            name = name.replace(" wolfsburg u19", " wolfsburg")
            name = name.replace(" wolfsburg u-19", " wolfsburg")
            name = re.sub(r'\b(st\.?|saint)\b', 'st', name)
            name = re.sub(r'\batl\.?\b', 'atletico', name)
            name = re.sub(r'\butd\b', 'united', name)
            name = re.sub(r'\bfc\b', '', name)
            name = re.sub(r'\bu-?(\d+)\b', '', name)
            name = re.sub(r'\bw\b', '', name)
            name = re.sub(r'[^a-z0-9]+', ' ', name)
            return name.strip()

        for match in matches_list:
            try:
                match_date = datetime.strptime(match[1], "%H:%M - %Y-%m-%d")
                #logdata("fetch_live_results_time", "Match: %s, Start: %s, Now: %s, Diff: %.2f minutes" % (match[0], match_date, now, (now - match_date).total_seconds() / 60))
                if match_date <= now + timedelta(hours=2):
                    match_name_norm = normalize_name(match[0].strip())  # Clean extra spaces
                    found = False
                    for live_match in matches_data:
                        live_name_norm = normalize_name(live_match["match_name"])
                        if not PY3:
                            match_name_norm = match_name_norm.decode('ascii', 'ignore') if isinstance(match_name_norm, str) else match_name_norm
                            live_name_norm = live_name_norm.decode('ascii', 'ignore') if isinstance(live_name_norm, str) else live_name_norm
                        similarity = SequenceMatcher(None, match_name_norm, live_name_norm).ratio()
                        if similarity >= 0.70:
                            if config.plugins.FootOnSat.livescore.value == "3":
                                match[5] = str(live_match["team1_score"]).strip()
                                match[6] = str(live_match["team2_score"]).strip()
                            else:
                                match[5] = ""
                                match[6] = ""
                            #logdata("fetch_live_results", "Assigned score to %s: %s-%s" % (match[0], match[5], match[6]))
                            found = True
                            break
                    if not found:
                        match[5] = ""
                        match[6] = ""
                        #logdata("fetch_live_results", "No match found for %s" % match[0])
                else:
                    match[5] = ""
                    match[6] = ""
                    #logdata("fetch_live_results", "Skipped upcoming match %s at %s" % (match[0], match[1]))
            except Exception as e:
                #logdata("fetch_live_results_error", "Error processing match %s: %s" % (match[0], str(e)))
                continue

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
        LIVE_DURATION = timedelta(hours=2)  # Consider matches live for 2 hours

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

                        team1_score = ""
                        team2_score = ""

                        append_match = False

                        if is_upcoming:
                            append_match = True
                            #logdata("getData-debug", f"Upcoming match appended: {match['match']} at {match['time']}")
                        elif is_live:
                            if config.plugins.FootOnSat.livescore.value in ["2", "3"]:
                                append_match = True
                                if config.plugins.FootOnSat.livescore.value == "3":
                                    team1_score = str(match.get('score1', "")).strip()
                                    team2_score = str(match.get('score2', "")).strip()
                                #logdata("getData-debug", f"Live match appended: {match['match']} at {match['time']} (scores: {team1_score}-{team2_score})")
                        else:
                            #logdata("getData-debug", f"Skipped past match: {match['match']} at {match['time']}")
                            pass

                        if append_match:
                            list.append([str(match['match']),
                                         str(match['time']) + ' - ' + str(match['date']),
                                         str(match['compet']),
                                         str(match['flags']['team1']),
                                         str(match['flags']['team2']),
                                         team1_score,
                                         team2_score])
                    else:
                        logdata("getData", "Ignored competition: " + str(match['match']) + ", Compet: " + compet)
                except KeyError:
                    #logdata("getData-error", "KeyError on match: " + str(match))
                    pass

            self.matches = list

            # Only fetch live results for live matches if needed
            if config.plugins.FootOnSat.livescore.value == "3":
                self.fetch_live_results()

            self.onWindowShow()
        else:
            self.session.openWithCallback(self.exit, MessageBox, _('No schedules in this section at this time'), MessageBox.TYPE_ERROR, timeout=10)

    def getChannels(self):
        list = []
        res = []
        gList = []
        self["list2"].l.setItemHeight(50)
        if reswidth == 2560:
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
        elif reswidth == 2560:
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
            self.onhideTimer.timeout.get().append(self.hideNotif)
        except:
            self.onhideTimer_conn = self.onhideTimer.timeout.connect(self.hideNotif)

    def checkforNotif(self):
        if fileExists(DB_PATH):
            self.deloldRecords()
            with connect(DB_PATH) as conn:
                cur = conn.cursor()
                rows = cur.execute("select * from LIVE_NOTIF")
                rows = rows.fetchall()
                now = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), "%Y-%m-%d %H:%M")
                if len(rows) > 0:
                    for row in rows:
                        first_notif = datetime.strptime(row[5], "%H:%M - %Y-%m-%d")
                        live_notif = datetime.strptime(row[2], "%H:%M - %Y-%m-%d")
                        if first_notif == now and row[6] == 'Waiting':
                            cur.execute("UPDATE LIVE_NOTIF set FIRST_NOTIF_STATUS = ?  WHERE FIRST_NOTIF = ? and MATCH = ?", ("Done", row[5], row[0],))
                            self.notify(row[0].strip(), row[1], row[3], row[4], row[8])
                        if live_notif == now and row[7] == 'Waiting':
                            cur.execute("DELETE FROM LIVE_NOTIF WHERE DATE = ? and MATCH = ?", (row[2], row[0],))
                            self.notify(row[0].strip(), row[1], row[3], row[4])

    def deloldRecords(self):
        with connect(DB_PATH) as conn:
            cur = conn.cursor()
            rows = cur.execute("select DATE from LIVE_NOTIF")
            rows = rows.fetchall()
            today = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), "%Y-%m-%d %H:%M")
            if len(rows) > 0:
                for row in rows:
                    record_date = datetime.strptime(row[0], "%H:%M - %Y-%m-%d")
                    if today > record_date:
                        cur.execute("DELETE FROM LIVE_NOTIF WHERE DATE = ?", (row[0],))

    def notify(self, match, compet, team1, team2, message=None):
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
                self.container.execute('aplay /usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/sound/notif1.wav')
                FootOnSatNotifDialog.dialog.show()
                self.onhideTimer.start(8000)

    def hideNotif(self):
        FootOnSatNotifDialog.dialog.hide()


class StandingsScreen(Screen):
    def __init__(self, session, league, url):
        self.session = session
        Screen.__init__(self, session)
        #logdata("StandingsScreen_init", "Initializing StandingsScreen for league: %s, url: %s" % (league, url))
        if reswidth == 1920:
            skin = "assets/skin/FHD/standings.xml"
        elif reswidth == 2560:
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        #logdata("fetch_standings", "Trying URL: %s" % url)
        request = compat_Request(url, headers=headers)
        try:
            response = compat_urlopen(request, timeout=20)
            logdata("fetch_standings", "HTTP response status: %s" % response.getcode())
            html = response.read()
            if PY3:
                html = html.decode('utf-8', errors="ignore")
            else:
                html = str(html)
            logdata("fetch_standings", "HTML fetched, length: %d" % len(html))
            # Save HTML for manual inspection
            with open("/tmp/standings_%s.html" % self.league, "w") as f:
                f.write(html)
            logdata("fetch_standings", "HTML saved to /tmp/standings_%s.html for inspection" % self.league)
            soup = BeautifulSoup(html, "html.parser")
            standings = []
            tables = []
            if self.league == "seriea":
                logdata("fetch_standings", "Processing Serie A standings from Sky Sports")
                # Find the standings table (likely <table> with headers like Position, Team, etc.)
                table = soup.find("table")
                if not table:
                    logdata("fetch_standings", "No table found for Serie A")
                    self.standings_data = []
                    self.display_standings()
                    return
                rows = table.find_all("tr")[1:]  # Skip header row
                logdata("fetch_standings", "Found %d rows for Serie A" % len(rows))
                for row_idx, row in enumerate(rows):
                    cells = row.find_all("td")
                    if len(cells) < 9:  # Expect at least 9 columns: Position, Team, Played, Won, Drawn, Lost, GF, GA, GD, Points
                        logdata("fetch_standings", "Skipping row %d with insufficient columns: %d" % (row_idx, len(cells)))
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
                    if goal_diff_text.lstrip('-+').isdigit():
                        goal_diff_value = int(goal_diff_text.lstrip('-+'))
                        goal_diff = "+" + str(goal_diff_value) if goal_diff_value > 0 else str(goal_diff_value)
                    else:
                        goal_diff = "0"
                    points = cells[9].get_text(strip=True) if len(cells) > 9 and cells[9].get_text(strip=True).isdigit() else "0"
                    logo_url = ""
                    img = cells[1].find("img")
                    if img and img.get("src"):
                        logo_url = img.get("src").split("?")[0]
                    if not team:
                        logdata("fetch_standings", "Skipping row %d with empty team name" % row_idx)
                        continue
                    logdata("fetch_standings_row", "Serie A Row %d Extracted: team=%s, position=%s, played=%s, points=%s, wins=%s, draws=%s, losses=%s, goals_scored=%s, goals_conceded=%s, goal_diff=%s, logo_url=%s" % (
                        row_idx, team, position, played, points, wins, draws, losses, goals_scored, goals_conceded, goal_diff, logo_url))
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
                    # Accept tables with at least 2 rows and multiple non-empty cells
                    if len(rows) > 1 and any(len(row.find_all("td")) > 2 and any(cell.get_text(strip=True) not in ["", "#"] for cell in row.find_all("td")) for row in rows[1:]):
                        tables.append(t)
                if not tables:
                    logdata("fetch_standings", "No valid standings tables found for %s" % self.league)
                    self.standings_data = []
                    self.display_standings()
                    return
                logdata("fetch_standings", "Found %d potential tables for %s" % (len(tables), self.league))
                table_limit = 2 if self.league == "afcchampions" else 1
                tables_to_process = tables[:table_limit]
                # FIX: If afcchampions, reverse order so that Table 2 (first table) appears before Table 1 (second table).
                if self.league == "afcchampions" and table_limit == 2:
                    tables_to_process.reverse()
                    t_display_idx = 2 # Start the display index at 2
                else:
                    t_display_idx = 1 # Normal index starting at 1
                for t_idx, table in enumerate(tables_to_process, 0): # Use 0-based enumerate here
                    logdata("fetch_standings", "Processing Table %d for %s" % (t_display_idx, self.league))
                    if self.league == "afcchampions":
                        standings.append("Table %d" % t_display_idx)
                        t_display_idx -= 1 # Decrement for the next table (2 -> 1)
                    rows = table.find_all("tr")[1:]
                    for row in rows:
                        cells = row.find_all("td")
                        if len(cells) < 2:  # Minimal: team and points
                            logdata("fetch_standings", "Skipping row with insufficient columns: %d" % len(cells))
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
                            logdata("fetch_standings_cell", "Table %d, Cell %d class: %s, value: %s" % (t_idx, idx, class_name, cell_text))
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
                            elif cell_text.lstrip('-+').isdigit():
                                goal_diff_value = int(cell_text.lstrip('-+'))
                                goal_diff = "+" + str(goal_diff_value) if goal_diff_value > 0 else str(goal_diff_value)
                        if not team:
                            logdata("fetch_standings", "Skipping row with empty team name: %s" % [cell.get_text(strip=True) for cell in cells])
                            continue
                        logdata("fetch_standings_row", "Table %d, Extracted: team=%s, position=%s, played=%s, points=%s, wins=%s, draws=%s, losses=%s, goals_scored=%s, goals_conceded=%s, goal_diff=%s, logo_url=%s" % (
                            t_idx, team, position, played, points, wins, draws, losses, goals_scored, goals_conceded, goal_diff, logo_url))
                        # ADD THIS LINE FOR CORRECTION:
                        if team == "Sintra Football": team = "Estrela Amadora"
                        if team == "Chengdu Qianbao FC": team = "Chengdu Rongcheng"
                        if team == "Artsakh": team = "RC Strasbourg"
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
            logdata("fetch_standings", "Total teams fetched: %d" % len([x for x in standings if not isinstance(x, str)]))
            if standings:
                try:
                    self.check_and_download_logos()
                except Exception as e:
                    logdata("fetch_standings_error", "Error in check_and_download_logos: %s" % str(e))
                    pass
            self.display_standings()
        except (compat_HTTPError, compat_URLError, Exception) as e:
            logdata("fetch_standings_error", "Failed to fetch standings for URL %s: %s" % (url, str(e)))
            self.standings_data = []
            self.display_standings()

    def check_and_download_logos(self):
        # --- WORKING CONVERSION FUNCTION RESTORED ---
        def convert_gif_to_png(src_path, dest_path):
            try:
                # Open the GIF file
                im = Image.open(src_path)
                # Save it as a PNG file
                im.save(dest_path, "PNG")
                #logdata("Logos", "Converted GIF to PNG for %s -> %s" % (os.path.basename(src_path).replace(".gif", ""), dest_path))
            except Exception as e:
                #logdata("Logos", "Failed to convert GIF for %s: %s" % (os.path.basename(src_path).replace(".gif", ""), str(e)))
                pass

        current_table = None
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/140.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        #logdata("Logos", "Starting check for league: %s" % self.league)

        # First: backup site (fctables.com)
        backup_url = json_urls.get(self.league)
        all_teams = [item[0] for item in self.standings_data if isinstance(item, list)]
        missing_teams = list(all_teams)
        logos_found = 0

        if backup_url:
            #logdata("Logos", "Fetching from backup site...")
            try:
                request = compat_Request(backup_url, headers=headers)
                response = compat_urlopen(request, timeout=20)
                html = response.read()

                if PY3:
                    html = html.decode("utf-8", errors="ignore")
                else:
                    pass

                soup = BeautifulSoup(html, "html.parser")
                imgs = soup.find_all("img")

                titles = [img.get("title") or img.get("alt") for img in imgs if img.get("title") or img.get("alt")]

                for team in missing_teams[:]:
                    match = difflib.get_close_matches(team, titles, n=1, cutoff=0.6)

                    if match:
                        img_tag = next(img for img in imgs if (img.get("title") == match[0] or img.get("alt") == match[0]))

                        logo_src = img_tag.get("src")
                        if not logo_src:
                            continue

                        logo_url_base = logo_src.split("?")[0]

                        # Skip placeholder/blank images
                        if logo_url_base.endswith("/blank.gif") or 'placeholder' in logo_url_base:
                            #logdata("Logos", "Skipping placeholder logo for '%s'." % team)
                            continue

                        # Convert relative URL to absolute URL using urljoin
                        if not logo_url_base.startswith(("http://", "https://")):
                            logo_url = urljoin(backup_url, logo_url_base)
                        else:
                            logo_url = logo_url_base
                        
                        
                        # --- CONVERSION LOGIC FOR BACKUP SITE ---
                        ext = ".gif" if logo_url.endswith(".gif") else (".png" if logo_url.endswith(".png") else ".jpg")
                        
                        # Final destination filename (ALWAYS .png for plugin)
                        filename_png = resolveFilename(SCOPE_PLUGINS,
                                                   "Extensions/FootOnSat/assets/standings/{}{}".format(
                                                       sanitize_team_name(team), ".png"))
                        
                        if not os.path.exists(filename_png):
                            try:
                                req = compat_Request(logo_url, headers=headers)
                                resp = compat_urlopen(req)
                                
                                if ext == ".gif" or ext == ".jpg":
                                    # Save temporarily if conversion is needed
                                    temp_file = filename_png.replace(".png", ext)
                                    with open(temp_file, "wb") as f:
                                        f.write(resp.read())
                                    
                                    convert_gif_to_png(temp_file, filename_png)
                                    os.remove(temp_file) # Delete temporary file
                                else:
                                    # Save directly if it's already a PNG
                                    with open(filename_png, "wb") as f:
                                        f.write(resp.read())
                                        
                                logos_found += 1
                                #logdata("Logos", "Saved '%s' to %s" % (team, filename_png))
                            except Exception as e:
                                #logdata("Logos", "Failed to download/convert logo for %s: %s" % (team, logo_url, str(e)))
                                pass
                        missing_teams.remove(team)
                        # --- END CONVERSION LOGIC ---
                        
            except Exception as e:
                #logdata("Logos", "Error fetching from %s -> %s" % (backup_url, str(e)))
                pass

        # Second: primary site (worldfootball.net) - Using Raw String Matching
        if missing_teams:
            primary_url = log_urls.get(self.league)
            if primary_url:
                #logdata("Logos", "Fetching missing logos from primary site...")
                try:
                    request = compat_Request(primary_url, headers=headers)
                    response = compat_urlopen(request, timeout=20)
                    html = response.read()

                    if PY3:
                        html = html.decode("utf-8", errors="ignore")
                    else:
                        pass

                    soup = BeautifulSoup(html, "html.parser")
                    imgs = soup.find_all("img")

                    # Use raw titles for matching
                    titles = [img.get("title") or img.get("alt") for img in imgs if img.get("title") or img.get("alt")]

                    for team in missing_teams[:]:

                        # Match raw input string against raw scraped titles
                        match = difflib.get_close_matches(team, titles, n=1, cutoff=0.6) 

                        match_found = False
                        if match:
                            original_title = match[0]
                            # Find the image tag based on title/alt
                            img_tag = next(img for img in imgs if (img.get("title") == original_title or img.get("alt") == original_title))
                            match_found = True

                        if not match_found:
                            #logdata("Logos", "Primary Site: No close match found for team: '%s'" % team)
                            continue # Skip to next team if no match was found

                        if match_found:
                            logo_url = img_tag.get("src").split("?")[0]
                            
                            # --- CONVERSION LOGIC FOR PRIMARY SITE ---
                            ext = ".gif" if logo_url.endswith(".gif") else (".png" if logo_url.endswith(".png") else ".jpg")
                            
                            # Final destination filename (ALWAYS .png for plugin)
                            filename_png = resolveFilename(SCOPE_PLUGINS,
                                                         "Extensions/FootOnSat/assets/standings/{}{}".format(
                                                             sanitize_team_name(team), ".png"))

                            if not os.path.exists(filename_png):
                                try:
                                    req = compat_Request(logo_url, headers=headers)
                                    resp = compat_urlopen(req)
                                    
                                    if ext == ".gif" or ext == ".jpg":
                                        # Save temporarily if conversion is needed
                                        temp_file = filename_png.replace(".png", ext)
                                        with open(temp_file, "wb") as f:
                                            f.write(resp.read())
                                        
                                        convert_gif_to_png(temp_file, filename_png)
                                        os.remove(temp_file) # Delete temporary file
                                    else:
                                        # Save directly if it's already a PNG
                                        with open(filename_png, "wb") as f:
                                            f.write(resp.read())
                                            
                                    logos_found += 1
                                    #logdata("Logos", "Found logo for '%s' using match to '%s'." % (team, original_title))
                                except Exception as e:
                                    #logdata("Logos", "Failed to download/convert logo for %s: %s" % (team, logo_url, str(e)))
                                    pass
                            missing_teams.remove(team)
                            # --- END CONVERSION LOGIC ---
                            
                except Exception as e:
                    #logdata("Logos", "Error fetching from %s -> %s" % (primary_url, str(e)))
                    pass

        # Final log of any still missing teams
        #for team in missing_teams:
            #logdata("Logos", "Missing logo for team: '%s'" % team)

        #logdata("Logos", "Completed check_and_download_logos(), total logos found: %d" % logos_found)

    def display_standings(self):
        gList = []

        # Determine ITEM_HEIGHT based on resolution (used multiple times)
        ITEM_HEIGHT = 65 if reswidth == 1920 else 85

        self["standings_list"].l.setItemHeight(ITEM_HEIGHT)
        if reswidth == 2560:
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

            # --- MAXIMIZED LOGO SIZE CODE (Using variables again) ---
            LOGO_SIZE_H = 50 if reswidth == 1920 else 60
            LOGO_Y_POS = 8

            # Adjust team name position to account for the larger logo space
            TEAM_NAME_X_POS = 130 + LOGO_SIZE_H + 10

            res = [ITEM_HEIGHT]
            # number
            res.append(MultiContentEntryText(pos=(20, 0), size=(50, ITEM_HEIGHT), font=0,
                                             flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=str(club_idx)))
            club_idx += 1

            # logo using file path
            flagteam_png = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/{}.png".format(sanitize_team_name(team)))
            flagteam_jpg = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/standings/{}.jpg".format(sanitize_team_name(team)))
            if reswidth == 1920:
              if os.path.exists(flagteam_png):
              	if PY3:
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(95, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=loadPNG(flagteam_png), flags=BT_SCALE))
              	else: # DreamOS
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(95, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=loadPNG(flagteam_png)))
              # logo fallback to jpg
              elif os.path.exists(flagteam_jpg):
              	if PY3:
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(95, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=LoadPixmap(flagteam_jpg), flags=BT_SCALE))
              	else: # DreamOS
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(95, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=LoadPixmap(flagteam_jpg)))
              # team name
              res.append(MultiContentEntryText(pos=(TEAM_NAME_X_POS, 0), size=(400, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team or "")))
              # matches played
              res.append(MultiContentEntryText(pos=(553, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(played or "")))
              # points
              res.append(MultiContentEntryText(pos=(708, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(points or "")))
              # wins
              res.append(MultiContentEntryText(pos=(852, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(wins or "")))
              # draws
              res.append(MultiContentEntryText(pos=(997, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(draws or "")))
              # losses
              res.append(MultiContentEntryText(pos=(1152, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(losses or "")))
              # goals scored
              res.append(MultiContentEntryText(pos=(1342, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_scored or "")))
              # goals conceded
              res.append(MultiContentEntryText(pos=(1520, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_conceded or "")))
              # goal diff
              res.append(MultiContentEntryText(pos=(1680, 0), size=(80, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goal_diff or "")))
            else: # UHD skins
              if os.path.exists(flagteam_png):
              	if PY3:
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(190, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=LoadPixmap(flagteam_png), flags=BT_SCALE))
              	else: # DreamOS
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(190, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=LoadPixmap(flagteam_png)))
              # logo fallback to jpg
              elif os.path.exists(flagteam_jpg):
              	if PY3:
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(190, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=LoadPixmap(flagteam_jpg), flags=BT_SCALE))
              	else: # DreamOS
              		res.append(MultiContentEntryPixmapAlphaBlend(pos=(190, LOGO_Y_POS), size=(LOGO_SIZE_H, LOGO_SIZE_H),
                                                               png=LoadPixmap(flagteam_jpg)))
              # team name
              res.append(MultiContentEntryText(pos=(TEAM_NAME_X_POS, 0), size=(800, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team or "")))
              # matches played
              res.append(MultiContentEntryText(pos=(1106, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(played or "")))
              # points
              res.append(MultiContentEntryText(pos=(1416, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(points or "")))
              # wins
              res.append(MultiContentEntryText(pos=(1704, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(wins or "")))
              # draws
              res.append(MultiContentEntryText(pos=(1994, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(draws or "")))
              # losses
              res.append(MultiContentEntryText(pos=(2304, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(losses or "")))
              # goals scored
              res.append(MultiContentEntryText(pos=(2684, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_scored or "")))
              # goals conceded
              res.append(MultiContentEntryText(pos=(3040, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goals_conceded or "")))
              # goal diff
              res.append(MultiContentEntryText(pos=(3360, 0), size=(160, ITEM_HEIGHT), font=0,
                                               flags=RT_VALIGN_CENTER | RT_HALIGN_CENTER, text=str(goal_diff or "")))

            gList.append(res)

        self["standings_list"].setList(gList)
        if not self.standings_data:
            #logdata("display_standings", "No standings data, showing MessageBox")
            self.session.openWithCallback(self.close, MessageBox, _('No standings available for this league.'), MessageBox.TYPE_INFO, timeout=10)
        else:
            #logdata("display_standings", "Displaying standings, total entries: %d" % len(gList))
            pass
