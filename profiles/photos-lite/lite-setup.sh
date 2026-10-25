#!/system/bin/sh
export PATH=/sbin:/system/bin:/system/xbin:/vendor/bin
[ -f /data/adb/.pixeliso-lite-setup-v1 ] && exit 0
while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 2; done
exec >>/data/adb/pixeliso-lite-setup.log 2>&1
settings put global window_animation_scale 0
settings put global transition_animation_scale 0
settings put global animator_duration_scale 0
settings put global activity_manager_constants max_cached_processes=6
settings put global wifi_scan_always_enabled 0
settings put global ble_scan_always_enabled 0
settings put global device_provisioned 1
settings put secure user_setup_complete 1
settings put system screen_off_timeout 600000
touch /data/adb/.pixeliso-lite-setup-v1
echo 'Photos Lite setup complete.'
