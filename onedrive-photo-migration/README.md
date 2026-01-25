# OneDrive Photo Migration Tool

Microsoft OneDrive上でGoogle Photos Takeoutの写真メタデータを修復し、整理されたフォルダ構造で保存するツールです。GitHub Actions上で完全に動作します。

## 機能

- OneDriveのフォルダA（ソース）から画像/動画ファイルを読み込み
- Google Photos TakeoutのJSONメタデータファイルから撮影日時を抽出
- EXIFメタデータの修復・書き込み
- 撮影日時に基づいた `YYYY/YYYY-MM` フォルダ構造で整理
- 重複ファイルの検出と隔離
- フォルダB（出力先）への自動アップロード
- 処理レポートの自動生成

## メタデータソースの優先順位

1. **Internal EXIF** - ファイル内蔵のEXIF情報（最優先）
2. **JSON** - Google Photos TakeoutのJSONメタデータ
3. **Filename** - ファイル名から日付パターンを抽出
4. **OneDrive LastModified** - OneDriveの更新日時（フォールバック）

## セットアップ手順

### 1. Azure ADアプリケーション登録

Microsoft Graph APIを使用するため、Azure ADでアプリケーションを登録する必要があります。

#### 1.1 Azureポータルでアプリ登録

1. [Azure Portal](https://portal.azure.com) にログイン
2. **Azure Active Directory** → **アプリの登録** → **新規登録**
3. 以下を入力:
   - **名前**: `OneDrive Photo Migration`（任意）
   - **サポートされているアカウントの種類**: 「この組織ディレクトリのみに含まれるアカウント」
   - **リダイレクトURI**: 空欄のまま
4. **登録** をクリック

#### 1.2 アプリケーションID（Client ID）の取得

登録後の「概要」ページで以下をメモ:
- **アプリケーション（クライアント）ID** → `AZURE_CLIENT_ID`
- **ディレクトリ（テナント）ID** → `AZURE_TENANT_ID`

#### 1.3 クライアントシークレットの作成

1. **証明書とシークレット** → **新しいクライアントシークレット**
2. **説明**: `GitHub Actions`（任意）
3. **有効期限**: 推奨は24ヶ月
4. **追加** をクリック
5. **値** をコピー（この画面を離れると二度と表示されません）→ `AZURE_CLIENT_SECRET`

#### 1.4 APIアクセス許可の設定

1. **APIのアクセス許可** → **アクセス許可の追加**
2. **Microsoft Graph** → **アプリケーションの許可**
3. 以下の権限を追加:
   - `Files.ReadWrite.All` - ファイルの読み書き
   - `User.Read.All` - ユーザー情報の読み取り（オプション）
4. **アクセス許可の追加** をクリック
5. **[テナント名]に管理者の同意を与えます** をクリック

> **注意**: 管理者の同意が必要です。組織のIT管理者に依頼してください。

### 2. GitHub Secretsの設定

リポジトリの Settings → Secrets and variables → Actions で以下を追加:

| Secret名 | 値 |
|----------|-----|
| `AZURE_CLIENT_ID` | アプリケーション（クライアント）ID |
| `AZURE_CLIENT_SECRET` | クライアントシークレットの値 |
| `AZURE_TENANT_ID` | ディレクトリ（テナント）ID |

### 3. OneDriveフォルダの準備

1. OneDriveにソースフォルダを作成（例: `Photos/Google Takeout`）
2. Google Takeoutからエクスポートしたファイルをアップロード
   - 画像/動画ファイル
   - 対応するJSONメタデータファイル
3. 出力先フォルダは自動作成されます（例: `Photos/Processed`）

## 使用方法

### GitHub Actionsで実行

1. リポジトリの **Actions** タブを開く
2. **OneDrive Photo Migration** ワークフローを選択
3. **Run workflow** をクリック
4. パラメータを入力:
   - **Source folder path**: ソースフォルダのパス（例: `Photos/Google Takeout`）
   - **Destination folder path**: 出力先フォルダのパス（例: `Photos/Processed`）
   - **Timezone offset**: タイムゾーン（日本は `9`）
   - **Create XMP sidecar files**: XMPファイルを作成するか
   - **Dry run**: テスト実行（ファイルリストのみ表示）
5. **Run workflow** をクリック

### ローカルで実行（テスト用）

```bash
# 依存関係のインストール
pip install -r requirements.txt

# ExifToolのインストール（Ubuntu/Debian）
sudo apt-get install exiftool

# 実行
python onedrive_photo_fixer.py \
  --client-id "YOUR_CLIENT_ID" \
  --client-secret "YOUR_CLIENT_SECRET" \
  --tenant-id "YOUR_TENANT_ID" \
  --src-folder "Photos/Google Takeout" \
  --dst-folder "Photos/Processed" \
  --timezone 9

# ドライラン（ファイルリストのみ表示）
python onedrive_photo_fixer.py \
  --client-id "YOUR_CLIENT_ID" \
  --client-secret "YOUR_CLIENT_SECRET" \
  --tenant-id "YOUR_TENANT_ID" \
  --src-folder "Photos/Google Takeout" \
  --dry-run
```

### 環境変数での設定

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
export ONEDRIVE_SRC_FOLDER="Photos/Google Takeout"
export ONEDRIVE_DST_FOLDER="Photos/Processed"
export TZ_OFFSET="9"

python onedrive_photo_fixer.py
```

## 対応ファイル形式

### 画像
- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)
- TIFF (.tiff, .tif)
- HEIC/HEIF (.heic, .heif)
- AVIF (.avif)

### RAW
- DNG (.dng)
- Canon CR2 (.cr2)
- Nikon NEF (.nef)
- Sony ARW (.arw)
- Fujifilm RAF (.raf)
- その他

### 動画
- MP4 (.mp4)
- MOV (.mov)
- AVI (.avi)
- MKV (.mkv)
- その他

## 出力構造

処理後のファイルは以下の構造で保存されます:

```
Photos/Processed/
├── 2023/
│   ├── 2023-01/
│   │   ├── IMG_0001.jpg
│   │   └── IMG_0001.jpg.xmp  (オプション)
│   ├── 2023-02/
│   └── ...
├── 2024/
│   └── ...
├── duplicates/
│   └── (重複ファイル)
└── migration_report.json
```

## 処理レポート

`migration_report.json` には以下の情報が含まれます:

```json
{
  "summary": {
    "total_files": 1000,
    "processed_success": 950,
    "duplicates_isolated": 30,
    "errors": 20,
    "duration_seconds": 3600
  },
  "metadata_source": {
    "Internal_Exif": 500,
    "JSON": 400,
    "Filename": 40,
    "OneDrive_LastModified": 10
  },
  "file_types": {
    ".jpg": 800,
    ".mp4": 150,
    ".png": 50
  }
}
```

## トラブルシューティング

### 認証エラー

```
Failed to acquire token: AADSTS7000215: Invalid client secret provided
```
→ クライアントシークレットが正しいか確認。期限切れの可能性もあります。

### アクセス許可エラー

```
403 Forbidden: Insufficient privileges
```
→ Azure ADで `Files.ReadWrite.All` の管理者同意が付与されているか確認。

### フォルダが見つからない

```
Folder not found: Photos/Google Takeout
```
→ OneDriveのフォルダパスが正しいか確認。大文字/小文字は区別されます。

### ExifToolエラー

```
ExifTool not found in PATH
```
→ GitHub Actionsでは自動インストールされます。ローカル実行時は `apt-get install exiftool` を実行。

## 制限事項

- **ファイルサイズ**: 単一ファイル最大250GB（OneDrive制限）
- **API制限**: Microsoft Graph APIには使用量制限があります
- **実行時間**: GitHub Actionsは最大6時間（大量ファイルは分割処理を推奨）
- **スレッド数**: API制限を避けるためデフォルトは1スレッド

## セキュリティ

- クライアントシークレットはGitHub Secretsで安全に管理
- 最小権限の原則に従い、必要な権限のみ付与
- 定期的なシークレットのローテーションを推奨

## ライセンス

MIT License

## 関連リンク

- [Microsoft Graph API ドキュメント](https://docs.microsoft.com/graph/)
- [Azure AD アプリ登録](https://docs.microsoft.com/azure/active-directory/develop/quickstart-register-app)
- [ExifTool](https://exiftool.org/)
- [Google Takeout](https://takeout.google.com/)
