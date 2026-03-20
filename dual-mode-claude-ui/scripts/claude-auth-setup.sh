#!/bin/bash
# ============================================================
# Claude CLI 認証セットアップ
# PCT 106 内で実行 (claude-ui ユーザーとして)
# ============================================================
# Pro → API Key フォールバックシステムの設定
#
# 認証優先順位:
#   1. Claude Pro サブスクリプション (claude auth login)
#   2. Anthropic API Key (ANTHROPIC_API_KEY 環境変数)
# ============================================================

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${CYAN}[i]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }

APP_DIR="/opt/dual-claude-ui"
ENV_FILE="${APP_DIR}/.env"

echo -e "${BOLD}${CYAN}Claude CLI 認証セットアップ${NC}"
echo ""

# ─── Claude CLI 確認 ──────────────────────────────────────
if ! command -v claude &>/dev/null; then
  echo "エラー: Claude CLI が見つかりません"
  echo "インストール: npm install -g @anthropic-ai/claude-code"
  exit 1
fi

CLAUDE_VER=$(claude --version 2>/dev/null | head -1)
log "Claude CLI: ${CLAUDE_VER}"
echo ""

# ─── 現在の認証状態 ───────────────────────────────────────
info "現在の認証状態を確認中..."
AUTH_STATUS=$(claude auth status 2>&1 || echo "not_authenticated")

if echo "$AUTH_STATUS" | grep -qi "logged in\|authenticated\|@"; then
  log "Claude Pro 認証済み"
  PRO_AUTH=true
else
  warn "Claude Pro 未認証"
  PRO_AUTH=false
fi

# ─── API Key 確認 ─────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  API_KEY=$(grep "^ANTHROPIC_API_KEY=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "")
else
  API_KEY="${ANTHROPIC_API_KEY:-}"
fi

if [[ -n "$API_KEY" && "$API_KEY" != "sk-ant-your-key-here" ]]; then
  log "Anthropic API Key: 設定済み (${API_KEY:0:15}...)"
  API_KEY_SET=true
else
  warn "Anthropic API Key: 未設定"
  API_KEY_SET=false
fi

echo ""
echo "認証状態サマリー:"
echo "  Claude Pro:   ${PRO_AUTH}"
echo "  API Key:      ${API_KEY_SET}"
echo ""

# ─── Pro 認証フロー ───────────────────────────────────────
if [[ "$PRO_AUTH" == false ]]; then
  echo -e "${BOLD}Claude Pro 認証を行いますか？${NC}"
  echo ""
  echo "プロセス:"
  echo "  1. ブラウザが開きます (またはURLが表示されます)"
  echo "  2. Claude.ai にログイン"
  echo "  3. 認証コードを入力"
  echo ""
  read -rp "今すぐ認証しますか？ [y/N]: " DO_AUTH

  if [[ "${DO_AUTH,,}" == "y" ]]; then
    info "Claude Pro 認証を開始..."
    echo ""
    claude auth login
    echo ""

    # 再確認
    if claude auth status 2>&1 | grep -qi "logged in\|authenticated\|@"; then
      log "Claude Pro 認証成功！"
      PRO_AUTH=true
    else
      warn "認証を確認できません。API keyフォールバックを使用します"
    fi
  fi
fi

# ─── API Key セットアップ (フォールバック) ─────────────────
if [[ "$API_KEY_SET" == false ]]; then
  echo ""
  echo -e "${BOLD}Anthropic API Key の設定 (Pro認証失敗時のフォールバック)${NC}"
  echo "https://console.anthropic.com でAPIキーを取得できます"
  echo ""
  read -rp "API Key を入力 (スキップ: Enter): " NEW_API_KEY

  if [[ -n "$NEW_API_KEY" ]]; then
    if [[ -f "$ENV_FILE" ]]; then
      # Update existing .env
      if grep -q "^ANTHROPIC_API_KEY=" "$ENV_FILE"; then
        sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=${NEW_API_KEY}|" "$ENV_FILE"
      else
        echo "ANTHROPIC_API_KEY=${NEW_API_KEY}" >> "$ENV_FILE"
      fi
    fi
    log "API Key を保存しました"
    API_KEY_SET=true
  fi
fi

# ─── フォールバック設定確認 ───────────────────────────────
echo ""
if [[ "$PRO_AUTH" == true ]]; then
  log "✅ Claude Pro 認証 → 利用可能"
  if [[ "$API_KEY_SET" == true ]]; then
    log "✅ API Key フォールバック → 設定済み"
  else
    warn "⚠️ API Key フォールバック → 未設定 (Pro認証が失効したら利用不可)"
  fi
elif [[ "$API_KEY_SET" == true ]]; then
  warn "⚠️ Claude Pro → 未認証"
  log "✅ API Key フォールバック → 利用可能"
else
  echo ""
  echo -e "${YELLOW}警告: Claude の認証が設定されていません！${NC}"
  echo "Mode 1 (Claude Code) は機能しません。"
  echo ""
  echo "解決方法:"
  echo "  A. sudo -u claude-ui claude auth login  (Pro認証)"
  echo "  B. .env に ANTHROPIC_API_KEY=sk-ant-xxx を設定"
fi

# ─── サービス再起動 ───────────────────────────────────────
if systemctl is-active --quiet dual-claude-ui.service 2>/dev/null; then
  info "サービスを再起動中..."
  systemctl restart dual-claude-ui.service
  log "サービス再起動完了"
fi

echo ""
log "認証セットアップ完了"
