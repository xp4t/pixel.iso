#!/system/bin/sh
# The kernel's virt_wifi driver exposes the VM's Ethernet/NAT link as VirtWifi.
# Run only for the fresh VM profile we seeded. Respect later user Wi-Fi choices.
[ -f /data/adb/.pixeliso-virtwifi-default ] || exit 0
[ -f /data/adb/.pixeliso-virtwifi-enabled-v1 ] && exit 0
[ -d /sys/module/virt_wifi ] || exit 0
export PATH=/sbin:/system/bin:/system/xbin:/vendor/bin
exec >>/data/adb/pixeliso-network.log 2>&1
while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 2; done
attempt=0
while [ "$attempt" -lt 60 ]; do
    attempt=$((attempt + 1))
    # Going through Android's Wi-Fi service keeps DHCP, DNS, routing and network
    # validation under ConnectivityService, including for ordinary applications.
    /system/bin/svc wifi enable
    sleep 2
    if ip -4 addr show wlan0 | grep -q 'inet '; then
        echo 'VirtWifi connected with a DHCP IPv4 address.'
        ip -4 addr show wlan0
        touch /data/adb/.pixeliso-virtwifi-enabled-v1
        exit 0
    fi
done
echo 'VirtWifi did not obtain an IPv4 address; check the VM NAT adapter and host connection.'
exit 1
