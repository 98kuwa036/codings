# 結論

**①Gentoo環境**: Ryzen 9 3900XT + Radeon RX 5700 XT向けに最適化したmake.confと、Qt6優先・完全QT環境のインストール手順を提供します。

**②Zed + Claude Code**: DistroboxのArch Linux環境でZed editorとClaude Codeを最大限活用するための設定を案内します。

---

## ①Gentoo KDE Plasma インストールガイド

### 最適化されたmake.conf

```bash
# Compiler flags
COMMON_FLAGS="-march=znver2 -O2 -pipe"
CFLAGS="${COMMON_FLAGS}"
CXXFLAGS="${COMMON_FLAGS}"
FCFLAGS="${COMMON_FLAGS}"
FFLAGS="${COMMON_FLAGS}"
LDFLAGS="-Wl,-O2 -Wl,--as-needed"

# CPU settings
MAKEOPTS="-j24 -l24"  # 12コア24スレッド
EMERGE_DEFAULT_OPTS="--jobs=4 --load-average=24"

# Portage features
FEATURES="parallel-fetch parallel-install candy"
ACCEPT_LICENSE="*"

# USE flags - 完全Qt環境
USE="qt6 qt5 kde plasma wayland \
     -gtk -gtk2 -gtk3 -gtk4 -gnome \
     vulkan opengl opencl vaapi vdpau \
     pulseaudio pipewire alsa \
     networkmanager bluetooth \
     X elogind dbus udev \
     jpeg png svg pdf \
     encode mp3 flac opus \
     threads lto pgo \
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

# Portage directories
PORTDIR="/var/db/repos/gentoo"
DISTDIR="/var/cache/distfiles"
PKGDIR="/var/cache/binpkgs"

# Ccache (オプション)
CCACHE_DIR="/var/cache/ccache"
```

### インストール手順

#### 1. カーネル設定（gentoo-sources 6.18系）

```bash
# カーネルインストール
emerge --ask sys-kernel/gentoo-sources

# 重要な設定項目
cd /usr/src/linux
make menuconfig
```

**必須設定:**
```
Processor type and features --->
  [*] Symmetric multi-processing support
  [*] AMD Zen CPU support
  Processor family (Zen 2)

Device Drivers --->
  Graphics support --->
    [*] AMD GPU
    [M] AMD Radeon
    [*] Enable amdgpu support for SI parts
    [*] Enable amdgpu support for CIK parts
    [*] Enable AMD powerplay component
    Display Engine Configuration --->
      [*] AMD DC - Enable new display engine
      [*] DCN 1.0 Raven family
    [M] AMD Audio CoProcessor IP(ACP) support

  Sound card support --->
    <M> Advanced Linux Sound Architecture
    <M> PCI sound devices --->
      [M] HD Audio

  USB support --->
    <*> xHCI HCD (USB 3.0) support

File systems --->
  <*> The Extended 4 (ext4) filesystem
  <*> Btrfs filesystem
  DOS/FAT/NT Filesystems --->
    <M> VFAT (Windows-95) fs support
  Pseudo filesystems --->
    [*] Tmpfs POSIX Access Control Lists
```

#### 2. ファームウェア

```bash
# AMD GPU用ファームウェア
echo "sys-kernel/linux-firmware redistributable" >> /etc/portage/package.license
emerge --ask sys-kernel/linux-firmware
```

#### 3. Qt6 & KDE Plasma インストール

```bash
# プロファイル選択
eselect profile list
eselect profile set default/linux/amd64/23.0/desktop/plasma

# Qt6優先設定
mkdir -p /etc/portage/package.use
echo "dev-qt/* qt6" >> /etc/portage/package.use/qt

# KDE Plasmaインストール
emerge --ask kde-plasma/plasma-meta

# 追加アプリケーション
emerge --ask \
  kde-apps/kde-apps-meta \
  kde-apps/konsole \
  kde-apps/dolphin \
  kde-apps/kate
```

#### 4. ディスプレイマネージャー

```bash
emerge --ask gui-libs/display-manager-init

# SDDM設定
rc-update add display-manager default
echo 'DISPLAYMANAGER="sddm"' > /etc/conf.d/display-manager
```

#### 5. オーディオ（PipeWire）

```bash
emerge --ask \
  media-video/pipewire \
  media-video/wireplumber

# ユーザー追加後
rc-update add elogind boot
```

#### 6. ネットワーク

```bash
emerge --ask net-misc/networkmanager
rc-update add NetworkManager default
```

---

## ②Zed Editor + Claude Code 設定

### Distrobox Arch環境セットアップ

```bash
# Gentooホストから
distrobox create --name arch-dev --image archlinux:latest
distrobox enter arch-dev

# Arch内部で
sudo pacman -Syu
sudo pacman -S base-devel git curl zed
```

### Zed設定ファイル (`~/.config/zed/settings.json`)

```json
{
  "assistant": {
    "default_model": {
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514"
    },
    "version": "2",
    "enabled": true
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
    "env": {
      "TERM": "xterm-256color"
    }
  },

  "project": {
    "default_directory": "~/projects"
  },

  "buffer_font_size": 14,
  "theme": {
    "mode": "system",
    "light": "One Light",
    "dark": "One Dark"
  },

  "ui_font_size": 16,
  "tab_size": 2,
  "soft_wrap": "editor_width",
  
  "format_on_save": "on",
  "autosave": "on_focus_change",
  
  "git": {
    "enabled": true,
    "autoFetch": true
  },

  "lsp": {
    "rust-analyzer": {
      "initialization_options": {
        "checkOnSave": {
          "command": "clippy"
        }
      }
    }
  }
}
```

### Claude Code最適活用のための keymap設定 (`~/.config/zed/keymap.json`)

```json
[
  {
    "context": "Editor",
    "bindings": {
      "ctrl-shift-space": "assistant::InlineAssist",
      "ctrl-shift-/": "assistant::ToggleFocus",
      "ctrl-shift-enter": "assistant::NewConversation"
    }
  },
  {
    "context": "Terminal",
    "bindings": {
      "ctrl-shift-c": "terminal::Copy",
      "ctrl-shift-v": "terminal::Paste"
    }
  }
]
```

### Claude Code ベストプラクティス

#### プロジェクト構造例（Omni-P4用）

```
~/projects/omni-p4/
├── .zed/
│   └── tasks.json          # カスタムタスク定義
├── esp-idf/                # ESP32-P4コード
│   ├── main/
│   └── components/
├── firmware/               # ファームウェアビルド
├── docs/                   # ドキュメント
│   └── architecture.md
└── scripts/                # ビルド・デプロイスクリプト
```

#### タスク定義 (`.zed/tasks.json`)

```json
{
  "tasks": [
    {
      "label": "ESP-IDF Build",
      "command": "idf.py",
      "args": ["build"],
      "cwd": "${workspaceFolder}/esp-idf"
    },
    {
      "label": "ESP-IDF Flash",
      "command": "idf.py",
      "args": ["-p", "/dev/ttyUSB0", "flash", "monitor"],
      "cwd": "${workspaceFolder}/esp-idf"
    },
    {
      "label": "Format Code",
      "command": "clang-format",
      "args": ["-i", "**/*.c", "**/*.h"]
    }
  ]
}
```

### Claude Codeとの効果的な対話パターン

**コード生成時:**
```
「ESP32-P4のI2S DMA設定コードを、デュアルチャネル対応で生成してください。
バッファサイズは4096、サンプルレート48kHz、24bit深度で。」
```

**デバッグ時:**
```
「このESP_ERROR_CHECK失敗の原因を特定して修正案を提示してください。
[エラーログ貼り付け]」
```

**リファクタリング時:**
```
「このaudio_pipeline.c内の関数を、責任ごとに分離してモジュール性を向上させてください。」
```

### 統合ターミナル活用

Zed内蔵ターミナルでESP-IDF環境を直接利用:

```bash
# Distrobox内にESP-IDF setup
cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32p4

# Zedから即座にアクセス
. ~/esp/esp-idf/export.sh
idf.py build
```

---

**次のステップ:**
1. Gentooインストール開始時に具体的なパーティション構成を相談
2. Zed + Claude Code環境構築後、Omni-P4の具体的コード開発を開始

ご質問やカスタマイズ要望があればお知らせください！
