# CUPS Integration - Maintenance & Update Tracking

このドキュメントでは、CUPS統合の依存関係更新の追跡とメンテナンス方法を説明します。

## 自動更新追跡システム

### 1. Dependabot（自動依存関係更新）

**設定ファイル:** `.github/dependabot.yml`

**機能:**
- 毎週月曜日にpyippライブラリの更新をチェック
- 新バージョンが利用可能な場合、自動的にPull Requestを作成
- GitHub Actionsの更新も毎月チェック

**確認方法:**
1. GitHubリポジトリの「Pull requests」タブを確認
2. `dependencies`ラベルが付いたPRを探す
3. PRの内容を確認して、変更ログを読む

**更新プロセス:**
```bash
# 1. Dependabotが作成したPRを確認
# 2. GitHub Actionsのテストが全て成功していることを確認
# 3. PRをマージ
# 4. 統合をテスト環境で検証
# 5. 問題なければプロダクション環境にデプロイ
```

### 2. GitHub Actions（互換性テスト）

**ワークフローファイル:** `.github/workflows/cups-integration-test.yml`

**実行タイミング:**
- コードがpushされた時
- Pull Requestが作成された時
- 毎週月曜日深夜0時（UTC）
- 手動トリガー可能

**テスト内容:**
1. **pyipp互換性テスト**
   - 現在のバージョン（0.9.0以上）でのテスト
   - 最新バージョンでのテスト
   - Python 3.11と3.12の両方でテスト

2. **CUPS/OpenPrinting更新チェック**
   - OpenPrinting CUPSの最新リリースを確認
   - pyippの最新リリースを確認
   - 現在のバージョンと比較

3. **コード品質チェック**
   - 構文チェック
   - Linting（ruff）
   - フォーマットチェック（black）
   - インポートソート（isort）

**結果の確認:**
1. GitHubリポジトリの「Actions」タブを開く
2. 最新のワークフロー実行を確認
3. テストサマリーで最新バージョン情報を確認

### 3. 手動更新チェック

#### pyippライブラリの更新確認

**公式リポジトリ:** https://github.com/ctalkington/python-ipp

**確認手順:**
```bash
# 最新バージョンを確認
pip index versions pyipp

# または
curl -s https://pypi.org/pypi/pyipp/json | jq -r '.info.version'
```

**更新方法:**
1. `custom_components/cups/requirements.txt`を更新
2. `custom_components/cups/manifest.json`の`requirements`を更新
3. 統合をテストして互換性を確認
4. バージョン番号を更新（例: 1.1.0 → 1.1.1）

#### CUPS/OpenPrinting更新の確認

**監視対象リポジトリ:**
- **CUPS 3.x:** https://github.com/OpenPrinting/cups
- **libcups:** https://github.com/OpenPrinting/libcups
- **cups-filters:** https://github.com/OpenPrinting/cups-filters
- **IPP仕様:** https://www.pwg.org/ipp/

**リリースノートの確認:**
```bash
# CUPS最新リリースを確認
curl -s https://api.github.com/repos/OpenPrinting/cups/releases/latest | jq -r '.tag_name'

# リリースノートを表示
curl -s https://api.github.com/repos/OpenPrinting/cups/releases/latest | jq -r '.body'
```

**重要な変更点:**
- IPP操作の変更（新規オペレーションコード）
- 属性の追加・非推奨化
- セキュリティ更新
- プロトコルバージョンの変更

## 更新の影響範囲

### pyipp更新時の影響

**影響を受けるファイル:**
- `__init__.py` - IPPクライアントの初期化
- `sensor.py` - プリンター情報の取得
- `binary_sensor.py` - 接続状態の監視

**確認ポイント:**
- `IPP`クラスのAPI変更
- `printer()`メソッドの戻り値構造
- エラーハンドリングの変更

### CUPS 3.x更新時の影響

**影響を受けるファイル:**
- `ipp_operations.py` - IPP操作の実装
- `const.py` - 定数定義

**確認ポイント:**
- 新規IPP操作の追加
- 既存操作の変更・非推奨化
- 属性タグの変更
- ステータスコードの追加

## 互換性マトリックス

| CUPS統合バージョン | pyipp | CUPS | Python | Home Assistant |
|-------------------|-------|------|--------|----------------|
| 1.1.0             | >=0.9.0 | 2.x/3.x | 3.11+ | 2023.1+ |
| 1.0.0             | >=0.9.0 | 2.x/3.x | 3.11+ | 2023.1+ |

## トラブルシューティング

### pyipp更新後の問題

**症状:** プリンター情報が取得できない

**対処法:**
```python
# pyippのAPIが変更されていないか確認
import pyipp
help(pyipp.IPP)

# プリンター情報の構造を確認
printer = await ipp.printer()
print(vars(printer))
```

### CUPS 3.x新機能への対応

**新しいIPP操作を追加する場合:**

1. `const.py`に操作コードを定義:
```python
IPP_OP_NEW_OPERATION = 0x00XX  # 新しい操作コード
```

2. `ipp_operations.py`にメソッドを実装:
```python
async def new_operation(self, ...):
    """新しい操作の説明."""
    attributes = {...}
    await self._send_ipp_request(IPP_OP_NEW_OPERATION, attributes)
```

3. `services.yaml`にサービスを定義

4. `__init__.py`にサービスハンドラーを追加

## モニタリングダッシュボード

### GitHub Actionsバッジ

READMEに追加する推奨バッジ:

```markdown
[![CUPS Integration Tests](https://github.com/98kuwa036/codings/actions/workflows/cups-integration-test.yml/badge.svg)](https://github.com/98kuwa036/codings/actions/workflows/cups-integration-test.yml)
[![Dependency Status](https://img.shields.io/librariesio/github/98kuwa036/codings)](https://libraries.io/github/98kuwa036/codings)
```

### 通知設定

**GitHub通知:**
1. リポジトリの「Watch」→「Custom」を選択
2. 以下を有効化:
   - Pull requests
   - Issues
   - Releases
   - Discussions

**メール通知:**
- Dependabot PRが作成された時
- GitHub Actionsが失敗した時
- 新しいリリースがある時

## 定期メンテナンスチェックリスト

### 毎週（自動）
- ✅ Dependabotが依存関係をチェック
- ✅ GitHub Actionsが互換性テストを実行

### 毎月（手動推奨）
- [ ] OpenPrinting CUPSのリリースノートを確認
- [ ] pyippのchangelogを確認
- [ ] IPP仕様の更新を確認
- [ ] セキュリティアドバイザリを確認

### 四半期毎（手動推奨）
- [ ] 統合の全機能を実際のプリンターでテスト
- [ ] ドキュメントの更新
- [ ] ユーザーフィードバックの確認
- [ ] パフォーマンスの測定

## リソース

### 公式ドキュメント
- [CUPS 3.0 Documentation](https://openprinting.github.io/cups/)
- [IPP Specification (RFC 8011)](https://tools.ietf.org/html/rfc8011)
- [pyipp Documentation](https://python-ipp.readthedocs.io/)
- [PWG IPP Workgroup](https://www.pwg.org/ipp/)

### コミュニティ
- [OpenPrinting Mailing List](https://lists.linuxfoundation.org/mailman/listinfo/printing-architecture)
- [Home Assistant Community](https://community.home-assistant.io/)

### セキュリティ
- [CUPS Security Advisories](https://github.com/OpenPrinting/cups/security/advisories)
- [GitHub Security Advisories](https://github.com/98kuwa036/codings/security/advisories)

## 貢献

更新や改善を見つけた場合:

1. Issueを作成して議論
2. ブランチを作成して変更
3. テストを追加/更新
4. Pull Requestを作成
5. GitHub Actionsのテストが通ることを確認
6. レビュー後にマージ

---

**最終更新:** 2024-12-09
**バージョン:** 1.1.0
