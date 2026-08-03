# -*- coding: utf-8 -*-
from enigma import eActionMap, eRCInput
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.PluginComponent import plugins
from Components.config import config, NoSave
from Components.FootMenu import FlexibleMenu
from Plugins.Extensions.FootOnSat.ui.Console import Console
from Plugins.Extensions.FootOnSat.ui.interface import FootOnSat, WebClientContextFactory
from Plugins.Extensions.FootOnSat.component.configs import ConfigDictionarySet
from twisted.web.client import getPage, downloadPage
from os.path import join, exists
import re, os, json, sys
from os import system
from sys import version_info
from .compat import *
from .setup import *
from Plugins.Extensions.FootOnSat.__init__ import __version__
from keymapparser import readKeymap
from GlobalActions import globalActionMap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

VER = float(__version__)

debug_Fetch_Live = config.plugins.FootOnSat.debug_Fetch_Live.value

if isUHD():
        from Plugins.Extensions.FootOnSat.assets.skin.skinUHD import *
else:
        from Plugins.Extensions.FootOnSat.assets.skin.skinFHD import *

PLUGINPATH="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"


class FootOnsatLauncher(Screen):

	def __init__(self, session, *args):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_launcher
		self["setupActions"] = ActionMap(["FootOnsatActions"],
		{
			'left': self.left,
			'right': self.right,
			'up': self.up,
			'down': self.down,
			'ok': self.ok,
			'blue': self.keyBlue,
			'green': self.ok,
			'red': self.exit,
			"yellow": self.keyYellow,
			"cancel": self.exit,
			"menu": self.showMenu,
		}, -1)
		self['menu'] = FlexibleMenu([])
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self["red"] = Label()
		self["red"].setText("V {}".format(__version__))
		self["green"] = Label()
		self["yellow"] = Label()
		self["blue"] = Label()
		self.menuList = []
		self.sort_mode = False
		self.selected_entry = None
		self.onLayoutFinish.append(self.callAPI)

	def showMenu(self):
		self.session.openWithCallback(self.closeLauncher, MenuFootOnSat)

	def closeLauncher(self, result=None):
		if result == "exit_launcher":
			self.close()

	def callAPI(self):
		if config.plugins.FootOnSat.updateonline.value:
			self.checkupdates()
		elif config.plugins.FootOnSat.updatebannersonline.value:
			self.checkbannersupdates()
		url = 'https://raw.githubusercontent.com/fairbird/footonsat-api/main/api.json'
		sniFactory = WebClientContextFactory(url)
		getPage(str.encode(url), contextFactory=sniFactory).addCallback(self.getData).addErrback(self.error)

	def getData(self, data):
		if not PY3:
			data = data.decode("utf-8")
		try:
			compet = json.loads(data).keys()
		except Exception as e:
			if debug_Fetch_Live: logdata("launcher", "getData : %s" % str(e))
			self.error("JSON parsing failed: " + str(e))
			return
		ordering = ["favorite", "live", "end", "today", "tomorrow", "championsleague", "europaleague", "ConferenceLeague", "premierleague", "laliga", "seriea",
		"bundesliga", "bundesliga2", "ligue1", "saudiarabia", "worldcup", "afcchampions", "afcchampionstwo","championship", "cafchampions", "superLig",
		"belgianpro", "eredivisie", "laliga2", "liganos", "basketball", "nba", "hockey", "nfl", "formula1"]
		# Ensure "live" is always present even if not in JSON
		if config.plugins.FootOnSat.livescore.value == "2":
			compet = list(compet)
			if "favorite" not in compet:
				compet.append("favorite")
			if "live" not in compet:
				compet.append("live")
			if "end" not in compet:
				compet.append("end")
		# Keep only items in ordering, then sort according to ordering
		# filtered_compet = [c for c in ordering if c in compet]
		# self.menuList = self.custom_sort(ordering, filtered_compet)
		self.menuList = self.custom_sort(ordering, compet)

		self.sub_menu_sort = NoSave(ConfigDictionarySet())
		self.sub_menu_sort.value = config.plugins.FootOnSat.sort.getConfigValue("footmenu", "footsubmenu") or {}
		idx = 0
		i = 10
		for _ in self.menuList:
			entry = [self.menuList.pop(idx)]
			m_weight = self.sub_menu_sort.getConfigValue("".join(entry), "sort") or i
			entry.append(m_weight)
			self.menuList.insert(idx, tuple(entry))
			self.sub_menu_sort.changeConfigValue(entry[0], "sort", m_weight)
			idx += 1
			i += 10
		self.full_list = list(self.menuList)
		self["blue"].setText(title190)
		try:
			self.hide_show_entries()
			self["menu"].setList(self.menuList)
			self.selectionChanged()
		except Exception as e:
			if debug_Fetch_Live: logdata("launcher", "getData : %s" % str(e))
			self.error("Menu rendering failed: " + str(e))

	def custom_sort(self, ordem_custom, origin):
		list_order_equals = [c for c in ordem_custom if (c in origin)]
		#list_no_equals = [c for c in origin if (not c in ordem_custom)] ## This follow # Keep only items in ordering in getData
		#list_order = list_order_equals + list_no_equals
		#return list_order
		return list_order_equals

	def error(self, error=None):
		if error:
			if debug_Fetch_Live: logdata("launcher", "API-error : %s" % str(e))
			self.session.openWithCallback(self.exit, MessageBox, title191 + ': %s' % str(error), MessageBox.TYPE_ERROR, timeout=10)

	def ok(self):
		if self.sort_mode and len(self.menuList):
			m_entry = self["menu"].getCurrent()[0]
			select = False
			if self.selected_entry is None:
				select = True
			elif self.selected_entry != m_entry:
				select = True
			if not select:
				self["green"].setText(title192)
				self.selected_entry = None
			else:
				self["green"].setText(title193)
			idx = 0
			for x in self.menuList:
				if m_entry == x[0] and select == True:
					self.selected_entry = m_entry
					break
				elif m_entry == x[0] and select == False:
					self.selected_entry = None
					break
				idx += 1
		elif len(self.menuList) and not self.sort_mode:
			compet = self['menu'].getCurrent()[0]
			self.session.open(FootOnSat, compet)

	def left(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self['menu'].left()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def right(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self['menu'].right()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def up(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self['menu'].up()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def down(self):
		self.cur_idx = self["menu"].getSelectedIndex()
		self['menu'].down()
		if self.sort_mode and self.selected_entry is not None:
			self.moveAction()

	def moveAction(self):
		if len(self.menuList) > 0:
			tmp_list = list(self.menuList)
			entry = tmp_list.pop(self.cur_idx)
			newpos = self["menu"].getSelectedIndex()
			tmp_list.insert(newpos, entry)
			self.menuList = list(tmp_list)
			self["menu"].setList(self.menuList)

	def selectionChanged(self):
		if self.sort_mode and len(self.menuList) > 0:
			selection = self["menu"].getCurrent()[0]
			if self.sub_menu_sort.getConfigValue(selection, "hidden"):
				self["yellow"].setText(title208)
			else:
				self["yellow"].setText(title207)
		else:
			self["yellow"].setText("")
		if len(self.menuList) > 0:
			curr = self["menu"].getCurrent()
			if curr:
				for summary in self.summaries:
					if "entry" in summary:
						summary["entry"].setText("%s %s" % (str(curr[0]).capitalize(), str(title143)))

	def keyBlue(self):
		if len(self.menuList) > 0:
			self.toggleSortMode()

	def keyYellow(self):
		if self.sort_mode:
			m_entry = self["menu"].getCurrent()[0]
			hidden = self.sub_menu_sort.getConfigValue(m_entry, "hidden") or 0
			if hidden:
				self.sub_menu_sort.removeConfigValue(m_entry, "hidden")
				self["yellow"].setText(title207)
			else:
				self.sub_menu_sort.changeConfigValue(m_entry, "hidden", 1)
				self["yellow"].setText(title208)

	def toggleSortMode(self):
		if self.sort_mode:
			self["green"].setText("")
			self["yellow"].setText("")
			self["blue"].setText(title190)
			self.sort_mode = False
			i = 10
			idx = 0
			for x in self.menuList:
				self.sub_menu_sort.changeConfigValue(x[0], "sort", i)
				if len(x) >= 2:
					entry = list(x)
					entry[1] = i
					entry = tuple(entry)
					self.menuList.pop(idx)
					self.menuList.insert(idx, entry)
				if self.selected_entry is not None:
					if x == self.selected_entry:
						self.selected_entry = None
				i += 10
				idx += 1
			self.full_list = list(self.menuList)
			config.plugins.FootOnSat.sort.changeConfigValue("footmenu", "footsubmenu", self.sub_menu_sort.value)
			config.plugins.FootOnSat.sort.save()
			self.hide_show_entries()
			self["menu"].setList(self.menuList)
		else:
			self["green"].setText(title192)
			self["blue"].setText(title276)
			self.sort_mode = True
			self.hide_show_entries()
			self["menu"].setList(self.menuList)
			self.selectionChanged()

	def hide_show_entries(self):
		m_list = list(self.full_list)
		if not self.sort_mode:
			rm_list = []
			for entry in m_list:
				if self.sub_menu_sort.getConfigValue(entry[0], "hidden"):
					rm_list.append(entry)
			for entry in rm_list:
				if entry in m_list:
					m_list.remove(entry)
		if not len(m_list):
			m_list.append((self.full_list[0][0], 10))
		m_list.sort(key=lambda listweight: int(listweight[1]))
		self.menuList = list(m_list)

	def exit(self, ret=None):
		if self.sort_mode:
			self.toggleSortMode()
		else:
			self.close()

	def checkupdates(self):
		try:
			from twisted.web.client import getPage, error
			url = b"https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh"
			getPage(url,timeout=10).addCallback(self.parseData).addErrback(self.errBack)
		except Exception as error:
			logdata("launcher", "checkupdates : %s" % error)

	def errBack(self,error=None):
		logdata("launcher", "errBack-erro : %s" % error)

	def parseData(self, data):
		if PY3:
			data = data.decode("utf-8")
		else:
			data = data.encode("utf-8")

		# initialize defaults
		self.new_version = None
		self.new_description = ""

		if data:
			lines = data.split("\n")
			desc_started = False
			desc_lines = []
			for line in lines:
				line = line.strip()
				if line.lower().startswith("version"):
					parts = line.split("=")
					if len(parts) > 1:
						version_str = parts[1].strip().strip('"').strip("'")
						if version_str:
							self.new_version = version_str
				elif line.startswith("description="):
					desc_started = True
					first_part = line.split("=", 1)[1].lstrip('"')
					if first_part.endswith('"'):
						self.new_description = first_part.rstrip('"').strip().strip('"').strip("'")
						desc_started = False
					else:
						desc_lines.append(first_part)
				elif desc_started:
					if line.endswith('"'):
						desc_lines.append(line.rstrip('"'))
						desc_started = False
						self.new_description = "\n".join(desc_lines)
					else:
						desc_lines.append(line)

			# version comparison with logging safeguard
			if self.new_version:
				try:
					if float(VER) >= float(self.new_version):
						logdata("Updates", "No new version available")
						if config.plugins.FootOnSat.updatebannersonline.value:
							self.checkbannersupdates()
					else:
						new_description = self.new_description
						logdata("Updates", "New version %s is available" % self.new_version)
						self.session.openWithCallback(
							self.install, MessageBox, title194 % self.new_version, MessageBox.TYPE_YESNO)
				except Exception as e:
					logdata("Update-check-error", str(e))
			else:
				logdata("Update-check", "No version found in install.sh")

	def install(self,answer=False):
		try:
			if answer:
				cmdlist = []
				cmd="wget -q https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh"
				cmdlist.append(cmd)
				self.session.open(Console, title="%s" % title105, cmdlist=cmdlist, finishedCallback=self.myCallback, closeOnSuccess=False)
		except Exception as e:
			logdata("launcher", "Install Error: %s" % str(e))
	
	def myCallback(self):
		return

	def checkbannersupdates(self):
		self.sha_file = join(PLUGINPATH, "assets/compet/.last_commit.sha")
		if not exists(self.sha_file): system("touch " + self.sha_file)
		def process_all(result):
			try:
				print("[CheckBannersUpdates] Starting extraction and copying process...")
				system("mkdir -p /tmp/b_ext && tar -xzf /tmp/b.tar.gz -C /tmp/b_ext")
				root_dir = os.listdir("/tmp/b_ext")[0]
				src_root = join("/tmp/b_ext", root_dir)
				print("[CheckBannersUpdates] Root dir found:", root_dir)

				# banners
				dest = join(PLUGINPATH, "assets/compet")
				system("cp -af %s %s" % (join(src_root, "banners/package.json"), join(dest, "package.json")))
				src_banners = join(src_root, "banners")
				if not exists(join(dest, "FHD")): os.makedirs(join(dest, "FHD"))
				system("cp -rf %s/* %s/" % (join(src_banners, "FHD"), join(dest, "FHD")))
				print("[CheckBannersUpdates] Banners copied successfully.")

				# teamlog
				src_teamlog = join(src_root, "banners/teamlog")
				if exists(src_teamlog):
					dest_teamlog = join(PLUGINPATH, "assets/teamlog")
					if not exists(dest_teamlog): os.makedirs(dest_teamlog)
					system("cp -rf %s/* %s/" % (src_teamlog, dest_teamlog))
					print("[CheckBannersUpdates] Teamlog copied successfully.")

				# standings
				src_standings = join(src_root, "banners/standings")
				if exists(src_standings):
					dest_standings = join(PLUGINPATH, "assets/standings")
					if not exists(dest_standings): os.makedirs(dest_standings)
					system("cp -rf %s/* %s/" % (src_standings, dest_standings))
					print("[CheckBannersUpdates] Standings copied successfully.")

				with open(self.sha_file, "w") as f: f.write(self.latest_sha)
				print("[CheckBannersUpdates] Update completed and SHA written:", self.latest_sha)
			except Exception as e:
				print("[CheckBannersUpdates] ERROR:", str(e))
			finally:
				system("rm -f /tmp/b.tar.gz && rm -rf /tmp/b_ext")
				print("[CheckBannersUpdates] Cleanup finished.")

		def check_commit(data):
			try:
				if PY3: data = data.decode("utf-8")
				self.latest_sha = json.loads(data)[0]['sha']
				local_sha = ""
				if exists(self.sha_file):
					with open(self.sha_file, "r") as f: local_sha = f.read().strip()
				if not local_sha or self.latest_sha != local_sha:
					url = "https://api.github.com/repos/fairbird/Banners_FootOnSat/tarball/main"
					downloadPage(str.encode(url), "/tmp/b.tar.gz").addCallback(process_all)
			except: pass
		try: getPage(b"https://api.github.com/repos/fairbird/Banners_FootOnSat/commits?path=banners&per_page=1", agent=b"Enigma2").addCallback(check_commit)
		except: pass

	def createSummary(self):
		return FootOnSatSummary


class KeyCaptureScreen(Screen):
	skin = """<screen position="center,center" size="500,100" title="" flags="wfNoBorder">
	<widget name="label" position="10,10" size="480,80" font="Regular;35" halign="center" valign="center"/>
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self["label"] = Label(title100)
		self.key_caught = False
		self["actions"] = ActionMap(["SetupActions", "WizardActions", "MenuActions"], 
			{
				"cancel": self.close,
				"ok": self.dummy,
				"up": self.dummy,
				"down": self.dummy,
				"left": self.dummy,
				"right": self.dummy
			}, -100)
		self.onFirstExecBegin.append(self.startHook)
		self.onClose.append(self.stopHook)

	def dummy(self):
		return 1

	def startHook(self):
		try:
			self.hook_slot = eActionMap.getInstance().bindAction('', -2147483648, self.keyPressed)
		except:
			pass

	def stopHook(self):
		try:
			if hasattr(self, 'hook_slot'):
				self.hook_slot = None
				eActionMap.getInstance().unbindAction('', self.keyPressed)
		except:
			pass

	def keyPressed(self, key, flag):
		if flag == 1:
			keyname = self.resolveKeyName(key)
			if keyname:
				if keyname in ("KEY_EXIT", "KEY_ESC"):
					self.close(None)
					return 1
				if not self.key_caught:
					self.key_caught = True
					self.close(keyname)
					return 1
		return 1

	def resolveKeyName(self, key):
		try:
			from keyids import KEYIDS
			for name, k_id in KEYIDS.items():
				if k_id == key:
					return name
		except:
			pass
		try:
			rc = eRCInput.getInstance()
			if hasattr(rc, 'getLabel'): return rc.getLabel(key)
			if hasattr(rc, 'getKeyName'): return rc.getKeyName(key)
		except:
			pass
		return None


class FootOnSatLive():
	def __init__(self):
		self.dialog = None

	def gotSession(self, session):
		self.session = session
		self.FootOnSatLive = None
		try:
			data_dir, _, _ = get_data_paths()
			if not exists(data_dir):
				os.makedirs(data_dir)
			keymap = os.path.join(data_dir, "keymap.xml")
			if not exists(keymap):
				try:
					keyfile = open(keymap, "w")
					keyfile.write('<keymap>\n\t<map context="GlobalActions">\n\t\t<key id="%s" mapto="showFootOnSatLive" flags="m" />\n\t</map>\n</keymap>' % config.plugins.FootOnSat.keyname.value)
					keyfile.close()
				except Exception:
					pass
		except Exception:
			keymap = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/db/keymap.xml")
		global globalActionMap
		try:
			readKeymap(keymap)
		except Exception:
			pass
		if 'showFootOnSatLive' in globalActionMap.actions:
			del globalActionMap.actions['showFootOnSatLive']
		globalActionMap.actions['showFootOnSatLive'] = self.ShowHide

	def ShowHide(self):
		try:
			section = config.plugins.FootOnSat.keysection.value if hasattr(config.plugins.FootOnSat, "keysection") else "live"
			self.session.open(FootOnSat, section)
		except Exception:
			pass

pSignal = FootOnSatLive()


class FootOnSatSummary(Screen):
        skin = """
        <screen name="FootOnSatSummary" position="0,0" size="400,240">
        	<widget source="entry" render="Label" position="0,40" size="400,40" font="FdLcD;48" valign="center" halign="center" />
        	<widget source="global.CurrentTime" render="Label" position="center,110" size="225,100" font="FdLcD;85" halign="center" >
			<convert type="ClockToText">Format:%H:%M</convert>
		</widget>
        </screen>"""

        def __init__(self, session, parent):
                Screen.__init__(self, session, parent=parent)
                curr = parent["menu"].getCurrent() if parent and "menu" in parent else None
                text = "%s %s" % (str(curr[0]).capitalize(), str(title143)) if curr and len(curr) > 0 else "FootOnSat"
                self["entry"] = StaticText(text)
