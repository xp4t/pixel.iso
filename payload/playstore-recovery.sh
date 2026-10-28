#!/system/bin/sh
# Recover the bundled Play Store's observed search-results cache crash once per
# boot. Watch new crash entries only; leave accounts, preferences and apps intact.
while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 3; done
logcat -b crash -T 1 -v brief | while IFS= read -r line; do
    case "$line" in
        *java.lang.ClassCastException:*com.google.android.finsky.stream.base.view.GridClusterPaddingView*)
            echo 'Repairing Play Store cache after search-results crash.' >>/data/adb/pixeliso-playstore-recovery.log
            am force-stop com.android.vending
            rm -rf /data/user/0/com.android.vending/cache/* /data/user/0/com.android.vending/code_cache/*
            am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p com.android.vending >>/data/adb/pixeliso-playstore-recovery.log 2>&1
            break
            ;;
    esac
done
