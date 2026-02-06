# -*- coding: utf-8 -*-
from os.path import join, exists

def DreamOS():
	if exists('/var/lib/dpkg/status'):
		return True
	return False

SKIN_launcher = """
<screen name="FootOnsatLauncher" position="0,0" size="2560,1440" backgroundColor="transparent" flags="wfNoBorder" title="MenuLauncher">
    <widget name="menu" boxSize="300" activeSize="330" panelheight="760" itemPerPage="12" margin="30" itemPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/Box_off.png" selPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/Box_on.png" position="300,center" size="2214,780" transparent="1"/>
    <eLabel backgroundColor="#50494f4f" position="1223,1018" size="138,48" cornerRadius="25" zPosition="-25" />
    <eLabel backgroundColor="#80000000" position="0,1160" size="2560,174" />
    <eLabel backgroundColor="#494f4f" position="0,1334" size="2560,174" />
    <widget backgroundColor="#80000000" font="FootFont;44" foregroundColor="#00ffffff" halign="right" noWrap="1" position="538,1259" render="Label" size="1574,54" source="session.Event_Now" transparent="1" valign="center" zPosition="5">
        <convert type="FootNextEventTime">TitleStartAndEndTime</convert>
    </widget>
    <widget backgroundColor="#80000000" font="FootFont;44" foregroundColor="#00ffffff" halign="right" noWrap="1" position="1507,1187" render="Label" size="600,47" source="session.CurrentService" transparent="1" valign="center" zPosition="110">
        <convert type="ServiceName">Name</convert>
        <convert type="FootNextTextToUpper" />
    </widget>
    <widget backgroundColor="#00999999" foregroundColor="#000E85A5" position="1914,1310" render="Progress" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/prograss_top.png" size="200,7" source="session.Event_Now" transparent="0" zPosition="5">
        <convert type="EventTime">Progress</convert>
    </widget>
    <widget alphatest="blend" position="2194,1158" render="FootPicon" size="294,176" source="session.CurrentService" zPosition="5">
        <convert type="ServiceName">Reference</convert>
    </widget>
    <ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/play_topbg.png" position="0,0" size="2560,267" zPosition="-12" transparent="1" />
    <widget backgroundColor="#ff2c2d2b" font="FootFont;147" foregroundColor="#00ffffff" halign="right" position="2120,50" render="Label" size="200,200" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %H</convert>
    </widget>
    <widget backgroundColor="#ff2c2d2b" font="FootFont;74" foregroundColor="#00ffffff" halign="left" position="2345,67" render="Label" size="134,74" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %M</convert>
    </widget>
    <widget backgroundColor="#ff2c2d2b" font="FootFont;40" foregroundColor="#00ffffff" halign="left" position="2340,154" render="Label" size="134,67" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %b %d</convert>
    </widget>
    <eLabel backgroundColor="#00ffffff" position="2330,147" size="100,4" zPosition="20" />
    <eLabel text="FootOnsat" position="79,78" size="236,64" zPosition="1" font="FootFont;64" halign="left" foregroundColor="#00ffffff" backgroundColor="#ff2c2d2b" transparent="1" />
    <ePixmap alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/ball.png" position="20,87" size="54,54" zPosition="-12" transparent="1" />
    <eLabel backgroundColor="red" position="0,1434" size="640,7" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;34" foregroundColor="foreground" halign="center" name="red" position="0,1334" size="640,100" transparent="0" valign="center" zPosition="2" />
    <eLabel backgroundColor="green" position="640,1434" size="640,7" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;34" foregroundColor="foreground" halign="center" name="green" position="640,1334" size="640,100" transparent="0" valign="center" zPosition="2" />
    <eLabel backgroundColor="yellow" position="1280,1434" size="640,7" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;34" foregroundColor="foreground" halign="center" name="yellow" position="1280,1334" size="640,100" transparent="0" valign="center" zPosition="2" />
    <eLabel backgroundColor="blue" position="1920,1434" size="640,7" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;34" foregroundColor="foreground" halign="center" name="blue" position="1920,1334" size="640,100" transparent="0" valign="center" zPosition="2" />
</screen>
"""

SKIN_interface = """
<screen name="footonsat" position="0,0" size="2560,1440" backgroundColor="transparent" flags="wfNoBorder" title="FootOnSat">
    <ePixmap position="0,0" zPosition="-1" size="2560,1440" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/bglist.png" scale="streach" />
    <ePixmap position="0,0" zPosition="1" size="2560,94" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" scale="streach" />
    <eLabel position="1774,782" zPosition="5" size="80,80" text="" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <eLabel position="1774,894" zPosition="5" size="80,85" text="" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <eLabel position="1776,1011" zPosition="5" size="80,85" text="" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <eLabel position="1780,1115" zPosition="5" size="80,80" text="" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <widget name="menu" position="171,32" size="822,58" font="Regular;34" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="menu2" position="1563,32" size="825,58" font="Regular;34" halign="right" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="channel" position="1934,811" size="514,52" font="Regular;34" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="sat" position="1934,927" size="514,52" font="Regular;34" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="freq" position="1934,1043" size="514,52" font="Regular;34" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="enc" position="1934,1147" size="514,54" font="Regular;34" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="key_red" position="296,1150" font="Regular;38" halign="left" foregroundColor="#FF0000" backgroundColor="#0000FF" zPosition="5" transparent="1" size="353,100" />
    <widget name="key_green" position="296,1170" size="514,54" font="Regular;38" halign="left" foregroundColor="#00FF00" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="key_yellow" position="1215,1150" font="Regular;38" halign="left" foregroundColor="yellow" backgroundColor="#0000FF" zPosition="5" transparent="1" size="353,100" />
    <widget name="key_blue" position="2067,1200" size="514,54" font="Regular;38" halign="left" foregroundColor="#1E90FF" backgroundColor="#0000FF" zPosition="5" transparent="1" />
    <widget name="list1" position="76,194" size="1627,875" scrollbarMode="showNever" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/button1450x175.png" foregroundColor="#00ffffff" foregroundColorSelected="#00F9C731" backgroundColorSelected="#0000FF" enableWrapAround="1" transparent="1" zPosition="2" /> 
    <widget name="list2" position="1754,200" size="747,456" scrollbarMode="showNever" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/list22selectionpixmap.png" foregroundColor="#00ffffff" foregroundColorSelected="#00F9C731" backgroundColorSelected="#0000FF" enableWrapAround="1" transparent="1" zPosition="3" />
    <widget font="Regular;47" foregroundColor="#00ffffff" backgroundColor="#16000000" halign="center" position="center,13" render="Label" size="473,70" source="global.CurrentTime" transparent="1" valign="center" zPosition="5">
        <convert type="ClockToText">Format:%H:%M  %a. %d.%m.%Y</convert>
    </widget>
    <widget name="counter" foregroundColor="#00ffffff" backgroundColor="#16000000" position="756,1167" halign="center" size="309,70" font="Regular;38" transparent="1" valign="center" zPosition="5" />
    <ePixmap position="767,1180" zPosition="6" size="43,43" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/spin-down.png" alphatest="blend" />
    <ePixmap position="1011,1180" zPosition="6" size="43,43" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/spin-up.png" alphatest="blend" />
</screen>
"""

SKIN_FootOnsatNotif = """
<screen name="LiveOnsatNotifScreen" position="734,54" zPosition="10" size="1200,234" title="Notif" backgroundColor="#262626" flags="wfNoBorder">
    <widget name="compet" zPosition="3" position="10,8" size="427,218" />
    <widget name="flag1" zPosition="5" position="451,94" size="54,40" alphatest="blend" />
    <widget name="flag2" zPosition="5" position="1134,94" size="54,40" alphatest="blend" />
    <widget name="match" font="Regular;32" position="509,54" zPosition="2" valign="center" halign="center" size="622,120" backgroundColor="transparent" transparent="1" />
    <widget name="message" font="Regular;35" position="509,114" zPosition="2" valign="center" halign="center" size="622,120" backgroundColor="transparent" transparent="1" />
    <widget name="live" zPosition="5" position="753,10" size="150,83" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/live_notifuhd.png" alphatest="blend" />
    <ePixmap position="0,0" zPosition="1" size="1200,234" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/notif_baruhd.png" alphatest="blend" />
</screen>
"""

SKIN_standings = """
<screen name="StandingsScreen" position="0,0" size="3840,2160" backgroundColor="#16000000" flags="wfNoBorder" title="Standings">
  <ePixmap position="0,0" zPosition="1" size="3840,140" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" />
    <!-- Title -->
  <widget name="title" position="0,32" size="2564,122" font="Regular;70" halign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1" zPosition="5" />
    <!-- Top separator line -->
    <eLabel backgroundColor="#00ffffff" position="65,360" size="2428,6" zPosition="5" />
    <!-- Column headers -->
    <eLabel text="Pos." font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="50,300" size="118,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Team" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="235,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Played" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="614,300" size="300,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Points" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="880,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Wins" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1123,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Draws" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1375,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Losses" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1610,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Goals Scored | Conceded | Difference" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1882,300" size="610,70" zPosition="5" transparent="1" halign="center" />
    <!-- Standings list -->  
    <widget name="standings_list" position="65,380" size="2434,940" scrollbarMode="showNever"
    		foregroundColor="#ffffff" foregroundColorSelected="#ffff00" enableWrapAround="1" transparent="1" zPosition="2" />
    <!-- Red key label -->
    <widget name="key_red" position="61,1358" size="502,60" font="Regular;38" halign="left" foregroundColor="#00ffffff" backgroundColor="#0000FF" zPosition="5" transparent="1" />
</screen>
"""

SKIN_standingsbasketball = """
<screen name="StandingsScreen" position="0,0" size="3840,2160" backgroundColor="#16000000" flags="wfNoBorder" title="Standings">
  <ePixmap position="0,0" zPosition="1" size="3840,140" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" />
    <!-- Title -->
    <widget name="title" position="0,32" size="2564,122" font="Regular;70" halign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1" zPosition="5" />
    <!-- Top separator line -->
    <eLabel backgroundColor="#00ffffff" position="65,360" size="2428,6" zPosition="5" />
    <!-- Column headers -->
    <eLabel text="Pos." font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="50,300" size="118,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Team" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="250,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Played" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="730,300" size="300,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Wins" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1030,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Losses" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1330,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="%s" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1630,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Difference" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1930,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <eLabel text="Win Percentage" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="2230,300" size="260,70" zPosition="5" transparent="1" halign="center" />
    <!-- Standings list -->  
    <widget name="standings_list" position="65,380" size="2434,948" scrollbarMode="showNever" foregroundColor="#ffffff" foregroundColorSelected="#ffff00" enableWrapAround="1" transparent="1" zPosition="2" />
    <!-- Red key label -->
    <widget name="key_red" position="61,1358" size="502,60" font="Regular;38" halign="left" foregroundColor="#00ffffff" backgroundColor="#0000FF" zPosition="5" transparent="1" />
</screen>
"""

SKIN_MatchDetails = """
<screen name="MatchDetailsScreen" position="0,0" size="2560,1440" title="Match Details" flags="wfNoBorder" backgroundColor="#16000000">
    <eLabel position="0,0" size="2560,208" backgroundColor="#003366" zPosition="0" />
    <widget name="title" position="80,40" size="2400,131" font="Regular;90" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" zPosition="1" />
    <widget name="home_name_big" position="50,210" size="980,160" font="Regular;80" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#101010" transparent="1" />
    <widget name="away_name_big" position="1535,210" size="980,160" font="Regular;80" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#101010" transparent="1" />
    <widget name="home_team" position="50,375" size="980,115" backgroundColor="#101010" transparent="1" alphatest="blend" />
    <widget name="away_team" position="1535,375" size="980,115" backgroundColor="#101010" transparent="1" alphatest="blend" />
    <widget name="score" position="970,145" size="640,300" font="Regular;80" halign="center" valign="center" foregroundColor="#ffcc00" backgroundColor="#101010" transparent="1" />
    <widget name="status" position="970,370" size="640,120" font="Regular;60" halign="center" valign="center" foregroundColor="#00ff00" backgroundColor="#101010" transparent="1" />
    <widget name="details_list" position="50,510" size="2462,780" scrollbarMode="showOnDemand" transparent="1" />
    <eLabel text="Move Left or Right for Statistics" position="1716,1330" size="800,120" font="Regular;38" foregroundColor="#ffffff" backgroundColor="#16000000" zPosition="5" transparent="1" halign="right" />  
    <widget name="key_red" position="50,1300" size="800,120" zPosition="1" font="Regular;38" halign="left" valign="center" backgroundColor="#101010" transparent="1" foregroundColor="red" />
</screen>
"""

SKIN_MatchStatistics = """
<screen name="MatchStatisticsScreen" position="0,0" size="2560,1440" title="Match Statistics" flags="wfNoBorder" backgroundColor="#101010">
    <eLabel position="0,0" size="2560,208" backgroundColor="#006633" zPosition="0" />
    <widget name="title" position="80,40" size="2400,131" font="Regular;90" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#006633" transparent="1" zPosition="1" />
    <widget name="home_team" position="50,210" size="980,160" font="Regular;80" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="away_team" position="1535,210" size="980,160" font="Regular;80" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="stats_list" position="50,429" size="2462,780" scrollbarMode="showOnDemand" transparent="1" />
    <eLabel text="Move Left or Right for Details" position="1716,1330" size="800,120" font="Regular;38" foregroundColor="#ffffff" backgroundColor="#16000000" zPosition="5" transparent="1" halign="right" />  
    <eLabel position="0,2152" size="3840,8" backgroundColor="#333333" />
    <widget name="key_red" position="50,1300" size="800,120" font="Regular;38" halign="left" valign="center" backgroundColor="#101010" transparent="1" foregroundColor="red" />
</screen>
"""

SKIN_MatchMedia = """
<screen name="MatchMediaScreen" position="0,0" size="2560,1440" title="Match Media" flags="wfNoBorder" backgroundColor="#16000000">
    <eLabel position="0,0" size="2560,208" backgroundColor="#660000" zPosition="0" />
    <widget name="title" position="80,40" size="2400,131" font="Regular;90" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#660000" transparent="1" zPosition="1" />
    <widget name="media_list" position="50,291" size="2462,999" scrollbarMode="showOnDemand" transparent="1" />
    <eLabel text="&lt; Statistics | Details &gt;" position="1716,1290" size="800,120" font="Regular;38" foregroundColor="#ffffff" backgroundColor="#16000000" zPosition="5" transparent="1" halign="right" valign="center" />
    <widget name="key_red" position="50,1300" size="800,120" zPosition="1" font="Regular;38" halign="left" valign="center" backgroundColor="#101010" transparent="1" foregroundColor="red" />
</screen>
"""

if DreamOS():
	SKIN_MenuFootOnSat = """
		<screen name="MenuFootOnSat" position="0,0" size="2560,1440" backgroundColor="transparent" flags="wfNoBorder" title="MenuFootOnSat">
		<ePixmap position="0,0" zPosition="-1" size="2560,1440" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/bglist.png" scale="streach" />
		<ePixmap position="0,0" zPosition="1" size="2560,94" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" scale="streach" />
		<eLabel position="76,194" size="1627,875" backgroundColor="#262626" zPosition="0" />
		<eLabel position="226,1235" size="300,3" backgroundColor="#FF0000" zPosition="5" />
		<eLabel position="740,1235" size="300,3" backgroundColor="#00FF00" zPosition="5" />
		<eLabel position="1245,1235" size="300,3" backgroundColor="#0000FF" zPosition="5" />
		<widget source="key_red" render="Label" position="201,1185" size="353,50" font="Regular;38" halign="center" foregroundColor="#00ffffff" backgroundColor="#0000FF" zPosition="5" transparent="1" />
		<widget source="key_green" render="Label" position="710,1185" size="353,50" font="Regular;38" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
		<widget source="key_blue" render="Label" position="1215,1185" size="353,50" font="Regular;38" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />	    
		<widget name="config" position="76,194" size="1627,840" backgroundColor="#00000000" backgroundColorSelected="#000033" foregroundColor="#ffffff" foregroundColorSelected="#ffff00" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />
		<widget source="help" render="Label" position="1760,389" size="710,188" font="Regular;29" foregroundColor="#00e5b243" backgroundColor="#16000000" halign="center" transparent="1" zPosition="5" />
		<widget name="Picture" position="1900,830" size="480,340" zPosition="5" alphatest="blend" />
		<widget font="Regular;47" foregroundColor="#00ffffff" backgroundColor="#16000000" halign="center" position="center,13" render="Label" size="811,70" source="global.CurrentTime" transparent="1" valign="center" zPosition="5">
			<convert type="ClockToText">Format:%H:%M:%S</convert>
			</widget>
		</screen>
	"""
else:
	SKIN_MenuFootOnSat = """
		<screen name="MenuFootOnSat" position="0,0" size="2560,1440" backgroundColor="transparent" flags="wfNoBorder" title="MenuFootOnSat">
			<ePixmap position="0,0" zPosition="-1" size="2560,1440" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/bglist.png" scale="streach" />
			<ePixmap position="0,0" zPosition="1" size="2560,94" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" scale="streach" />
			<eLabel position="76,194" size="1627,875" backgroundColor="#262626" zPosition="0" />
			<eLabel position="326,1235" size="300,3" backgroundColor="#FF0000" zPosition="5" />
			<eLabel position="785,1235" size="300,3" backgroundColor="#00FF00" zPosition="5" />
			<eLabel position="1245,1235" size="300,3" backgroundColor="#0000FF" zPosition="5" />
			<widget source="key_red" render="Label" position="296,1185" size="353,50" font="Regular;38" halign="center" foregroundColor="#00ffffff" backgroundColor="#0000FF" zPosition="5" transparent="1" />
			<widget source="key_green" render="Label" position="760,1185" size="353,50" font="Regular;38" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget source="key_blue" render="Label" position="1215,1185" size="353,50" font="Regular;38" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget name="config" font="Regular;28" secondfont="Regular;28" itemHeight="45" position="76,194" size="1627,875" backgroundColor="#00000000" backgroundColorSelected="#262626" foregroundColor="#ffffff" foregroundColorSelected="#ffff00" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />
			<widget source="help" render="Label" position="1760,389" size="710,188" font="Regular;29" foregroundColor="#00e5b243" backgroundColor="#16000000" halign="center" transparent="1" zPosition="5" />
			<widget name="Picture" position="1900,830" size="480,340" zPosition="5" alphatest="blend" />
			<widget font="Regular;47" foregroundColor="#00ffffff" backgroundColor="#16000000" halign="center" position="center,13" render="Label" size="811,70" source="global.CurrentTime" transparent="1" valign="center" zPosition="5">
				<convert type="ClockToText">Format:%d-%m-%Y     %H:%M:%S</convert>
			</widget>
		</screen>
	"""

SKIN_SelectionScreen = """
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
</screen>
"""
