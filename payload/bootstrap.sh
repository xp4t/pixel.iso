#!/magisk/busybox sh
export ASH_STANDALONE=1
export PATH=/sbin:/system/bin:/system/xbin:/vendor/bin
mkdir -p /data/adb
chmod 0700 /data/adb
exec >>/data/adb/pixeliso-bootstrap.log 2>&1
set -x

mount -t tmpfs -o mode=0755 tmpfs /sbin
for binary in magisk32 magisk64 magiskinit magiskpolicy busybox; do
    cp /magisk/$binary /sbin/$binary
    chmod 0755 /sbin/$binary
done
ln -sf magisk64 /sbin/magisk
ln -sf magisk /sbin/su
ln -sf magisk /sbin/resetprop
ln -sf magiskpolicy /sbin/supolicy
mkdir -p /sbin/.magisk/mirror /sbin/.magisk/block
touch /sbin/.magisk/config

mkdir -p /data/adb/magisk /data/adb/modules /data/adb/service.d /data/adb/post-fs-data.d
cp /sbin/magisk32 /sbin/magisk64 /sbin/magiskinit /sbin/magiskpolicy /sbin/busybox /data/adb/magisk/
cp /magisk/magiskboot /data/adb/magisk/
cp -a /magisk/assets/. /data/adb/magisk/
cp /magisk/magisk.apk /data/adb/magisk.apk
chmod 0755 /data/adb/magisk/*
if [ -f /magisk/lite-setup.sh ]; then
    cp /magisk/lite-setup.sh /data/adb/service.d/pixeliso-lite-setup.sh
    chmod 0755 /data/adb/service.d/pixeliso-lite-setup.sh
fi

# Seed the VM-only open network before WifiService loads its configuration.
# Existing saved networks and physical Wi-Fi adapters are never overwritten.
if [ -d /sys/module/virt_wifi ] && [ ! -e /data/misc/wifi/WifiConfigStore.xml ]; then
    mkdir -p /data/misc/wifi
    cp /magisk/virtwifi-config.xml /data/misc/wifi/WifiConfigStore.xml
    chown 1000:1000 /data/misc/wifi/WifiConfigStore.xml
    chmod 0600 /data/misc/wifi/WifiConfigStore.xml
    restorecon /data/misc/wifi/WifiConfigStore.xml
    touch /data/adb/.pixeliso-virtwifi-default
fi
if [ -f /data/adb/.pixeliso-virtwifi-default ]; then
    cp /magisk/connect-virtwifi.sh /data/adb/service.d/pixeliso-network.sh
    chmod 0755 /data/adb/service.d/pixeliso-network.sh
fi

# Seed only once. Subsequent boots respect user disable/remove operations.
if [ ! -f /data/adb/.pixeliso-seeded-v1 ]; then
    cp -a /magisk/modules/. /data/adb/modules/
    chown -R 0:0 /data/adb/modules
    find /data/adb/modules -type d -exec chmod 0755 {} \;
    find /data/adb/modules -type f -exec chmod 0644 {} \;
    if [ -f /data/adb/modules/zygisk_lsposed/daemon ]; then
        chmod 0744 /data/adb/modules/zygisk_lsposed/daemon
    fi
    cp /magisk/install-managers.sh /data/adb/service.d/pixeliso-managers.sh
    chmod 0755 /data/adb/service.d/pixeliso-managers.sh
    /sbin/magisk --daemon
    zygisk=1
    [ -f /magisk/lite-setup.sh ] && zygisk=0
    /sbin/magisk --sqlite "INSERT OR REPLACE INTO settings (key,value) VALUES ('zygisk',$zygisk);"
    touch /data/adb/.pixeliso-seeded-v1
fi

restorecon -R /data/adb
for module in /data/adb/modules/*; do
    [ -f "$module/disable" ] && continue
    [ -f "$module/sepolicy.rule" ] && /sbin/magiskpolicy --live --apply "$module/sepolicy.rule"
done
/sbin/magisk --daemon
