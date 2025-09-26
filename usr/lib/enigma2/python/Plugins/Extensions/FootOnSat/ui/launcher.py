# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigYesNo, ConfigSubsection, getConfigListEntry, NoSave, configfile
from Plugins.Extensions.FootOnSat.ui.Console import Console
from Plugins.Extensions.FootOnSat.ui.interface import FootOnSat, WebClientContextFactory, readFromFile
from Plugins.Extensions.FootOnSat.component.configs import ConfigDictionarySet
from Components.FootMenu import FlexibleMenu
from Plugins.Extensions.FootOnSat.__init__ import __version__
from twisted.web.client import getPage
import re
import os
import json
import sys
import traceback
from sys import version_info

PY3 = version_info[0] == 3

config.plugins.FootOnSat = ConfigSubsection()
config.plugins.FootOnSat.sort = ConfigDictionarySet(default={"footmenu": {"footsubmenu": {}}})
config.plugins.FootOnSat.updateonline = ConfigYesNo(default=True)

def DreamOS():
	if os.path.exists('/var/lib/dpkg/status'):
		return True
	return False

def trace_error():
	try:
		traceback.print_exc(file=sys.stdout)
		traceback.print_exc(file=open("/tmp/FootOnSat.log", "a"))
	except:
		pass

def logdata(label_name = "", data = None):
	try:
		data=str(data)
		fp = open("/tmp/FootOnSat.log", "a")
		fp.write( str(label_name) + " : " + data+"\n")
		fp.close()
	except:
		trace_error()    
		pass

VER = float(__version__)


class FootOnsatLauncher(Screen):

	def __init__(self, session, *args):
		self.session = session
		Screen.__init__(self, session)
		skin = "assets/skin/FHD/launcher.xml"
		self.skin = readFromFile(skin)
		self["setupActions"] = ActionMap(["FootOnsatActions"],
		{
			'left': self.left,
			'right': self.right,
			'up': self.up,
			'down': self.down,
			'ok': self.ok,
			'blue': self.keyBlue,
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
		self.session.open(MenuFootOnSat)

	def callAPI(self):
		if config.plugins.FootOnSat.updateonline.value:
			self.checkupdates()
		url = 'https://raw.githubusercontent.com/fairbird/footonsat-api/main/api.json'
		sniFactory = WebClientContextFactory(url)
		getPage(str.encode(url), contextFactory=sniFactory).addCallback(self.getData).addErrback(self.error)

	def getData(self, data):
		if isinstance(data, bytes):
			data = data.decode("utf-8")
		compet = json.loads(data).keys()
		ordering = ["today", "championsleague", "europaleague", "ConferenceLeague", "premierleague", "laliga", "seriea",
		"bundesliga", "ligue1", "superLig", "saudiarabia", "afcchampions","championship"]
		# Keep only items in ordering, then sort according to ordering
		filtered_compet = [c for c in ordering if c in compet]
		self.menuList = self.custom_sort(ordering, filtered_compet)

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
		self.hide_show_entries()
		self["menu"].setList(self.menuList)
		self.selectionChanged()

	def custom_sort(self, ordem_custom, origin):
		list_order_equals = [c for c in ordem_custom if (c in origin)]
		list_no_equals = [c for c in origin if (not c in ordem_custom)]
		list_order = list_order_equals + list_no_equals
		return list_order

	def error(self, error=None):
		if error:
			self.session.openWithCallback(self.exit, MessageBox, _('An Unexpected Error Occurred During The API Request !!'), MessageBox.TYPE_ERROR, timeout=10)

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
	if DreamOS():
		skin = """
				<screen name="MenuFootOnSat" position="center,center" size="1040,560" title="Menu FootOnSat">
					<widget source="global.CurrentTime" render="Label" position="5,5" size="1022,50" font="Regular;35" halign="center" foregroundColor="#00ffa500" backgroundColor="#16000000" transparent="1">
						<convert type="ClockToText">Format:%d-%m-%Y	%H:%M:%S</convert>
					</widget>
					<widget name="config" position="18,70" size="1005,344" scrollbarMode="showOnDemand"/>
					<eLabel text="" foregroundColor="#00ff2525" backgroundColor="#00ff2525" size="235,5" position="223,550" zPosition="-10"/>
					<eLabel text="" foregroundColor="#00389416" backgroundColor="#00389416" size="235,5" position="585,550" zPosition="-10"/>
					<widget render="Label" source="key_red" position="223,515" size="235,40" zPosition="5" valign="center" halign="center" backgroundColor="#16000000" font="Regular;28" transparent="1" foregroundColor="#00ffffff" shadowColor="black"/>
					<widget render="Label" source="key_green" position="585,515" size="235,40" zPosition="5" valign="center" halign="center" backgroundColor="#16000000" font="Regular;28" transparent="1" foregroundColor="#00ffffff" shadowColor="black" shadowOffset="-1,-1"/>
				</screen>"""
	else:
		skin = """
				<screen name="MenuFootOnSat" position="center,center" size="1040,560" title="Menu FootOnSat">
					<widget source="global.CurrentTime" render="Label" position="5,5" size="1022,50" font="Regular;35" halign="center" foregroundColor="#00ffa500" backgroundColor="#16000000" transparent="1">
						<convert type="ClockToText">Format:%d-%m-%Y	%H:%M:%S</convert>
					</widget>
					<widget name="config" font="Regular;28" secondfont="Regular;28" itemHeight="45" position="18,70" size="1005,344" scrollbarMode="showOnDemand"/>
					<eLabel text="" foregroundColor="#00ff2525" backgroundColor="#00ff2525" size="235,5" position="223,550" zPosition="-10"/>
					<eLabel text="" foregroundColor="#00389416" backgroundColor="#00389416" size="235,5" position="585,550" zPosition="-10"/>
					<widget render="Label" source="key_red" position="223,515" size="235,40" zPosition="5" valign="center" halign="center" backgroundColor="#16000000" font="Regular;28" transparent="1" foregroundColor="#00ffffff" shadowColor="black"/>
					<widget render="Label" source="key_green" position="585,515" size="235,40" zPosition="5" valign="center" halign="center" backgroundColor="#16000000" font="Regular;28" transparent="1" foregroundColor="#00ffffff" shadowColor="black" shadowOffset="-1,-1"/>
				</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.list = []
		ConfigListScreen.__init__(self, self.list)

		self["setupActions"] = ActionMap(["FootOnsatActions"],
		{
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
		}, -1)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enable checking for Online Update"), config.plugins.FootOnSat.updateonline, _(" This option to Enable or Disable checking for Online Update")))
		self['config'].list = self.list
		self['config'].l.setList(self.list)

	def cancel(self):
		self.close()

	def save(self):
		for x in self["config"].list:
			if len(x)>1:
				x[1].save()
		configfile.save()
		self.close()
