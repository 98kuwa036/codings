# Dual Mode Claude UI

**claudecodeui** にインスパイアされたデュアルモードWebUI。

## 2つのモード

### ⚡ Mode 1: Claude Code
- Claude CLI を介した直接会話
- Pro サブスクリプション優先 → Anthropic API Key フォールバック
- セッション履歴の継続
- PTY ターミナル (シェルアクセス)
- プロジェクト管理

### ⛩️ Mode 2: 武士団 オーケストレーション
- PCT 100 の [Bushidan Multi-Agent](https://github.com/98kuwa036/Bushidan-Multi-Agent) システムへの接続
- 10役職体制 (大元帥〜隠密) によるLLMルーティング
- LangGraph ワークフロー + HITL
- リアルタイム WebSocket 通信

## PCT 106 へのインストール

### Proxmox ホストから (推奨)
```bash
bash scripts/proxmox-deploy.sh 106 \
  --port 4000 \
  --api-key sk-ant-your-key \
  --orch-host 192.168.1.100
```

### PCT 106 内で直接
```bash
bash install-pct106.sh \
  --port 4000 \
  --orch-host 192.168.1.100 \
  --api-key sk-ant-your-key
```

### Claude Pro 認証 (後から実行)
```bash
sudo -u claude-ui bash /opt/dual-claude-ui/scripts/claude-auth-setup.sh
```

## 認証フォールバックシステム

```
Claude CLI 起動時
    ↓
Pro サブスクリプション認証 (claude auth login)
    ↓ 失敗
ANTHROPIC_API_KEY 環境変数
    ↓ 失敗
エラー表示 → 再認証案内
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `PORT` | サーバーポート | `4000` |
| `UI_PASSWORD` | UIパスワード (空=認証なし) | `` |
| `JWT_SECRET` | JWT署名キー | ランダム生成 |
| `ANTHROPIC_API_KEY` | APIキー (フォールバック) | `` |
| `ORCHESTRATION_HOST` | PCT 100 IPアドレス | `192.168.1.100` |
| `ORCHESTRATION_PORT` | Bushidan ポート | `8067` |
| `ORCHESTRATION_PASSWORD` | Bushidan パスワード | `` |

## 管理コマンド

```bash
systemctl status dual-claude-ui
systemctl restart dual-claude-ui
journalctl -u dual-claude-ui -f
```

## アーキテクチャ

```
Browser
  ├── /ws     → Mode 1: Claude CLI (stream-json)
  ├── /shell  → Mode 1: PTY Terminal (node-pty)
  └── /orch   → Mode 2: PCT 100 WebSocket Proxy
                   └── ws://pct100:8067/ws/chat (Bushidan)
```
