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
from time import strftime
from sqlite3 import connect
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from enigma import eTimer, gRGB, loadPNG, gPixmapPtr, RT_WRAP, ePoint, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont, getDesktop, eConsoleAppContainer
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
from .compat import PY3, compat_urlopen, compat_str, compat_HTTPError, compat_URLError, compat_Request

try:
    from enigma import BT_SCALE, RT_VALIGN_CENTER, RT_HALIGN_LEFT
except ImportError:
    BT_SCALE = 0
    RT_VALIGN_CENTER = 0
    RT_HALIGN_LEFT = 0

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

reswidth = getDesktop(0).size().width()

ignore_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/ignore")
ignore_file = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/ignore/ignore-match.json")
DB_PATH = '/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/db/footonsat.db'

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
        self["setupActions"] = ActionMap(["FootOnsatActions"],
        {
            "ok": self.ok,
            "down": self.listDOWN,
            "up": self.listUP,
            "left": self.left,
            "right": self.right,
            "red": self.keyRed,
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
        self["key_red"].hide()
        self["key_yellow"].hide()
        self["key_blue"].hide()
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
                banner = FootOnSat.setCompet(compet.lower())
                match_date = self.getTime(match_date)
                if not fileExists(flagTeam1):
                    flagTeam1 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
                if not fileExists(flagTeam2):
                    flagTeam2 = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/flags/default.png")
                if self.checkIfexist(match):
                    notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_on.png")
                else:
                    notif = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/icon/notif_off.png")
                res.append(MultiContentEntryText())
                res.append(MultiContentEntryPixmapAlphaBlend(pos=(420, 69), size=(40, 30), png=loadPNG(flagTeam1)))
                res.append(MultiContentEntryText(pos=(482, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team1_score), color=0xFF0000))
                if reswidth == 2560:
                		res.append(MultiContentEntryPixmapAlphaBlend(pos=(1190, 69), size=(40, 30), png=loadPNG(flagTeam2)))
                else:
                		res.append(MultiContentEntryPixmapAlphaBlend(pos=(1142, 69), size=(40, 30), png=loadPNG(flagTeam2)))
                res.append(MultiContentEntryText(pos=(1092, 60), size=(50, 50), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(team2_score), color=0xFF0000))
                try:
                    res.append(MultiContentEntryPixmapAlphaTest(pos=(65, 6), size=(320, 163), png=loadPNG(banner), flags=BT_SCALE))
                except TypeError:
                    res.append(MultiContentEntryPixmapAlphaTest(pos=(65, 6), size=(320, 163), png=loadPNG(banner)))
                res.append(MultiContentEntryPixmapAlphaBlend(pos=(-20, 63), size=(70, 50), png=loadPNG(notif)))
                res.append(MultiContentEntryText(pos=(498, 66), size=(570, 36), font=0, flags=RT_VALIGN_CENTER | RT_HALIGN_LEFT, text=str(match)))
                res.append(MultiContentEntryText(pos=(420, 120), size=(450, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text="Kick-off : " + str(match_date)))
                res.append(MultiContentEntryText(pos=(420, 15), size=(785, 36), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(compet)))
                gList.append(res)
                res = []
            self["list1"].setList(gList)
            if self.link == "today":
                self['key_red'].show()
                self['key_yellow'].show()
            else:
                self['key_red'].hide()
                self['key_yellow'].hide()
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
        """Fetch and parse only live results from Flashscore.com (mobile)"""
        url = "https://m.flashscore.com/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/140.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        request = compat_Request(url, headers=headers)
        response = compat_urlopen(request, timeout=6)
        html = response.read()
        if PY3:
            html = html.decode('utf-8')
        else:
            html = compat_str(html)

        soup = BeautifulSoup(html, "html.parser")
        matches_data = []

        for a_tag in soup.find_all("a", class_=["live"]):
            score_text = a_tag.get_text(strip=True)
            previous_text = a_tag.find_previous(text=True)
            if not previous_text:
                continue
            previous_text = previous_text.strip()
            previous_text = re.sub(r'\s*-\s*', ' - ', previous_text)

            if ":" in score_text and " - " in previous_text:
                teams = previous_text.split(" - ")
                if len(teams) != 2:
                    continue
                team1, team2 = [t.strip() for t in teams]
                team1_score, team2_score = score_text.split(":")
                match_name = "%s vs %s" % (team1, team2)
                matches_data.append({
                    "match_name": match_name,
                    "team1_score": team1_score.strip(),
                    "team2_score": team2_score.strip()
                })

        # Assign live scores to matches
        matches_list = [list(match) for match in self.matches]

        def normalize_name(name):
            return name.strip().lower()

        for match in matches_list:
            match_date = datetime.strptime(match[1], "%H:%M - %Y-%m-%d")
            if match_date <= datetime.now():
                match_name_norm = normalize_name(match[0])
                found = False
                for live_match in matches_data:
                    live_name_norm = normalize_name(live_match["match_name"])
                    similarity = SequenceMatcher(None, match_name_norm, live_name_norm).ratio()
                    if similarity >= 0.60:
                        if config.plugins.FootOnSat.livescore.value == "3":
                            # Only fill scores for choice 3
                            match[5] = compat_str(live_match["team1_score"]).strip()
                            match[6] = compat_str(live_match["team2_score"]).strip()
                        else:
                            match[5] = ""
                            match[6] = ""
                        found = True
                        break
                if not found:
                    match[5] = ""
                    match[6] = ""
            else:
                match[5] = ""
                match[6] = ""
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
            logdata("getData", "Failed to load ignored competitions: " + str(e))

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
                            logdata("getData-debug", f"Upcoming match appended: {match['match']} at {match['time']}")
                        elif is_live:
                            if config.plugins.FootOnSat.livescore.value in ["2", "3"]:
                                append_match = True
                                if config.plugins.FootOnSat.livescore.value == "3":
                                    team1_score = str(match.get('score1', "")).strip()
                                    team2_score = str(match.get('score2', "")).strip()
                                logdata("getData-debug", f"Live match appended: {match['match']} at {match['time']} (scores: {team1_score}-{team2_score})")
                        else:
                            logdata("getData-debug", f"Skipped past match: {match['match']} at {match['time']}")

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
                    logdata("getData-error", "KeyError on match: " + str(match))
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
