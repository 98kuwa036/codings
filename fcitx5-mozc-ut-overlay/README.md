# fcitx5-mozc-ut Gentoo Overlay

This overlay provides `fcitx5-mozc-ut` - Mozc with Fcitx5 support and **all** UT dictionaries from [utuhiro78's merge-ut-dictionaries](https://github.com/utuhiro78/merge-ut-dictionaries).

## Included UT Dictionaries

All 8 dictionaries are included:

| Dictionary | Description | Source |
|------------|-------------|--------|
| alt-cannadic | Alternative Cannadic dictionary | [mozcdic-ut-alt-cannadic](https://github.com/utuhiro78/mozcdic-ut-alt-cannadic) |
| edict2 | Japanese-English dictionary | [mozcdic-ut-edict2](https://github.com/utuhiro78/mozcdic-ut-edict2) |
| jawiki | Japanese Wikipedia dictionary | [mozcdic-ut-jawiki](https://github.com/utuhiro78/mozcdic-ut-jawiki) |
| neologd | Neologism dictionary (mecab-ipadic-NEologd) | [mozcdic-ut-neologd](https://github.com/utuhiro78/mozcdic-ut-neologd) |
| personal-names | Personal name dictionary | [mozcdic-ut-personal-names](https://github.com/utuhiro78/mozcdic-ut-personal-names) |
| place-names | Place name dictionary (Japan Post ZIP code) | [mozcdic-ut-place-names](https://github.com/utuhiro78/mozcdic-ut-place-names) |
| skk-jisyo | SKK Japanese dictionary | [mozcdic-ut-skk-jisyo](https://github.com/utuhiro78/mozcdic-ut-skk-jisyo) |
| sudachidict | Sudachi morphological dictionary | [mozcdic-ut-sudachidict](https://github.com/utuhiro78/mozcdic-ut-sudachidict) |

## Installation

### 1. Add the overlay

Create the overlay configuration file:

```bash
sudo mkdir -p /etc/portage/repos.conf
```

Create `/etc/portage/repos.conf/fcitx5-mozc-ut.conf`:

```ini
[fcitx5-mozc-ut]
location = /var/db/repos/fcitx5-mozc-ut
sync-type = git
sync-uri = https://github.com/YOUR_USERNAME/fcitx5-mozc-ut-overlay.git
auto-sync = yes
```

Or manually clone:

```bash
sudo mkdir -p /var/db/repos
sudo git clone https://github.com/YOUR_USERNAME/fcitx5-mozc-ut-overlay.git /var/db/repos/fcitx5-mozc-ut
```

### 2. Unmask the package (if needed)

```bash
echo "app-i18n/fcitx5-mozc-ut ~amd64" | sudo tee -a /etc/portage/package.accept_keywords/fcitx5-mozc-ut
```

### 3. Install

```bash
sudo emerge -av app-i18n/fcitx5-mozc-ut
```

## USE Flags

| Flag | Description |
|------|-------------|
| `emacs` | Enable Emacs support |
| `gui` | Build mozc_tool GUI configuration tool |
| `renderer` | Build mozc_renderer for candidate window |

## Requirements

- Gentoo Linux (amd64)
- Fcitx5
- Bazel >= 6.4.0
- Qt6 (for gui/renderer USE flags)

## Configuration

After installation, add Mozc to your Fcitx5 input methods:

1. Run `fcitx5-configtool`
2. Add "Mozc" to your input method list
3. If using GUI tools: `mozc_tool --mode=config_dialog`

## Version

- Mozc: 2.32.5994.102 (November 2025)
- UT Dictionaries: Latest commits as of January 2025

## License

- Mozc: BSD-3-Clause
- UT Dictionaries: Various (see individual repositories)

## Credits

- [Google Mozc](https://github.com/google/mozc)
- [Fcitx Mozc](https://github.com/fcitx/mozc)
- [utuhiro78's UT Dictionaries](https://github.com/utuhiro78/merge-ut-dictionaries)
