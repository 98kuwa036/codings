# デプロイメントガイド

## 概要

このPWAアプリケーションは、既存のGASアプリをオフライン対応にするための完全なフレームワークを提供します。

## 実装済みコンポーネント

### ✅ コア機能

1. **IndexedDB管理** (`shared/js/offline-db.js`)
   - データの永続化
   - オフライン同期キュー管理
   - マスターデータキャッシュ

2. **ネットワーク状態監視** (`shared/js/network-status.js`)
   - オンライン/オフライン検知
   - 自動同期トリガー
   - ユーザーへの状態通知

3. **データ同期** (`shared/js/sync-manager.js`)
   - Last-Write-Wins戦略
   - 自動リトライ
   - エラーハンドリング

4. **Service Worker** (`intake-delivery/sw.js`, `login/sw.js`)
   - リソースキャッシュ
   - オフラインフォールバック
   - バックグラウンド同期

5. **OCRヘルパー** (`shared/js/ocr-helper.js`)
   - Tesseract.js統合
   - オンライン/オフライン自動切り替え
   - 進捗通知

### 📋 必要な追加実装

既存のGASアプリケーションをPWA化するには、以下のステップが必要です：

## ステップ1: HTML/CSS/JSの移植

### 入出庫記録アプリ

```bash
# 既存ファイルから必要なコードを抽出
/home/user/codings/Intake-delivery-record/PageVersion.html
→ /home/user/codings/pwa-warehouse-app/intake-delivery/index.html

# JavaScript分割
/home/user/codings/Intake-delivery-record/JavaScript_*.html
→ /home/user/codings/pwa-warehouse-app/intake-delivery/js/
```

**必要な変更**:
1. GASテンプレート構文 (`<?= ... ?>`) を削除
2. `google.script.run` 呼び出しをオフライン対応版に置き換え
3. Service Worker登録コード追加
4. 共有モジュールのインポート

### ログインアプリ

```bash
/home/user/codings/loginform/index.html
→ /home/user/codings/pwa-warehouse-app/login/index.html
```

## ステップ2: GAS統合

### 既存GAS関数をAPI化

```javascript
// Code.gs の例
function doPost(e) {
  const action = e.parameter.action;

  switch(action) {
    case 'login':
      return loginUser(e.parameter);
    case 'register':
      return registerRecord(e.parameter);
    case 'sync':
      return syncData(e.parameter);
    default:
      return ContentService.createTextOutput(
        JSON.stringify({ error: 'Unknown action' })
      ).setMimeType(ContentService.MimeType.JSON);
  }
}
```

### クライアント側の実装

```javascript
// pwa-warehouse-app/shared/js/gas-adapter.js を作成

class GASAdapter {
  constructor(scriptUrl) {
    this.scriptUrl = scriptUrl;
  }

  async call(functionName, ...args) {
    if (typeof google !== 'undefined' && google.script && google.script.run) {
      // GAS環境内
      return new Promise((resolve, reject) => {
        google.script.run
          .withSuccessHandler(resolve)
          .withFailureHandler(reject)
          [functionName](...args);
      });
    } else {
      // スタンドアロン環境
      const response = await fetch(this.scriptUrl, {
        method: 'POST',
        body: new FormData(Object.assign({
          action: functionName,
          args: JSON.stringify(args)
        }))
      });
      return response.json();
    }
  }
}

const gasAdapter = new GASAdapter('YOUR_GAS_URL_HERE');
```

## ステップ3: オフライン対応の実装

### データ保存

```javascript
// 入出庫記録の保存
async function saveRecord(record) {
  // 1. IndexedDBに保存
  const localId = await offlineDB.addRecord(record);

  // 2. オンラインなら即座に同期
  if (navigator.onLine) {
    try {
      await syncManager.syncRecord({ ...record, id: localId });
    } catch (error) {
      console.log('Sync failed, will retry later:', error);
    }
  }

  return localId;
}
```

### マスターデータ取得

```javascript
// 品目リストの取得
async function getItemList() {
  // 1. まずキャッシュから取得
  let items = await offlineDB.getMasterData('items');

  // 2. オンラインなら更新を試みる
  if (navigator.onLine) {
    try {
      items = await syncManager.syncMasterData('items');
    } catch (error) {
      console.log('Using cached data:', error);
    }
  }

  return items || [];
}
```

## ステップ4: Service Worker登録

各HTMLファイルに以下を追加：

```html
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/intake-delivery/sw.js')
      .then(registration => {
        console.log('SW registered:', registration);
      })
      .catch(error => {
        console.log('SW registration failed:', error);
      });
  });
}
</script>
```

## ステップ5: Tesseract.js統合

### CDNからの読み込み

```html
<!-- Tesseract.js for offline OCR -->
<script src="https://cdn.jsdelivr.net/npm/tesseract.js@4/dist/tesseract.min.js"></script>
```

### OCR実行

```javascript
async function performOCR(imageFile) {
  try {
    const result = await ocrManager.performOCR(imageFile, {
      visionApiAvailable: typeof google !== 'undefined',
      progressCallback: (status) => {
        console.log('OCR Status:', status);
        updateUIWithStatus(status);
      }
    });

    return result.text;
  } catch (error) {
    if (!navigator.onLine) {
      alert('OCR機能はオフラインでは使用できません。オンライン接続後に再試行してください。');
    }
    throw error;
  }
}
```

## ステップ6: manifestファイルの設定

各アプリの `manifest.json` を更新：

```json
{
  "start_url": "/intake-delivery/index.html?pwa=true",
  "scope": "/intake-delivery/",
  "icons": [
    {
      "src": "../shared/icons/warehouse-icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "../shared/icons/warehouse-icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

## ステップ7: アイコン生成

SVGからPNGアイコンを生成：

```bash
# ImageMagick使用例
convert -background none -resize 192x192 \
  shared/icons/warehouse-icon.svg \
  shared/icons/warehouse-icon-192.png

convert -background none -resize 512x512 \
  shared/icons/warehouse-icon.svg \
  shared/icons/warehouse-icon-512.png
```

## ステップ8: デプロイ

### ローカルテスト

```bash
# 簡易HTTPサーバー起動
cd /home/user/codings/pwa-warehouse-app
python3 -m http.server 8000

# ブラウザでアクセス
# http://localhost:8000/intake-delivery/
# http://localhost:8000/login/
```

### 本番デプロイ

1. **GAS Webアプリとして公開**:
   - GASプロジェクトに全ファイルをアップロード
   - 「ウェブアプリケーションとして導入」
   - アクセス権限を設定

2. **外部Webサーバー使用**:
   - GitHub Pages、Firebase Hosting、Netlifyなど
   - HTTPS必須（PWA要件）
   - GAS APIエンドポイントを設定

## トラブルシューティング

### Service Workerが動作しない

- HTTPSでアクセスしているか確認
- スコープが正しく設定されているか確認
- DevToolsでService Worker状態を確認

### データが同期されない

- ネットワーク接続を確認
- GAS APIエンドポイントが正しいか確認
- CORS設定を確認（外部サーバー使用時）

### OCRが動作しない

- Tesseract.jsがロードされているか確認
- 画像フォーマットが対応しているか確認
- ファイルサイズを確認（10MB以下推奨）

## 完全実装の例

完全な実装例は以下のリポジトリを参照：

```
/home/user/codings/pwa-warehouse-app/examples/
```

（このディレクトリに完全実装のサンプルを配置予定）

## サポート

問題が発生した場合は、以下を確認してください：

1. ブラウザのコンソールログ
2. Service Workerのステータス
3. IndexedDBの内容
4. ネットワークリクエスト

詳細なデバッグ方法は `README.md` を参照してください。
