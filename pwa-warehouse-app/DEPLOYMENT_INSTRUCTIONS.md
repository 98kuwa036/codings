# デプロイメント手順

## 方法1: GitHub Pages（推奨・無料）

### 前提条件
- GitHubアカウント
- リポジトリが既にGitHubにプッシュ済み

### 手順

1. **GitHubリポジトリにアクセス**
   - https://github.com/98kuwa036/codings にアクセス

2. **Settings → Pages に移動**
   - リポジトリページの「Settings」タブをクリック
   - 左サイドバーの「Pages」をクリック

3. **GitHub Pagesを設定**
   - **Source**: `Deploy from a branch`
   - **Branch**: `main` を選択
   - **Folder**: `/ (root)` を選択
   - 「Save」をクリック

4. **デプロイ完了を待つ**
   - 数分後、ページ上部に以下のような通知が表示されます:
   ```
   Your site is live at https://98kuwa036.github.io/codings/
   ```

5. **アクセスURL**
   - ログイン: `https://98kuwa036.github.io/codings/pwa-warehouse-app/login/index.html`
   - 入出庫記録: `https://98kuwa036.github.io/codings/pwa-warehouse-app/intake-delivery/index.html`

---

## 方法2: Netlify（無料・高速）

### 手順

1. **Netlifyにアクセス**
   - https://www.netlify.com/ にアクセス
   - 「Sign up」でアカウント作成（GitHubアカウントで連携可能）

2. **新しいサイトを作成**
   - ダッシュボードで「Add new site」→「Import an existing project」をクリック
   - 「Deploy with GitHub」を選択
   - リポジトリ `98kuwa036/codings` を選択

3. **ビルド設定**
   - **Base directory**: `pwa-warehouse-app`
   - **Build command**: （空欄のまま）
   - **Publish directory**: `.`（またはそのまま）
   - 「Deploy site」をクリック

4. **カスタムドメイン設定（オプション）**
   - Site settings → Domain management
   - カスタムドメインを追加可能

5. **アクセスURL**
   - Netlifyが自動生成: `https://<random-name>.netlify.app/login/index.html`

---

## 方法3: Vercel（無料・高速）

### 手順

1. **Vercelにアクセス**
   - https://vercel.com/ にアクセス
   - GitHubアカウントでサインアップ

2. **新しいプロジェクトをインポート**
   - 「Add New」→「Project」をクリック
   - GitHubリポジトリ `codings` を選択

3. **設定**
   - **Framework Preset**: `Other`
   - **Root Directory**: `pwa-warehouse-app`
   - **Build Command**: （空欄）
   - **Output Directory**: `.`
   - 「Deploy」をクリック

4. **アクセスURL**
   - `https://<project-name>.vercel.app/login/index.html`

---

## 方法4: Google Cloud Storage（GCS）

GASと同じGoogle環境でホスティングしたい場合:

### 手順

1. **Google Cloud Consoleにアクセス**
   - https://console.cloud.google.com/

2. **バケットを作成**
   - Cloud Storage → Buckets → Create bucket
   - 名前: `pwa-warehouse-app`（グローバルでユニークな名前）
   - Location: `asia-northeast1`（東京）
   - Storage class: `Standard`
   - Access control: `Fine-grained`
   - 作成

3. **ファイルをアップロード**
   - バケット内で「Upload files」または「Upload folder」
   - `pwa-warehouse-app` フォルダ全体をアップロード

4. **公開設定**
   - バケット → Permissions → Add principal
   - **New principals**: `allUsers`
   - **Role**: `Storage Object Viewer`
   - Save

5. **ウェブサイト設定**
   - バケット → Edit website configuration
   - **Main page**: `login/index.html`
   - **404 page**: `login/index.html`
   - Save

6. **アクセスURL**
   ```
   https://storage.googleapis.com/<bucket-name>/login/index.html
   ```

---

## 方法5: Firebase Hosting（Google推奨）

### 前提条件
- Node.js インストール済み
- Firebase CLI インストール: `npm install -g firebase-tools`

### 手順

1. **Firebase CLIでログイン**
```bash
firebase login
```

2. **プロジェクトディレクトリで初期化**
```bash
cd C:\Users\OSAMU-KUWABARA\OneDrive\ドキュメント\GitHub\codings\pwa-warehouse-app
firebase init hosting
```

設定:
- **Use an existing project**: GASプロジェクトと同じFirebaseプロジェクトを選択
- **Public directory**: `.`（現在のディレクトリ）
- **Configure as SPA**: `No`
- **Set up automatic builds with GitHub**: `No`（手動デプロイの場合）

3. **デプロイ**
```bash
firebase deploy --only hosting
```

4. **アクセスURL**
```
https://<project-id>.web.app/login/index.html
https://<project-id>.firebaseapp.com/login/index.html
```

---

## 推奨デプロイ方法

### 開発・テスト環境
→ **GitHub Pages**（無料、簡単、リポジトリと統合）

### 本番環境
→ **Firebase Hosting**（Google環境統合、CDN、高速、SSL自動）

### 企業環境
→ **自社サーバー** または **Google Cloud Storage**

---

## デプロイ後の確認事項

✅ **HTTPSで動作すること**（PWA必須要件）
✅ **Service Workerが登録されること**
   - DevTools > Application > Service Workers で確認
✅ **manifest.jsonが正しく読み込まれること**
   - DevTools > Application > Manifest で確認
✅ **オフライン動作が可能なこと**
   - DevTools > Network > Offline でテスト
✅ **IndexedDBにデータが保存されること**
   - DevTools > Application > Storage > IndexedDB で確認
✅ **GAS APIとの通信が成功すること**
   - Console でエラーがないか確認

---

## トラブルシューティング

### 問題: CORSエラーが発生する

**GAS側の設定が必要です:**

GASスクリプト（Code.gs）に以下を追加:

```javascript
function doGet(e) {
  const output = HtmlService.createHtmlOutputFromFile('index');
  output.setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  return output;
}

function doPost(e) {
  // CORS対応
  const allowedOrigins = [
    'https://98kuwa036.github.io',
    'https://your-app.netlify.app',
    'https://your-app.vercel.app'
  ];

  // リクエストヘッダーから Origin を取得
  const origin = e.parameter.origin || '';

  // レスポンスヘッダーを設定
  const response = {
    success: true,
    data: {}
  };

  return ContentService
    .createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}
```

### 問題: Service Workerが登録されない

1. **HTTPS確認**: `https://` でアクセスしているか確認
2. **パス確認**: `sw.js` が正しいディレクトリにあるか確認
3. **Console確認**: エラーメッセージを確認

### 問題: PWAインストールバナーが表示されない

必要条件:
- ✅ HTTPS
- ✅ manifest.json
- ✅ Service Worker登録
- ✅ 192x192以上のアイコン
- ✅ start_url設定
- ✅ ユーザーが一定時間サイトを訪問

---

## 次のステップ

1. **デプロイ方法を選択**（推奨: GitHub Pages または Firebase）
2. **デプロイ実行**
3. **動作確認**
4. **ユーザーにURLを共有**

ご不明な点があれば、お気軽にお尋ねください！
