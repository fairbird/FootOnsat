# -*- coding: utf-8 -*-
import os
import re
import json
import sys
import io
import shutil
import importlib
from os.path import join, exists, splitext, isfile
from twisted.web.client import getPage
from twisted.internet.ssl import ClientContextFactory
from twisted.internet._sslverify import ClientTLSOptions
from twisted.python.failure import Failure
from twisted.internet.threads import deferToThread

from enigma import addFont, getDesktop, eActionMap, eRCInput, eListboxPythonMultiContent, gFont, ePoint, eSize, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_HALIGN_CENTER
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from keyids import KEYIDS
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
from Components.config import config, ConfigYesNo, ConfigInteger, ConfigSubsection, ConfigNumber, ConfigSelection, getConfigListEntry, configfile, ConfigText
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Extensions.FootOnSat.ui.Console import Console
from Plugins.Extensions.FootOnSat.component.configs import ConfigDictionarySet
from .compat import *
from Plugins.Extensions.FootOnSat.__init__ import __version__


try:
	from enigma import BT_SCALE
except ImportError:
	BT_SCALE = 0


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

def get_terminated_file():
	data_dir, _, _ = get_data_paths()
	return join(data_dir, "terminated_matches.json")

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

FONT_DEFAULT_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/fonts/LiberationSans-Regular.ttf"
FONT_SEARCH_PATH = "/usr/share/fonts"

def get_font_choices():
	font_files = []

	try:
		for root, dirs, files in os.walk(FONT_SEARCH_PATH):
			dirs.sort()
			for filename in files:
				if os.path.splitext(filename)[1].lower() in (".ttf", ".otf", ".ttc"):
					font_path = os.path.join(root, filename)
					if os.path.isfile(font_path):
						font_files.append((font_path, os.path.splitext(filename)[0]))
	except Exception:
		pass

	font_files.sort(key=lambda item: (item[1].lower(), item[0].lower()))

	return [("default", "default")] + font_files


def get_foot_font_path():
	selected = config.plugins.FootOnSat.font.value

	if selected != "default" and os.path.isfile(selected):
		return selected

	return FONT_DEFAULT_PATH


config.plugins.FootOnSat.showplugin = ConfigText(default="")
config.plugins.FootOnSat.live_events = ConfigText(default="")
config.plugins.FootOnSat.keyname = ConfigText(default=title340)
config.plugins.FootOnSat.keysection = ConfigText(default="live")
config.plugins.FootOnSat.devicepath = ConfigSelection(default=default_data_dir,choices=mounted_devices)
config.plugins.FootOnSat.sort = ConfigDictionarySet(default={"footmenu": {"footsubmenu": {}}})
config.plugins.FootOnSat.updateonline = ConfigYesNo(default=True)
config.plugins.FootOnSat.updatebannersonline = ConfigYesNo(default=True)
config.plugins.FootOnSat.enableflag = ConfigYesNo(default=True)
config.plugins.FootOnSat.notiftime = ConfigInteger(default=6, limits=(6, 20))
config.plugins.FootOnSat.notiffile = ConfigText(default="notif1", visible_width = 250, fixed_size = False)
config.plugins.FootOnSat.WakingUp = ConfigInteger(default=3, limits=(1, 60))
config.plugins.FootOnSat.useDashMP4 = ConfigYesNo(default=True)
config.plugins.FootOnSat.debug_ZAP = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Notif = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Ignore = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_favorite = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Standings = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_Fetch_Live = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_MatchMedia = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_MatchDetails = ConfigYesNo(default=False)
config.plugins.FootOnSat.debug_MatchStatistics = ConfigYesNo(default=False)
config.plugins.FootOnSat.font = ConfigSelection(default="default", choices=get_font_choices())
config.plugins.FootOnSat.backcolor = ConfigSelection(default = "default", choices = [
	("default", "%s" % title21),
	("rad", "%s" % title1),
	("blue", "%s" % title5),
	("white", "%s" % title2),
	("black", "%s" % title4),
	("yellow", "%s" % title307),
	("green", "%s" % title3)
	])
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
config.plugins.FootOnSat.livescore_pages = ConfigSelection(default = "100", choices = [
	("50", "50"),
	("100", "100"),
	("200", "200"),
	("300", "300"),
	("400", "400")
	])
config.plugins.FootOnSat.livescore = ConfigSelection(default = "2", choices = [
	("1", "%s" % title8),
	("2", "%s" % title9)
	])
config.plugins.FootOnSat.livescoresearchlevel = ConfigSelection(default = "1", choices = [
	("1", "%s" % title308),
	("2", "%s" % title309)
	])
config.plugins.FootOnSat.source = ConfigSelection(default = "flashscore", choices = [
	("flashscore", "%s" % title320),
	("livescore", "%s" % title343),
	("fotmob", "%s" % title324),
	("sofascore", "%s" % title314),
	("espn", "%s" % title316),
#	("sportscore", "%s" % title315),
	])
config.plugins.FootOnSat.livescoresections = ConfigSelection(default = "1", choices = [
	("1", "%s" % title10),
	("2", "%s" % title11),
	])
config.plugins.FootOnSat.espn_limit = ConfigInteger(default=500, limits=(50, 1000))
config.plugins.FootOnSat.backup_enabled = ConfigYesNo(default=False)
backup_path_choices = [("/tmp", "/tmp")]
if exists('/proc/mounts'):
	try:
		with open('/proc/mounts', 'r') as f:
			for line in f.readlines():
				parts = line.split()
				if len(parts) >= 2:
					mp = parts[1].replace("\\040", " ")
					if mp.startswith("/media/") and not mp.startswith("/media/net") and not mp.startswith("/media/autofs") and mp not in [c[0] for c in backup_path_choices]:
						backup_path_choices.append((mp, mp))
	except Exception:
		pass
config.plugins.FootOnSat.backup_path = ConfigSelection(default="/tmp", choices=backup_path_choices)
config.plugins.FootOnSat.backup_custom = ConfigText(default="")
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
	("7", "%s" % title20),
	("0", "%s" % title333)
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

PLUGIN_INTERNAL_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
CURRENT_REAL_PATH = os.path.realpath(PLUGIN_INTERNAL_PATH)

install_choices = [("internal", "%s" % title323)]
for part in mounted_partitions:
	try:
		mountpoint = part.mountpoint
		if mountpoint and mountpoint not in device_paths:
			if os.path.isdir(mountpoint):
				install_choices.append((join(mountpoint, "FootOnSat"), join(mountpoint, "FootOnSat")))
	except Exception:
		pass

if CURRENT_REAL_PATH != PLUGIN_INTERNAL_PATH and CURRENT_REAL_PATH not in [c[0] for c in install_choices]:
	install_choices.append((CURRENT_REAL_PATH, CURRENT_REAL_PATH))

default_path = CURRENT_REAL_PATH if CURRENT_REAL_PATH != PLUGIN_INTERNAL_PATH else "internal"
config.plugins.FootOnSat.installpath = ConfigSelection(default=default_path, choices=install_choices)

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

def getDesktopSize():
	s = getDesktop(0).size()
	return (s.width(), s.height())

def isUHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 2560 or desktopSize[0] == 3840

def isFHD():
	desktopSize = getDesktopSize()
	return desktopSize[0] == 1920

if isUHD():
	from Plugins.Extensions.FootOnSat.assets.skin.skinUHD import SKIN_MenuFootOnSat, SKIN_SelectionScreen, SKIN_CombinedNotificationsScreen, SKIN_BackupSelectionScreen
else:
	from Plugins.Extensions.FootOnSat.assets.skin.skinFHD import SKIN_MenuFootOnSat, SKIN_SelectionScreen, SKIN_CombinedNotificationsScreen, SKIN_BackupSelectionScreen


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


def get_live_event_options():
	return [
		("goal", title327),
		("var", title342),
		("penalty", title329),
		("red_card", title330),
		("half_time", title129),
		("second_half", title211),
		("full_time", title126),
		("extra_time", title216),
		("penalties", title217),
	]


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
		self.keyname = config.plugins.FootOnSat.keyname.value
		self.lang = config.plugins.FootOnSat.lang.value
		self.old_notiffile = config.plugins.FootOnSat.notiffile.value
		self.old_WakingUp = config.plugins.FootOnSat.WakingUp.value
		self.icons_value = config.plugins.FootOnSat.icons.value
		self.backcolor = config.plugins.FootOnSat.backcolor.value
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
		self.old_installpath = config.plugins.FootOnSat.installpath.value
		self.old_font = config.plugins.FootOnSat.font.value
		self.font_preview_aliases = {}
		self.getToneFile()
		self.onLayoutFinish.append(self.applyFontPreview)
		self.createSetup()

	def _update_backup_paths(self):
		paths = [("/tmp", "/tmp")]
		if exists('/proc/mounts'):
			try:
				with open('/proc/mounts', 'r') as f:
					for line in f.readlines():
						parts = line.split()
						if len(parts) >= 2:
							mp = parts[1].replace("\\040", " ")
							if mp.startswith("/media/") and not mp.startswith("/media/net") and not mp.startswith("/media/autofs") and mp not in [c[0] for c in paths]:
								paths.append((mp, mp))
			except Exception:
				pass
		
		curr = config.plugins.FootOnSat.backup_path.value
		if curr and curr not in [c[0] for c in paths]:
			paths.append((curr, curr))
			
		config.plugins.FootOnSat.backup_path.setChoices(paths)

	def select_backup_custom(self):
		plugin_path = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
		current = config.plugins.FootOnSat.backup_custom.value
		self.session.openWithCallback(self._backup_selection_closed, BackupSelectionScreen, plugin_path, current)

	def _backup_selection_closed(self, result=None):
		if result is not None:
			config.plugins.FootOnSat.backup_custom.value = result
			config.plugins.FootOnSat.backup_custom.save()
			configfile.save()
			self.createSetup()

	def _restore_backup(self):
		base_dir = config.plugins.FootOnSat.backup_path.value
		backup_dir = os.path.join(base_dir, "FootOnSat_BackUp")
		files = []
		try:
			for f in os.listdir(backup_dir):
				if f.startswith("Backup-FootOnSat-v") and f.endswith(".tar.gz"):
					files.append(f)
		except:
			pass
			
		if not files:
			self.session.open(MessageBox, _(title352), MessageBox.TYPE_INFO, timeout=5)
			return
			
		list_data = [(f.replace(".tar.gz", ""), f) for f in files]
		self.session.openWithCallback(self._confirm_restore, ChoiceBox, title=_(title351), list=list_data)

	def _confirm_restore(self, choice):
		if not choice:
			return
		base_dir = config.plugins.FootOnSat.backup_path.value
		backup_dir = os.path.join(base_dir, "FootOnSat_BackUp")
		backup_file = os.path.join(backup_dir, choice[1])
		msg = _(title353) % choice[0]
		self.session.openWithCallback(lambda ret: self._do_restore(ret, backup_file), MessageBox, msg, MessageBox.TYPE_YESNO)

	def _do_restore(self, answer, backup_file):
		if answer:
			plugin_path = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
			os.system("tar -xzf '%s' -C '%s'" % (backup_file, plugin_path))
			
			km_src = os.path.join(plugin_path, "keymap.xml")
			km_dst = "/etc/enigma2/footonsat/keymap.xml"
			if os.path.exists(km_src):
				try:
					if not os.path.exists("/etc/enigma2/footonsat"): os.makedirs("/etc/enigma2/footonsat")
					shutil.copyfile(km_src, km_dst)
				except: pass
		
		self.session.openWithCallback(self.restart, MessageBox, _(title354), MessageBox.TYPE_YESNO)

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(title91))
		self.list.append(getConfigListEntry(_("%s") % title321, config.plugins.FootOnSat.installpath, _("%s") % title322))
		self.list.append(getConfigListEntry(_("%s") % title31, config.plugins.FootOnSat.lang, _("%s") % title32))
		self.list.append(getConfigListEntry(_("%s") % title33, config.plugins.FootOnSat.showplugin, _("%s") % title34))
		self.list.append(getConfigListEntry(_("%s") % title301, config.plugins.FootOnSat.keyname, _("%s") % title302))
		self.list.append(getConfigListEntry(_("%s") % title35, config.plugins.FootOnSat.updateonline, _("%s") % title36))
		self.list.append(getConfigListEntry(_("%s") % title37, config.plugins.FootOnSat.updatebannersonline, _("%s") % title38))
		self.list.append(getConfigListEntry(_("%s") % title39, config.plugins.FootOnSat.pluginicon, _("%s") % title40))
		self.list.append(getConfigListEntry(_("%s") % title41, config.plugins.FootOnSat.icons, _("%s") % title42))
		if config.plugins.FootOnSat.icons.value != "icons_renkli":
			self.list.append(getConfigListEntry(_("%s") % title304, config.plugins.FootOnSat.backcolor, _("%s") % title305))
		self.list.append(getConfigListEntry(_("%s") % title367, config.plugins.FootOnSat.font, _("%s") % title368))
		self.list.append(getConfigListEntry(title92))
		self.list.append(getConfigListEntry(_("%s") % title43, config.plugins.FootOnSat.enableflag, _("%s") % title44))
		self.list.append(getConfigListEntry(_("%s") % title45, config.plugins.FootOnSat.devicepath, _("%s") % title46))
		self.list.append(getConfigListEntry(title93))
		self.list.append(getConfigListEntry(_("%s") % title47, config.plugins.FootOnSat.livescore, _("%s") % title48))
		if config.plugins.FootOnSat.livescore.value in ["2"]:
			self.list.append(getConfigListEntry(_("%s") % title312, config.plugins.FootOnSat.source, _("%s") % title313))
			if config.plugins.FootOnSat.source.value == "espn":
				self.list.append(getConfigListEntry(_("%s") % title318, config.plugins.FootOnSat.espn_limit, _("%s") % title319))
			elif config.plugins.FootOnSat.source.value == "livescore":
				self.list.append(getConfigListEntry(_("%s") % title344, config.plugins.FootOnSat.livescore_pages, _("%s") % title345))
			elif config.plugins.FootOnSat.source.value in ["flashscore", "fotmob"]:
				pass
			else:
				self.list.append(getConfigListEntry(_("%s") % title310, config.plugins.FootOnSat.livescoresearchlevel, _("%s") % title311))
			self.list.append(getConfigListEntry(_("%s") % title49, config.plugins.FootOnSat.livescoresections, _("%s") % title50))
			self.list.append(getConfigListEntry(_("%s") % title51, config.plugins.FootOnSat.finished, _("%s") % title52))
			self.list.append(getConfigListEntry(_("%s") % title53, config.plugins.FootOnSat.livecolor, _("%s") % title54))
		self.list.append(getConfigListEntry(title94))
		self.list.append(getConfigListEntry(_("%s") % title57, config.plugins.FootOnSat.notiftime, _("%s") % title58))
		selected_events = set(config.plugins.FootOnSat.live_events.value.split(','))
		selected_events.discard('')

		all_event_keys = set(key for key, text in get_live_event_options())
		selected_events.intersection_update(all_event_keys)

		notify_value = config.plugins.FootOnSat.notify.value
		pre_selected_count = sum(1 for values in (
			("1", "4", "6", "7"),
			("1", "3", "5", "7"),
			("1", "2", "5", "6")
		) if notify_value in values)

		total_selected = pre_selected_count + len(selected_events)
		total_options = 3 + len(all_event_keys)

		if total_selected == total_options:
			live_events_text = title339
		elif total_selected:
			live_events_text = title341 % total_selected
		else:
			live_events_text = title340

		self.live_events_display = ConfigSelection(
			default=live_events_text,
			choices=[(live_events_text, live_events_text)]
		)
		self.list.append(getConfigListEntry(title334, self.live_events_display, title335))
		self.list.append(getConfigListEntry(_("%s") % title59, config.plugins.FootOnSat.notify_zap, _("%s") % title60))
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
			
		self.list.append(getConfigListEntry(title346))
		self.list.append(getConfigListEntry(_("%s") % title347, config.plugins.FootOnSat.backup_enabled, _(title360)))
		if config.plugins.FootOnSat.backup_enabled.value:
			self._update_backup_paths()
			self.list.append(getConfigListEntry(_("%s") % title348, config.plugins.FootOnSat.backup_path, _(title361)))
			custom_val = config.plugins.FootOnSat.backup_custom.value
			custom_text = title340 if not custom_val else title358 % len(custom_val.split(','))
			self.backup_custom_display = ConfigSelection(default=custom_text, choices=[(custom_text, custom_text)])
			self.list.append(getConfigListEntry(_("%s") % title349, self.backup_custom_display, _(title362)))
			
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

	def sectionSelected(self, choice):
		if choice:
			config.plugins.FootOnSat.keysection.value = choice[0]
			config.plugins.FootOnSat.keysection.save()
			self.keySave()
			self.createSetup()

	def keyCaptured(self, keyname=None):
		if keyname:
			config.plugins.FootOnSat.keyname.value = keyname
			config.plugins.FootOnSat.keyname.save()
			sections = [
				("live", _("Live")),
				("today", _("Today")),
				("yesterday", _("Yesterday")),
				("tomorrow", _("Tomorrow")),
				("end", _("Finished")),
				("favorite", _("Favorite")),
				("basketball", _("Basketball")),
				("nba", _("NBA")),
				("hockey", _("Hockey")),
				("nfl", _("NFL")),
				("championsleague", _("Champions League")),
				("europaleague", _("Europa League")),
				("ConferenceLeague", _("Conference League")),
				("premierleague", _("Premier League")),
				("laliga", _("La Liga")),
				("laliga2", _("La Liga 2")),
				("championship", _("Championship")),
				("seriea", _("Serie A")),
				("ligue1", _("Ligue 1")),
				("eredivisie", _("Eredivisie")),
				("saudiarabia", _("Saudi Arabia")),
				("bundesliga", _("Bundesliga")),
				("bundesliga2", _("Bundesliga 2")),
				("belgianpro", _("Belgian Pro League")),
				("superLig", _("Super Lig")),
				("liganos", _("Liga NOS")),
				("afcchampions", _("AFC Champions")),
				("afcchampionstwo", _("AFC Champions Two"))
			]
			self.session.openWithCallback(self.sectionSelected, ChoiceBox, title=_("Select section to open"), list=sections)

	def keyOk(self):
		cur = self["config"].getCurrent()
		if cur and len(cur) > 1 and cur[1] == config.plugins.FootOnSat.keyname:
			self.session.openWithCallback(self.keyCaptured, KeyCaptureScreen)
		if cur and len(cur) > 1 and cur[1] == config.plugins.FootOnSat.showplugin:
			self.session.open(SelectionScreen)
		if cur and len(cur) > 1 and cur[1] == self.live_events_display:
			self.session.openWithCallback(self.liveEventsClosed, CombinedNotificationsScreen)
		if cur and len(cur) > 1 and cur[1] == config.plugins.FootOnSat.notiffile:
			tone_list = self.getToneList()
			if tone_list:
				self.session.openWithCallback(self.saveToneSelection, ChoiceBox, title=_("%s") % title101, list=tone_list)
			else:
				self.session.open(MessageBox, _("%s") % title102, MessageBox.TYPE_INFO)
		if cur and len(cur) > 1 and hasattr(self, 'backup_custom_display') and cur[1] == self.backup_custom_display:
			self.select_backup_custom()
			return

	def liveEventsClosed(self, *args):
		self.createSetup()

	def keySave(self):
		try:
			data_dir, _, _ = get_data_paths()
			if not exists(data_dir):
				os.makedirs(data_dir)
			keymap_path = os.path.join(data_dir, "keymap.xml")
			keyfile = open(keymap_path, "w")
			keyfile.write('<keymap>\n\t<map context="GlobalActions">\n\t\t<key id="%s" mapto="showFootOnSatLive" flags="m" />\n\t</map>\n</keymap>' % config.plugins.FootOnSat.keyname.value)
			keyfile.close()
		except Exception as error:
			logdata("keySave keymap error:", error)

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
			if cur[1] == config.plugins.FootOnSat.font:
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
			elif index == "default":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/Box_on.png')
			elif index == "rad":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/Box_on_red.png')
			elif index == "blue":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/Box_on_blue.png')
			elif index == "white":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/Box_on_white.png')
			elif index == "black":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/Box_on_black.png')
			elif index == "yellow":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/Box_on_yellow.png')
			elif index == "green":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/Box_on_green.png')
			if pic and self['Picture'].instance and exists(pic):
				self["Picture"].instance.setScale(1)
				self["Picture"].instance.setPixmapFromFile(pic)
				self["Picture"].instance.show()
			else:
				self['Picture'].hide()
		except Exception as error:
			#logdata("Picture preview error:", str(error))
			pass

	def applyFontPreview(self):
		try:
			font_path = get_foot_font_path()
			if not isfile(font_path):
				return
			instance = self["config"].instance
			if not instance:
				return
			preview_alias = self.font_preview_aliases.get(font_path)
			if not preview_alias:
				preview_alias = "FootFontPreview%d" % (len(self.font_preview_aliases) + 1)
				addFont(font_path, preview_alias, 100, 0)
				self.font_preview_aliases[font_path] = preview_alias
			font_size = 45 if isUHD() else 30
			preview_font = gFont(preview_alias, font_size)
			try:
				instance.setEntryFont(preview_font)
			except Exception:
				try:
					instance.setFont(preview_font)
				except Exception:
					pass
			try:
				instance.setValueFont(preview_font)
			except Exception:
				pass
			try:
				instance.setHeaderFont(preview_font)
			except Exception:
				pass
			try:
				self["config"].l.invalidate()
			except Exception:
				self["config"].l.setList(self["config"].list)
		except Exception as error:
			#logdata("Font preview error:", error)
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

		if cur and len(cur) > 1 and cur[1] == config.plugins.FootOnSat.font:
			ConfigListScreen.keyLeft(self)
			self.applyFontPreview()
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

		if cur and len(cur) > 1 and cur[1] == config.plugins.FootOnSat.font:
			ConfigListScreen.keyRight(self)
			self.applyFontPreview()
			return

		ConfigListScreen.keyRight(self)
		self.Picture()
		self.createSetup()

	def cancel(self):
		for x in self["config"].list:
			if len(x) > 1:
				x[1].cancel()

		self.applyFontPreview()
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

		# Save Hotkey
		self.keySave()

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

		# Check if keyname has actually changed
		if self.keyname != config.plugins.FootOnSat.keyname.value: Restart_changed = True

		# Check if languages has actually changed
		if self.lang != config.plugins.FootOnSat.lang.value: Restart_changed = True

		# Check if notiffile has actually changed
		if self.old_notiffile != config.plugins.FootOnSat.notiffile.value: Restart_changed = True

		# Check if plugin icon has actually changed
		if self.pluginicon != config.plugins.FootOnSat.pluginicon.value: Restart_changed = True

		# Check if plugin backcolor has actually changed
		if self.backcolor != config.plugins.FootOnSat.backcolor.value: Restart_changed = True

		# Check if plugin font has actually changed
		if self.old_font != config.plugins.FootOnSat.font.value: Restart_changed = True

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

		path_changed = (self.old_installpath != config.plugins.FootOnSat.installpath.value)
		if path_changed:			
			plugin_path = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
			old_real_path = os.path.realpath(plugin_path)
			new_base = config.plugins.FootOnSat.installpath.value
			
			if new_base == "internal" or new_base == "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat":
				new_real_path = plugin_path
			else:
				if new_base.lower().endswith("footonsat"):
					new_real_path = new_base[:-9] + "FootOnSat"
				else:
					new_real_path = os.path.join(new_base, "FootOnSat")
			
			self.wait_dialog = self.session.open(MessageBox, _("Wait while moving the plugin to:\n%s" % new_real_path), MessageBox.TYPE_INFO, enable_input=False)
			
			def move_plugin():
				try:
					if old_real_path == new_real_path:
						return True
						
					if os.path.islink(plugin_path):
						os.unlink(plugin_path)
						
					if new_real_path != plugin_path:
						new_base_dir = os.path.dirname(new_real_path)
						if not os.path.exists(new_base_dir):
							os.makedirs(new_base_dir)
						if os.path.exists(new_real_path):
							shutil.rmtree(new_real_path)
							
						shutil.copytree(old_real_path, new_real_path)
						
						if os.path.exists(plugin_path) and not os.path.islink(plugin_path):
							shutil.rmtree(plugin_path)
							
						os.symlink(new_real_path, plugin_path)
						
						if old_real_path != plugin_path and os.path.exists(old_real_path):
							shutil.rmtree(old_real_path)
					else:
						if not os.path.exists(plugin_path):
							os.makedirs(plugin_path)
							
						for item in os.listdir(old_real_path):
							s = os.path.join(old_real_path, item)
							d = os.path.join(plugin_path, item)
							if os.path.isdir(s):
								shutil.copytree(s, d)
							else:
								shutil.copy2(s, d)
								
						if os.path.exists(old_real_path) and old_real_path != plugin_path:
							shutil.rmtree(old_real_path)
							
					return True
				except Exception as e:
					print("[FootOnSat] Move Error: %s" % str(e))
					return False
					
			def move_finished(result):
				if hasattr(self, 'wait_dialog') and self.wait_dialog:
					self.wait_dialog.close()
				if result:
					for x in self["config"].list:
						if len(x) > 1:
							x[1].save()
					configfile.save()
					self.close("exit_launcher")
				else:
					self.session.open(MessageBox, _("Failed to move the plugin! Please check the logs."), MessageBox.TYPE_ERROR)
			deferToThread(move_plugin).addCallback(move_finished)
			return
			
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
		list.append((_(title351), "Restore_Backup"))
		self.session.openWithCallback(self.reinstall, ChoiceBox, title=_("%s") % title269, list=list)

	def reinstall(self, select):
		self.list = []
		if select:
			if select[1] == "ReInstall_Plugin":
				self.session.openWithCallback(self.doreinstall, MessageBox, _("%s") % title104, MessageBox.TYPE_YESNO)
			elif select[1] == "Update_Languages":
				self.session.openWithCallback(self.doUpdateinstall, MessageBox, _("%s") % title268, MessageBox.TYPE_YESNO)
			elif select[1] == "Restore_Backup":
				self._restore_backup()
		else:
			self.close()

	def doreinstall(self, answer=False):
		try:
			if answer:
				if config.plugins.FootOnSat.backup_enabled.value:
					create_system_backup()
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


class KeyCaptureScreen(Screen):
	skin = """<screen position="center,center" size="500,100" title="" flags="wfNoBorder">
	<widget name="label" position="10,10" size="480,80" font="Regular;35" halign="center" valign="center"/>
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self["label"] = Label(title303)
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


class LiveEventsSelectionScreen(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SKIN_SelectionScreen
		ConfigListScreen.__init__(self, [], session=session)
		self.session = session
		self.setup_title = _("%s") % title325
		self.setTitle(self.setup_title)

		self.empty_box = LoadPixmap(resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/checkbox_empty.png'))
		self.checked_box = LoadPixmap(resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/checkbox_checked.png'))

		# Use existing titles to avoid duplication
		self.event_options = [
			("goal", title327),
			("var", title328),
			("penalty", title329),
			("red_card", title330),
			("half_time", title129),
			("full_time", title126),
			("extra_time", title216),
			("penalties", title217),
		]

		self.selection_states = dict((key, False) for key, _ in self.event_options)
		self.current_value = config.plugins.FootOnSat.live_events.value
		if self.current_value:
			for item in self.current_value.split(','):
				if item in self.selection_states:
					self.selection_states[item] = True

		self["list"] = List([])
		self.updateList()

		self["key_green"] = Label(title98)
		self["key_red"] = Label(title107)

		self["setupActions"] = ActionMap(["FootOnsatActions"], {
			"ok": self.select_option,
			"cancel": self.close,
			"back": self.close,
			"green": self.save
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def updateList(self):
		current_index = self["list"].getIndex() or 0
		self.list = []
		for key, text in self.event_options:
			pixmap = self.checked_box if self.selection_states[key] else self.empty_box
			self.list.append((text, pixmap, key))

		self["list"].setList(self.list)
		self["list"].setIndex(current_index if current_index < len(self.list) else 0)

	def select_option(self):
		current = self["list"].getCurrent()
		if current:
			self.selection_states[current[2]] = not self.selection_states[current[2]]
			self.updateList()

	def save(self):
		selected = [key for key, state in self.selection_states.items() if state]
		config.plugins.FootOnSat.live_events.value = ','.join(selected)
		config.plugins.FootOnSat.live_events.save()
		configfile.save()
		self.close(True)


class CombinedNotificationsScreen(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SKIN_CombinedNotificationsScreen

		if isUHD():
			self.ITEM_H = 130              # Height of each list row
			self.FONT_SIZE = 45            # Font size of option text
			self.CHECKBOX_SIZE = 45        # Width and height of checkbox icons
			self.CHECKBOX_Y = 35           # Vertical position of checkbox icons
			self.TEXT_X_OFFSET = 100       # Horizontal distance between checkbox and text
			self.MARGIN_X = 40             # Left margin inside each option column
			self.LIST_WIDTH = 2075         # Total width of the list content
			self.LIST_X = 40               # Horizontal position of the list on screen
			self.LIST_Y = 40               # Vertical position of the list on screen
			self.SELECTION_WIDTH = 520     # Width of the selection highlight frame
			self.SELECTION_HEIGHT = 122    # Height of the selection highlight frame
		else:
			self.ITEM_H = 65
			self.FONT_SIZE = 30
			self.CHECKBOX_SIZE = 30
			self.CHECKBOX_Y = 17
			self.TEXT_X_OFFSET = 50
			self.MARGIN_X = 20
			self.LIST_WIDTH = 1360
			self.LIST_X = 20
			self.LIST_Y = 20
			self.SELECTION_WIDTH = 300
			self.SELECTION_HEIGHT = 57

		self.session = session
		self["list"] = MenuList([], enableWrapAround=False, content=eListboxPythonMultiContent)
		self["selection"] = Pixmap()
		self["key_green"] = Label(title98)
		self["key_red"] = Label(title107)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions", "WizardActions"], {
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"ok": self.toggle,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
		}, -2)

		self.checked_box = LoadPixmap(resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/checkbox_checked.png'))
		self.empty_box = LoadPixmap(resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/icon/checkbox_empty.png'))

		val = config.plugins.FootOnSat.notify.value
		self.pre_options = [
			{"key": "30min", "text": title336, "checked": val in ("1", "4", "6", "7")},
			{"key": "15min", "text": title337, "checked": val in ("1", "3", "5", "7")},
			{"key": "start", "text": title338, "checked": val in ("1", "2", "5", "6")},
		]

		live_val = config.plugins.FootOnSat.live_events.value
		live_selected = live_val.split(",") if live_val else []

		self.event_options = [
			{"key": key, "text": text, "checked": key in live_selected}
			for key, text in get_live_event_options()
		]

		self.current_row = 1
		self.current_col = 0
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(title331)
		if self["list"].instance:
			self["list"].instance.setSelectionEnable(0)
		self.update_list()

	def _event_rows(self):
		return (len(self.event_options) + 2) // 3

	def _row_columns(self, row):
		if row == 1:
			return len(self.pre_options)
		if row >= 3:
			start = (row - 3) * 3
			return max(0, min(3, len(self.event_options) - start))
		return 0

	def _fix_selection(self):
		rows = self._event_rows()

		if not rows:
			self.current_row = 1
			self.current_col = 0
			return

		if self.current_row != 1:
			self.current_row = max(3, min(self.current_row, 2 + rows))

		columns = self._row_columns(self.current_row)
		self.current_col = max(0, min(self.current_col, columns - 1))

	def update_list(self):
		self._fix_selection()

		self["list"].l.setItemHeight(self.ITEM_H)
		self["list"].l.setFont(0, gFont('Regular', self.FONT_SIZE))

		list_width = self.LIST_WIDTH
		grid_width = int(list_width * 0.78)
		col_w = grid_width // 3
		grid_x = (list_width - grid_width) // 2
		gList = []

		# Pre-match Title
		res = [MultiContentEntryText()]
		res.append(MultiContentEntryText(pos=(self.MARGIN_X, 0), size=(list_width - self.MARGIN_X, self.ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=title365, color=0xffcc00))
		gList.append(res)

		# Pre-match Options
		res = [MultiContentEntryText()]
		start_x = grid_x + (3 - len(self.pre_options)) * col_w // 2

		for c_idx, opt in enumerate(self.pre_options):
			x = start_x + c_idx * col_w
			icon = self.checked_box if opt["checked"] else self.empty_box

			if DreamOS():
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(x + self.MARGIN_X, self.CHECKBOX_Y), size=(self.CHECKBOX_SIZE, self.CHECKBOX_SIZE), png=icon))
			else:
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(x + self.MARGIN_X, self.CHECKBOX_Y), size=(self.CHECKBOX_SIZE, self.CHECKBOX_SIZE), png=icon, flags=BT_SCALE))

			color = 0x00ff00 if (self.current_row == 1 and c_idx == self.current_col) else 0xffffff
			res.append(MultiContentEntryText(pos=(x + self.MARGIN_X + self.TEXT_X_OFFSET, 0), size=(col_w - self.MARGIN_X - self.TEXT_X_OFFSET, self.ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=opt["text"], color=color))

		gList.append(res)

		# Live Events Title
		res = [MultiContentEntryText()]
		res.append(MultiContentEntryText(pos=(self.MARGIN_X, 0), size=(list_width - self.MARGIN_X, self.ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=title366, color=0xffcc00))
		gList.append(res)

		# Live Events - 3 options per row, centered automatically
		for row_index, start in enumerate(range(0, len(self.event_options), 3), 3):
			options = self.event_options[start:start + 3]
			start_x = grid_x + (3 - len(options)) * col_w // 2
			res = [MultiContentEntryText()]

			for c_idx, opt in enumerate(options):
				x = start_x + c_idx * col_w
				icon = self.checked_box if opt["checked"] else self.empty_box
				if DreamOS():
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x + self.MARGIN_X, self.CHECKBOX_Y), size=(self.CHECKBOX_SIZE, self.CHECKBOX_SIZE), png=icon))
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x + self.MARGIN_X, self.CHECKBOX_Y), size=(self.CHECKBOX_SIZE, self.CHECKBOX_SIZE), png=icon, flags=BT_SCALE))

				color = 0x00ff00 if (self.current_row == row_index and c_idx == self.current_col) else 0xffffff
				res.append(MultiContentEntryText(pos=(x + self.MARGIN_X + self.TEXT_X_OFFSET, 0), size=(col_w - self.MARGIN_X - self.TEXT_X_OFFSET, self.ITEM_H), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=opt["text"], color=color))

			gList.append(res)

		self["list"].setList(gList)

		list_row = 1 if self.current_row == 1 else self.current_row + 1

		if gList and self["list"].instance:
			self["list"].instance.moveSelectionTo(list_row)

		if self["selection"].instance:
			columns = self._row_columns(self.current_row)
			start_x = grid_x + (3 - columns) * col_w // 2

			x = self.LIST_X + start_x + self.current_col * col_w + self.MARGIN_X - 8
			y = self.LIST_Y + list_row * self.ITEM_H + 4

			self["selection"].instance.resize(eSize(self.SELECTION_WIDTH, self.SELECTION_HEIGHT))
			self["selection"].instance.setScale(1)
			self["selection"].instance.move(ePoint(x, y))
			self["selection"].show()

		if gList and self["list"].instance:
			self["list"].instance.moveSelectionTo(self.current_row)

		if self["selection"].instance:
			columns = self._row_columns(self.current_row)
			start_x = grid_x + (3 - columns) * col_w // 2

			x = self.LIST_X + start_x + self.current_col * col_w + self.MARGIN_X - 8
			y = self.LIST_Y + self.current_row * self.ITEM_H + 4

			self["selection"].instance.resize(eSize(self.SELECTION_WIDTH, self.SELECTION_HEIGHT))
			self["selection"].instance.setScale(1)
			self["selection"].instance.move(ePoint(x, y))
			self["selection"].show()

	def toggle(self):
		if self.current_row == 1:
			options = self.pre_options
			index = self.current_col
		else:
			options = self.event_options
			index = (self.current_row - 3) * 3 + self.current_col

		if 0 <= index < len(options):
			options[index]["checked"] = not options[index]["checked"]

		self.update_list()

	def up(self):
		last_row = 2 + self._event_rows()

		if self.current_row == 1:
			self.current_row = last_row
		elif self.current_row == 3:
			self.current_row = 1
		else:
			self.current_row -= 1

		self.update_list()

	def down(self):
		last_row = 2 + self._event_rows()

		if self.current_row == 1:
			self.current_row = 3
		elif self.current_row < last_row:
			self.current_row += 1
		else:
			self.current_row = 1

		self.update_list()

	def left(self):
		columns = self._row_columns(self.current_row)
		if columns:
			self.current_col = (self.current_col - 1) % columns
		self.update_list()

	def right(self):
		columns = self._row_columns(self.current_row)
		if columns:
			self.current_col = (self.current_col + 1) % columns
		self.update_list()

	def save(self):
		has_30 = self.pre_options[0]["checked"]
		has_15 = self.pre_options[1]["checked"]
		has_start = self.pre_options[2]["checked"]

		if has_30 and has_15 and has_start: code = "1"
		elif not has_30 and not has_15 and has_start: code = "2"
		elif not has_30 and has_15 and not has_start: code = "3"
		elif has_30 and not has_15 and not has_start: code = "4"
		elif not has_30 and has_15 and has_start: code = "5"
		elif has_30 and not has_15 and has_start: code = "6"
		elif has_30 and has_15 and not has_start: code = "7"
		else: code = "0"

		config.plugins.FootOnSat.notify.value = code
		config.plugins.FootOnSat.notify.save()

		selected_events = [opt["key"] for opt in self.event_options if opt["checked"]]
		config.plugins.FootOnSat.live_events.value = ",".join(selected_events)
		config.plugins.FootOnSat.live_events.save()

		configfile.save()
		self.close(True)

	def cancel(self):
		self.close(False)


def create_system_backup():
	import shutil
	plugin_path = "/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
	base_dir = config.plugins.FootOnSat.backup_path.value
	backup_dir = os.path.join(base_dir, "FootOnSat_BackUp")
	
	if not os.path.exists(backup_dir):
		try:
			os.makedirs(backup_dir)
		except:
			pass
			
	version = str(__version__)
	backup_file = os.path.join(backup_dir, "Backup-FootOnSat-v%s.tar.gz" % version)
	mandatory = ["plugin.py", "__init__.py", "keymap.xml", "ui", "logo", "db", "component", "satfinder", "assets/skin", "assets/sound", "assets/languages", "assets/icon", "assets/fonts", "assets/__init__.py"]
	
	custom_str = config.plugins.FootOnSat.backup_custom.value
	custom = custom_str.split(',') if custom_str else []
	
	all_items = mandatory + custom
	unique_items = []
	
	for item in all_items:
		item = item.strip()
		if item and item not in unique_items and os.path.exists(os.path.join(plugin_path, item)):
			unique_items.append(item)
			
	unique_items.sort(key=len)
	items_to_backup = []
	
	for item in unique_items:
		is_child = False
		for parent in items_to_backup:
			if item.startswith(parent + '/'):
				is_child = True
				break
		if not is_child:
			items_to_backup.append(item)
			
	if items_to_backup:
		km_src = "/etc/enigma2/footonsat/keymap.xml"
		km_dst = os.path.join(plugin_path, "keymap.xml")
		if os.path.exists(km_src) and not os.path.exists(km_dst):
			try: 
				shutil.copyfile(km_src, km_dst)
			except: 
				pass
				
		if "keymap.xml" not in items_to_backup and os.path.exists(km_dst):
			items_to_backup.append("keymap.xml")

		tar_cmd = "tar -czf '%s' --exclude='*.pyc' --exclude='*.pyo' --exclude='__pycache__' -C '%s' %s" % (backup_file, plugin_path, " ".join(["'%s'" % i for i in items_to_backup]))
		os.system(tar_cmd)


class BackupSelectionScreen(Screen):
	def __init__(self, session, root_path, current_selected):
		Screen.__init__(self, session)
		self.skin = SKIN_BackupSelectionScreen
		self.session = session
		self.root_path = root_path
		self.current_path = root_path
		self.selected = set(current_selected.split(',')) if current_selected else set()
		
		self.MANDATORY = [
			"plugin.py", "__init__.py", "keymap.xml", "ui", "logo", "db", "component", "satfinder",
			"assets/skin", "assets/sound", "assets/languages", "assets/icon", "assets/fonts", "assets/__init__.py"
		]

		self["key_green"] = Label(title98)
		self["key_red"] = Label(title107)
		self["key_blue"] = Label(title291)
		self["key_yellow"] = Label(title363)

		self["list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.list_items = []
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
			"ok": self.enter_dir,
			"blue": self.toggle_select,
			"yellow": self.toggle_all,
			"cancel": self.go_back,
			"red": self.close,
			"green": self.save,
			"right": self.jump_bottom,
			"left": self.jump_top,
		}, -1)
		
		self.load_files()

	def jump_top(self):
		if self["list"].instance:
			self["list"].instance.moveSelectionTo(0)

	def jump_bottom(self):
		if self["list"].instance and self.list_items:
			self["list"].instance.moveSelectionTo(len(self.list_items) - 1)

	def load_files(self):
		self.list_items = []
		if self.current_path != self.root_path:
			self.list_items.append(("..", 0xFFFFFF, "..", "parent"))

		try:
			for item in sorted(os.listdir(self.current_path)):
				if item in ("__pycache__",) or item.endswith(".pyc") or item.endswith(".pyo"):
					continue
				full_path = os.path.join(self.current_path, item)
				rel_path = os.path.relpath(full_path, self.root_path).replace('\\', '/')
				
				is_dir = os.path.isdir(full_path)
				is_mandatory = any(rel_path == m or rel_path.startswith(m + '/') for m in self.MANDATORY)
				
				if is_mandatory:
					mark = "*"
					mark_color = 0xFF0000 
				elif rel_path in self.selected:
					mark = "X"
					mark_color = 0x00FF00 
				else:
					mark = " "
					mark_color = 0xFFFFFF 
					
				display_name = item + ("/" if is_dir else "")
				self.list_items.append((mark, mark_color, display_name, rel_path))
		except Exception:
			pass
			
		selectable = []
		for mark, mark_color, display_name, rel_path in self.list_items:
			if rel_path == "parent": continue
			is_mandatory = any(rel_path == m or rel_path.startswith(m + '/') for m in self.MANDATORY)
			if not is_mandatory:
				selectable.append(rel_path)
				
		all_sel = self._get_all_selectable()
		if all_sel and all(p in self.selected for p in all_sel):
			self["key_yellow"].setText(title364)
		else:
			self["key_yellow"].setText(title363)
			
		self.update_list()

	def update_list(self):
		gList = []
		
		if isUHD():
			item_h = 85      # Height of each row
			font_size = 55   # Size of the text
			mark_w = 135     # Width of the checkbox [*] area
			text_w = 1300    # Width of the file/folder name area
		else:
			item_h = 70
			font_size = 42
			mark_w = 80
			text_w = 900

		for mark, mark_color, display_name, rel_path in self.list_items:
			res = [MultiContentEntryText()]
			res.append(MultiContentEntryText(pos=(0, 0), size=(mark_w, item_h), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text="[%s]" % mark, color=mark_color))
			res.append(MultiContentEntryText(pos=(mark_w, 0), size=(text_w, item_h), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF))
			gList.append(res)
		
		if not gList:
			res = [MultiContentEntryText()]
			res.append(MultiContentEntryText(pos=(0, 0), size=(text_w + mark_w, item_h), font=0, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text="Empty Folder", color=0xAAAAAA))
			gList.append(res)
			
		self["list"].l.setItemHeight(item_h)
		self["list"].l.setFont(0, gFont('Regular', font_size))
		self["list"].setList(gList)

	def toggle_select(self):
		idx = self["list"].getSelectedIndex()
		if idx < 0 or idx >= len(self.list_items):
			return
			
		mark, mark_color, display_name, rel_path = self.list_items[idx]
		
		if rel_path == "parent":
			return
			
		is_mandatory = any(rel_path == m or rel_path.startswith(m + '/') for m in self.MANDATORY)
		if is_mandatory:
			self.session.open(MessageBox, _(title359), MessageBox.TYPE_INFO, timeout=3)
			return
			
		if rel_path in self.selected:
			self.selected.remove(rel_path)
		else:
			self.selected.add(rel_path)
		self.load_files()

	def toggle_all(self):
		all_selectable = self._get_all_selectable()
		if not all_selectable:
			return
			
		if all(p in self.selected for p in all_selectable):
			self.selected.clear()
		else:
			self.selected.update(all_selectable)
			
		self.load_files()

	def _get_all_selectable(self):
		all_selectable = []
		for root, dirs, files in os.walk(self.root_path):
			if '__pycache__' in dirs:
				dirs.remove('__pycache__')
				
			rel_root = os.path.relpath(root, self.root_path).replace('\\', '/')
			if rel_root == '.':
				rel_root = ''
				
			for d in dirs:
				rel_path = os.path.join(rel_root, d).replace('\\', '/') if rel_root else d
				is_mandatory = any(rel_path == m or rel_path.startswith(m + '/') for m in self.MANDATORY)
				if not is_mandatory:
					all_selectable.append(rel_path)
					
			for f in files:
				if f.endswith('.pyc') or f.endswith('.pyo'):
					continue
				rel_path = os.path.join(rel_root, f).replace('\\', '/') if rel_root else f
				is_mandatory = any(rel_path == m or rel_path.startswith(m + '/') for m in self.MANDATORY)
				if not is_mandatory:
					all_selectable.append(rel_path)
		return all_selectable

	def enter_dir(self):
		idx = self["list"].getSelectedIndex()
		if idx < 0 or idx >= len(self.list_items):
			return
			
		mark, mark_color, display_name, rel_path = self.list_items[idx]
		
		if rel_path == "parent":
			self.go_back()
			return
			
		full_path = os.path.join(self.current_path, display_name.replace("/", ""))
		if os.path.isdir(full_path):
			self.current_path = full_path
			self.load_files()
		else:
			self.toggle_select()

	def go_back(self):
		if self.current_path != self.root_path:
			self.current_path = os.path.dirname(self.current_path)
			self.load_files()
		else:
			self.close(None)

	def save(self):
		for m in self.MANDATORY:
			if os.path.exists(os.path.join(self.root_path, m)):
				self.selected.add(m)
		self.close(",".join(list(self.selected)))
