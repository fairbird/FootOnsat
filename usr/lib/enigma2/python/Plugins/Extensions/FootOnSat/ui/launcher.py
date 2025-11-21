# -*- coding: utf-8 -*-
from enigma import getDesktop
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Sources.List import List
from Components.Harddisk import harddiskmanager
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigYesNo, ConfigInteger, ConfigSubsection, ConfigSelection, getConfigListEntry, NoSave, configfile, ConfigText
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from Components.FootMenu import FlexibleMenu
from Plugins.Extensions.FootOnSat.ui.Console import Console
from Plugins.Extensions.FootOnSat.ui.interface import FootOnSat, WebClientContextFactory, logdata, isUHD
from Plugins.Extensions.FootOnSat.component.configs import ConfigDictionarySet
from Plugins.Extensions.FootOnSat.__init__ import __version__
from twisted.web.client import getPage
from os.path import join, exists, splitext, isfile
import re
import os
import json
import sys
from sys import version_info
from . import compat

PY3 = version_info[0] == 3

if isUHD():
        from .skin.skinUHD import *
else:
        from .skin.skinFHD import *

mounted_partitions = harddiskmanager.getMountedPartitions()
mounted_devices = []
default_ignore_dir = "/etc/enigma2/ignore"
ignore_paths = ["/media/net", "/"]
mounted_devices = [(default_ignore_dir, default_ignore_dir)]
for part in mounted_partitions:
	try:
		mountpoint = part.mountpoint
		if mountpoint and mountpoint not in ignore_paths and mountpoint != default_ignore_dir:
			final_path = join(mountpoint, "ignore")
			mounted_devices.append((final_path, final_path))
	except Exception:
		pass

config.plugins.FootOnSat = ConfigSubsection()
config.plugins.FootOnSat.showplugin = ConfigText(default="")
config.plugins.FootOnSat.devicepath = ConfigSelection(default=default_ignore_dir,choices=mounted_devices)
config.plugins.FootOnSat.sort = ConfigDictionarySet(default={"footmenu": {"footsubmenu": {}}})
config.plugins.FootOnSat.updateonline = ConfigYesNo(default=True)
config.plugins.FootOnSat.enableflag = ConfigYesNo(default=True)
config.plugins.FootOnSat.notiftime = ConfigInteger(default=6, limits=(6, 20))
config.plugins.FootOnSat.notiffile = ConfigText(default="notif1", visible_width = 250, fixed_size = False)
config.plugins.FootOnSat.finished = ConfigSelection(default = "2", choices = [
	("2", _("2 hours")),
	("3", _("3 hours"))
	])
config.plugins.FootOnSat.livescoresections = ConfigSelection(default = "1", choices = [
	("1", _("All Sections")),
	("2", _("Match Today Only")),
	])
config.plugins.FootOnSat.livescore = ConfigSelection(default = "3", choices = [
	("1", _("No Live match")),
	("2", _("Live match + No live Score")),
	("3", _("Live match + Live Score"))
	])
config.plugins.FootOnSat.notify_zap = ConfigSelection(default = "1", choices = [
	("1", _("sound + Notifications + Zap")),
	("2", _("sound + Zap only")),
	])
config.plugins.FootOnSat.notify = ConfigSelection(default = "1", choices = [
	("1", _("All three notifications")),
	("2", _("Only when started match")),
	("3", _("Only 15 minutes before the match starts")),
	("4", _("Only 30 minutes before the match starts")),
	("5", _("Only Before 15 min + Start match")),
	("6", _("Only Before 30 min + Start match")),
	("7", _("Only Before 15 min + Before 30 min"))
	])
config.plugins.FootOnSat.icons = ConfigSelection(default = "icons_default", choices = [
	("icons_default", _("default icons")),
	("icons_buwalla", _("buwalla icons")),
	("icons_renkli", _("renkli icons")),
	("italia2012_icons", _("italia2012 Full style color"))
	])

VER = float(__version__)

DEFAULT_IGNORE_DIR = "/etc/enigma2/ignore"
def get_ignore_paths():
	try:
		selected_path = config.plugins.FootOnSat.devicepath.value
	except Exception:
		selected_path = DEFAULT_IGNORE_DIR
	normalized_path = os.path.normpath(selected_path)
	if normalized_path == DEFAULT_IGNORE_DIR or normalized_path.endswith("/ignore"):
		ignore_dir = normalized_path
	else:
		ignore_dir = join(normalized_path, "ignore")
	ignore_file = join(ignore_dir, "ignore-match.json")
	if not exists(ignore_dir):
		try:
			os.makedirs(ignore_dir)
		except Exception:
			pass
	return ignore_dir, ignore_file

def DreamOS():
	if exists('/var/lib/dpkg/status'):
		return True
	return False

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
		self["red"].setText("V{}".format(__version__))
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
		url = 'https://raw.githubusercontent.com/fairbird/footonsat-api/main/api.json'
		sniFactory = WebClientContextFactory(url)
		getPage(str.encode(url), contextFactory=sniFactory).addCallback(self.getData).addErrback(self.error)

	def getData(self, data):
		if not PY3:
			data = data.decode("utf-8")
		try:
			compet = json.loads(data).keys()
		except Exception as e:
			logdata("getData-json-error", str(e))
			self.error("JSON parsing failed: " + str(e))
			return
		ordering = ["today", "championsleague", "europaleague", "ConferenceLeague", "premierleague", "laliga", "seriea",
		"bundesliga", "ligue1", "saudiarabia", "worldcup", "afcchampions", "afcchampionstwo","championship", "cafchampions", "superLig",
		"belgianpro", "eredivisie", "laliga2", "liganos", "basketball", "nba", "hockey", "nfl", "formula1"]
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
		self["blue"].setText("Edit mode on")
		try:
			self.hide_show_entries()
			self["menu"].setList(self.menuList)
			self.selectionChanged()
		except Exception as e:
			logdata("getData-menu-error", str(e))
			self.error("Menu rendering failed: " + str(e))

	def custom_sort(self, ordem_custom, origin):
		list_order_equals = [c for c in ordem_custom if (c in origin)]
		#list_no_equals = [c for c in origin if (not c in ordem_custom)] ## This follow # Keep only items in ordering in getData
		#list_order = list_order_equals + list_no_equals
		#return list_order
		return list_order_equals

	def error(self, error=None):
		if error:
			logdata("API-error", str(error))
			self.session.openWithCallback(self.exit, MessageBox, _('Error: %s') % str(error), MessageBox.TYPE_ERROR, timeout=10)

	def ok(self):
		if self.sort_mode and len(self.menuList):
			m_entry = self["menu"].getCurrent()[0]
			select = False
			if self.selected_entry is None:
				select = True
			elif self.selected_entry != m_entry:
				select = True
			if not select:
				self["green"].setText(_("Move mode on"))
				self.selected_entry = None
			else:
				self["green"].setText(_("Move mode off"))
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
				self["yellow"].setText("show")
			else:
				self["yellow"].setText("hide")
		else:
			self["yellow"].setText("")

	def keyBlue(self):
		if len(self.menuList) > 0:
			self.toggleSortMode()

	def keyYellow(self):
		if self.sort_mode:
			m_entry = self["menu"].getCurrent()[0]
			hidden = self.sub_menu_sort.getConfigValue(m_entry, "hidden") or 0
			if hidden:
				self.sub_menu_sort.removeConfigValue(m_entry, "hidden")
				self["yellow"].setText(_("hide"))
			else:
				self.sub_menu_sort.changeConfigValue(m_entry, "hidden", 1)
				self["yellow"].setText(_("show"))

	def toggleSortMode(self):
		if self.sort_mode:
			self["green"].setText("")
			self["yellow"].setText("")
			self["blue"].setText(_("Edit mode on"))
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
			self["green"].setText(_("Move mode on"))
			self["blue"].setText(_("Edit mode off"))
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
			trace_error()

	def errBack(self,error=None):
		logdata("errBack-error",error)

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
					else:
						new_description = self.new_description
						logdata("Updates", "New version %s is available" % self.new_version)
						self.session.openWithCallback(
							self.install,
							MessageBox,
							_("New version %s is available.\n\nDo want ot install now." % self.new_version),
							MessageBox.TYPE_YESNO
						)
				except Exception as e:
					logdata("Update-check-error", str(e))
			else:
				logdata("Update-check", "No version found in install.sh")

	def install(self,answer=False):
		try:
			if answer:
				cmdlist = []
				cmd="wget https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh"
				cmdlist.append(cmd)
				self.session.open(Console, title='Installing last update, enigma will be started after install', cmdlist=cmdlist, finishedCallback=self.myCallback, closeOnSuccess=False)
		except:
			trace_error()
	
	def myCallback(self):
		return


class MenuFootOnSat(ConfigListScreen, Screen):

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.configChanged = False
		self.skin = SKIN_MenuFootOnSat

		self["setupActions"] = ActionMap(["FootOnsatActions"],
		{
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"ok": self.keyOk,
		}, -1)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))

		self["Picture"] = Pixmap()
		self["help"] = StaticText()
		self.old_notiffile = config.plugins.FootOnSat.notiffile.value
		self.icons_value = config.plugins.FootOnSat.icons.value
		self.getToneFile()
		self.createSetup()

	def createSetup(self):
		self.configChanged = True
		self.list = []
		self.list.append(getConfigListEntry(_("Show Plugin #press OK to change"), config.plugins.FootOnSat.showplugin, _("This option to show Plugin in any where you like")))
		self.list.append(getConfigListEntry(_("Enable checking for Online Update"), config.plugins.FootOnSat.updateonline, _("This option to Enable or Disable checking for Online Update")))
		self.list.append(getConfigListEntry(_("Enable flags of teams"), config.plugins.FootOnSat.enableflag, _("This option to Enable or Disable flags of teams with logo")))
		self.list.append(getConfigListEntry(_("Enable live match + Live score"), config.plugins.FootOnSat.livescore, _("This feature allows you to show or hide the matches still live with or withou result")))
		if config.plugins.FootOnSat.livescore.value in ["2", "3"]:
			self.list.append(getConfigListEntry(_("Select appear live + score of match in"), config.plugins.FootOnSat.livescoresections, _("This feature allows you to show matches live with result in sections")))
			self.list.append(getConfigListEntry(_("Hide matches that started before"), config.plugins.FootOnSat.finished, _("This option is to specify the time that matches that have finished remain before they disappear from the list")))
		self.list.append(getConfigListEntry(_("Path to store ignore file"), config.plugins.FootOnSat.devicepath, _("This option to set the path of save file for ignore matches")))
		self.list.append(getConfigListEntry(_("Choose time for notifications"), config.plugins.FootOnSat.notiftime, _("This feature allows you to choose the number of seconds for notifications to appear.\nMove <Left | Right> to change seconds from (6 - 20)")))
		self.list.append(getConfigListEntry(_("Choose to notifications and Zap"), config.plugins.FootOnSat.notify_zap, _("This feature allows you to specify the notifications and Zap to selected channel")))
		self.list.append(getConfigListEntry(_("Choose to display notifications"), config.plugins.FootOnSat.notify, _("This feature allows you to specify the times for notifications to appear when matches start")))
		self.list.append(getConfigListEntry(_("Choose tone of notifications #press OK to change"), config.plugins.FootOnSat.notiffile, _("This feature allows you to select a notification tone when matches start")))
		self.list.append(getConfigListEntry(_("Select Icons Style"), config.plugins.FootOnSat.icons, _("This option to enable to select Icons Style.\nChoose and Press Save (Green Button)")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self["config"].onSelectionChanged.append(self.updateHelp)
		self["config"].onSelectionChanged.append(self.Picture)
		self.onShow.append(self.Picture)

	def keyOk(self):
		cur = self["config"].getCurrent()
		if cur and len(cur) > 1 and cur[1] == config.plugins.FootOnSat.showplugin:
			self.session.open(SelectionScreen)
		if cur and len(cur) > 1 and cur[1] == config.plugins.FootOnSat.notiffile:
			tone_list = self.getToneList()
			if tone_list:
				self.session.openWithCallback(self.saveToneSelection, ChoiceBox, title=_("Select tone file"), list=tone_list)
			else:
				self.session.open(MessageBox, _("No .wav files found in sound folder!"), MessageBox.TYPE_INFO)

	@staticmethod
	def getToneFile():
		tone_name = config.plugins.FootOnSat.notiffile.value
		found_file = None
		# 1. check plugin folder
		plugin_path = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/sound/')
		f = join(plugin_path, tone_name + ".wav")
		if exists(f) and isfile(f):
			found_file = f
		# 2. check all mounted partitions /sound folders
		if not found_file:
			for part in harddiskmanager.getMountedPartitions():
				mp = join(part.mountpoint, "sound")
				f = join(mp, tone_name + ".wav")
				if exists(f) and isfile(f):
					found_file = f
					break
		# 3. fallback to default
		if not found_file:
			found_file = join(plugin_path, "notif1.wav")
			config.plugins.FootOnSat.notiffile.value = "notif1"
			config.plugins.FootOnSat.notiffile.save()
			configfile.save()
		return found_file

	def getToneList(self):
		# scan plugin + mounted folders for all .wav files
		tone_files = set()
		paths = [resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/sound/')]
		for part in harddiskmanager.getMountedPartitions():
			mp = join(part.mountpoint, "sound")
			if exists(mp):
				paths.append(mp)
		for path in paths:
			if exists(path):
				for f in os.listdir(path):
					if f.lower().endswith(".wav") and isfile(join(path, f)):
						tone_files.add(os.path.splitext(f)[0])
		# check if current config value exists, else fallback
		if config.plugins.FootOnSat.notiffile.value not in tone_files:
			config.plugins.FootOnSat.notiffile.value = "notif1"
			config.plugins.FootOnSat.notiffile.save()
			configfile.save()
			tone_files.add("notif1")
		# natural sort
		def natural_key(s):
			return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

		return sorted([(name, name) for name in tone_files], key=lambda x: natural_key(x[0]))

	def saveToneSelection(self, selection):
		if selection:
			selected_tone = selection[1]
			config.plugins.FootOnSat.notiffile.value = selected_tone
			config.plugins.FootOnSat.notiffile.save()
			configfile.save()
			try:
				self["config"].invalidate(config.plugins.FootOnSat.notiffile)
			except Exception:
				pass

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur:
			self["help"].text = cur[2]

	def Picture(self):
		try:
			cur = self["config"].getCurrent()
			if not cur:
				self['Picture'].hide()
				return
			index = cur[1].value if hasattr(cur[1], "value") else None
			pic = None
			if index == "icons_default":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/compet/preview/icons_default.png')
			elif index == "icons_buwalla":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/compet/preview/icons_buwalla.png')
			elif index == "icons_renkli":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/compet/preview/icons_renkli.png')
			elif index == "italia2012_icons":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/compet/preview/italia2012_icons.png')
			if pic and self['Picture'].instance and exists(pic):
				self['Picture'].instance.setPixmapFromFile(pic)
				self['Picture'].show()
			else:
				self['Picture'].hide()
		except Exception as error:
			logdata("Picture preview:", error)

	def keyLeft(self):
		cur = self["config"].getCurrent()
		if cur and cur[1] == config.plugins.FootOnSat.notiftime:
			val = config.plugins.FootOnSat.notiftime.value
			limits = config.plugins.FootOnSat.notiftime.limits
			if isinstance(limits[0], int):
				low, high = limits
			else:
				low, high = limits[0]
			if val > low:
				config.plugins.FootOnSat.notiftime.value = val - 1
				try:
					self["config"].invalidate(config.plugins.FootOnSat.notiftime)
				except Exception:
					self["config"].invalidate()
				self["config"].l.setList(self["config"].list)
			return
		ConfigListScreen.keyLeft(self)
		self.Picture()
		self.createSetup()

	def keyRight(self):
		cur = self["config"].getCurrent()
		if cur and cur[1] == config.plugins.FootOnSat.notiftime:
			val = config.plugins.FootOnSat.notiftime.value
			limits = config.plugins.FootOnSat.notiftime.limits
			if isinstance(limits[0], int):
				low, high = limits
			else:
				low, high = limits[0]
			if val < high:
				config.plugins.FootOnSat.notiftime.value = val + 1
				try:
					self["config"].invalidate(config.plugins.FootOnSat.notiftime)
				except Exception:
					self["config"].invalidate()
				self["config"].l.setList(self["config"].list)
			return
		ConfigListScreen.keyRight(self)
		self.Picture()
		self.createSetup()

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def save(self):
		changed = False
		for x in self["config"].list:
			if len(x) > 1:
				config_item = x[1]
				if hasattr(config_item, 'isChanged') and config_item.isChanged():
					changed = True
					break
		# Check if notiffile has actually changed
		if self.old_notiffile != config.plugins.FootOnSat.notiffile.value:
			changed = True
		# Handle icons download
		if self.icons_value != config.plugins.FootOnSat.icons.value:
			changed = True
			extract_path = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
			urls = {
				"icons_default": "icons_default.tar.gz",
				"icons_buwalla": "icons_buwalla.tar.gz",
				"icons_renkli": "icons_renkli.tar.gz",
				"italia2012_icons": "italia2012_icons.tar.gz",
			}
			if config.plugins.FootOnSat.icons.value in urls:
				os.system("wget -O - https://github.com/fairbird/FootOnsat/raw/refs/heads/main/Download/Style-Icons-Files/%s | tar -xz -C %s" % (urls[config.plugins.FootOnSat.icons.value], extract_path))
		# Save all other config items
		for x in self["config"].list:
			if len(x) > 1:
				x[1].save()
		configfile.save()
		if changed:
			self.close("exit_launcher")
		else:
			self.close()

	def restart(self,answer=None):
		if answer:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close(True)


class SelectionScreen(Screen, ConfigListScreen):
        skin = """
        	<screen name="SelectionScreen" position="center,center" size="738,524" title="Select Options">
        		<widget source="list" render="Listbox" position="10,10" size="716,461" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
				    {
				        "template": [
				            MultiContentEntryText(pos=(85,10), size=(650,50), font=0, text=0),
				            MultiContentEntryPixmapAlphaBlend(pos=(0,0), size=(50,50), png=1)
				        ],
				        "fonts": [gFont("Regular", 35)],
				        "itemHeight": 60
				    }
				</convert>
        		</widget>
        		<eLabel text="" foregroundColor="#00ff2525" backgroundColor="#00ff2525" position="105,517" size="165,2" zPosition="-10"/>
        		<eLabel text="" foregroundColor="#00389416" backgroundColor="#00389416" position="482,517" size="165,2" zPosition="-10"/>
        		<widget name="key_red" position="70,480" size="246,40" zPosition="5" valign="center" halign="center" backgroundColor="#16000000" font="Regular;35" transparent="1" foregroundColor="#00ffffff" shadowColor="black"/>
        		<widget name="key_green" position="445,480" size="246,40" zPosition="5" valign="center" halign="center" backgroundColor="#16000000" font="Regular;35" transparent="1" foregroundColor="#00ffffff" shadowColor="black" shadowOffset="-1,-1"/>
        	</screen>"""
        def __init__(self, session):
                Screen.__init__(self, session)
                ConfigListScreen.__init__(self, [], session=session)
                self.session = session
                self.setup_title = _("Select your choose")
                self.setTitle(self.setup_title)

                # Load pixmaps for checkboxes
                self.empty_box = LoadPixmap(resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/checkbox_empty.png'))
                self.checked_box = LoadPixmap(resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/checkbox_checked.png'))

                # Initialize selection states
                self.selection_states = {
                        "Menu": False,
                        "Channellist": False,
                        "Extensions": False
                }

                # Get current config value and update selection states
                self.current_value = config.plugins.FootOnSat.showplugin.value
                if self.current_value:
                        selected_items = self.current_value.split(',')
                        for item in selected_items:
                                if item in self.selection_states:
                                        self.selection_states[item] = True

                # Create list of options with their checkbox states
                self.list = []

                # Set up the list component
                self["list"] = List(self.list)

                # Now update the list
                self.updateList()

                # Set up labels
                self["key_green"] = Label(_("Save"))
                self["key_red"] = Label(_("Cancel"))

                # Set up actions
                self["setupActions"] = ActionMap(["FootOnsatActions"], {
                        "ok": self.select_option,
                        "cancel": self.close,
                        "back": self.close,
                        "green": self.save
                }, -2)  # Higher priority to ensure OK is captured (DreamOS images need it)

                self.onLayoutFinish.append(self.layoutFinished)

        def layoutFinished(self):
                self.setTitle(self.setup_title)

        def updateList(self):
                # Store the current index before updating the list
                current_index = self["list"].getIndex() or 0
                self.list = []
                choices = [
                        ("Menu", _("Menu")),
                        ("Channellist", _("Channellist")),
                        ("Extensions", _("Extensions"))
                ]

                for key, text in choices:
                        pixmap = self.checked_box if self.selection_states[key] else self.empty_box
                        self.list.append((text, pixmap, key))

                self["list"].setList(self.list)
                # Restore the previous index, ensuring it's within bounds
                if current_index < len(self.list):
                        self["list"].setIndex(current_index)
                else:
                        self["list"].setIndex(0)  # Fallback to first item if index is out of range

        def select_option(self):
                current = self["list"].getCurrent()
                if current:
                        key = current[2]
                        self.selection_states[key] = not self.selection_states[key]
                        self.updateList()

        def save(self):
                # Save all selected options as comma-separated string
                selected_options = [key for key, state in self.selection_states.items() if state]
                new_value = ','.join(selected_options)
                config.plugins.FootOnSat.showplugin.value = new_value
                config.plugins.FootOnSat.showplugin.save()

                if self.current_value != new_value:
                        self.session.openWithCallback(self.restart, MessageBox, _("You need to restart GUI\nDo you want to do it now ?!"))
                else:
                        self.close(True)

        def restart(self,answer=None):
                if answer:
                        self.session.open(TryQuitMainloop, 3)
                else:
                        self.close(True)
