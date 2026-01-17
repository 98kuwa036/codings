# 結論

Btrfs向けに最適化したmake.confとインストール手順を更新します。サブボリューム構成、スナップショット運用、SSD最適化を含めた完全な設定を提供します。

---

## 更新版: Btrfs最適化 make.conf

```bash
# Compiler flags
COMMON_FLAGS="-march=znver2 -O2 -pipe"
CFLAGS="${COMMON_FLAGS}"
CXXFLAGS="${COMMON_FLAGS}"
FCFLAGS="${COMMON_FLAGS}"
FFLAGS="${COMMON_FLAGS}"
LDFLAGS="-Wl,-O2 -Wl,--as-needed"

# CPU settings
MAKEOPTS="-j24 -l24"
EMERGE_DEFAULT_OPTS="--jobs=4 --load-average=24"

# Portage features
FEATURES="parallel-fetch parallel-install candy"
ACCEPT_LICENSE="*"

# USE flags - Btrfs追加
USE="qt6 qt5 kde plasma wayland \
     -gtk -gtk2 -gtk3 -gtk4 -gnome \
     vulkan opengl opencl vaapi vdpau \
     pulseaudio pipewire alsa \
     networkmanager bluetooth \
     X elogind dbus udev \
     jpeg png svg pdf \
     encode mp3 flac opus \
     threads lto pgo \
     btrfs zstd lzo \
     -systemd -doc -examples"

# Video card
VIDEO_CARDS="amdgpu radeonsi"
LLVM_TARGETS="AMDGPU X86"

# Input devices
INPUT_DEVICES="libinput"

# Qt優先設定
QT_QPA_PLATFORMTHEME="kde"

# Language
L10N="ja en"
LINGUAS="ja en"

# Mirrors (日本)
GENTOO_MIRRORS="https://ftp.jaist.ac.jp/pub/Linux/Gentoo/ \
                https://ftp.riken.jp/Linux/gentoo/"

# Portage directories - Btrfsサブボリューム考慮
PORTDIR="/var/db/repos/gentoo"
DISTDIR="/var/cache/distfiles"
PKGDIR="/var/cache/binpkgs"

# Ccache
CCACHE_DIR="/var/cache/ccache"
```

---

## Btrfs パーティション・サブボリューム構成

### 推奨パーティション構成

```
/dev/nvme0n1p1  512M   EFI System (FAT32)
/dev/nvme0n1p2  16G    Swap
/dev/nvme0n1p3  残り全て Btrfs (/)
```

### Btrfs サブボリューム構造

```
@                    # / (root)
@home               # /home
@snapshots          # /.snapshots
@var_log            # /var/log
@var_cache          # /var/cache
@var_tmp            # /var/tmp
@portage            # /var/db/repos/gentoo
@distfiles          # /var/cache/distfiles
@ccache             # /var/cache/ccache
```

### インストール時のBtrfsセットアップ

```bash
# パーティション作成 (例: NVMe SSD)
parted -a optimal /dev/nvme0n1
  mklabel gpt
  mkpart primary fat32 1MiB 513MiB
  set 1 esp on
  mkpart primary linux-swap 513MiB 16.5GiB
  mkpart primary btrfs 16.5GiB 100%
  quit

# ファイルシステム作成
mkfs.vfat -F32 /dev/nvme0n1p1
mkswap /dev/nvme0n1p2
mkfs.btrfs -L gentoo -f /dev/nvme0n1p3

# Btrfsマウントとサブボリューム作成
mount /dev/nvme0n1p3 /mnt/gentoo

# サブボリューム作成
btrfs subvolume create /mnt/gentoo/@
btrfs subvolume create /mnt/gentoo/@home
btrfs subvolume create /mnt/gentoo/@snapshots
btrfs subvolume create /mnt/gentoo/@var_log
btrfs subvolume create /mnt/gentoo/@var_cache
btrfs subvolume create /mnt/gentoo/@var_tmp
btrfs subvolume create /mnt/gentoo/@portage
btrfs subvolume create /mnt/gentoo/@distfiles
btrfs subvolume create /mnt/gentoo/@ccache

# アンマウント
umount /mnt/gentoo

# 正しいマウント構成
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@ /dev/nvme0n1p3 /mnt/gentoo

# ディレクトリ作成
mkdir -p /mnt/gentoo/{home,.snapshots,var/log,var/cache,var/tmp,var/db/repos/gentoo,var/cache/distfiles,var/cache/ccache,boot}

# 各サブボリュームマウント
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@home /dev/nvme0n1p3 /mnt/gentoo/home
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@snapshots /dev/nvme0n1p3 /mnt/gentoo/.snapshots
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@var_log /dev/nvme0n1p3 /mnt/gentoo/var/log
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@var_cache /dev/nvme0n1p3 /mnt/gentoo/var/cache
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@var_tmp /dev/nvme0n1p3 /mnt/gentoo/var/tmp
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@portage /dev/nvme0n1p3 /mnt/gentoo/var/db/repos/gentoo
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@distfiles /dev/nvme0n1p3 /mnt/gentoo/var/cache/distfiles
mount -o noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@ccache /dev/nvme0n1p3 /mnt/gentoo/var/cache/ccache

# EFIパーティションマウント
mount /dev/nvme0n1p1 /mnt/gentoo/boot

# Swapアクティベート
swapon /dev/nvme0n1p2
```

### /etc/fstab 設定

```bash
# /etc/fstab

# Root subvolume
UUID=<btrfs-uuid>  /                    btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@           0 0

# Home subvolume
UUID=<btrfs-uuid>  /home                btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@home       0 0

# Snapshots subvolume
UUID=<btrfs-uuid>  /.snapshots          btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@snapshots  0 0

# Var log (no compression for logs)
UUID=<btrfs-uuid>  /var/log             btrfs  noatime,space_cache=v2,ssd,discard=async,subvol=@var_log                   0 0

# Var cache
UUID=<btrfs-uuid>  /var/cache           btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@var_cache  0 0

# Var tmp
UUID=<btrfs-uuid>  /var/tmp             btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@var_tmp    0 0

# Portage tree
UUID=<btrfs-uuid>  /var/db/repos/gentoo btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@portage    0 0

# Distfiles
UUID=<btrfs-uuid>  /var/cache/distfiles btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@distfiles  0 0

# Ccache
UUID=<btrfs-uuid>  /var/cache/ccache    btrfs  noatime,compress=zstd:1,space_cache=v2,ssd,discard=async,subvol=@ccache     0 0

# EFI
UUID=<efi-uuid>    /boot                vfat   defaults,noatime  0 2

# Swap
UUID=<swap-uuid>   none                 swap   sw                0 0
```

**UUID取得:**
```bash
blkid | grep nvme0n1p3  # Btrfs UUID
blkid | grep nvme0n1p1  # EFI UUID
blkid | grep nvme0n1p2  # Swap UUID
```

---

## カーネル設定（Btrfs対応追加）

```bash
make menuconfig
```

**Btrfs必須オプション:**
```
File systems --->
  <*> Btrfs filesystem
  [*]   Btrfs POSIX Access Control Lists
  [*]   Btrfs will run sanity tests upon loading
  [*]   Btrfs debugging support
  [*]   Btrfs assert support

General setup --->
  <*> Kernel .config support
  [*]   Enable access to .config through /proc/config.gz
  
Compression --->
  <*> Zstd compression support
  <*> LZO compression support
  <*> LZ4 compression support
```

---

## Btrfs管理ツール・スクリプト

### 必須パッケージ

```bash
emerge --ask sys-fs/btrfs-progs
emerge --ask sys-fs/compsize        # 圧縮率確認
emerge --ask app-backup/snapper     # スナップショット管理
```

### Snapper設定（自動スナップショット）

```bash
# Snapper設定作成
snapper -c root create-config /

# 設定編集 (/etc/snapper/configs/root)
TIMELINE_CREATE="yes"
TIMELINE_CLEANUP="yes"

# Timeline設定
TIMELINE_MIN_AGE="1800"
TIMELINE_LIMIT_HOURLY="5"
TIMELINE_LIMIT_DAILY="7"
TIMELINE_LIMIT_WEEKLY="0"
TIMELINE_LIMIT_MONTHLY="0"
TIMELINE_LIMIT_YEARLY="0"

# Snapper有効化
rc-update add snapper default
```

### システム更新前の自動スナップショット

```bash
# /etc/portage/bashrc
post_pkg_preinst() {
    if [[ "${EBUILD_PHASE}" == "preinst" ]]; then
        /usr/bin/snapper -c root create --description "emerge: ${CATEGORY}/${PF}" --cleanup-algorithm number
    fi
}
```

### 便利な管理スクリプト

**容量確認スクリプト (`~/bin/btrfs-stats.sh`):**
```bash
#!/bin/bash

echo "=== Btrfs Filesystem Usage ==="
btrfs filesystem usage /

echo -e "\n=== Compression Ratio ==="
compsize /

echo -e "\n=== Subvolume List ==="
btrfs subvolume list /

echo -e "\n=== Recent Snapshots ==="
snapper -c root list | tail -10
```

**古いスナップショット削除 (`~/bin/btrfs-cleanup.sh`):**
```bash
#!/bin/bash

# 30日以上前のスナップショットを削除
snapper -c root cleanup number

# Btrfs balance (月1回推奨)
if [ "$(date +%d)" = "01" ]; then
    btrfs balance start -dusage=50 -musage=50 /
fi
```

---

## Btrfs最適化Tips

### 1. 定期的なメンテナンス

**週次scrub (データ整合性チェック):**
```bash
# Cron設定 (/etc/cron.weekly/btrfs-scrub)
#!/bin/bash
btrfs scrub start /
```

### 2. SSD最適化

```bash
# Discardは既にfstabでasync設定済み
# 追加最適化: I/Oスケジューラ

# /etc/udev/rules.d/60-ioschedulers.rules
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"
ACTION=="add|change", KERNEL=="sd[a-z]|hd[a-z]", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="mq-deadline"
```

### 3. 圧縮効果の確認

```bash
# インストール後、定期的に確認
compsize -x /
compsize -x /home
compsize -x /var/cache/distfiles
```

---

## トラブルシューティング

### スナップショットからのロールバック

```bash
# 起動時にトラブルが発生した場合
# Live USBから起動

mount /dev/nvme0n1p3 /mnt

# 現在の@を@.brokenにリネーム
mv /mnt/@ /mnt/@.broken

# スナップショットから復元
btrfs subvolume snapshot /mnt/.snapshots/XX/snapshot /mnt/@

# 再起動
reboot
```

### ディスク容量不足時

```bash
# メタデータバランス
btrfs balance start -m /

# 未使用チャンク削除
btrfs balance start -dusage=0 /
```

---

これでBtrfs環境に完全対応した設定になりました。スナップショット機能により、システム更新時も安全にロールバック可能です。

ご質問があればお知らせください！
