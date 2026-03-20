#!/bin/bash
# ============================================================
# Proxmox ホストから PCT 106 へのデプロイスクリプト
# Proxmox ホスト上で実行してください (root)
# ============================================================
# 使い方:
#   bash proxmox-deploy.sh [PCT_ID] [OPTIONS]
#
# 例:
#   bash proxmox-deploy.sh 106
#   bash proxmox-deploy.sh 106 --port 4000 --api-key sk-ant-xxx
# ============================================================

set -euo pipefail

PCT_ID=${1:-106}
shift 2>/dev/null || true

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${CYAN}[i]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }

echo -e "${BOLD}${CYAN}"
echo "┌─────────────────────────────────────────────────┐"
echo "│  Proxmox → PCT ${PCT_ID} デプロイ               │"
echo "│  Dual Mode Claude UI インストーラー             │"
echo "└─────────────────────────────────────────────────┘"
echo -e "${NC}"

# ─── PCT 106 の確認 ───────────────────────────────────────
info "PCT ${PCT_ID} の状態確認..."
if ! pct status "${PCT_ID}" &>/dev/null; then
  echo "エラー: PCT ${PCT_ID} が見つかりません"
  exit 1
fi

STATUS=$(pct status "${PCT_ID}" | awk '{print $2}')
if [[ "$STATUS" != "running" ]]; then
  info "PCT ${PCT_ID} を起動中..."
  pct start "${PCT_ID}"
  sleep 5
fi
log "PCT ${PCT_ID} は実行中"

# ─── インストールスクリプトをコピー ──────────────────────
info "インストールスクリプトを PCT ${PCT_ID} に転送..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Push the entire dual-mode-claude-ui directory into the container
pct push "${PCT_ID}" "${SCRIPT_DIR}/install-pct106.sh" /tmp/install-dual-claude-ui.sh

log "転送完了"

# ─── PCT 106 内でインストール実行 ─────────────────────────
info "PCT ${PCT_ID} でインストールを実行中..."
echo ""
warn "インタラクティブなステップがある場合はプロンプトが表示されます"
echo ""

pct exec "${PCT_ID}" -- bash /tmp/install-dual-claude-ui.sh "$@"

# ─── 結果確認 ─────────────────────────────────────────────
echo ""
info "PCT ${PCT_ID} のサービス状態確認..."
pct exec "${PCT_ID}" -- systemctl status dual-claude-ui --no-pager -l | head -20

# PCT の IP 取得
PCT_IP=$(pct exec "${PCT_ID}" -- hostname -I 2>/dev/null | awk '{print $1}')
if [[ -n "$PCT_IP" ]]; then
  echo ""
  log "デプロイ完了!"
  echo -e "${BOLD}アクセス URL: http://${PCT_IP}:4000${NC}"
fi
