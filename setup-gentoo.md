# 結論

OpenRC版の完全統合環境に修正します。systemd関連をすべてOpenRCサービス管理に置き換え、Gentoo本来のinit systemで動作する構成を提供します。

---

## Phase 1: Gentoo Base System Installation (OpenRC版)

### 1.1 パーティション & Btrfs構築

```bash
# === ライブUSBから実行 ===

# パーティション作成 (NVMe SSD想定)
parted -a optimal /dev/nvme0n1
  mklabel gpt
  mkpart primary fat32 1MiB 513MiB
  set 1 esp on
  mkpart primary linux-swap 513MiB 17GiB
  mkpart primary btrfs 17GiB 100%
  quit

# ファイルシステム作成
mkfs.vfat -F32 -n EFI /dev/nvme0n1p1
mkswap -L SWAP /dev/nvme0n1p2
mkfs.btrfs -L GENTOO -f /dev/nvme0n1p3

# Btrfsサブボリューム構築
mount /dev/nvme0n1p3 /mnt/gentoo

btrfs subvolume create /mnt/gentoo/@
btrfs subvolume create /mnt/gentoo/@home
btrfs subvolume create /mnt/gentoo/@snapshots
btrfs subvolume create /mnt/gentoo/@var_log
btrfs subvolume create /mnt/gentoo/@var_cache
btrfs subvolume create /mnt/gentoo/@var_tmp
btrfs subvolume create /mnt/gentoo/@portage
btrfs subvolume create /mnt/gentoo/@distfiles
btrfs subvolume create /mnt/gentoo/@ccache
btrfs subvolume create /mnt/gentoo/@containers

umount /mnt/gentoo

# 最適化マウント
BTRFS_OPTS="noatime,compress=zstd:1,space_cache=v2,ssd,discard=async"

mount -o ${BTRFS_OPTS},subvol=@ /dev/nvme0n1p3 /mnt/gentoo

mkdir -p /mnt/gentoo/{home,.snapshots,var/{log,cache,tmp,db/repos/gentoo,cache/{distfiles,ccache}},boot,.local/share/containers}

mount -o ${BTRFS_OPTS},subvol=@home /dev/nvme0n1p3 /mnt/gentoo/home
mount -o ${BTRFS_OPTS},subvol=@snapshots /dev/nvme0n1p3 /mnt/gentoo/.snapshots
mount -o ${BTRFS_OPTS},subvol=@var_log /dev/nvme0n1p3 /mnt/gentoo/var/log
mount -o ${BTRFS_OPTS},subvol=@var_cache /dev/nvme0n1p3 /mnt/gentoo/var/cache
mount -o ${BTRFS_OPTS},subvol=@var_tmp /dev/nvme0n1p3 /mnt/gentoo/var/tmp
mount -o ${BTRFS_OPTS},subvol=@portage /dev/nvme0n1p3 /mnt/gentoo/var/db/repos/gentoo
mount -o ${BTRFS_OPTS},subvol=@distfiles /dev/nvme0n1p3 /mnt/gentoo/var/cache/distfiles
mount -o ${BTRFS_OPTS},subvol=@ccache /dev/nvme0n1p3 /mnt/gentoo/var/cache/ccache
mount -o ${BTRFS_OPTS},subvol=@containers /dev/nvme0n1p3 /mnt/gentoo/.local/share/containers

mount /dev/nvme0n1p1 /mnt/gentoo/boot
swapon /dev/nvme0n1p2
```

### 1.2 Stage3展開 & Chroot (OpenRC版)

```bash
cd /mnt/gentoo

# OpenRC Stage3ダウンロード (最新版URL確認: https://www.gentoo.org/downloads/)
wget https://distfiles.gentoo.org/releases/amd64/autobuilds/latest-stage3-amd64-desktop-openrc.tar.xz

tar xpvf stage3-*.tar.xz --xattrs-include='*.*' --numeric-owner

# make.conf設定
nano /mnt/gentoo/etc/portage/make.conf
```

### 1.3 最終版 make.conf (OpenRC対応)

```bash
# /mnt/gentoo/etc/portage/make.conf

# ===== Compiler Optimization =====
COMMON_FLAGS="-march=znver2 -mtune=znver2 -O2 -pipe"
CFLAGS="${COMMON_FLAGS}"
CXXFLAGS="${COMMON_FLAGS}"
FCFLAGS="${COMMON_FLAGS}"
FFLAGS="${COMMON_FLAGS}"
LDFLAGS="-Wl,-O2 -Wl,--as-needed -Wl,--hash-style=gnu"

# ===== CPU & Build Parallelism =====
MAKEOPTS="-j24 -l24"
EMERGE_DEFAULT_OPTS="--jobs=4 --load-average=20 --keep-going --verbose"

# ===== Portage Features =====
FEATURES="parallel-fetch parallel-install split-log split-elog candy ccache"
CCACHE_SIZE="20G"

# ===== USE Flags - 完全Qt6環境 + OpenRC =====
USE="qt6 qt5 kde plasma wayland X \
     -gtk -gtk2 -gtk3 -gtk4 -gnome \
     vulkan opengl opencl vaapi vdpau \
     pulseaudio pipewire alsa jack \
     networkmanager bluetooth wifi \
     elogind dbus udev \
     btrfs zstd lzo lz4 \
     jpeg png svg webp pdf \
     encode mp3 flac opus aac vorbis \
     threads lto pgo graphite \
     distcc ccache \
     -systemd -doc -examples -test"

# ===== Hardware Specific =====
VIDEO_CARDS="amdgpu radeonsi"
LLVM_TARGETS="AMDGPU X86"
INPUT_DEVICES="libinput"
CPU_FLAGS_X86="aes avx avx2 f16c fma3 mmx mmxext pclmul popcnt rdrand sha sse sse2 sse3 sse4_1 sse4_2 sse4a ssse3"

# ===== Qt Settings =====
QT_QPA_PLATFORMTHEME="kde"

# ===== Language & Localization =====
L10N="ja en"
LINGUAS="ja en"
LC_MESSAGES=C.utf8

# ===== Accept =====
ACCEPT_KEYWORDS="~amd64"
ACCEPT_LICENSE="*"

# ===== Mirrors (Japan) =====
GENTOO_MIRRORS="https://ftp.jaist.ac.jp/pub/Linux/Gentoo/ \
                https://ftp.riken.jp/Linux/gentoo/ \
                https://ftp.iij.ad.jp/pub/linux/gentoo/"

# ===== Directories =====
PORTDIR="/var/db/repos/gentoo"
DISTDIR="/var/cache/distfiles"
PKGDIR="/var/cache/binpkgs"
CCACHE_DIR="/var/cache/ccache"

# ===== Portage Log =====
PORTAGE_LOGDIR="/var/log/portage"
PORTAGE_ELOG_CLASSES="warn error log"
PORTAGE_ELOG_SYSTEM="save"

# ===== Misc =====
GRUB_PLATFORMS="efi-64"
```

### 1.4 Chroot & 基本設定 (OpenRC)

```bash
cp --dereference /etc/resolv.conf /mnt/gentoo/etc/

mount --types proc /proc /mnt/gentoo/proc
mount --rbind /sys /mnt/gentoo/sys
mount --make-rslave /mnt/gentoo/sys
mount --rbind /dev /mnt/gentoo/dev
mount --make-rslave /mnt/gentoo/dev
mount --bind /run /mnt/gentoo/run
mount --make-slave /mnt/gentoo/run

chroot /mnt/gentoo /bin/bash
source /etc/profile
export PS1="(chroot) ${PS1}"

# Portage同期
emerge-webrsync
emerge --sync

# プロファイル選択 (OpenRC版)
eselect profile list
eselect profile set default/linux/amd64/23.0/desktop/plasma

# タイムゾーン
echo "Asia/Tokyo" > /etc/timezone
emerge --config sys-libs/timezone-data

# ロケール
nano /etc/locale.gen
# 以下をアンコメント:
# en_US.UTF-8 UTF-8
# ja_JP.UTF-8 UTF-8

locale-gen
eselect locale set ja_JP.utf8
env-update && source /etc/profile
```

---

## Phase 2: Kernel Configuration & Build

### 2.1 カーネルソースインストール

```bash
emerge --ask sys-kernel/gentoo-sources sys-kernel/linux-firmware

eselect kernel list
eselect kernel set 1

ls -l /usr/src/linux
```

### 2.2 カーネル設定 (OpenRC必須項目含む)

```bash
cd /usr/src/linux
make defconfig
make menuconfig
```

**OpenRC必須設定:**

```
General setup --->
  [*] Initial RAM filesystem and RAM disk support
  [ ] Support for systemd (無効化)
  [*] System V IPC
  [*] POSIX Message Queues
  [*] Control Group support --->
    [*] Memory controller
    [*] CPU controller
  [*] Namespaces support --->
    [*] UTS namespace
    [*] IPC namespace
    [*] User namespace
    [*] PID namespace
    [*] Network namespace

Processor type and features --->
  [*] Symmetric multi-processing support
  [*] AMD microcode loading support
  Processor family (Zen 2) --->

Device Drivers --->
  Graphics support --->
    [*] AMD GPU
    <M> AMD Radeon
    [*] Enable amdgpu support for SI parts
    [*] Enable amdgpu support for CIK parts
    Display Engine Configuration --->
      [*] AMD DC - Enable new display engine
      [*] DCN 2.0 family
  Generic Driver Options --->
    [*] Maintain a devtmpfs filesystem to mount at /dev
    [*] Automount devtmpfs at /dev
  Sound card support --->
    <*> Advanced Linux Sound Architecture --->
      [*] PCI sound devices --->
        <M> Intel HD Audio

File systems --->
  <*> Btrfs filesystem
  [*] Btrfs POSIX Access Control Lists
  <*> FUSE (Filesystem in Userspace) support
  [*] Overlay filesystem support
  DOS/FAT/NT Filesystems --->
    <M> VFAT (Windows-95) fs support
  Pseudo filesystems --->
    [*] Tmpfs POSIX Access Control Lists
    [*] Tmpfs extended attributes

Networking support --->
  Networking options --->
    [*] Network packet filtering framework (Netfilter)
```

### 2.3 カーネルビルド & インストール

```bash
make -j24
make modules_install
make install

# Initramfs生成
emerge --ask sys-kernel/dracut
dracut --force --hostonly
```

---

## Phase 3: System Configuration (OpenRC)

### 3.1 fstab設定

```bash
blkid

nano /etc/fstab
```

```bash
# /etc/fstab

# Btrfs subvolumes
UUID=<nvme0n1p3-uuid>  /                          btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@            0 0
UUID=<nvme0n1p3-uuid>  /home                      btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@home        0 0
UUID=<nvme0n1p3-uuid>  /.snapshots                btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@snapshots   0 0
UUID=<nvme0n1p3-uuid>  /var/log                   btrfs  noatime,space_cache=v2,ssd,discard=async,subvol=@var_log                     0 0
UUID=<nvme0n1p3-uuid>  /var/cache                 btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@var_cache   0 0
UUID=<nvme0n1p3-uuid>  /var/tmp                   btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@var_tmp     0 0
UUID=<nvme0n1p3-uuid>  /var/db/repos/gentoo       btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@portage     0 0
UUID=<nvme0n1p3-uuid>  /var/cache/distfiles       btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@distfiles   0 0
UUID=<nvme0n1p3-uuid>  /var/cache/ccache          btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@ccache      0 0
UUID=<nvme0n1p3-uuid>  /.local/share/containers   btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@containers  0 0

# EFI
UUID=<nvme0n1p1-uuid>  /boot  vfat  defaults,noatime  0 2

# Swap
UUID=<nvme0n1p2-uuid>  none   swap  sw               0 0
```

### 3.2 ネットワーク & ホスト名 (OpenRC)

```bash
echo "gentoo-omni" > /etc/hostname

nano /etc/hosts
```

```
127.0.0.1     localhost
::1           localhost
127.0.1.1     gentoo-omni.localdomain gentoo-omni
```

```bash
# NetworkManager (OpenRC)
emerge --ask net-misc/networkmanager

# OpenRCサービス登録
rc-update add NetworkManager default

# elogind (セッション管理)
emerge --ask sys-auth/elogind
rc-update add elogind boot
```

### 3.3 ブートローダー (GRUB)

```bash
emerge --ask sys-boot/grub

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GENTOO
grub-mkconfig -o /boot/grub/grub.cfg
```

### 3.4 ユーザー作成

```bash
useradd -m -G wheel,audio,video,usb,portage -s /bin/bash osamu
passwd osamu
passwd root

# sudo有効化
emerge --ask app-admin/sudo
EDITOR=nano visudo
# %wheel ALL=(ALL:ALL) ALL をアンコメント
```

---

## Phase 4: KDE Plasma Installation (OpenRC)

```bash
# KDE Plasma (OpenRC版)
emerge --ask kde-plasma/plasma-meta

# 必須アプリ
emerge --ask \
  kde-apps/konsole \
  kde-apps/dolphin \
  kde-apps/kate \
  kde-apps/spectacle \
  kde-apps/gwenview \
  kde-apps/okular

# ディスプレイマネージャー (SDDM - OpenRC)
emerge --ask x11-misc/sddm

# OpenRCサービス登録
rc-update add dbus default
rc-update add sddm default

# オーディオ (PipeWire + OpenRC)
emerge --ask \
  media-video/pipewire \
  media-video/wireplumber

# Gentoo OpenRC用PipeWireセッション設定
mkdir -p /etc/pipewire/pipewire.conf.d
```

**`/etc/pipewire/pipewire.conf.d/10-openrc.conf`:**

```conf
context.exec = [
    { path = "wireplumber" args = "" }
]
```

```bash
# 日本語入力
emerge --ask \
  app-i18n/fcitx5 \
  app-i18n/fcitx5-mozc \
  app-i18n/fcitx5-configtool

# フォント
emerge --ask \
  media-fonts/noto \
  media-fonts/noto-cjk \
  media-fonts/noto-emoji
```

### 4.1 OpenRC init設定

```bash
# デフォルトランレベル確認
rc-status

# 有効サービス確認
rc-update show
```

**重要なOpenRCサービス:**
```bash
rc-update add dbus default
rc-update add elogind boot
rc-update add NetworkManager default
rc-update add sddm default
```

### 4.2 再起動

```bash
exit
cd
umount -l /mnt/gentoo/dev{/shm,/pts,}
umount -R /mnt/gentoo
reboot
```

---

## Phase 5: Distrobox & Development Environment (OpenRC)

### 5.1 Distrobox インストール

```bash
# Gentoo起動後、ユーザーでログイン

# Podman & Distrobox
sudo emerge --ask \
  app-containers/podman \
  app-containers/distrobox

# cgroup v2設定 (OpenRC)
sudo nano /etc/rc.conf
```

**`/etc/rc.conf` に追加:**

```bash
# cgroup v2 for Podman
rc_cgroup_mode="unified"
```

```bash
# ユーザーネームスペース設定
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER

# 再ログイン
exit
# 再度ログイン
```

### 5.2 開発用Distrobox作成

```bash
# arch-dev: メイン開発環境
distrobox create --name arch-dev \
  --image archlinux:latest \
  --home /home/osamu \
  --volume /usr/src:/usr/src:ro \
  --additional-flags "--cpus 12 --memory 16g"

# kernel-build: カーネルビルド専用
distrobox create --name kernel-build \
  --image archlinux:latest \
  --volume /usr/src:/usr/src:rw \
  --volume /lib/modules:/lib/modules:rw \
  --additional-flags "--privileged --cpus 24"
```

### 5.3 arch-dev 環境構築

```bash
distrobox enter arch-dev

# 基本パッケージ
sudo pacman -Syu
sudo pacman -S --noconfirm \
  base-devel git curl wget \
  zed \
  rust rust-analyzer \
  python python-pip \
  nodejs npm \
  clang llvm \
  cmake ninja \
  gdb valgrind \
  tree ripgrep fd bat \
  tmux zsh

# ESP-IDF (Omni-P4開発用)
mkdir -p ~/esp
cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32,esp32s3,esp32p4

# ESP-IDF自動ロード
echo '. $HOME/esp/esp-idf/export.sh' >> ~/.bashrc
```

### 5.4 kernel-build 環境構築

```bash
distrobox enter kernel-build

sudo pacman -Syu
sudo pacman -S --noconfirm \
  qt6-base qt6-tools \
  base-devel bc cpio flex bison \
  libelf pahole perl python \
  rsync tar xz zstd
```

---

## Phase 6: OpenRC自動メンテナンス設定

### 6.1 Btrfs Scrub サービス (OpenRC)

**`/etc/init.d/btrfs-scrub`:**

```bash
#!/sbin/openrc-run

description="Btrfs filesystem scrub"

depend() {
    need localmount
    after *
}

start() {
    ebegin "Starting btrfs scrub on /"
    /usr/bin/btrfs scrub start -B /
    eend $?
}
```

```bash
sudo chmod +x /etc/init.d/btrfs-scrub
```

**月次実行 (cron):**

```bash
sudo crontab -e
```

```cron
# Btrfs scrub - 毎月1日 3:00AM
0 3 1 * * /etc/init.d/btrfs-scrub start
```

### 6.2 Snapper設定 (OpenRC)

```bash
sudo emerge --ask app-backup/snapper

# Snapper設定作成
sudo snapper -c root create-config /

# 設定編集
sudo nano /etc/snapper/configs/root
```

```ini
# Timeline設定
TIMELINE_CREATE="yes"
TIMELINE_CLEANUP="yes"
TIMELINE_MIN_AGE="1800"
TIMELINE_LIMIT_HOURLY="5"
TIMELINE_LIMIT_DAILY="7"
TIMELINE_LIMIT_WEEKLY="0"
TIMELINE_LIMIT_MONTHLY="0"
TIMELINE_LIMIT_YEARLY="0"
```

**Snapper タイマー (OpenRC cron):**

```bash
sudo crontab -e
```

```cron
# Snapper timeline - 毎時
0 * * * * /usr/bin/snapper -c root create --cleanup-algorithm timeline

# Snapper cleanup - 毎日 4:00AM
0 4 * * * /usr/bin/snapper -c root cleanup timeline
```

### 6.3 システム更新前スナップショット (OpenRC)

**`/etc/portage/bashrc`:**

```bash
post_pkg_preinst() {
    if [[ "${EBUILD_PHASE}" == "preinst" ]]; then
        /usr/bin/snapper -c root create --description "emerge: ${CATEGORY}/${PF}" --cleanup-algorithm number 2>/dev/null || true
    fi
}
```

---

## Phase 7: 統合管理スクリプト (OpenRC版)

### 7.1 統合管理スクリプト

**`~/bin/omni-sys-manager.sh`:**

```bash
#!/bin/bash
# Omni-P4 System Manager (OpenRC Edition)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_service() { echo -e "${BLUE}[SERVICE]${NC} $1"; }

# ===== OpenRC Service Management =====
service_status() {
    log_service "OpenRC Services Status:"
    echo ""
    rc-status --all
}

service_restart() {
    local service=$1
    log_service "Restarting $service..."
    sudo rc-service "$service" restart
}

# ===== Gentoo System =====
gentoo_update() {
    log_info "Updating Gentoo system..."
    
    # Pre-update snapshot
    sudo snapper -c root create --description "Pre-update: $(date +%Y%m%d)" --cleanup-algorithm number
    
    # Sync portage
    sudo emerge --sync
    
    # Update system
    sudo emerge --update --deep --newuse --with-bdeps=y @world
    
    # Cleanup
    sudo emerge --depclean
    sudo eclean-dist --deep
    
    log_info "Gentoo update completed"
}

gentoo_kernel_update() {
    log_info "Updating Gentoo kernel..."
    
    cd /usr/src/linux
    
    # Backup current config
    cp .config ~/kernel-config-backup-$(date +%Y%m%d).config
    
    # Update kernel
    sudo emerge --ask sys-kernel/gentoo-sources
    
    # Rebuild
    sudo make -j24
    sudo make modules_install
    sudo make install
    
    # Update initramfs
    sudo dracut --force --hostonly
    
    # Update GRUB
    sudo grub-mkconfig -o /boot/grub/grub.cfg
    
    log_info "Kernel update completed. Reboot required."
}

# ===== Distrobox Environments =====
distrobox_update_all() {
    log_info "Updating all Distrobox containers..."
    
    for container in arch-dev kernel-build; do
        if distrobox list | grep -q "$container"; then
            log_info "Updating $container..."
            distrobox enter "$container" -- sudo pacman -Syu --noconfirm
        fi
    done
    
    log_info "All containers updated"
}

# ===== Btrfs Management =====
btrfs_status() {
    log_info "Btrfs filesystem status:"
    echo ""
    
    echo "=== Filesystem Usage ==="
    sudo btrfs filesystem usage /
    echo ""
    
    echo "=== Compression Ratio ==="
    sudo compsize / 2>/dev/null || log_warn "Install sys-fs/compsize for compression stats"
    echo ""
    
    echo "=== Recent Snapshots ==="
    sudo snapper -c root list | tail -10
}

btrfs_cleanup() {
    log_info "Running Btrfs maintenance..."
    
    # Snapshot cleanup
    sudo snapper -c root cleanup number
    
    # Balance (monthly)
    if [ "$(date +%d)" = "01" ]; then
        log_info "Running monthly balance..."
        sudo btrfs balance start -dusage=50 -musage=50 /
    fi
    
    log_info "Btrfs cleanup completed"
}

btrfs_scrub() {
    log_info "Starting Btrfs scrub (data integrity check)..."
    sudo /etc/init.d/btrfs-scrub start
}

# ===== OpenRC Specific =====
openrc_services_check() {
    log_service "Checking critical OpenRC services..."
    echo ""
    
    CRITICAL_SERVICES="dbus elogind NetworkManager sddm"
    
    for service in $CRITICAL_SERVICES; do
        if rc-service "$service" status &>/dev/null; then
            echo -e "${GREEN}✓${NC} $service is running"
        else
            echo -e "${RED}✗${NC} $service is NOT running"
        fi
    done
}

openrc_services_restart_all() {
    log_service "Restarting all critical services..."
    
    sudo rc-service dbus restart
    sudo rc-service elogind restart
    sudo rc-service NetworkManager restart
    
    log_service "Services restarted (SDDM excluded, manual restart recommended)"
}

# ===== Backup =====
backup_configs() {
    log_info "Backing up configuration files..."
    
    BACKUP_DIR=~/backups/configs-$(date +%Y%m%d)
    mkdir -p "$BACKUP_DIR"
    
    # Zed configs
    cp -r ~/.config/zed "$BACKUP_DIR/" 2>/dev/null || true
    
    # Kernel config
    [ -f /usr/src/linux/.config ] && cp /usr/src/linux/.config "$BACKUP_DIR/kernel.config"
    
    # make.conf
    sudo cp /etc/portage/make.conf "$BACKUP_DIR/"
    
    # OpenRC runlevels
    rc-update show > "$BACKUP_DIR/rc-update.txt"
    
    # Package lists
    qlist -I > "$BACKUP_DIR/installed-packages.txt"
    
    log_info "Backup saved to $BACKUP_DIR"
}

# ===== Menu =====
show_menu() {
    clear
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║   Omni-P4 System Manager (OpenRC Edition)    ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    echo "  Gentoo System:"
    echo "    1) Update system packages"
    echo "    2) Update kernel"
    echo ""
    echo "  Distrobox:"
    echo "    3) Update all containers"
    echo ""
    echo "  Btrfs Management:"
    echo "    4) Show filesystem status"
    echo "    5) Run cleanup & maintenance"
    echo "    6) Run scrub (integrity check)"
    echo ""
    echo "  OpenRC Services:"
    echo "    7) Check critical services"
    echo "    8) Show all services status"
    echo "    9) Restart critical services"
    echo ""
    echo "  Backup:"
    echo "    b) Backup configurations"
    echo ""
    echo "  0) Exit"
    echo ""
    read -rp "Select option: " choice
    
    case $choice in
        1) gentoo_update ;;
        2) gentoo_kernel_update ;;
        3) distrobox_update_all ;;
        4) btrfs_status ;;
        5) btrfs_cleanup ;;
        6) btrfs_scrub ;;
        7) openrc_services_check ;;
        8) service_status ;;
        9) openrc_services_restart_all ;;
        b|B) backup_configs ;;
        0) exit 0 ;;
        *) log_error "Invalid option" ;;
    esac
    
    echo ""
    read -rp "Press Enter to continue..."
    show_menu
}

# Main
if [ $# -eq 0 ]; then
    show_menu
else
    case $1 in
        update) gentoo_update ;;
        kernel) gentoo_kernel_update ;;
        distrobox) distrobox_update_all ;;
        btrfs-status) btrfs_status ;;
        btrfs-cleanup) btrfs_cleanup ;;
        services) openrc_services_check ;;
        backup) backup_configs ;;
        *) log_error "Unknown command: $1" ;;
    esac
fi
```

```bash
mkdir -p ~/bin
chmod +x ~/bin/omni-sys-manager.sh
```

### 7.2 便利なエイリアス (OpenRC版)

**`~/.bashrc` に追加:**

```bash
# ===== Omni-P4 Development Aliases (OpenRC Edition) =====

# System management
alias omni-sys='~/bin/omni-sys-manager.sh'
alias omni-update='~/bin/omni-sys-manager.sh update'
alias omni-kernel='~/bin/omni-sys-manager.sh kernel'

# OpenRC service management
alias rc-stat='rc-status'
alias rc-check='~/bin/omni-sys-manager.sh services'
alias rc-restart='sudo rc-service'

# Distrobox shortcuts
alias dev='distrobox enter arch-dev'
alias kernel='distrobox enter kernel-build'

# Kernel development
alias kxconfig='xhost +local: && distrobox enter kernel-build -- bash -c "export DISPLAY=:0 && cd /usr/src/linux && make xconfig"'
alias kmenu='distrobox enter kernel-build -- bash -c "cd /usr/src/linux && make menuconfig"'
alias kbuild='distrobox enter kernel-build -- bash -c "cd /usr/src/linux && make -j24"'
alias kinstall='cd /usr/src/linux && sudo make modules_install && sudo make install && sudo dracut --force --hostonly && sudo grub-mkconfig -o /boot/grub/grub.cfg'

# ESP-IDF (Omni-P4)
alias esp-build='distrobox enter arch-dev -- bash -c ". ~/esp/esp-idf/export.sh && cd ~/projects/omni-p4/esp-idf && idf.py build"'
alias esp-flash='distrobox enter arch-dev -- bash -c ". ~/esp/esp-idf/export.sh && cd ~/projects/omni-p4/esp-idf && idf.py -p /dev/ttyUSB0 flash monitor"'
alias esp-menu='distrobox enter arch-dev -- bash -c ". ~/esp/esp-idf/export.sh && cd ~/projects/omni-p4/esp-idf && idf.py menuconfig"'

# Btrfs management
alias btrfs-stat='sudo btrfs filesystem usage /'
alias btrfs-compress='sudo compsize /'
alias btrfs-snap='sudo snapper -c root list'
alias btrfs-create-snap='sudo snapper -c root create --description "Manual: $(date +%Y%m%d_%H%M%S)"'

# Git shortcuts
alias gs='git status'
alias ga='git add'
alias gc='git commit -m'
alias gp='git push'
alias gl='git log --oneline --graph --decorate --all'

# Development
alias zed='distrobox enter arch-dev -- zed'
```

---

## Phase 8: Zed Editor統合 (変更なし)

Zedの設定は前回提案と同じです:
- `~/.config/zed/settings.json`
- `~/.config/zed/keymap.json`
- `~/.config/zed/tasks/omni-p4.json`

---

## Phase 9: OpenRC特有の運用Tips

### 9.1 サービス管理基本コマンド

```bash
# サービス状態確認
rc-status

# 特定サービス確認
rc-service NetworkManager status

# サービス再起動
sudo rc-service NetworkManager restart

# 起動時サービス登録
sudo rc-update add service-name default

# サービス削除
sudo rc-update del service-name default

# ランレベル確認
rc-update show
```

### 9.2 トラブルシューティング

**問題: NetworkManagerが起動しない**

```bash
# ログ確認
sudo rc-service NetworkManager status
tail -f /var/log/messages

# 手動起動
sudo rc-service NetworkManager start

# 依存関係確認
rc-service NetworkManager describe
```

**問題: SDDMが起動しない**

```bash
# elogind確認 (必須依存)
sudo rc-service elogind status
sudo rc-service elogind start

# SDDM再起動
sudo rc-service sddm restart

# ログ確認
journalctl -xe  # OpenRCでも使用可能
```

### 9.3 起動時間最適化

```bash
# 並列起動有効化
sudo nano /etc/rc.conf
```

```bash
# 並列起動
rc_parallel="YES"

# タイムアウト設定
rc_timeout_stopsec="30"
```

---

## まとめ: OpenRC版完全統合環境

### ✅ 達成した統合 (OpenRC版)

1. **Gentoo OpenRC Base**
   - systemd完全排除
   - elogindでセッション管理
   - 軽量で高速な起動

2. **OpenRCサービス管理**
   - rc-update/rc-serviceで完全制御
   - cronベースの自動メンテナンス
   - Snapperスナップショット自動化

3. **Distrobox統合**
   - Podman + cgroup v2対応
   - OpenRC環境下で完全動作

4. **開発環境**
   - Zed + Claude Code
   - ESP-IDF + カーネルビルド
   - 統合管理スクリプト

### 🚀 OpenRC版の利点

- **軽量**: systemdより省メモリ
- **シンプル**: initスクリプトが理解しやすい
- **カスタマイズ性**: 細かい制御が可能
- **Gentoo本来の設計**: Gentooの哲学に忠実

ご質問や追加のカスタマイズがあればお知らせください！
