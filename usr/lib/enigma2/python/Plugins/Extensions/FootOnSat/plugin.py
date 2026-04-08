# -*- coding: utf-8 -*-
import os
from Components.config import config
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from enigma import addFont, getDesktop

from Plugins.Extensions.FootOnSat.ui.setup import *
from Plugins.Extensions.FootOnSat.ui.interface import FootOnSatNotifDialog
from Plugins.Extensions.FootOnSat.ui.launcher import FootOnsatLauncher

addFont("/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/fonts/miso-bold.ttf", "FootFont", 100, 0)
addFont("/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/fonts/font_default.otf", "ArabicFont", 100, 0)
addFont("/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/fonts/google-icons.ttf", "FootIcons", 100, 0)


def DreamOS():
	if os.path.exists('/var/lib/dpkg/status'):
		return True
	return False

def isHD():
	if getDesktop(0).size().width() < 1920:
		return True
	else:
		return False

def main_menu(menuid, **kwargs):
	if menuid == "mainmenu" and config.plugins.FootOnSat.showplugin.value:
		return [(_("FootOnSat"), main, "FootOnSat", 45)]
	else:
		return []

def main(session, **kwargs):
	if isHD():
		session.open(MessageBox, _("%s") % title112, MessageBox.TYPE_ERROR)
	else:
		session.open(FootOnsatLauncher)

def sessionstart(reason, **kwargs):
	if reason == 0 and not isHD():
		FootOnSatNotifDialog.startNotif(kwargs["session"])

description = _("FootOnSat")

if config.plugins.FootOnSat.pluginicon.value == "logo1":
	ICON = "logo/logo1.png"
elif config.plugins.FootOnSat.pluginicon.value == "logo2":
	ICON = "logo/logo2.png"
elif config.plugins.FootOnSat.pluginicon.value == "logo3":
	ICON = "logo/logo3.png"
elif config.plugins.FootOnSat.pluginicon.value == "logo4":
	ICON = "logo/logo4.png"
elif config.plugins.FootOnSat.pluginicon.value == "logo5":
	ICON = "logo/logo5.png"
elif config.plugins.FootOnSat.pluginicon.value == "logo6":
	ICON = "logo/logo6.png"
else:
	ICON = "logo/logo7.png"

def Plugins(**kwargs):
	result = [
		PluginDescriptor(
			where = [PluginDescriptor.WHERE_SESSIONSTART],
			fnc = sessionstart
		),
		PluginDescriptor(
			name=_("FootOnSat"),
			description = _("%s") % title113,
			where = PluginDescriptor.WHERE_PLUGINMENU,
			icon = ICON,
			fnc = main
		),
	]

	show = config.plugins.FootOnSat.showplugin.value
	selected_options = show.split(",") if show else []

	menulist = PluginDescriptor(
		name=_("FootOnSat"),
		description=description,
		where=PluginDescriptor.WHERE_MENU,
		fnc=main_menu
	)

	extDescriptor = PluginDescriptor(
		name=_("FootOnSat"),
		description=description,
		where=PluginDescriptor.WHERE_EXTENSIONSMENU,
		fnc=main
	)

	if hasattr(PluginDescriptor, "WHERE_CHANNEL_CONTEXT_MENU"):
		contextlist = PluginDescriptor(
			name=_("FootOnSat"),
			description=description,
			where=PluginDescriptor.WHERE_CHANNEL_CONTEXT_MENU,
			fnc=main
		)

	if "Menu" in selected_options:
		result.append(menulist)
	if "Extensions" in selected_options:
		result.append(extDescriptor)
	if "Channellist" in selected_options:
		result.append(contextlist)
		if DreamOS():
			result.append(
				PluginDescriptor(
					name=_("FootOnSat"),
					description=description,
					where=PluginDescriptor.WHERE_CHANNEL_SELECTION_RED,
					fnc=main
				)
			)
	return result
