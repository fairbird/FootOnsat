# -*- coding: utf-8 -*-
from enigma import getDesktop
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Sources.List import List
from Components.Harddisk import harddiskmanager
from Components.ConfigList import ConfigListScreen
from Components.PluginComponent import plugins
from Components.config import config, ConfigYesNo, ConfigInteger, ConfigSubsection, ConfigSelection, getConfigListEntry, configfile, ConfigText
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Extensions.FootOnSat.ui.Console import Console
from Plugins.Extensions.FootOnSat.component.configs import ConfigDictionarySet
from os.path import join, exists, splitext, isfile
import re, os, json, sys, io
from .compat import *
import importlib

def logdata(label_name = "", data = None):
	try:
		data = str(data)
		with open("/tmp/FootOnSat.log", "a") as fp:
			fp.write(str(label_name) + " : " + data + "\n")
	except:
		pass

def trace_error():
	try:
		with open("/tmp/FootOnSat.log", "a") as f:
			traceback.print_exc(file=f)
		traceback.print_exc(file=sys.stdout)
	except:
		pass

def DreamOS():
	if exists('/var/lib/dpkg/status'):
		return True
	return False

DEFAULT_DATA_DIR = "/etc/enigma2/footonsat"
def get_data_paths():
	try:
		selected_path = config.plugins.FootOnSat.devicepath.value
	except Exception:
		selected_path = DEFAULT_DATA_DIR
	normalized_path = os.path.normpath(selected_path)
	if normalized_path == DEFAULT_DATA_DIR or normalized_path.endswith("/footonsat"):
		data_dir = normalized_path
	else:
		data_dir = join(normalized_path, "footonsat")
	
	ignore_file = join(data_dir, "ignore-match.json")
	fav_file = join(data_dir, "favorite_teams.json")
	
	if not exists(data_dir):
		try:
			os.makedirs(data_dir)
		except Exception:
			pass
	return data_dir, ignore_file, fav_file

def DreamOS():
	if exists('/var/lib/dpkg/status'):
		return True
	return False

mounted_partitions = harddiskmanager.getMountedPartitions()
mounted_devices = []
default_data_dir = "/etc/enigma2/footonsat"
device_paths = ["/media/net", "/"]
mounted_devices = [(default_data_dir, default_data_dir)]
for part in mounted_partitions:
	try:
		mountpoint = part.mountpoint
		if mountpoint and mountpoint not in device_paths and mountpoint != default_data_dir:
			final_path = join(mountpoint, "footonsat")
			mounted_devices.append((final_path, final_path))
	except Exception:
		pass

config.plugins.FootOnSat = ConfigSubsection()
############ Keep it here do not move it 
_lang_dir = resolveFilename(SCOPE_PLUGINS, "Extensions/FootOnSat/assets/languages")

def _get_lang_name(filepath):
	try:
		with io.open(filepath, 'r', encoding='utf-8') as f:
			lines = f.readlines()
			if len(lines) >= 2:
				# Second line: # English translation by (XXXXXX)
				line = lines[1].strip().lstrip('#').strip()
				name = line.split('translation')[0].strip()
				if name:
					return name
	except:
		pass
	return None

_available_langs = []
try:
	for _file in sorted(os.listdir(_lang_dir)):
		if _file.endswith('.py') and _file != '__init__.py':
			_code = _file[:-3].upper()
			_name = _get_lang_name(os.path.join(_lang_dir, _file))
			if _name:
				_available_langs.append((_code, _name))
except:
	pass

if not _available_langs:
	_available_langs = [("EN", "English")]

config.plugins.FootOnSat.lang = ConfigSelection(default="EN", choices=_available_langs)
_lang = config.plugins.FootOnSat.lang.value.lower()
try:
	_mod = importlib.import_module("Plugins.Extensions.FootOnSat.assets.languages.%s" % _lang)
	globals().update(vars(_mod))
except:
	from Plugins.Extensions.FootOnSat.assets.languages.en import *
#############################
config.plugins.FootOnSat.showplugin = ConfigText(default="")
config.plugins.FootOnSat.devicepath = ConfigSelection(default=default_data_dir,choices=mounted_devices)
config.plugins.FootOnSat.sort = ConfigDictionarySet(default={"footmenu": {"footsubmenu": {}}})
config.plugins.FootOnSat.updateonline = ConfigYesNo(default=True)
config.plugins.FootOnSat.updatebannersonline = ConfigYesNo(default=True)
config.plugins.FootOnSat.enableflag = ConfigYesNo(default=True)
config.plugins.FootOnSat.notiftime = ConfigInteger(default=6, limits=(6, 20))
config.plugins.FootOnSat.notiffile = ConfigText(default="notif1", visible_width = 250, fixed_size = False)
config.plugins.FootOnSat.WakingUp = ConfigInteger(default=3, limits=(1, 60))
config.plugins.FootOnSat.useDashMP4 = ConfigYesNo(default=True)
config.plugins.FootOnSat.extrafetch = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_ZAP = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Notif = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Ignore = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_favorite = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Standings = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Fetch_Live = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_MatchMedia = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_MatchDetails = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_MatchStatistics = ConfigYesNo(default=False)
config.plugins.FootOnSat.pluginicon = ConfigSelection(default = "logo1", choices = [
	("logo1", "%s 1" % title0),
	("logo2", "%s 2" % title0),
	("logo3", "%s 3" % title0),
	("logo4", "%s 4" % title0),
	("logo5", "%s 5" % title0),
	("logo6", "%s 6" % title0),
	("logo7", "%s 7" % title0)
	])
config.plugins.FootOnSat.maxResolution = ConfigSelection(default="22", choices=[
	("38", "4096x3072"), ("37", "1920x1080"), ("22", "1280x720"),
	("35", "854x480"), ("18", "640x360"), ("5", "400x240"), ("17", "176x144")
])
config.plugins.FootOnSat.livecolor = ConfigSelection(default="0xFF0000", choices = [
	("0xFF0000", "%s" % title1),
	("0xFFFFFF", "%s" % title2),
	("0x00FF00", "%s" % title3),
	("0x000000", "%s" % title4),
	("0x0000FF", "%s" % title5),
	])
config.plugins.FootOnSat.finished = ConfigSelection(default = "5", choices = [
	("3", "3 %s" % title6),
	("4", "4 %s" % title6),
	("5", "5 %s" % title6),
	("6", "6 %s" % title6),
	("7", "7 %s" % title6),
	("8", "8 %s" % title6),
	("9999", "%s" % title7)
	])
config.plugins.FootOnSat.livescore = ConfigSelection(default = "2", choices = [
	("1", "%s" % title8),
	("2", "%s" % title9)
	])
config.plugins.FootOnSat.livescoresections = ConfigSelection(default = "1", choices = [
	("1", "%s" % title10),
	("2", "%s" % title11),
	])
config.plugins.FootOnSat.notify_zap = ConfigSelection(default = "1", choices = [
	("1", "%s" % title12),
	("2", "%s" % title13),
	])
config.plugins.FootOnSat.notify = ConfigSelection(default = "1", choices = [
	("1", "%s" % title14),
	("2", "%s" % title15),
	("3", "%s" % title16),
	("4", "%s" % title17),
	("5", "%s" % title18),
	("6", "%s" % title19),
	("7", "%s" % title20)
	])
config.plugins.FootOnSat.icons = ConfigSelection(default = "icons_default", choices = [
	("icons_default", "%s" % title21),
	("icons_buwalla", "%s" % title22),
	("icons_renkli", "%s" % title23),
	("icons_italia2012", "%s" % title24)
	])

config.plugins.FootOnSat.playmethod = ConfigSelection(default = "1", choices = [
	("1", "%s" % title25),
	("2", "%s" % title26),
	])

if DreamOS():
	config.plugins.FootOnSat.player = ConfigSelection(default="4097", choices=[
		("4097", "%s" % title27),
		("8193", "%s" % title28)
	])
else:
	config.plugins.FootOnSat.player = ConfigSelection(default="5002", choices=[
		("4097", "%s" % title29),
		("5002", "%s" % title30)
	])

def getDesktopSize():
	s = getDesktop(0).size()
	return (s.width(), s.height())

def isUHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] >= 2560

def isFHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 1920

if isUHD():
	from Plugins.Extensions.FootOnSat.assets.skin.skinUHD import SKIN_MenuFootOnSat, SKIN_SelectionScreen
else:
	from Plugins.Extensions.FootOnSat.assets.skin.skinFHD import SKIN_MenuFootOnSat, SKIN_SelectionScreen


class MenuFootOnSat(ConfigListScreen, Screen):

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.skin = SKIN_MenuFootOnSat

		self["setupActions"] = ActionMap(["FootOnsatActions"],
		{
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"blue": self.install,
			"ok": self.keyOk,
		}, -1)

		self["key_red"] = StaticText(_("%s") % title97)
		self["key_green"] = StaticText(_("%s") % title98)
		self["key_blue"] = StaticText(_("%s") % title99)

		self["Picture"] = Pixmap()
		self["help"] = StaticText()
		self.lang = config.plugins.FootOnSat.lang.value
		self.old_notiffile = config.plugins.FootOnSat.notiffile.value
		self.old_WakingUp = config.plugins.FootOnSat.WakingUp.value
		self.icons_value = config.plugins.FootOnSat.icons.value
		self.pluginicon = config.plugins.FootOnSat.pluginicon.value
		self.debug_ZAP = config.plugins.FootOnSat.debug_ZAP.value
		self.debug_Notif = config.plugins.FootOnSat.debug_Notif.value
		self.debug_Ignore = config.plugins.FootOnSat.debug_Ignore.value
		self.debug_favorite = config.plugins.FootOnSat.debug_favorite.value
		self.debug_Standings = config.plugins.FootOnSat.debug_Standings.value
		self.debug_Fetch_Live = config.plugins.FootOnSat.debug_Fetch_Live.value
		self.debug_MatchMedia = config.plugins.FootOnSat.debug_MatchMedia.value
		self.debug_MatchDetails = config.plugins.FootOnSat.debug_MatchDetails.value
		self.debug_MatchStatistics = config.plugins.FootOnSat.debug_MatchStatistics.value
		self.getToneFile()
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(title91))
		self.list.append(getConfigListEntry(_("%s") % title31, config.plugins.FootOnSat.lang, _("%s") % title32))
		self.list.append(getConfigListEntry(_("%s") % title33, config.plugins.FootOnSat.showplugin, _("%s") % title34))
		self.list.append(getConfigListEntry(_("%s") % title35, config.plugins.FootOnSat.updateonline, _("%s") % title36))
		self.list.append(getConfigListEntry(_("%s") % title37, config.plugins.FootOnSat.updatebannersonline, _("%s") % title38))
		self.list.append(getConfigListEntry(_("%s") % title39, config.plugins.FootOnSat.pluginicon, _("%s") % title40))
		self.list.append(getConfigListEntry(_("%s") % title41, config.plugins.FootOnSat.icons, _("%s") % title42))
		self.list.append(getConfigListEntry(title92))
		self.list.append(getConfigListEntry(_("%s") % title43, config.plugins.FootOnSat.enableflag, _("%s") % title44))
		self.list.append(getConfigListEntry(_("%s") % title45, config.plugins.FootOnSat.devicepath, _("%s") % title46))
		self.list.append(getConfigListEntry(title93))
		self.list.append(getConfigListEntry(_("%s") % title47, config.plugins.FootOnSat.livescore, _("%s") % title48))
		if config.plugins.FootOnSat.livescore.value in ["2"]:
			self.list.append(getConfigListEntry(_("%s") % title49, config.plugins.FootOnSat.livescoresections, _("%s") % title50))
			self.list.append(getConfigListEntry(_("%s") % title51, config.plugins.FootOnSat.finished, _("%s") % title52))
			self.list.append(getConfigListEntry(_("%s") % title53, config.plugins.FootOnSat.livecolor, _("%s") % title54))
			self.list.append(getConfigListEntry(_("%s") % title55, config.plugins.FootOnSat.extrafetch, _("%s") % title56))
		self.list.append(getConfigListEntry(title94))
		self.list.append(getConfigListEntry(_("%s") % title57, config.plugins.FootOnSat.notiftime, _("%s") % title58))
		self.list.append(getConfigListEntry(_("%s") % title59, config.plugins.FootOnSat.notify_zap, _("%s") % title60))
		self.list.append(getConfigListEntry(_("%s") % title61, config.plugins.FootOnSat.notify, _("%s") % title62))
		self.list.append(getConfigListEntry(_("%s") % title63, config.plugins.FootOnSat.notiffile, _("%s") % title64))
		self.list.append(getConfigListEntry(_("%s") % title297, config.plugins.FootOnSat.WakingUp, _("%s") % title298))
		self.list.append(getConfigListEntry(title95))
		self.list.append(getConfigListEntry(_("%s") % title65, config.plugins.FootOnSat.useDashMP4, _("%s") % title66))
		self.list.append(getConfigListEntry(_("%s") % title67, config.plugins.FootOnSat.maxResolution, _("%s") % title68))
		if DreamOS():
			self.list.append((_("%s") % title69, config.plugins.FootOnSat.player, _("%s") % title70)) 
		has_serviceapp = False
		for p in plugins.getPlugins(where=PluginDescriptor.WHERE_MENU):
			if 'ServiceApp' in p.path:
				has_serviceapp = True
				break
		if has_serviceapp:
			self.list.append((_("%s") % title71, config.plugins.FootOnSat.player, _("%s") % title72))
		else:
			self.list.append((_("%s") % title73, config.plugins.FootOnSat.playmethod, _("%s") % title74))
		self.list.append(getConfigListEntry(title96))
		self.list.append(getConfigListEntry(_("%s") % title75, config.plugins.FootOnSat.debug_ZAP, _("%s") % title76))
		self.list.append(getConfigListEntry(_("%s") % title77, config.plugins.FootOnSat.debug_Notif, _("%s") % title78))
		self.list.append(getConfigListEntry(_("%s") % title79, config.plugins.FootOnSat.debug_Ignore, _("%s") % title80))
		self.list.append(getConfigListEntry(_("%s") % title294, config.plugins.FootOnSat.debug_favorite, _("%s") % title295))
		self.list.append(getConfigListEntry(_("%s") % title81, config.plugins.FootOnSat.debug_Fetch_Live, _("%s") % title82))
		self.list.append(getConfigListEntry(_("%s") % title83, config.plugins.FootOnSat.debug_Standings, _("%s") % title84))
		self.list.append(getConfigListEntry(_("%s") % title85, config.plugins.FootOnSat.debug_MatchMedia, _("%s") % title86))
		self.list.append(getConfigListEntry(_("%s") % title87, config.plugins.FootOnSat.debug_MatchDetails, _("%s") % title88))
		self.list.append(getConfigListEntry(_("%s") % title89, config.plugins.FootOnSat.debug_MatchStatistics, _("%s") % title90))
		
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
				self.session.openWithCallback(self.saveToneSelection, ChoiceBox, title=_("%s") % title101, list=tone_list)
			else:
				self.session.open(MessageBox, _("%s") % title102, MessageBox.TYPE_INFO)

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
			elif index == "icons_italia2012":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/compet/preview/icons_italia2012.png')
			elif index == "logo1":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo/logo1.png')
			elif index == "logo2":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo/logo2.png')
			elif index == "logo3":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo/logo3.png')
			elif index == "logo4":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo/logo4.png')
			elif index == "logo5":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo/logo5.png')
			elif index == "logo6":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo/logo6.png')
			elif index == "logo7":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo/logo7.png')
			if pic and self['Picture'].instance and exists(pic):
				self["Picture"].instance.setScale(1)
				self["Picture"].instance.setPixmapFromFile(pic)
				self["Picture"].instance.show()
			else:
				self['Picture'].hide()
		except Exception as error:
			#logdata("Picture preview error:", str(error))
			pass

	def keyLeft(self):
		cur = self["config"].getCurrent()
		if cur and (cur[1] == config.plugins.FootOnSat.notiftime or cur[1] == config.plugins.FootOnSat.WakingUp):
			cfg = cur[1]
			val = cfg.value
			limits = cfg.limits
			if isinstance(limits[0], int):
				low, high = limits
			else:
				low, high = limits[0]
			if val > low:
				cfg.value = val - 1
				try:
					self["config"].invalidate(cfg)
				except Exception:
					self["config"].invalidate()
				self["config"].l.setList(self["config"].list)
			return
		ConfigListScreen.keyLeft(self)
		self.Picture()
		self.createSetup()

	def keyRight(self):
		cur = self["config"].getCurrent()
		if cur and (cur[1] == config.plugins.FootOnSat.notiftime or cur[1] == config.plugins.FootOnSat.WakingUp):
			cfg = cur[1]
			val = cfg.value
			limits = cfg.limits
			if isinstance(limits[0], int):
				low, high = limits
			else:
				low, high = limits[0]
			if val < high:
				cfg.value = val + 1
				try:
					self["config"].invalidate(cfg)
				except Exception:
					self["config"].invalidate()
				self["config"].l.setList(self["config"].list)
			return
		ConfigListScreen.keyRight(self)
		self.Picture()
		self.createSetup()

	def cancel(self):
		for x in self["config"].list:
			if len(x) > 1:
				x[1].cancel()
		self.close()

	def save(self):
		changed = False
		Restart_changed = False # New flag

		# Check for general config changes
		for x in self["config"].list:
			if len(x) > 1:
				config_item = x[1]
				if hasattr(config_item, 'isChanged') and config_item.isChanged():
					changed = True
					break

		# Check if debug has actually changed
		if self.debug_ZAP != config.plugins.FootOnSat.debug_ZAP.value: Restart_changed = True
		if self.debug_Notif != config.plugins.FootOnSat.debug_Notif.value: Restart_changed = True
		if self.debug_Ignore != config.plugins.FootOnSat.debug_Ignore.value: Restart_changed = True
		if self.debug_favorite != config.plugins.FootOnSat.debug_favorite.value: Restart_changed = True
		if self.debug_Standings != config.plugins.FootOnSat.debug_Standings.value: Restart_changed = True
		if self.debug_Fetch_Live != config.plugins.FootOnSat.debug_Fetch_Live.value: Restart_changed = True
		if self.debug_MatchMedia != config.plugins.FootOnSat.debug_MatchMedia.value: Restart_changed = True
		if self.debug_MatchDetails != config.plugins.FootOnSat.debug_MatchDetails.value: Restart_changed = True
		if self.debug_MatchStatistics != config.plugins.FootOnSat.debug_MatchStatistics.value: Restart_changed = True

		# Check if languages has actually changed
		if self.lang != config.plugins.FootOnSat.lang.value: Restart_changed = True

		# Check if notiffile has actually changed
		if self.old_notiffile != config.plugins.FootOnSat.notiffile.value: Restart_changed = True

		# Check if plugin icon has actually changed
		if self.pluginicon != config.plugins.FootOnSat.pluginicon.value: Restart_changed = True

		# Handle icons download and set Restart_changed flag
		if self.icons_value != config.plugins.FootOnSat.icons.value:
			changed = True # General changed flag also set for safety/consistency
			Restart_changed = True # Set the specific flag for restart prompt
			extract_path = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
			urls = {
				"icons_default": "icons_default.tar.gz",
				"icons_buwalla": "icons_buwalla.tar.gz",
				"icons_renkli": "icons_renkli.tar.gz",
				"icons_italia2012": "icons_italia2012.tar.gz",
			}
			if config.plugins.FootOnSat.icons.value in urls:
				os.system("wget -q -O - https://github.com/fairbird/FootOnsat/raw/refs/heads/main/Download/Style-Icons-Files/%s | tar -xz -C %s" % (urls[config.plugins.FootOnSat.icons.value], extract_path))
		
		# 4. Save all config items
		for x in self["config"].list:
			if len(x) > 1:
				x[1].save()
		configfile.save()
		
		if Restart_changed:
			self.session.openWithCallback(self.restart, MessageBox, title103)
		elif changed:
			self.close("exit_launcher")
		else:
			self.close()

	def install(self):
		list = []
		list.append((title270, "ReInstall_Plugin"))
		list.append((title271, "Update_Languages"))
		self.session.openWithCallback(self.reinstall, ChoiceBox, title=_("%s") % title269, list=list)

	def reinstall(self, select):
		self.list = []
		if select:
			if select[1] == "ReInstall_Plugin":
				self.session.openWithCallback(self.doreinstall, MessageBox, _("%s") % title104, MessageBox.TYPE_YESNO)
			elif select[1] == "Update_Languages":
				self.session.openWithCallback(self.doUpdateinstall, MessageBox, _("%s") % title268, MessageBox.TYPE_YESNO)
		else:
			self.close()

	def doreinstall(self,answer=False):
		try:
			if answer:
				cmdlist = []
				cmd="wget -q https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh"
				cmdlist.append(cmd)
				self.session.open(Console, title="%s" % title105, cmdlist=cmdlist, finishedCallback=self.myCallback, closeOnSuccess=False)
		except:
			trace_error()

	def doUpdateinstall(self, answer=False):
		try:
			if answer:
				cmdlist = []
				extract_path = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
				cmd = "wget -q -O - https://github.com/fairbird/FootOnsat/raw/refs/heads/main/Download/languages/languages_update.tar.gz | tar -xz -C %s" % extract_path
				cmdlist.append(cmd)
				self.session.open(Console, title="%s" % title105, cmdlist=cmdlist, finishedCallback=self.myCallbackUpdate, closeOnSuccess=False)
		except:
			trace_error()

	def myCallback(self):
		return

	def myCallbackUpdate(self):
		self.session.openWithCallback(self.restart, MessageBox, title103)
	
	def restart(self,answer=None):
		if answer:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close(True)


class SelectionScreen(Screen, ConfigListScreen):
        def __init__(self, session):
                Screen.__init__(self, session)
                self.skin = SKIN_SelectionScreen
                ConfigListScreen.__init__(self, [], session=session)
                self.session = session
                self.setup_title = _("%s") % title106
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
                self["key_green"] = Label(title98)
                self["key_red"] = Label(title107)

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
                        ("Menu", _("%s") % title108),
                        ("Channellist", _("%s") % title109),
                        ("Extensions", _("%s") % title110)
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
                        self.session.openWithCallback(self.restart, MessageBox, _("%s") % title111)
                else:
                        self.close(True)

        def restart(self,answer=None):
                if answer:
                        self.session.open(TryQuitMainloop, 3)
                else:
                        self.close(True)
