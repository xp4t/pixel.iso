# Sourced by the Android-x86 initrd after the Android root and /system exist.
# Kept inside initrd.img so the stock installer carries the integration over.
pixeliso_mount_live_data()
{
    # Magisk deliberately skips module startup when /data itself is tmpfs.
    # A sparse, RAM-backed ext2 loop filesystem makes Live mode work as well.
    # This is volatile and never formats an attached VM disk.
    image=/android/magisk/live-data.img
    /pixeliso/busybox truncate -s 3G "$image" &&
        /pixeliso/busybox mke2fs -F -m 0 -I 256 "$image" &&
        mount -o loop,noatime "$image" data
}

if [ -z "$INSTALL" ]; then
    cp -a /pixeliso /android/magisk
    chmod 0755 /android/magisk /android/magisk/*.sh /android/magisk/busybox
    echo 'import /magisk/pixeliso.rc' >> /android/init.rc
    policy=/android/sepolicy
    if [ -f "$policy" ]; then
        /pixeliso/magiskpolicy --load "$policy" --save "$policy.pixeliso" --magisk &&
            mv "$policy.pixeliso" "$policy"
    fi
fi
