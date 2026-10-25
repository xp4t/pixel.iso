#!/system/bin/sh
[ -f /data/adb/.pixeliso-managers-installed-v1 ] && exit 0
while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 3; done
mkdir -p /data/local/tmp
exec >>/data/adb/pixeliso-managers.log 2>&1
# Always install the bundled full manager on the first run. Magisk may already
# have installed its tiny downloader stub while handling boot completion.
cp /magisk/magisk.apk /data/local/tmp/pixeliso-magisk.apk
chmod 0644 /data/local/tmp/pixeliso-magisk.apk
until pm install -r /data/local/tmp/pixeliso-magisk.apk; do sleep 10; done
rm -f /data/local/tmp/pixeliso-magisk.apk
if [ -f /data/adb/modules/zygisk_lsposed/manager.apk ]; then
    cp /data/adb/modules/zygisk_lsposed/manager.apk /data/local/tmp/pixeliso-lsposed.apk
    chmod 0644 /data/local/tmp/pixeliso-lsposed.apk
    until pm install -r /data/local/tmp/pixeliso-lsposed.apk; do sleep 10; done
    rm -f /data/local/tmp/pixeliso-lsposed.apk
fi
touch /data/adb/.pixeliso-managers-installed-v1
