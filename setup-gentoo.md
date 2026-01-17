# 結論

Gentoo KDE (Btrfs) + Distrobox Arch + Zed Editor + Claude Code の完全統合環境を、初回セットアップから日常運用まで一貫したワークフローで提供します。

---

## 完全統合システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│  Gentoo Linux (KDE Plasma Wayland/X11)                      │
│  ├─ Btrfs (zstd圧縮, スナップショット自動管理)                 │
│  ├─ Kernel: gentoo-sources 6.18 (Ryzen最適化)               │
│  └─ Hardware: Ryzen 9 3900XT + RX 5700 XT                   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Distrobox: arch-dev (開発環境)                      │    │
│  │  ├─ Zed Editor (Claude Code統合)                    │    │
│  │  ├─ カーネルビルド環境 (Qt6 xconfig)                  │    │
│  │  ├─ ESP-IDF (Omni-P4開発)                           │    │
│  │  └─ 各種開発ツール                                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Distrobox: kernel-build (カーネル専用)              │    │
│  │  ├─ /usr/src マウント                                │    │
│  │  ├─ Qt6 + xconfig                                    │    │
│  │  └─ ビルドツールチェーン                               │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Gentoo Base System Installation

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
btrfs subvolume create /mnt/gentoo/@containers  # Distrobox用

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

### 1.2 Stage3展開 & Chroot

```bash
cd /mnt/gentoo

# Stage3ダウンロード (最新版URL確認: https://www.gentoo.org/downloads/)
wget https://distfiles.gentoo.org/releases/amd64/autobuilds/latest-stage3-amd64-desktop-systemd.tar.xz

tar xpvf stage3-*.tar.xz --xattrs-include='*.*' --numeric-owner

# make.conf設定
nano /mnt/gentoo/etc/portage/make.conf
```

### 1.3 最終版 make.conf

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

# ===== USE Flags - 完全Qt6環境 =====
USE="qt6 qt5 kde plasma wayland X \
     -gtk -gtk2 -gtk3 -gtk4 -gnome \
     vulkan opengl opencl vaapi vdpau \
     pulseaudio pipewire alsa jack \
     networkmanager bluetooth wifi \
     elogind dbus udev systemd \
     btrfs zstd lzo lz4 \
     jpeg png svg webp pdf \
     encode mp3 flac opus aac vorbis \
     threads lto pgo graphite \
     distcc ccache \
     -doc -examples -test"

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
ACCEPT_KEYWORDS="~amd64"  # Testing branch (最新パッケージ)
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

### 1.4 Chroot & 基本設定

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

# プロファイル選択
eselect profile list
eselect profile set default/linux/amd64/23.0/desktop/plasma/systemd

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

### 2.2 カーネル設定必須項目

```bash
cd /usr/src/linux
make defconfig

# 以下を有効化:
make menuconfig
```

**最小必須設定:**

```
General setup --->
  [*] Initial RAM filesystem and RAM disk support
  [*] Support for paging of anonymous memory (swap)
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
        <M> Intel/SiS/nVidia/AMD/ALi AC97 Controller
        <M> Intel/SiS/nVidia/AMD MC97 Modem

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

## Phase 3: System Configuration

### 3.1 fstab設定

```bash
# UUID取得
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

### 3.2 ネットワーク & ホスト名

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
# NetworkManager
emerge --ask net-misc/networkmanager
systemctl enable NetworkManager
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

## Phase 4: KDE Plasma Installation

```bash
# KDE Plasma
emerge --ask kde-plasma/plasma-meta

# 必須アプリ
emerge --ask \
  kde-apps/konsole \
  kde-apps/dolphin \
  kde-apps/kate \
  kde-apps/spectacle \
  kde-apps/gwenview \
  kde-apps/okular

# ディスプレイマネージャー
emerge --ask gui-apps/sddm
systemctl enable sddm

# オーディオ (PipeWire)
emerge --ask \
  media-video/pipewire \
  media-video/wireplumber

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

### 4.1 再起動

```bash
exit
cd
umount -l /mnt/gentoo/dev{/shm,/pts,}
umount -R /mnt/gentoo
reboot
```

---

## Phase 5: Distrobox & Development Environment

### 5.1 Distrobox インストール

```bash
# Gentoo起動後、ユーザーでログイン

# Podman & Distrobox
sudo emerge --ask \
  app-containers/podman \
  app-containers/distrobox

# ユーザーネームスペース設定
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER

# セッション再ログイン必要
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
  zed-git \
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

## Phase 6: Zed Editor + Claude Code Integration

### 6.1 Zed設定ディレクトリ構造

```bash
mkdir -p ~/.config/zed/{tasks,snippets}
```

### 6.2 統合設定ファイル

**`~/.config/zed/settings.json`:**

```json
{
  "assistant": {
    "default_model": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514"
    },
    "version": "2",
    "enabled": true,
    "button": true
  },

  "features": {
    "inline_completion_provider": "supermaven"
  },

  "language_models": {
    "anthropic": {
      "api_url": "https://api.anthropic.com",
      "version": "1"
    }
  },

  "terminal": {
    "shell": {
      "program": "/bin/bash"
    },
    "working_directory": "current_project_directory",
    "font_size": 14,
    "env": {
      "TERM": "xterm-256color"
    },
    "blinking": "terminal_controlled",
    "alternate_scroll": "on"
  },

  "project": {
    "default_directory": "~/projects"
  },

  "vim_mode": false,
  "buffer_font_family": "JetBrains Mono",
  "buffer_font_size": 14,
  "buffer_line_height": {
    "custom": 1.5
  },

  "theme": {
    "mode": "system",
    "light": "One Light",
    "dark": "One Dark"
  },

  "ui_font_size": 16,
  "ui_font_family": "Noto Sans CJK JP",

  "tab_size": 2,
  "soft_wrap": "editor_width",
  "show_whitespaces": "selection",
  "remove_trailing_whitespace_on_save": true,
  "ensure_final_newline_on_save": true,

  "format_on_save": "on",
  "autosave": "on_focus_change",
  "auto_update": true,

  "git": {
    "enabled": true,
    "autoFetch": true,
    "autoFetchInterval": 300
  },

  "lsp": {
    "rust-analyzer": {
      "initialization_options": {
        "checkOnSave": {
          "command": "clippy"
        },
        "cargo": {
          "features": "all"
        }
      }
    },
    "clangd": {
      "initialization_options": {
        "compilationDatabasePath": "build"
      }
    }
  },

  "languages": {
    "C": {
      "tab_size": 2,
      "format_on_save": "on"
    },
    "C++": {
      "tab_size": 2,
      "format_on_save": "on"
    },
    "Rust": {
      "tab_size": 4,
      "format_on_save": "on"
    },
    "Python": {
      "tab_size": 4,
      "format_on_save": "on"
    }
  },

  "file_scan_exclusions": [
    "**/.git",
    "**/.svn",
    "**/.hg",
    "**/CVS",
    "**/.DS_Store",
    "**/Thumbs.db",
    "**/.ccls-cache",
    "**/.cache",
    "**/node_modules",
    "**/target",
    "**/build",
    "**/.venv"
  ]
}
```

### 6.3 キーマップ設定

**`~/.config/zed/keymap.json`:**

```json
[
  {
    "context": "Editor",
    "bindings": {
      "ctrl-shift-space": "assistant::InlineAssist",
      "ctrl-shift-/": "assistant::ToggleFocus",
      "ctrl-shift-enter": "assistant::NewConversation",
      "ctrl-shift-l": "editor::SelectLine",
      "ctrl-d": "editor::SelectNext",
      "ctrl-shift-k": "editor::DeleteLine",
      "alt-up": "editor::MoveLineUp",
      "alt-down": "editor::MoveLineDown"
    }
  },
  {
    "context": "Terminal",
    "bindings": {
      "ctrl-shift-c": "terminal::Copy",
      "ctrl-shift-v": "terminal::Paste",
      "ctrl-shift-n": "terminal::NewTerminal"
    }
  },
  {
    "context": "Workspace",
    "bindings": {
      "ctrl-shift-p": "command_palette::Toggle",
      "ctrl-p": "file_finder::Toggle",
      "ctrl-shift-f": "workspace::DeploySearch",
      "ctrl-`": "terminal::ToggleFocus"
    }
  }
]
```

### 6.4 統合タスク定義

**`~/.config/zed/tasks/omni-p4.json`:**

```json
{
  "label": "Omni-P4 Development Tasks",
  "tasks": [
    {
      "label": "ESP-IDF: Build",
      "command": "distrobox",
      "args": [
        "enter", "arch-dev", "--",
        "bash", "-c",
        "cd ~/projects/omni-p4/esp-idf && . ~/esp/esp-idf/export.sh && idf.py build"
      ],
      "cwd": "${workspaceFolder}"
    },
    {
      "label": "ESP-IDF: Flash & Monitor",
      "command": "distrobox",
      "args": [
        "enter", "arch-dev", "--",
        "bash", "-c",
        "cd ~/projects/omni-p4/esp-idf && . ~/esp/esp-idf/export.sh && idf.py -p /dev/ttyUSB0 flash monitor"
      ],
      "cwd": "${workspaceFolder}"
    },
    {
      "label": "ESP-IDF: Menuconfig",
      "command": "distrobox",
      "args": [
        "enter", "arch-dev", "--",
        "bash", "-c",
        "cd ~/projects/omni-p4/esp-idf && . ~/esp/esp-idf/export.sh && idf.py menuconfig"
      ],
      "cwd": "${workspaceFolder}"
    },
    {
      "label": "Gentoo Kernel: xconfig",
      "command": "bash",
      "args": [
        "-c",
        "xhost +local: && distrobox enter kernel-build -- bash -c 'export DISPLAY=:0 && cd /usr/src/linux && make xconfig'"
      ]
    },
    {
      "label": "Gentoo Kernel: menuconfig",
      "command": "distrobox",
      "args": [
        "enter", "kernel-build", "--",
        "bash", "-c",
        "cd /usr/src/linux && make menuconfig"
      ]
    },
    {
      "label": "Gentoo Kernel: Build",
      "command": "distrobox",
      "args": [
        "enter", "kernel-build", "--",
        "bash", "-c",
        "cd /usr/src/linux && make -j24"
      ]
    },
    {
      "label": "Gentoo Kernel: Install",
      "command": "bash",
      "args": [
        "-c",
        "cd /usr/src/linux && sudo make modules_install && sudo make install && sudo grub-mkconfig -o /boot/grub/grub.cfg"
      ]
    },
    {
      "label": "Format: C/C++ (clang-format)",
      "command": "clang-format",
      "args": ["-i", "${file}"],
      "cwd": "${fileDirname}"
    },
    {
      "label": "Git: Commit Snapshot",
      "command": "git",
      "args": ["commit", "-am", "WIP: $(date +%Y%m%d_%H%M%S)"],
      "cwd": "${workspaceFolder}"
    },
    {
      "label": "Btrfs: Create Snapshot",
      "command": "sudo",
      "args": [
        "snapper", "-c", "root", "create",
        "--description", "Manual snapshot: ${workspaceFolder}",
        "--cleanup-algorithm", "number"
      ]
    }
  ]
}
```

---

## Phase 7: システム管理自動化

### 7.1 統合管理スクリプト

**`~/bin/omni-sys-manager.sh`:**

```bash
#!/bin/bash
# Omni-P4 System Manager

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

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
    sudo compsize /
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
    sudo btrfs scrub start /
    sudo btrfs scrub status /
}

# ===== Backup =====
backup_configs() {
    log_info "Backing up configuration files..."
    
    BACKUP_DIR=~/backups/configs-$(date +%Y%m%d)
    mkdir -p "$BACKUP_DIR"
    
    # Zed configs
    cp -r ~/.config/zed "$BACKUP_DIR/"
    
    # Kernel config
    cp /usr/src/linux/.config "$BACKUP_DIR/kernel.config"
    
    # make.conf
    sudo cp /etc/portage/make.conf "$BACKUP_DIR/"
    
    # Package lists
    sudo eix-installed all > "$BACKUP_DIR/installed-packages.txt"
    
    log_info "Backup saved to $BACKUP_DIR"
}

# ===== Menu =====
show_menu() {
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║     Omni-P4 System Manager                   ║"
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
    echo "  Backup:"
    echo "    7) Backup configurations"
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
        7) backup_configs ;;
        0) exit 0 ;;
        *) log_error "Invalid option" ;;
    esac
    
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
        backup) backup_configs ;;
        *) log_error "Unknown command: $1" ;;
    esac
fi
```

```bash
chmod +x ~/bin/omni-sys-manager.sh
```

### 7.2 便利なエイリアス

**`~/.bashrc` に追加:**

```bash
# ===== Omni-P4 Development Aliases =====

# System management
alias omni-sys='~/bin/omni-sys-manager.sh'
alias omni-update='~/bin/omni-sys-manager.sh update'
alias omni-kernel='~/bin/omni-sys-manager.sh kernel'

# Distrobox shortcuts
alias dev='distrobox enter arch-dev'
alias kernel='distrobox enter kernel-build'

# Kernel development
alias kxconfig='xhost +local: && distrobox enter kernel-build -- bash -c "export DISPLAY=:0 && cd /usr/src/linux && make xconfig"'
alias kmenu='distrobox enter kernel-build -- bash -c "cd /usr/src/linux && make menuconfig"'
alias kbuild='distrobox enter kernel-build -- bash -c "cd /usr/src/linux && make -j24"'
alias kinstall='cd /usr/src/linux && sudo make modules_install && sudo make install && sudo grub-mkconfig -o /boot/grub/grub.cfg'

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

### 7.3 Systemd自動メンテナンスタイマー

**`/etc/systemd/system/btrfs-scrub.service`:**

```ini
[Unit]
Description=Btrfs scrub on /
ConditionPathIsMountPoint=/

[Service]
Type=oneshot
ExecStart=/usr/bin/btrfs scrub start -B /
```

**`/etc/systemd/system/btrfs-scrub.timer`:**

```ini
[Unit]
Description=Monthly Btrfs scrub

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
```

**有効化:**

```bash
sudo systemctl enable --now btrfs-scrub.timer
```

---

## Phase 8: プロジェクト構造テンプレート

### 8.1 Omni-P4プロジェクト構造

```bash
mkdir -p ~/projects/omni-p4/{esp-idf,firmware,mechanical,docs,scripts,tests}

cd ~/projects/omni-p4
```

**ディレクトリ構造:**

```
~/projects/omni-p4/
├── esp-idf/                    # ESP32-P4メインコード
│   ├── main/
│   │   ├── main.c
│   │   ├── audio_pipeline.c
│   │   ├── i2s_driver.c
│   │   └── dac_control.c
│   ├── components/
│   │   ├── audio_processing/
│   │   └── bluetooth_control/
│   ├── CMakeLists.txt
│   └── sdkconfig
├── firmware/                   # ビルド成果物
│   └── build/
├── mechanical/                 # 3Dモデル
│   ├── enclosure-v4.1.step
│   └── assembly.pdf
├── docs/                       # ドキュメント
│   ├── architecture.md
│   ├── audio-pipeline.md
│   └── hardware-specs.md
├── scripts/                    # 自動化スクリプト
│   ├── flash-dev.sh
│   └── monitor.sh
├── tests/                      # テストコード
│   └── unit/
├── .zed/
│   └── tasks.json
├── .gitignore
└── README.md
```

### 8.2 .gitignore

```gitignore
# ESP-IDF
build/
sdkconfig.old
*.pyc

# Editors
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Temporary
*.tmp
*.bak
*.log
```

---

## Phase 9: 日常運用ワークフロー

### 典型的な開発セッション

```bash
# 1. 朝の起動
omni-sys  # システム状態確認

# 2. プロジェクト開始
cd ~/projects/omni-p4
zed .  # Zed Editorで開く

# 3. ESP-IDF開発
# Zedターミナルで:
dev  # arch-dev環境に入る
. ~/esp/esp-idf/export.sh
cd esp-idf
idf.py build

# 4. Claude Codeと対話
# Zed内で Ctrl+Shift+Space
# 「ESP32-P4のI2S DMA設定で、デュアルチャネル対応のバッファ管理コードを生成してください」

# 5. フラッシュ & テスト
esp-flash

# 6. 定期コミット
git add .
git commit -m "feat: デュアルI2S対応実装"

# 7. システムスナップショット（重要な変更前）
btrfs-create-snap
```

### 週次メンテナンス

```bash
# 日曜朝に実行
omni-update              # Gentoo更新
distrobox update --all   # コンテナ更新
btrfs-cleanup           # Btrfs整理
backup-configs          # 設定バックアップ
```

---

## まとめ: 完全統合環境の特徴

### ✅ 達成した統合

1. **Gentoo Base System**
   - Ryzen最適化ビルド
   - Btrfsスナップショット自動管理
   - Qt6完全環境

2. **開発環境分離**
   - arch-dev: Zed + Claude Code + ESP-IDF
   - kernel-build: カーネル設定専用
   - ホストの安定性維持

3. **Zed + Claude Code統合**
   - ワンコマンドでタスク実行
   - ESP-IDF/カーネルビルド自動化
   - Claude Codeとシームレス連携

4. **システム管理自動化**
   - スナップショット自動作成
   - 定期メンテナンススクリプト
   - 設定バックアップ

### 🚀 次のステップ

この環境で以下が可能です:

1. Omni-P4のESP32-P4コード開発
2. Claude Codeとの自然な対話でコード生成
3. カーネルカスタマイズ
4. 安全なシステム実験（スナップショット保護）

ご質問や追加のカスタマイズがあればお知らせください！
