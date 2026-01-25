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
import re, os, json, sys
from .compat import *


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
        from Plugins.Extensions.FootOnSat.assets.skin.skinUHD import *
else:
        from Plugins.Extensions.FootOnSat.assets.skin.skinFHD import *

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
config.plugins.FootOnSat.useDashMP4 = ConfigYesNo(default=True)
config.plugins.FootOnSat.extrafetch = ConfigYesNo(default=False)
config.plugins.FootOnSat.pluginicon = ConfigSelection(default = "logo1", choices = [
	("logo1", _("logo 1")),
	("logo2", _("logo 2")),
	("logo3", _("logo 3"))
	])
config.plugins.FootOnSat.maxResolution = ConfigSelection(default='22', choices=[
	('38', '4096x3072'), ('37', '1920x1080'), ('22', '1280x720'),
	('35', '854x480'), ('18', '640x360'), ('5', '400x240'), ('17', '176x144')
])
config.plugins.FootOnSat.livecolor = ConfigSelection(default="0xFF0000", choices = [
	("0xFF0000", _("RED")),
	("0xFFFFFF", _("WHITE")),
	("0x00FF00", _("GREEN")),
	("0x000000", _("BLACK")),
	("0x0000FF", _("BLUE")),
	])
config.plugins.FootOnSat.finished = ConfigSelection(default = "3", choices = [
	("3", _("3 hours")),
	("4", _("4 hours")),
	("5", _("5 hours")),
	("6", _("6 hours")),
	("7", _("7 hours")),
	("8", _("8 hours")),
	("9999", _("Disable (Always keep)"))
	])
config.plugins.FootOnSat.livescore = ConfigSelection(default = "2", choices = [
	("1", _("No live Score + Status")),
	("2", _("Live Score + Status"))
	])
config.plugins.FootOnSat.livescoresections = ConfigSelection(default = "1", choices = [
	("1", _("All Sections")),
	("2", _("Live and Match End sections only")),
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
	("icons_italia2012", _("italia2012 Full style color"))
	])

if DreamOS():
	config.plugins.FootOnSat.player = ConfigSelection(default='4097', choices=[
		('4097', _('Default (4097)')),
		('8193', _('DreamOS GstPlayer (8193)'))
	])
else:
	config.plugins.FootOnSat.player = ConfigSelection(default='5002', choices=[
		('4097', _('Default (4097)')),
		('5002', _('ExtePlayer'))
	])

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
			"blue": self.reinstall,
			"ok": self.keyOk,
		}, -1)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))
		self["key_blue"] = StaticText(_("Install Plugin"))

		self["Picture"] = Pixmap()
		self["help"] = StaticText()
		self.old_notiffile = config.plugins.FootOnSat.notiffile.value
		self.icons_value = config.plugins.FootOnSat.icons.value
		self.pluginicon = config.plugins.FootOnSat.pluginicon.value
		self.getToneFile()
		self.createSetup()

	def createSetup(self):
		self.configChanged = True
		self.list = []
		self.list.append(getConfigListEntry("_____________________________礑 Plugin 礑__________________________________________"))
		self.list.append(getConfigListEntry(_("Show Plugin #press OK to change"), config.plugins.FootOnSat.showplugin, _("This option to show Plugin in any where you like")))
		self.list.append(getConfigListEntry(_("Enable checking for Online Update"), config.plugins.FootOnSat.updateonline, _("This option to Enable or Disable checking for Online Update")))
		self.list.append(getConfigListEntry(_("Choose the icon of plugin"), config.plugins.FootOnSat.pluginicon, _("This option to allows you to select the icon of plugin.\n\nChoose and Press Save (Green Button)")))
		self.list.append(getConfigListEntry(_("Select Icons Style"), config.plugins.FootOnSat.icons, _("This option to allows you to select Icons Style.\nChoose and Press Save (Green Button)")))
		self.list.append(getConfigListEntry("______________________________礑 Other 礑__________________________________________"))
		self.list.append(getConfigListEntry(_("Enable flags of teams"), config.plugins.FootOnSat.enableflag, _("This option to Enable or Disable flags of teams with logo")))
		self.list.append(getConfigListEntry(_("Path to store ignore file"), config.plugins.FootOnSat.devicepath, _("This option to set the path of save file for ignore matches")))
		self.list.append(getConfigListEntry("_______________________________礑 Live 礑__________________________________________"))
		self.list.append(getConfigListEntry(_("Enable Live score + status"), config.plugins.FootOnSat.livescore, _("This feature allows you to show or hide the matches with or without result + status")))
		if config.plugins.FootOnSat.livescore.value in ["2"]:
			self.list.append(getConfigListEntry(_("Select appear live + score of match in"), config.plugins.FootOnSat.livescoresections, _("This feature allows you to show matches live with result in sections")))
			self.list.append(getConfigListEntry(_("Time to keep finished matches"), config.plugins.FootOnSat.finished, _("This option specifies how long finished matches remain in the 'Match End' section before they disappear")))
			self.list.append(getConfigListEntry(_("Color of score and status"), config.plugins.FootOnSat.livecolor, _("This option allows you to choose the color of score and status.")))
			self.list.append(getConfigListEntry(_("Activate an additional url"), config.plugins.FootOnSat.extrafetch, _("This option allows you to activate an additional URL link to download data.\n\nActivating this will take longer for the fetch process on (Saturday and Sunday) to more than 1 minute.")))
		self.list.append(getConfigListEntry("____________________________礑 notifications 礑__________________________________________"))
		self.list.append(getConfigListEntry(_("Choose time for notifications"), config.plugins.FootOnSat.notiftime, _("This feature allows you to choose the number of seconds for notifications to appear.\n\nMove <Left | Right> to change seconds from (6 - 20)")))
		self.list.append(getConfigListEntry(_("Choose to notifications and Zap"), config.plugins.FootOnSat.notify_zap, _("This feature allows you to specify the notifications and Zap to selected channel")))
		self.list.append(getConfigListEntry(_("Choose to display notifications"), config.plugins.FootOnSat.notify, _("This feature allows you to specify the times for notifications to appear when matches start")))
		self.list.append(getConfigListEntry(_("Choose tone of notifications #press OK to change"), config.plugins.FootOnSat.notiffile, _("This feature allows you to select a notification tone when matches start")))
		self.list.append(getConfigListEntry("_______________________________礑 Media 礑__________________________________________"))
		self.list.append(getConfigListEntry(_("Use DASH MP4 format"), config.plugins.FootOnSat.useDashMP4, _("Specify or you want to use DASH MP4 format streams if available.\n\nThis requires playing two streams together and may cause problems for some receivers.")))
		self.list.append(getConfigListEntry(_("Maximum video resolution"), config.plugins.FootOnSat.maxResolution, _("What maximum resolution used when playing video, if available.\n\nIf you have a slow Internet connection, you can use a lower resolution.")))
		if DreamOS():
			self.list.append((_('Media Player:'), config.plugins.FootOnSat.player, _('Specify the player which will be used for media playback.'))) 
		for p in plugins.getPlugins(where=PluginDescriptor.WHERE_MENU):
			if 'ServiceApp' in p.path:
				self.list.append((_('Media player:'),config.plugins.FootOnSat.player, _('Specify the player which will be used for media playback.')))
				break
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
			elif index == "icons_italia2012":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/assets/compet/preview/icons_italia2012.png')
			elif index == "logo1":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo1.png')
			elif index == "logo2":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo2.png')
			elif index == "logo3":
				pic = resolveFilename(SCOPE_PLUGINS, 'Extensions/FootOnSat/logo3.png')
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
			if len(x) > 1:
				x[1].cancel()
		self.close()

	def save(self):
		changed = False
		icons_changed = False # New flag

		# Check for general config changes
		for x in self["config"].list:
			if len(x) > 1:
				config_item = x[1]
				if hasattr(config_item, 'isChanged') and config_item.isChanged():
					changed = True
					break
		
		# Check if notiffile has actually changed
		if self.old_notiffile != config.plugins.FootOnSat.notiffile.value:
			changed = True

		# Check if plugin icon has actually changed
		if self.pluginicon != config.plugins.FootOnSat.pluginicon.value:
			icons_changed = True

		# Handle icons download and set icons_changed flag
		if self.icons_value != config.plugins.FootOnSat.icons.value:
			changed = True # General changed flag also set for safety/consistency
			icons_changed = True # Set the specific flag for restart prompt
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
		
		if icons_changed:
			self.session.openWithCallback(self.restart, MessageBox, _("You need to restart GUI\nDo you want to do it now ?!"))
		elif changed:
			self.close("exit_launcher")
		else:
			self.close()

	def reinstall(self):
		self.session.openWithCallback(self.doinstall, MessageBox, _("Do You want to Reinstall pluign again ?!"), MessageBox.TYPE_YESNO)

	def doinstall(self,answer=False):
		try:
			if answer:
				cmdlist = []
				cmd="wget -q https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh"
				cmdlist.append(cmd)
				self.session.open(Console, title='Installing last update, enigma will be started after install', cmdlist=cmdlist, finishedCallback=self.myCallback, closeOnSuccess=False)
		except:
			trace_error()
	
	def myCallback(self):
		return

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
