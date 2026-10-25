#!/magisk/busybox sh
export PATH=/sbin:/system/bin:/system/xbin:/vendor/bin
sleep 15
{
    echo 'PIXELISO: boot completed'
    echo "Android=$(getprop ro.build.version.release) SDK=$(getprop ro.build.version.sdk)"
    echo "Model=$(getprop ro.product.model) Device=$(getprop ro.product.device) ABI=$(getprop ro.product.cpu.abi)"
    echo "Magisk=$(magisk -v)"
    su -c id
    magisk --sqlite "SELECT key,value FROM settings WHERE key='zygisk';"
    ps -A | grep -E 'lspd|zygote'
    echo 'Modules:'
    cat /data/adb/modules/*/module.prop
} > /data/adb/pixeliso-status.txt 2>&1
if grep -q 'PIXELISO_TEST=1' /proc/cmdline; then
    cat /data/adb/pixeliso-status.txt > /dev/ttyS0
    cat /data/adb/pixeliso-bootstrap.log > /dev/ttyS0
fi
