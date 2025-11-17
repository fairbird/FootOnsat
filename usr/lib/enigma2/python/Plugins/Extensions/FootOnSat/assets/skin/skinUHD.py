# -*- coding: utf-8 -*-

SKIN_launcher = """
<screen name="FootOnsatLauncher" position="0,0" size="2560,1440" backgroundColor="transparent" flags="wfNoBorder" title="MenuLauncher">
    <widget name="menu" boxSize="300" activeSize="330" panelheight="760" itemPerPage="12" margin="30" itemPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/Box_off.png" selPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/Box_on.png" position="300,center" size="2214,780" transparent="1"/>
    <eLabel backgroundColor="#50494f4f" position="1243,1018" size="100,48" cornerRadius="35" zPosition="-25" />
    <eLabel backgroundColor="#80000000" position="0,1160" size="2560,174" />
    <eLabel backgroundColor="#494f4f" position="0,1334" size="2560,174" />
    <widget backgroundColor="#80000000" font="FootFont;44" foregroundColor="white" halign="right" noWrap="1" position="538,1259" render="Label" size="1574,54" source="session.Event_Now" transparent="1" valign="center" zPosition="5">
        <convert type="FootNextEventTime">TitleStartAndEndTime</convert>
    </widget>
    <widget backgroundColor="#80000000" font="FootFont;44" foregroundColor="white" halign="right" noWrap="1" position="1507,1187" render="Label" size="600,47" source="session.CurrentService" transparent="1" valign="center" zPosition="110">
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
    <widget backgroundColor="#ff2c2d2b" font="FootFont;147" foregroundColor="white" halign="right" position="2120,50" render="Label" size="200,200" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %H</convert>
    </widget>
    <widget backgroundColor="#ff2c2d2b" font="FootFont;74" foregroundColor="white" halign="left" position="2345,67" render="Label" size="134,74" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %M</convert>
    </widget>
    <widget backgroundColor="#ff2c2d2b" font="FootFont;40" foregroundColor="white" halign="left" position="2340,154" render="Label" size="134,67" source="global.CurrentTime" transparent="1" valign="top" zPosition="20">
        <convert type="ClockToText">Format: %b %d</convert>
    </widget>
    <eLabel backgroundColor="white" position="2330,147" size="100,4" zPosition="20" />
    <eLabel text="FootOnsat" position="79,78" size="236,64" zPosition="1" font="FootFont;64" halign="left" foregroundColor="white" backgroundColor="#ff2c2d2b" transparent="1" />
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
    <eLabel position="1774,782" zPosition="5" size="80,80" text="" foregroundColor="white" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <eLabel position="1774,894" zPosition="5" size="80,85" text="" foregroundColor="white" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <eLabel position="1776,1011" zPosition="5" size="80,85" text="" foregroundColor="white" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <eLabel position="1780,1115" zPosition="5" size="80,80" text="" foregroundColor="white" backgroundColor="#16000000" font="FootIcons;80" transparent="1" />
    <widget name="channel" position="1934,811" size="514,52" font="Regular;34" halign="left" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="sat" position="1934,927" size="514,52" font="Regular;34" halign="left" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="freq" position="1934,1043" size="514,52" font="Regular;34" halign="left" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="enc" position="1934,1147" size="514,54" font="Regular;34" halign="left" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="key_red" position="296,1150" font="Regular;38" halign="left" foregroundColor="red" backgroundColor="#0000FF" zPosition="5" transparent="1" size="353,100" />
	<widget name="key_green" position="296,1170" size="514,54" font="Regular;38" halign="left" foregroundColor="#00FF00" backgroundColor="#101c1c1c" zPosition="5" transparent="1" />
    <widget name="key_yellow" position="1215,1150" font="Regular;38" halign="left" foregroundColor="yellow" backgroundColor="#0000FF" zPosition="5" transparent="1" size="353,100" />
    <widget name="key_blue" position="2067,1200" size="514,54" font="Regular;38" halign="left" foregroundColor="#1E90FF" backgroundColor="#0000FF" zPosition="5" transparent="1" />
    <widget name="list1" position="76,194" size="1627,875" scrollbarMode="showNever" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/button1450x175.png" foregroundColor="white" foregroundColorSelected="#00F9C731" backgroundColorSelected="#0000FF" enableWrapAround="1" transparent="1" zPosition="2" itemsPerPage="5" /> 
    <widget name="list2" position="1754,200" size="747,456" scrollbarMode="showNever" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/list22selectionpixmap.png" foregroundColor="white" foregroundColorSelected="#00F9C731" backgroundColorSelected="#0000FF" enableWrapAround="1" transparent="1" zPosition="3" />
    <widget font="Regular;47" foregroundColor="#00ffffff" backgroundColor="#16000000" halign="center" position="1184,13" render="Label" size="191,70" source="global.CurrentTime" transparent="1" valign="center" zPosition="5">
        <convert type="ClockToText">Default</convert>
    </widget>
    <widget name="counter" foregroundColor="#00ffffff" backgroundColor="#16000000" position="874,1167" size="191,70" font="Regular;38" transparent="1" valign="center" zPosition="5" />
    <ePixmap position="767,1180" zPosition="6" size="43,43" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/spin-down.png" alphatest="blend" />
    <ePixmap position="1011,1180" zPosition="6" size="43,43" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/spin-up.png" alphatest="blend" />
</screen>
"""

SKIN_FootOnsatNotif = """
<screen name="LiveOnsatNotifScreen" position="734,54" zPosition="10" size="1200,234" title="Notif" backgroundColor="#101c1c1c" flags="wfNoBorder">
    <widget name="compet" zPosition="3" position="10,8" size="427,218" />
    <widget name="flag1" zPosition="5" position="444,94" size="54,40" alphatest="blend" />
    <widget name="flag2" zPosition="5" position="1134,94" size="54,40" alphatest="blend" />
    <widget name="match" font="Regular;32" position="507,54" zPosition="2" valign="center" halign="center" size="614,120" backgroundColor="#31000000" transparent="1" />
    <widget name="message" font="Regular;35" position="520,114" zPosition="2" valign="center" halign="center" size="560,120" backgroundColor="#31000000" transparent="1" />
    <widget name="live" zPosition="5" position="1074,4" size="134,67" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/live_notif.png" alphatest="blend" />
    <ePixmap position="0,0" zPosition="1" size="1200,234" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat/assets/icon/notif_bar.png" alphatest="blend" />
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
    <widget name="standings_list" position="65,380" size="2434,958" scrollbarMode="showNever"
    		foregroundColor="#ffffff" foregroundColorSelected="#ffff00" enableWrapAround="1" transparent="1" zPosition="2" />

    <!-- Red key label -->
    <widget name="key_red" position="61,1376" size="1179,60" font="Regular;38" halign="left"
        	foregroundColor="red" backgroundColor="#0000FF" zPosition="5" transparent="1" />
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
    <widget name="standings_list" position="65,380" size="2434,958" scrollbarMode="showNever" foregroundColor="#ffffff" foregroundColorSelected="#ffff00" enableWrapAround="1" transparent="1" zPosition="2" />

    <!-- Red key label -->
    <widget name="key_red" position="61,1376" size="1179,60" font="Regular;38" halign="left" foregroundColor="red" backgroundColor="#0000FF" zPosition="5" transparent="1" />
</screen>
"""
