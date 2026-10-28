#!/system/bin/sh
# Setup can download Data Transfer Tool as a regular app, without the privileged
# settings permission its migration activity expects. Wait for that install.
while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 3; done
exec >>/data/adb/pixeliso-setup-permissions.log 2>&1
attempt=0
while [ "$attempt" -lt 180 ]; do
    if pm path com.google.android.apps.pixelmigrate >/dev/null 2>&1; then
        pm grant com.google.android.apps.pixelmigrate android.permission.WRITE_SECURE_SETTINGS && exit 0
    fi
    attempt=$((attempt + 1))
    sleep 5
done
