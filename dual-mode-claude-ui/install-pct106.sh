#!/bin/bash
# ============================================================
# Dual Mode Claude UI - PCT 106 Installation Script
# ============================================================
# Installs:
#   1. Node.js 20 LTS
#   2. Claude CLI (Pro → Anthropic API fallback)
#   3. Dual Mode Claude UI application
#   4. Systemd service (auto-start on boot)
#
# Usage (run on PCT 106 or via pct exec):
#   bash install-pct106.sh [OPTIONS]
#
# Options:
#   --port PORT           UI server port (default: 4000)
#   --password PASS       UI password (default: none)
#   --orch-host HOST      PCT 100 IP (default: auto-detect)
#   --orch-port PORT      Bushidan port (default: 8067)
#   --api-key KEY         Anthropic API key for fallback
#   --app-dir DIR         Install directory (default: /opt/dual-claude-ui)
#   --non-interactive     Skip all prompts
# ============================================================

set -euo pipefail

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${BLUE}[i]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }
step() { echo -e "\n${BOLD}${CYAN}━━━ $* ━━━${NC}"; }

# ─── Defaults ─────────────────────────────────────────────────────────────────
APP_PORT=4000
UI_PASSWORD=""
ORCH_HOST=""
ORCH_PORT=8067
ORCH_PASSWORD=""
ANTHROPIC_API_KEY=""
APP_DIR="/opt/dual-claude-ui"
SERVICE_USER="claude-ui"
NON_INTERACTIVE=false
REPO_URL="https://github.com/98kuwa036/codings"  # Replace with actual repo URL
BRANCH="claude/dual-mode-claude-ui-t4RnR"

# ─── Argument Parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)           APP_PORT="$2"; shift 2 ;;
    --password)       UI_PASSWORD="$2"; shift 2 ;;
    --orch-host)      ORCH_HOST="$2"; shift 2 ;;
    --orch-port)      ORCH_PORT="$2"; shift 2 ;;
    --orch-password)  ORCH_PASSWORD="$2"; shift 2 ;;
    --api-key)        ANTHROPIC_API_KEY="$2"; shift 2 ;;
    --app-dir)        APP_DIR="$2"; shift 2 ;;
    --non-interactive) NON_INTERACTIVE=true; shift ;;
    *) warn "Unknown option: $1"; shift ;;
  esac
done

# ─── Banner ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║          Dual Mode Claude UI - PCT 106 Setup         ║"
echo "║  Mode 1: Claude Code    │  Mode 2: 武士団 Orch       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Root Check ───────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  err "このスクリプトはrootで実行してください"
  err "sudo bash install-pct106.sh"
  exit 1
fi

# ─── OS Detection ─────────────────────────────────────────────────────────────
step "システム確認"
if [[ -f /etc/debian_version ]]; then
  DISTRO="debian"
  PKG_UPDATE="apt-get update -qq"
  PKG_INSTALL="apt-get install -y -qq"
  log "Debian/Ubuntu を検出"
elif [[ -f /etc/alpine-release ]]; then
  DISTRO="alpine"
  PKG_UPDATE="apk update -q"
  PKG_INSTALL="apk add -q"
  log "Alpine Linux を検出"
else
  err "サポートされていないOS (Debian/Ubuntu/Alpine が必要)"
  exit 1
fi

# ─── Auto-detect PCT 100 IP ───────────────────────────────────────────────────
if [[ -z "$ORCH_HOST" ]]; then
  # Try common Proxmox network ranges
  for subnet in "192.168.1" "10.0.0" "172.16.0"; do
    if ip route | grep -q "^${subnet}"; then
      GATEWAY="${subnet}.1"
      # PCT 100 is typically on the same /24, probe common IPs
      for host_octet in 100 200; do
        candidate="${subnet}.${host_octet}"
        if timeout 1 bash -c "echo > /dev/tcp/${candidate}/${ORCH_PORT}" 2>/dev/null; then
          ORCH_HOST="$candidate"
          log "PCT 100 を自動検出: ${ORCH_HOST}:${ORCH_PORT}"
          break 2
        fi
      done
    fi
  done
  if [[ -z "$ORCH_HOST" ]]; then
    warn "PCT 100 を自動検出できませんでした"
    if [[ "$NON_INTERACTIVE" == false ]]; then
      read -rp "PCT 100 の IPアドレスを入力してください: " ORCH_HOST
    else
      ORCH_HOST="192.168.1.100"
      warn "デフォルトを使用: ${ORCH_HOST}"
    fi
  fi
fi

# ─── Interactive Config ────────────────────────────────────────────────────────
if [[ "$NON_INTERACTIVE" == false ]]; then
  echo ""
  info "設定を確認してください:"
  echo "  アプリポート:    ${APP_PORT}"
  echo "  インストール先:  ${APP_DIR}"
  echo "  PCT 100ホスト:  ${ORCH_HOST}:${ORCH_PORT}"

  if [[ -z "$UI_PASSWORD" ]]; then
    read -rp "UIパスワードを設定 (空欄=認証なし): " UI_PASSWORD
  fi
  if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    read -rp "Anthropic APIキー (フォールバック用、空欄=スキップ): " ANTHROPIC_API_KEY
  fi
  if [[ -z "$ORCH_PASSWORD" ]]; then
    read -rp "武士団パスワード (PCT 100): " ORCH_PASSWORD
  fi
  echo ""
fi

# ─── STEP 1: System Dependencies ──────────────────────────────────────────────
step "システム依存関係のインストール"
$PKG_UPDATE

if [[ "$DISTRO" == "debian" ]]; then
  $PKG_INSTALL \
    curl wget git ca-certificates gnupg \
    build-essential python3 python3-pip \
    procps htop lsof jq
elif [[ "$DISTRO" == "alpine" ]]; then
  $PKG_INSTALL \
    curl wget git ca-certificates gnupg \
    build-base python3 py3-pip \
    procps htop jq bash
fi
log "システム依存関係 完了"

# ─── STEP 2: Node.js 20 LTS ───────────────────────────────────────────────────
step "Node.js 20 LTS のインストール"
if command -v node &>/dev/null && [[ $(node -v | cut -d. -f1 | tr -d 'v') -ge 20 ]]; then
  log "Node.js $(node -v) は既にインストール済み"
else
  if [[ "$DISTRO" == "debian" ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    $PKG_INSTALL nodejs
  elif [[ "$DISTRO" == "alpine" ]]; then
    $PKG_INSTALL nodejs npm
  fi
  log "Node.js $(node -v) インストール完了"
fi

# ─── STEP 3: Claude CLI ────────────────────────────────────────────────────────
step "Claude CLI のインストール (Pro → API フォールバック対応)"
npm install -g @anthropic-ai/claude-code 2>&1 | tail -3
CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "不明")
log "Claude CLI インストール完了: ${CLAUDE_VERSION}"

# ─── STEP 4: Service User ─────────────────────────────────────────────────────
step "サービスユーザーの作成"
if ! id "$SERVICE_USER" &>/dev/null; then
  useradd -r -m -s /bin/bash -d "/home/${SERVICE_USER}" "$SERVICE_USER"
  log "ユーザー作成: ${SERVICE_USER}"
else
  log "ユーザー既存: ${SERVICE_USER}"
fi

# ─── STEP 5: Claude Auth (Pro Login) ─────────────────────────────────────────
step "Claude Pro 認証設定"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Claude Pro認証 (重要)${NC}"
echo ""
echo "Claude CLIはProサブスクリプションを優先し、"
echo "失敗時はANTHROPIC_API_KEYにフォールバックします。"
echo ""
echo "今すぐPro認証を行いますか？"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [[ "$NON_INTERACTIVE" == false ]]; then
  read -rp "Claude Pro認証を実行しますか？ [y/N]: " DO_AUTH
  if [[ "${DO_AUTH,,}" == "y" ]]; then
    info "ブラウザが開きます。Claude Proアカウントでログインしてください..."
    su -c "claude auth login" "$SERVICE_USER" || warn "Pro認証をスキップ (API keyフォールバックを使用)"
  else
    info "Pro認証をスキップ。後で: sudo -u ${SERVICE_USER} claude auth login"
  fi
else
  warn "Non-interactive mode: Pro認証はスキップ。後で手動で実行してください"
  info "コマンド: sudo -u ${SERVICE_USER} claude auth login"
fi

# ─── STEP 6: Install Application ─────────────────────────────────────────────
step "アプリケーションのインストール: ${APP_DIR}"
mkdir -p "$APP_DIR"

# Clone or copy the application
if [[ -d "/home/user/codings/dual-mode-claude-ui" ]]; then
  # Local install (running from the repo)
  info "ローカルリポジトリからコピー..."
  cp -r /home/user/codings/dual-mode-claude-ui/. "$APP_DIR/"
  log "ローカルコピー完了"
else
  # Remote install
  info "リポジトリからクローン..."
  if git -C "$APP_DIR" rev-parse --git-dir &>/dev/null; then
    git -C "$APP_DIR" pull origin "$BRANCH" 2>&1 | tail -3
  else
    git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$APP_DIR" 2>&1 | tail -5
  fi
  log "リポジトリクローン完了"
fi

# ─── STEP 7: Environment Configuration ───────────────────────────────────────
step "環境設定の作成"
JWT_SECRET=$(openssl rand -hex 32)

cat > "${APP_DIR}/.env" << EOF
# Dual Mode Claude UI - Environment Configuration
# Generated by install-pct106.sh on $(date)

# Server
PORT=${APP_PORT}
NODE_ENV=production

# Authentication
JWT_SECRET=${JWT_SECRET}
UI_PASSWORD=${UI_PASSWORD}

# Claude CLI Auth (Pro → API Fallback)
# Primary: claude auth login (Pro subscription)
# Fallback: ANTHROPIC_API_KEY
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# PCT 100 Orchestration (Bushidan Multi-Agent)
ORCHESTRATION_HOST=${ORCH_HOST}
ORCHESTRATION_PORT=${ORCH_PORT}
ORCHESTRATION_PASSWORD=${ORCH_PASSWORD}

# Features
ENABLE_SHELL=true
ENABLE_FILE_EXPLORER=true
EOF

log ".env 作成完了"

# ─── STEP 8: Install Dependencies & Build ─────────────────────────────────────
step "Node.js 依存関係のインストール & ビルド"
cd "$APP_DIR"

# Install with node-pty for shell support
npm install --omit=dev 2>&1 | tail -5

# Try to build (optional - graceful degrade if no devDependencies)
if npm list vite &>/dev/null 2>&1; then
  npm run build 2>&1 | tail -10
  log "フロントエンドビルド完了"
else
  npm install 2>&1 | tail -5
  npm run build 2>&1 | tail -10
  log "依存関係フルインストール & ビルド完了"
fi

# node-pty requires native build
if ! npm ls node-pty &>/dev/null 2>&1; then
  warn "node-pty ビルド試行中..."
  npm install node-pty --save 2>&1 | tail -5 || warn "node-pty 失敗 (PTY/シェル機能は無効)"
fi

# ─── STEP 9: Permissions ─────────────────────────────────────────────────────
step "パーミッション設定"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "$APP_DIR"
chmod -R 755 "$APP_DIR"
chmod 600 "${APP_DIR}/.env"
log "パーミッション設定完了"

# ─── STEP 10: Systemd Service ─────────────────────────────────────────────────
step "Systemd サービスの設定"

cat > /etc/systemd/system/dual-claude-ui.service << EOF
[Unit]
Description=Dual Mode Claude UI (Claude Code + 武士団 Orchestration)
Documentation=https://github.com/98kuwa036/codings
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/node ${APP_DIR}/server/index.js
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dual-claude-ui

# Security
NoNewPrivileges=true
PrivateTmp=true

# Claude CLI PATH
Environment=PATH=/usr/local/bin:/usr/bin:/bin:/home/${SERVICE_USER}/.npm-global/bin
Environment=HOME=/home/${SERVICE_USER}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dual-claude-ui.service
systemctl restart dual-claude-ui.service
sleep 3

if systemctl is-active --quiet dual-claude-ui.service; then
  log "サービス起動成功"
else
  warn "サービスの起動を確認: journalctl -u dual-claude-ui -n 30"
fi

# ─── STEP 11: Firewall (optional) ────────────────────────────────────────────
step "ファイアウォール設定 (オプション)"
if command -v ufw &>/dev/null; then
  ufw allow "${APP_PORT}/tcp" comment "Dual Claude UI" &>/dev/null || true
  log "UFW: ポート ${APP_PORT} を開放"
elif command -v iptables &>/dev/null; then
  iptables -I INPUT -p tcp --dport "${APP_PORT}" -j ACCEPT 2>/dev/null || true
  log "iptables: ポート ${APP_PORT} を開放"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║              インストール完了！                      ║"
echo "╠══════════════════════════════════════════════════════╣"
printf "║  UI URL:   %-42s║\n" "http://${LOCAL_IP}:${APP_PORT}"
printf "║  モード1:  %-42s║\n" "Claude Code (claude CLI)"
printf "║  モード2:  %-42s║\n" "武士団 → PCT 100 (${ORCH_HOST}:${ORCH_PORT})"
printf "║  認証:     %-42s║\n" "${UI_PASSWORD:-(なし)}"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  次のステップ:                                       ║"
echo "║  1. Claude Pro認証: sudo -u ${SERVICE_USER} claude auth login"
echo "║  2. ブラウザで上記URLにアクセス                     ║"
echo "║  3. モードを切り替えて使用開始                       ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  管理コマンド:                                       ║"
echo "║  systemctl status dual-claude-ui                    ║"
echo "║  journalctl -u dual-claude-ui -f                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Pro auth reminder
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
  echo -e "${YELLOW}[!] 警告: APIキーが設定されていません。${NC}"
  echo -e "    Claude Pro認証を必ず実行してください:"
  echo -e "    ${BOLD}sudo -u ${SERVICE_USER} claude auth login${NC}"
  echo ""
fi
