# OpenWrt Build Guide — GL.iNet GL-MT6000 (Flint 2)

## Environment

- **Device**: GL.iNet GL-MT6000 (Flint 2)
- **SoC**: MediaTek MT7986A (Filogic 830)
- **Target**: `mediatek/filogic`
- **Architecture**: `aarch64_cortex-a53`
- **Branch**: `openwrt-25.12`
- **Package manager**: APK (default in OpenWrt 25.x, replaces opkg)

## Prerequisites

```bash
sudo apt-get install -y build-essential clang flex bison g++ gawk \
  gcc-multilib g++-multilib gettext git libncurses-dev libssl-dev \
  python3-distutils python3-setuptools rsync swig unzip zlib1g-dev \
  file wget
```

## Build Steps

### 1. Update and install feeds

```bash
./scripts/feeds update -a
./scripts/feeds install -a
```

### 2. Configure for GL-MT6000

Create `.config` with the minimal device selection plus required packages:

```bash
cat > .config << 'EOF'
CONFIG_TARGET_mediatek=y
CONFIG_TARGET_mediatek_filogic=y
CONFIG_TARGET_mediatek_filogic_DEVICE_glinet_gl-mt6000=y

# Package manager
CONFIG_PACKAGE_opkg=y

# Web UI (LuCI)
CONFIG_PACKAGE_luci=y
CONFIG_PACKAGE_luci-base=y
CONFIG_PACKAGE_uhttpd=y
CONFIG_PACKAGE_uhttpd-mod-ubus=y
CONFIG_PACKAGE_rpcd-mod-luci=y
CONFIG_PACKAGE_liblucihttp=y
CONFIG_PACKAGE_liblucihttp-ucode=y

# Version & package feed URL (required for apk/opkg to work after flash)
CONFIG_IMAGEOPT=y
CONFIG_VERSIONOPT=y
CONFIG_VERSION_NUMBER="25.12.2"
CONFIG_VERSION_REPO="https://downloads.openwrt.org/releases/25.12.2"
EOF

make defconfig
```

> `CONFIG_IMAGEOPT` and `CONFIG_VERSIONOPT` must both be set, otherwise
> `VERSION_REPO` is ignored and the device won't know where to download packages.

### 3. Compile

```bash
make -j$(nproc) 2>&1 | tee build.log
```

Output firmware:
```
bin/targets/mediatek/filogic/
  openwrt-25.12.2-*-glinet_gl-mt6000-squashfs-sysupgrade.bin   ← flash this
  openwrt-25.12.2-*-glinet_gl-mt6000-squashfs-factory.bin
```

## Incremental Builds

After the first full build, only rebuild what changed:

| Change | Command |
|--------|---------|
| Single package | `make package/<name>/compile -j$(nproc)` |
| Force rebuild a package | `make package/<name>/{clean,compile} -j$(nproc)` |
| Kernel / DTS only | `make target/linux/compile -j$(nproc)` |
| Regenerate firmware image | `make target/install -j$(nproc)` |
| Everything (incremental) | `make -j$(nproc)` |

## Flashing

### Transfer firmware to device

```bash
scp bin/targets/mediatek/filogic/openwrt-25.12.2-*-glinet_gl-mt6000-squashfs-sysupgrade.bin \
    root@192.168.1.1:/tmp/
```

### Flash on device (preserves config)

```bash
sysupgrade -v /tmp/openwrt-25.12.2-*-glinet_gl-mt6000-squashfs-sysupgrade.bin
```

> Add `-n` to wipe all settings (clean install). Omit `-n` to keep `/etc/config/`.

## Package Management on Device

OpenWrt 25.x uses **APK** by default:

```bash
apk update
apk add iperf3
apk add curl
```

opkg is also installed and usable for compatibility:

```bash
opkg update
opkg install <package>
```

## Troubleshooting

**Web UI not accessible after flash**
- Confirm `uhttpd` is running: `ps | grep uhttpd`
- Try a different browser (cache issues)
- Default address: `http://192.168.1.1`

**`apk update` / `opkg update` finds no packages**
- Check `/etc/apk/repositories` or `/etc/opkg/distfeeds.conf` exists
- If missing, `CONFIG_IMAGEOPT`, `CONFIG_VERSIONOPT`, and `CONFIG_VERSION_REPO` were not set at build time — rebuild with those options

**Build fails with missing dependency**
- Check `build.log` for the error: `tail -50 build.log`
- Common: `sudo apt-get install -y swig`
