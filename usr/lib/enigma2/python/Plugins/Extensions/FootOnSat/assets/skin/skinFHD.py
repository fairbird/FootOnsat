# -*- coding: utf-8 -*-
from os.path import join, exists
from Plugins.Extensions.FootOnSat.ui.setup import *


def DreamOS():
	if exists('/var/lib/dpkg/status'):
		return True
	return False

SKIN_launcher = """
<screen name="FootOnsatLauncher" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="MenuLauncher">
    <widget name="menu" boxSize="240" activeSize="285" panelheight="570" itemPerPage="12" margin="30" itemPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/Box_off.png" selPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/Box_on.png" position="center,center" size="1660,585" transparent="1"/>
    <eLabel backgroundColor="#80000000" position="0,870" size="1920,130" />
    <eLabel backgroundColor="#494f4f" position="0,1000" size="1920,130" />
    <widget backgroundColor="#80000000" font="FootFont;33" foregroundColor="#00ffffff" halign="right" noWrap="1" position="403,944" render="Label" size="1180,40" source="session.Event_Now" transparent="1" valign="center" zPosition="5">
        <convert type="FootNextEventTime">TitleStartAndEndTime</convert>
    </widget>
    <widget backgroundColor="#80000000" font="FootFont;33" foregroundColor="#00ffffff" halign="right" noWrap="1" position="1130,890" render="Label" size="450,35" source="session.CurrentService" transparent="1" valign="center" zPosition="110">
        <convert type="ServiceName">Name</convert>
        <convert type="FootNextTextToUpper" />
    </widget>
    <widget backgroundColor="#00999999" foregroundColor="#000E85A5" position="1435,982" render="Progress" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/prograss_top.png" size="150,5" source="session.Event_Now" transparent="0" zPosition="5">
        <convert type="EventTime">Progress</convert>
    </widget>
    <widget alphatest="blend" position="1645,868" render="FootPicon" size="220,132" source="session.CurrentService" zPosition="5">
        <convert type="ServiceName">Reference</convert>
    </widget>
    <ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/play_topbg.png" position="0,0" size="1920,200" zPosition="-12" transparent="1" />
    <widget backgroundColor="#ff2c2d2b" font="FootFont;110" foregroundColor="#00ffffff" halign="right" position="1590,37" render="Label" size="150,150" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %H</convert>
    </widget>
    <widget backgroundColor="#ff2c2d2b" font="FootFont;55" foregroundColor="#00ffffff" halign="left" position="1750,50" render="Label" size="100,55" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %M</convert>
    </widget>
    <widget backgroundColor="#ff2c2d2b" font="FootFont;30" foregroundColor="#00ffffff" halign="left" position="1750,115" render="Label" size="100,50" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %b %d</convert>
    </widget>
    <eLabel backgroundColor="#00ffffff" position="1750,110" size="85,3" zPosition="20" />
    <eLabel text="FootOnsat" position="59,58" size="177,48" zPosition="1" font="FootFont;48" halign="left" foregroundColor="#00ffffff" backgroundColor="#ff2c2d2b" transparent="1" />
    <ePixmap alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/ball.png" position="15,65" size="40,40" zPosition="-12" transparent="1" />
    <eLabel backgroundColor="red" position="0,1075" size="480,5" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;25" foregroundColor="foreground" halign="center" name="red" position="0,1000" size="480,75" transparent="0" valign="center" zPosition="2" />
    <eLabel backgroundColor="green" position="480,1075" size="480,5" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;25" foregroundColor="foreground" halign="center" name="green" position="480,1000" size="480,75" transparent="0" valign="center" zPosition="2" />
    <eLabel backgroundColor="yellow" position="960,1075" size="480,5" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;25" foregroundColor="foreground" halign="center" name="yellow" position="960,1000" size="480,75" transparent="0" valign="center" zPosition="2" />
    <eLabel backgroundColor="blue" position="1440,1075" size="480,5" zPosition="2" />
    <widget backgroundColor="#494f4f" font="FootFont;25" foregroundColor="foreground" halign="center" name="blue" position="1440,1000" size="480,75" transparent="0" valign="center" zPosition="2" />
</screen>
"""

SKIN_interface = """
<screen name="footonsat" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="FootOnSat">
    <ePixmap position="0,0" zPosition="-1" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/bglist.png"/>
    <ePixmap position="0,0" zPosition="1" size="1920,70" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" />
    <eLabel position="1330,586" zPosition="5" size="60,60" text="&#xe333;" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;60" transparent="1"/>
    <eLabel position="1330,670" zPosition="5" size="60,60" text="&#xeb3a;" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;60" transparent="1" />
    <eLabel position="1335,758" zPosition="5" size="50,50" text="&#xf04e;" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;50" transparent="1" />
    <eLabel position="1330,843" zPosition="5" size="60,50" text="&#xe870;" foregroundColor="#00ffffff" backgroundColor="#16000000" font="FootIcons;60" transparent="1" />
    widget name="menu" position="5,15" size="890,45" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" zPosition="5" transparent="1" />
    <widget name="menu2" position="1074,15" size="805,45" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" zPosition="5" transparent="1"/>
    <widget name="channel" position="1450,600" size="385,39" font="Regular;25" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="sat" position="1450,684" size="385,39" font="Regular;25" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="freq" position="1450,765" size="385,39" font="Regular;25" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="enc" position="1450,860" size="385,40" font="Regular;25" halign="left" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="key_red" position="108,880" size="385,40" font="Regular;28" halign="center" foregroundColor="#FF0000" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="key_green" position="108,880" size="385,40" font="Regular;28" halign="center" foregroundColor="#00FF00" backgroundColor="#101c1c1c" zPosition="1" transparent="1" />
    <widget name="key_yellow" position="849,880" size="385,40" font="Regular;28" halign="center" foregroundColor="#FFFF00" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="key_blue" position="1550,900" size="385,40" font="Regular;28" halign="left" foregroundColor="#1E90FF" backgroundColor="#0000FF" zPosition="5" transparent="1" />
    <widget name="list1" position="57,145" size="1220,700" scrollbarMode="showNever" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/button1180x45.png" foregroundColor="#00ffffff" backgroundColorSelected="#0000FF" enableWrapAround="1"  transparent="1" zPosition="2" /> 
    <widget name="list2" position="1315,150" size="560,350" scrollbarMode="showNever" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/list2selectionpixmap.png" foregroundColor="#00ffffff" backgroundColorSelected="#0000FF" enableWrapAround="1" transparent="1" zPosition="3" />
    <widget font="Regular;35" foregroundColor="#00ffffff" backgroundColor="#16000000" halign="center" position="center,15" render="Label" size="143,52" source="global.CurrentTime" transparent="1" valign="center" zPosition="5">
        <convert type="ClockToText">Default</convert>
    </widget>
    <widget name="counter" foregroundColor="#00ffffff" backgroundColor="#16000000" position="655,875" size="143,52" font="Regular;28" transparent="1" valign="center" zPosition="5" />
    <ePixmap position="575,885" zPosition="6" size="32,32" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/spin-down.png" alphatest="blend" />
    <ePixmap position="758,885" zPosition="6" size="32,32" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/spin-up.png" alphatest="blend" />
</screen>
"""

SKIN_FootOnsatNotif = """
<screen name="LiveOnsatNotifScreen" position="550,40" zPosition="10" size="900,175" title="Notif" backgroundColor="#101c1c1c" flags="wfNoBorder">
    <widget name="compet" zPosition="3" position="7,6" size="320,163" />
    <widget name="flag1" zPosition="5" position="333,70" size="40,30" alphatest="blend" />
    <widget name="flag2" zPosition="5" position="850,70" size="40,30" alphatest="blend" />
    <widget name="match" font="Regular;24" position="380,40" zPosition="2" valign="center" halign="center" size="460,90" backgroundColor="#31000000" transparent="1" />
    <widget name="message" font="Regular;26" position="390,85" zPosition="2" valign="center" halign="center" size="420,90" backgroundColor="#31000000" transparent="1" />
    <widget name="live" zPosition="5" position="545,3" size="100,50" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/live_notif.png" alphatest="blend" />
    <ePixmap position="0,0" zPosition="1" size="900,175" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/notif_bar.png" alphatest="blend" />
</screen>
"""

SKIN_standings = """
<screen name="StandingsScreen" position="0,0" size="1920,1080" backgroundColor="#16000000" flags="wfNoBorder" title="Standings">
  <ePixmap position="0,0" zPosition="1" size="1920,70" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend"/>
 
    <!-- Title -->
    <widget name="title" position="center,15" size="600,52" font="Regular;35" halign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1" zPosition="5"/>

    <!-- Top separator line -->
    <eLabel backgroundColor="#00ffffff" position="60,180" size="1800,3" zPosition="5"/>

    <!-- Column headers -->
    <eLabel text="{0}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="65,140" size="59,35" zPosition="5" transparent="1" halign="center"/>
    <eLabel text="{1}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="230,140" size="130,35" zPosition="5" transparent="1" halign="center"/>
    <eLabel text="{2}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="572,140" size="150,35" zPosition="5" transparent="1" halign="center"/>
    <eLabel text="{3}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="745,140" size="130,35" zPosition="5" transparent="1" halign="center"/>
    <eLabel text="{4}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="889,140" size="130,35" zPosition="5" transparent="1" halign="center"/>
    <eLabel text="{5}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1040,140" size="130,35" zPosition="5" transparent="1" halign="center"/>
    <eLabel text="{6}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1199,140" size="130,35" zPosition="5" transparent="1" halign="center"/>
    <eLabel text="{7}|{8}|{9}" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1357,140" size="500,35" zPosition="5" transparent="1" halign="center"/>

    <!-- Standings list -->  
    <widget name="standings_list" position="60,190" size="1800,785" scrollbarMode="showNever" 
        	foregroundColor="#00ffffff" backgroundColorSelected="#0000FF" enableWrapAround="1" transparent="1" zPosition="2"/>

    <!-- Red key label -->
    <widget name="key_red" position="45,990" size="600,40" font="Regular;28" halign="center" 
        	foregroundColor="#00ff2525" backgroundColor="#16000000" zPosition="5" transparent="1" />
</screen>
""".format(title196, title197, title198, title199, title200, title201, title202, title203, title204, title205)

SKIN_standingsbasketball = """
<screen name="StandingsScreen" position="0,0" size="1920,1080" backgroundColor="#16000000" flags="wfNoBorder" title="Standings">
  <ePixmap position="0,0" zPosition="1" size="1920,70" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend"/>
 
    <!-- Title -->
    <widget name="title" position="center,15" size="600,52" font="Regular;35" halign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1" zPosition="5"/>

    <!-- Top separator line -->
    <eLabel backgroundColor="#00ffffff" position="60,180" size="1800,3" zPosition="5"/>

    <!-- Column headers -->
    <eLabel text="{0}" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="65,140" size="59,35" zPosition="5" transparent="1" halign="center" />
    <eLabel text="{1}" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="230,140" size="130,35" zPosition="5" transparent="1" halign="center" />
    <eLabel text="{2}" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="572,140" size="150,35" zPosition="5" transparent="1" halign="center" />
    <eLabel text="{3}" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="780,140" size="130,35" zPosition="5" transparent="1" halign="center" />
    <eLabel text="{4}" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="987,140" size="130,35" zPosition="5" transparent="1" halign="center" />
    <eLabel text="%s" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1177,140" size="130,35" zPosition="5" transparent="1" halign="center" />
    <eLabel text="{5}" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1305,140" size="250,35" zPosition="5" transparent="1" halign="center" />
    <eLabel text="{6}" font="Regular;34" foregroundColor="#00ffffff" backgroundColor="#16000000" position="1540,140" size="250,35" zPosition="5" transparent="1" halign="center" />

    <!-- Standings list -->  
    <widget name="standings_list" position="60,190" size="1800,785" scrollbarMode="showNever" 
        foregroundColor="#00ffffff" backgroundColorSelected="#0000FF" enableWrapAround="1" transparent="1" zPosition="2"/>

    <!-- Red key label -->
    <widget name="key_red" position="45,990" size="600,40" font="Regular;28" halign="center" 
        foregroundColor="#00ff2525" backgroundColor="#16000000" zPosition="5" transparent="1" />
</screen>
""".format(title196, title197, title198, title200, title202, title205, title206)

SKIN_MatchDetails = """
<screen name="MatchDetailsScreen" position="0,0" size="1920,1080" title="Match Details" flags="wfNoBorder" backgroundColor="#16000000">
    <eLabel position="0,0" size="1920,120" backgroundColor="#003366" zPosition="0" />
    <widget name="title" position="40,20" size="1840,80" font="Regular;50" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#003366" transparent="1" zPosition="1"/>
    
    <widget name="home_name_big" position="100,180" size="700,150" font="Regular;70" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#101010" transparent="1" />
    <widget name="away_name_big" position="1120,180" size="700,150" font="Regular;70" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#101010" transparent="1" />

    <widget name="home_team" position="375,340" size="150,100" alphatest="blend" />
    <widget name="away_team" position="1395,340" size="150,100" alphatest="blend" />

    <widget name="score" position="800,200" size="320,150" font="Regular;120" halign="center" valign="center" foregroundColor="#ffcc00" backgroundColor="#101010" transparent="1" />
    <widget name="status" position="800,350" size="320,60" font="Regular;34" halign="center" valign="center" foregroundColor="#00ff00" backgroundColor="#101010" transparent="1" />
    
    <widget name="details_list" position="50,450" size="1780,545" scrollbarMode="showOnDemand" transparent="1" />

    <eLabel text="&lt; {0} | {1} &gt;" position="910,1000" size="969,60" font="Regular;35" foregroundColor="#ffffff" backgroundColor="#16000000" zPosition="5" transparent="1" halign="center" valign="center" />

    <eLabel position="0,1076" size="1920,4" backgroundColor="#333333" />
    <widget name="key_red" position="40,1000" size="400,60" zPosition="1" font="Regular;34" halign="left" valign="center" backgroundColor="#101010" transparent="1" foregroundColor="red" />
</screen>
""".format(title179, title197)

SKIN_MatchStatistics = """
<screen name="MatchStatisticsScreen" position="0,0" size="1920,1080" title="Match Statistics" flags="wfNoBorder" backgroundColor="#16000000">
    <eLabel position="0,0" size="1920,120" backgroundColor="#006633" zPosition="0" />
    <widget name="title" position="40,20" size="1840,80" font="Regular;50" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#006633" transparent="1" zPosition="1" />
	
    <widget name="home_team" position="100,150" size="700,100" font="Regular;60" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
    <widget name="away_team" position="1120,150" size="700,100" font="Regular;60" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
	
    <widget name="stats_list" position="100,280" size="1780,700" scrollbarMode="showOnDemand" transparent="1" />

    <eLabel text="&lt; {0} | {1} &gt;" position="910,1000" size="969,60" font="Regular;35" foregroundColor="#ffffff" backgroundColor="#16000000" zPosition="5" transparent="1" halign="center" valign="center" />
   
    <eLabel position="0,1076" size="1920,4" backgroundColor="#333333" />
    <widget name="key_red" position="40,1000" size="400,60" zPosition="1" font="Regular;34" halign="left" valign="center" backgroundColor="#101010" transparent="1" foregroundColor="red" />
</screen>
""".format(title171, title179)

SKIN_MatchMedia = """
<screen name="MatchMediaScreen" position="0,0" size="1920,1080" title="Match Media" flags="wfNoBorder" backgroundColor="#16000000">
    <eLabel position="0,0" size="1920,120" backgroundColor="#660000" zPosition="0" />
    <widget name="title" position="40,20" size="1840,80" font="Regular;50" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#660000" transparent="1" zPosition="1"/>
    
    <widget name="media_list" position="100,180" size="1720,800" scrollbarMode="showOnDemand" transparent="1" />

    <eLabel text="&lt; {0} | {1} &gt;" position="910,1000" size="969,60" font="Regular;35" foregroundColor="#ffffff" backgroundColor="#16000000" zPosition="5" transparent="1" halign="center" valign="center" />

    <eLabel position="0,1076" size="1920,4" backgroundColor="#333333" />
    <widget name="key_red" position="40,1000" size="400,60" zPosition="1" font="Regular;34" halign="left" valign="center" backgroundColor="#101010" transparent="1" foregroundColor="red" />
</screen>
""".format(title177, title171)

if DreamOS():
	SKIN_MenuFootOnSat = """
		<screen name="MenuFootOnSat" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="MenuFootOnSat">
			<ePixmap position="0,0" zPosition="-1" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/bglist.png"/>
			<ePixmap position="0,0" zPosition="1" size="1920,70" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" />
			<eLabel position="143,920" size="300,3" backgroundColor="#FF0000" zPosition="5" />
			<eLabel position="514,920" size="300,3" backgroundColor="#00FF00" zPosition="5" />
			<eLabel position="884,920" size="300,3" backgroundColor="#0000FF" zPosition="5" />
			<widget source="key_red" render="Label" position="108,880" size="385,40" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget source="key_green" render="Label" position="474,880" size="385,40" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget source="key_blue" render="Label" position="849,880" size="385,40" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget name="config" position="75,145" size="1169,720" backgroundColor="#16000000" scrollbarMode="showOnDemand" transparent="1" />
			<widget source="help" render="Label" position="1315,165" size="532,350" font="Regular;28" foregroundColor="#00e5b243" backgroundColor="#16000000" valign="center" halign="center" transparent="1" zPosition="5"/>
			<widget name="Picture" position="1380,623" size="400,225" zPosition="5" alphatest="blend"/>
			<widget font="Regular;35" foregroundColor="#00ffffff" backgroundColor="#16000000" halign="center" position="center,15" render="Label" size="650,52" source="global.CurrentTime" transparent="1" valign="center" zPosition="5">
				<convert type="ClockToText">Format:%d-%m-%Y&#160;%H:%M:%S</convert>
			</widget>
		</screen>
	"""
else:
	SKIN_MenuFootOnSat = """
		<screen name="MenuFootOnSat" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="MenuFootOnSat">
			<ePixmap position="0,0" zPosition="-1" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/bglist.png"/>
			<ePixmap position="0,0" zPosition="1" size="1920,70" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/infobar_top.png" alphatest="blend" />
			<eLabel position="143,920" size="300,3" backgroundColor="#FF0000" zPosition="5" />
			<eLabel position="514,920" size="300,3" backgroundColor="#00FF00" zPosition="5" />
			<eLabel position="884,920" size="300,3" backgroundColor="#0000FF" zPosition="5" />
			<widget source="key_red" render="Label" position="108,880" size="385,40" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget source="key_green" render="Label" position="474,880" size="385,40" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget source="key_blue" render="Label" position="849,880" size="385,40" font="Regular;30" halign="center" foregroundColor="#00ffffff" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
			<widget name="config" font="Regular;28" secondfont="Regular;28" itemHeight="45" position="75,145" size="1169,720" backgroundColor="#16000000" scrollbarMode="showOnDemand" transparent="1" />
			<widget source="help" render="Label" position="1315,165" size="532,350" font="Regular;28" foregroundColor="#00e5b243" backgroundColor="#16000000" valign="center" halign="center" transparent="1" zPosition="5"/>
			<widget name="Picture" position="1380,623" size="400,225" zPosition="5" alphatest="blend"/>
			<widget font="Regular;35" foregroundColor="#00ffffff" backgroundColor="#16000000" halign="center" position="center,15" render="Label" size="650,52" source="global.CurrentTime" transparent="1" valign="center" zPosition="5">
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

if DreamOS():
	SKIN_TeamListScreen = """
	<screen name="TeamListScreen" position="center,center" size="800,800" title="Select" backgroundColor="#16000000">
		<widget name="list" position="16,19" size="774,774" foregroundColor="#00ffffff" backgroundColor="#16000000" scrollbarMode="showOnDemand" transparent="1"/>
	</screen>
	"""
else:
	SKIN_TeamListScreen = """
	<screen name="TeamListScreen" position="center,center" size="800,800" title="Select" backgroundColor="#16000000">
		<widget name="list" position="16,19" size="774,774" itemHeight="40" font="Regular;28" foregroundColor="#00ffffff" backgroundColor="#16000000" scrollbarMode="showOnDemand" transparent="1"/>
	</screen>
	"""
