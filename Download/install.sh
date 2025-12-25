#!/bin/sh

#wget -q "--no-check-certificate" https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/install.sh -O - | /bin/sh
VERSION=5.8
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/FootOnSat"
DB_FILE="$PLUGIN_PATH/db/footonsat.db"
ASSETS_PATH="$PLUGIN_PATH/assets"
IGNORE_PATH="$PLUGIN_PATH/ignore"
TMP_DB="/tmp/footonsat.db"
TMP_ASSETS="/tmp/assets"

E2Settings='/etc/enigma2/settings'
SETTING_NAME="config.plugins.FootOnSat.icons"
CURRENT_VALUE=$(
    grep "^$SETTING_NAME=" "$E2Settings" \
    | awk -F '=' '{print $2}' \
    | tr -d '\n\r' \
    | sed 's#s/##'
)

[ -z "$CURRENT_VALUE" ] && CURRENT_VALUE="icons_default"

if [ -f /etc/apt/apt.conf ] ; then
	STATUS='/var/lib/dpkg/status'
	OS='DreamOS'
elif [ -f /etc/opkg/opkg.conf ] ; then
	STATUS='/var/lib/opkg/status'
	OS='Opensource'
fi

ARCH=$(uname -m)

if echo "$ARCH" | grep -qi 'armv7l'; then
	echo ':Your Device IS ARM processor ...'
	DEVICE="arm"
elif echo "$ARCH" | grep -qi 'aarch64'; then
	echo ':Your Device IS AARCH64 processor ...'
	DEVICE="arm64"
elif echo "$ARCH" | grep -qi 'mips'; then
	echo ':Your Device IS MIPS processor ...'
	DEVICE="mips"
elif echo "$ARCH" | grep -qi 'sh4'; then
	echo ':Your Device IS SH4 processor ...'
	DEVICE="sh4"
else
	echo 'Unknown Device'
	DEVICE="unknown"
fi

# Find the highest python3.xx version in /usr/bin
PYTHON_BIN=$(ls /usr/bin/python3.*[0-9] 2>/dev/null | \
    sed 's/[^0-9]*\([0-9]\+\)$/\1/' | sort -n | tail -n 1 | \
    xargs -I{} ls /usr/bin/python3.{} 2>/dev/null | head -n 1)
if [ -n "$PYTHON_BIN" ]; then
    PYTHON_VERSION=$(basename "$PYTHON_BIN")
    # Check if /usr/bin/python3 symlink exists
    if [ ! -L /usr/bin/python3 ]; then
        echo "Creating symlink: /usr/bin/python3 -> $PYTHON_BIN"
        sudo ln -sf "$PYTHON_BIN" /usr/bin/python3
    else
        echo "/usr/bin/python3 symlink already exists"
    fi
	echo ""
    # Check if /usr/bin/python symlink exists
    if [ ! -L /usr/bin/python ]; then
        echo "Creating symlink: /usr/bin/python -> $PYTHON_BIN"
        sudo ln -sf "$PYTHON_BIN" /usr/bin/python
    else
        echo "/usr/bin/python symlink already exists"
    fi
	echo ""
fi

if [ -d $PLUGIN_PATH ]; then

	if [ -f "$DB_FILE" ]; then
		echo ""
		echo "Backup old db..."
		cp -a "$DB_FILE" "$TMP_DB" >/dev/null 2>&1
	fi
	echo ""
#	echo "Backup current style ..."
#	mkdir -p "$TMP_ASSETS/compet" >/dev/null 2>&1
#	mkdir -p "$TMP_ASSETS/skin" >/dev/null 2>&1
#	cp -a "$ASSETS_PATH/compet/icons" "$TMP_ASSETS/compet" >/dev/null 2>&1
#	cp -a "$ASSETS_PATH/skin" "$TMP_ASSETS" >/dev/null 2>&1
#	cp -a "$ASSETS_PATH/icon" "$TMP_ASSETS" >/dev/null 2>&1
#    echo "Remove old version."
#    if [ "$OS" = "Opensource" ]; then
#        opkg remove enigma2-plugin-extensions-footonsat
#    else
#       apt-get purge --auto-remove enigma2-plugin-extensions-footonsat
#    fi

fi
echo ""
if python --version 2>&1 | grep -q '^Python 3\.'; then
   echo "You have Python3 image"
   PYTHON='PY3'
   SQLITE3='python3-sqlite3'
   PYSIX='python3-six'
   SOUP4='python3-beautifulsoup4'
   DIFFLIB='python3-difflib'
   THREADING='python3-threading'
   PLI='python3-pillow'
   REQUESTES='python3-requests'
else
   echo "You have Python2 image"
   PYTHON='PY2'
   SQLITE3='python-sqlite3'
   PYSIX='python-six'
   SOUP4='python-beautifulsoup4'
   DIFFLIB='python-difflib'
   THREADING='python-threading'
   PLI='python-imaging'
   REQUESTES='python-requests'
fi

if grep -q "$SQLITE3" "$STATUS"; then
    sqlite='Installed'
fi

if grep -q "$PYSIX" "$STATUS"; then
    six='Installed'
fi

if grep -q 'alsa-utils-aplay' "$STATUS"; then
    aplay='Installed'
fi

if grep -q "$SOUP4" "$STATUS"; then
    beautifulsoup4='Installed'
fi

if grep -q "$DIFFLIB" "$STATUS"; then
    difflib='Installed'
fi

if grep -q "$THREADING" "$STATUS"; then
    threading='Installed'
fi

if grep -q "$PLI" "$STATUS"; then
    pil='Installed'
fi

if grep -q "$REQUESTES" "$STATUS"; then
    requestes='Installed'
fi

if [ "$sqlite" = "Installed" -a "$six" = "Installed" -a "$aplay" = "Installed" -a "$beautifulsoup4" = "Installed" -a \
      "$difflib" = "Installed" -a "$threading" = "Installed" -a "$pil" = "Installed" -a "$requestes" = "Installed" ]; then
     echo ""
else

    if [ "$OS" != "DreamOS" ]; then
        echo "=========================================================================="
        echo "Some Depends Need to Be downloaded From Feeds ...."
        echo "=========================================================================="
        echo "Opkg Update ..."
        echo "========================================================================"
        opkg update
        echo "========================================================================"
        echo " Downloading alsa-utils-aplay ......"
        opkg install ffmpeg
        opkg install alsa-utils-aplay
        echo "========================================================================"
        echo "========================================================================"
        echo " Downloading $SQLITE3 , $PYSIX , $SOUP4 , $DIFFLIB , $THREADING , $PLI , $REQUESTES  ......"
        opkg install $SQLITE3
        opkg install $PYSIX
        opkg install $SOUP4
        opkg install $DIFFLIB
        opkg install $THREADING
        opkg install $PLI
        opkg install $REQUESTES
        echo "========================================================================"
    else
        echo "=========================================================================="
        echo "Some Depends Need to Be downloaded From Feeds ...."
        echo "=========================================================================="
        echo "apt Update ..."
        echo "========================================================================"
        apt-get update
        echo "========================================================================"
        echo " Downloading alsa-utils-aplay ......"
        apt-get install ffmpeg -y
        apt-get install alsa-utils-aplay -y
        echo "========================================================================"
        echo "========================================================================"
        echo " Downloading $SQLITE3 , $PYSIX , $SOUP4 , $DIFFLIB , $THREADING , $PLI , $REQUESTES ......"
        apt-get install $SQLITE3 -y
        apt-get install $PYSIX -y
        apt-get install $SOUP4 -y
        apt-get install $DIFFLIB -y
        apt-get install $THREADING -y
        apt-get install $PLI -y
        apt-get install $REQUESTES -y
        echo "========================================================================"
    fi
fi

if ! grep -q 'ffmpeg' "$STATUS" || ! grep -q 'alsa-utils-aplay' "$STATUS"; then
	if [ "$DEVICE" = "arm64" ]; then
		cd /tmp
		wget -q "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/Pacakges/arm64/alsa-utils-aplay.deb"
		wget -q "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/Pacakges/arm64/alsa-utils-amixer.deb"
		wget -q "https://raw.githubusercontent.com/fairbird/FootOnsat/main/Download/Pacakges/arm64/alsa-utils-arecord.deb"
		dpkg -i --force-overwrite *.deb
		apt-get install -f -y
		cd ..
	fi
fi

if ! grep -q 'ffmpeg' "$STATUS" || ! grep -q 'alsa-utils-aplay' "$STATUS"; then
    echo "#########################################################"
    echo "#   ffmpeg and/or alsa-utils-aplay Not found in feed    #"
    echo "#  Notification sound will not work without alsa aplay  #"
    echo "#########################################################"
fi

if grep -q "$SQLITE3" "$STATUS"; then
	: # Null command (do nothing, but satisfy the shell syntax)
else
	echo "#########################################################"
	echo "#       $SQLITE3 Not found in feed                      #"
	echo "#########################################################"
	exit 1
fi

if grep -q "$PYSIX" "$STATUS"; then
	: # Null command (do nothing, but satisfy the shell syntax)
else
	echo "#########################################################"
	echo "#       $PYSIX Not found in feed                        #"
	echo "#########################################################"
	exit 1
fi

if grep -q "$SOUP4" "$STATUS"; then
	: # Null command (do nothing, but satisfy the shell syntax)
else
	echo "#########################################################"
	echo "#       $SOUP4 Not found in feed                        #"
	echo "#########################################################"
	exit 1
fi

if grep -q "$DIFFLIB" "$STATUS"; then
	: # Null command (do nothing, but satisfy the shell syntax)
else
	echo "#########################################################"
	echo "#       $DIFFLIB Not found in feed                      #"
	echo "#########################################################"
	exit 1
fi

if grep -q "$THREADING" "$STATUS"; then
	: # Null command (do nothing, but satisfy the shell syntax)
else
	echo "#########################################################"
	echo "#       $THREADING Not found in feed                    #"
	echo "#########################################################"
	exit 1
fi

if grep -q "$PLI" "$STATUS"; then
	: # Null command (do nothing, but satisfy the shell syntax)
else
	echo "#########################################################"
	echo "#       $PLI Not found in feed                          #"
	echo "#########################################################"
	exit 1
fi

if grep -q "$REQUESTES" "$STATUS"; then
	: # Null command (do nothing, but satisfy the shell syntax)
else
	echo "#########################################################"
	echo "#       $REQUESTES Not found in feed                    #"
	echo "#########################################################"
	exit 1
fi

echo " ** Download and install FootOnsat ** "
echo ""
cd /tmp
set -e
rm -rf *main* >/dev/null 2>&1
rm -rf *FootOnsat* >/dev/null 2>&1
wget -q "https://github.com/fairbird/FootOnsat/archive/refs/heads/main.tar.gz"
if [ -f "/tmp/main.tar.gz" ]; then
	echo "remove old version"
	echo ""
	rm -rf $PLUGIN_PATH >/dev/null 2>&1
	echo "Send new version"
	echo ""
	tar -xzf main.tar.gz
	cp -r FootOnsat-main/usr / >/dev/null 2>&1
fi
if [ -d $PLUGIN_PATH ]; then
	if [ -f "$TMP_DB" ]; then
		echo ""
		echo "Restore old db ..."
		cp -a "$TMP_DB" "$DB_FILE" >/dev/null 2>&1
	fi
	echo ""
	echo "Restore current style is: $CURRENT_VALUE"
	echo ""
	FILE_NAME=""
	case "$CURRENT_VALUE" in
	    "icons_renkli")
		  FILE_NAME="icons_renkli.tar.gz"
		  ;;
	    "icons_buwalla")
		  FILE_NAME="icons_buwalla.tar.gz"
		  ;;
	    "icons_italia2012")
		  FILE_NAME="icons_italia2012.tar.gz"
		  ;;
	    *)
		  FILE_NAME="icons_default.tar.gz"
		  ;;
	esac
	if [ -n "$FILE_NAME" ]; then
	    cd /tmp/FootOnsat-main/Download/Style-Icons-Files
	    tar -xzf "${FILE_NAME}" >/dev/null 2>&1
	    cp -r assets "$PLUGIN_PATH" >/dev/null 2>&1
	fi
fi

echo "clean tmp ..."
cd /tmp
rm -rf *FootOnsat* >/dev/null 2>&1
rm -rf *footonsat* >/dev/null 2>&1
rm -rf *main* >/dev/null 2>&1
#rm -rf *assets* >/dev/null 2>&1
#rm -rf *ui* >/dev/null 2>&1
rm -rf *TMP_DB* >/dev/null 2>&1
cd ..
echo
echo
echo ""
echo "#########################################################"
echo "#          FootOnsat INSTALLED SUCCESSFULLY             #"
echo "#        BY ZIKO & Redouane & Raed (fairbird)           #"
echo "#########################################################"
echo "#                Restart Enigma2 GUI                    #"
echo "#########################################################"
sleep 2
killall -9 enigma2
exit 0
