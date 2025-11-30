# 実装ガイド - 完全版PWA化手順

## 目次

1. [概要](#概要)
2. [既存コードの準備](#既存コードの準備)
3. [PWA化の実装](#pwa化の実装)
4. [テストとデバッグ](#テストとデバッグ)
5. [チェックリスト](#チェックリスト)

## 概要

このガイドでは、既存のGASアプリケーション（intake-delivery-recordとloginform）を完全にPWA化する手順を説明します。

## 既存コードの準備

### 1. 既存ファイルのバックアップ

```bash
# 既存のGASプロジェクトファイルをバックアップ
cp -r /home/user/codings/Intake-delivery-record /home/user/codings/Intake-delivery-record.backup
cp -r /home/user/codings/loginform /home/user/codings/loginform.backup
```

### 2. PWAプロジェクトへのコピー

すでに準備されているPWAフレームワークに既存コードを統合します：

```bash
PWA_DIR="/home/user/codings/pwa-warehouse-app"
```

## PWA化の実装

### Phase 1: ログインアプリのPWA化

#### 1.1 HTMLの作成

`/home/user/codings/pwa-warehouse-app/login/index.html` を作成：

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#2563eb">
  <title>倉庫管理 - ログイン</title>

  <!-- PWA Manifest -->
  <link rel="manifest" href="manifest.json">

  <!-- スタイルシート -->
  <link rel="stylesheet" href="css/styles.css">

  <!-- アイコン -->
  <link rel="icon" type="image/svg+xml" href="../shared/icons/warehouse-icon.svg">
</head>
<body>
  <!-- ログインフォームをここに配置 -->
  <!-- 既存のloginform/index.htmlからコピー -->

  <!-- 共有モジュール -->
  <script src="../shared/js/offline-db.js"></script>
  <script src="../shared/js/network-status.js"></script>

  <!-- アプリケーションロジック -->
  <script src="js/app.js"></script>

  <!-- Service Worker登録 -->
  <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', async () => {
        try {
          const registration = await navigator.serviceWorker.register('sw.js');
          console.log('Service Worker registered:', registration.scope);
        } catch (error) {
          console.error('Service Worker registration failed:', error);
        }
      });
    }
  </script>
</body>
</html>
```

#### 1.2 アプリケーションロジックの実装

`/home/user/codings/pwa-warehouse-app/login/js/app.js` を作成：

```javascript
// 既存のloginform/JavaScript.htmlの内容をコピーし、以下を変更：

// 1. GAS依存の削除
// Before:
// google.script.run.withSuccessHandler(...).checkLogin(...)

// After:
async function performLogin(id, password) {
  try {
    if (navigator.onLine) {
      // オンライン: サーバーに認証リクエスト
      const response = await fetch(GAS_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'login', id, password })
      });
      const result = await response.json();

      if (result.success) {
        // 認証情報をIndexedDBに保存
        await offlineDB.saveUser({
          id: result.userId,
          loginId: id,
          name: result.name,
          lastLogin: Date.now()
        });
      }

      return result;
    } else {
      // オフライン: キャッシュされた認証情報で確認
      const user = await offlineDB.getUserByLoginId(id);

      if (user) {
        return {
          success: true,
          message: 'オフラインログイン（キャッシュ）',
          userId: user.id,
          name: user.name
        };
      } else {
        return {
          success: false,
          message: 'オフラインでは初回ログインできません'
        };
      }
    }
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

// 2. データベース初期化
document.addEventListener('DOMContentLoaded', async () => {
  try {
    await offlineDB.init();
    console.log('Database initialized');

    // 既存の初期化処理を実行
    initializeEventListeners();
    updateUILanguage();
  } catch (error) {
    console.error('Initialization error:', error);
    alert('アプリケーションの初期化に失敗しました');
  }
});
```

### Phase 2: 入出庫記録アプリのPWA化

#### 2.1 HTMLの統合

`/home/user/codings/pwa-warehouse-app/intake-delivery/index.html` を作成：

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#2563eb">
  <title>入出庫記録ツール</title>

  <!-- PWA Manifest -->
  <link rel="manifest" href="manifest.json">

  <!-- スタイル（既存のPageVersion.htmlから抽出） -->
  <style>
    /* 既存のスタイルをここにコピー */
  </style>
</head>
<body>
  <!-- 既存のUIをここにコピー -->

  <!-- 共有モジュール -->
  <script src="../shared/js/offline-db.js"></script>
  <script src="../shared/js/network-status.js"></script>
  <script src="../shared/js/sync-manager.js"></script>
  <script src="../shared/js/ocr-helper.js"></script>

  <!-- Tesseract.js for Offline OCR -->
  <script src="https://cdn.jsdelivr.net/npm/tesseract.js@4/dist/tesseract.min.js"></script>

  <!-- アプリケーションロジック -->
  <script src="js/app.js"></script>
  <script src="js/ui.js"></script>
  <script src="js/api.js"></script>

  <!-- Service Worker登録 -->
  <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', async () => {
        try {
          const registration = await navigator.serviceWorker.register('sw.js');
          console.log('Service Worker registered:', registration.scope);
        } catch (error) {
          console.error('Service Worker registration failed:', error);
        }
      });
    }
  </script>
</body>
</html>
```

#### 2.2 データ保存とロード

`/home/user/codings/pwa-warehouse-app/intake-delivery/js/api.js`:

```javascript
// GASアダプター
class IntakeDeliveryAPI {
  constructor(gasUrl) {
    this.gasUrl = gasUrl;
  }

  async registerRecord(record) {
    // 1. ローカルに保存
    const localId = await offlineDB.addRecord({
      ...record,
      timestamp: Date.now(),
      synced: false
    });

    // 2. オンラインなら即座に同期
    if (navigator.onLine) {
      try {
        const result = await this.syncToServer(record);

        if (result.success) {
          await offlineDB.markAsSynced(localId, result.serverId);
        }

        return { success: true, localId, serverId: result.serverId };
      } catch (error) {
        console.log('Sync failed, will retry later:', error);
        return { success: true, localId, pending: true };
      }
    }

    return { success: true, localId, offline: true };
  }

  async syncToServer(record) {
    const response = await fetch(this.gasUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'register',
        data: record
      })
    });

    return await response.json();
  }

  async getItemList() {
    // キャッシュから取得
    let items = await offlineDB.getMasterData('items');

    // オンラインなら更新
    if (navigator.onLine) {
      try {
        items = await syncManager.syncMasterData('items');
      } catch (error) {
        console.log('Using cached items:', error);
      }
    }

    return items || [];
  }
}

const api = new IntakeDeliveryAPI(GAS_API_URL);
```

#### 2.3 OCR統合

`/home/user/codings/pwa-warehouse-app/intake-delivery/js/ui.js`:

```javascript
// OCR機能
async function handleOCRCapture() {
  const fileInput = document.getElementById('ocr-camera-input');

  fileInput.onchange = async (e) => {
    const file = e.target.files[0];

    if (!file) return;

    try {
      showLoadingIndicator('OCR処理中...');

      const result = await ocrManager.performOCR(file, {
        visionApiAvailable: false, // GAS環境外ではfalse
        progressCallback: (status) => {
          updateLoadingStatus(status.message);
        }
      });

      // 抽出されたテキストをテキストエリアに設定
      document.getElementById('reg-name').value = result.text;

      hideLoadingIndicator();
      alert('テキスト抽出完了！品名を確認・編集してください。');
    } catch (error) {
      hideLoadingIndicator();

      if (!navigator.onLine) {
        alert('オフライン時のOCR処理に失敗しました。\n\nTesseract.jsの読み込みに問題がある可能性があります。\nオンライン時に再度お試しください。');
      } else {
        alert('OCRエラー: ' + error.message);
      }
    }
  };

  fileInput.click();
}
```

### Phase 3: 同期機能の実装

#### 3.1 自動同期

すでに実装済みの `network-status.js` が自動的に同期をトリガーします：

```javascript
// オンライン復帰時に自動実行される
networkStatus.addListener(async (isOnline) => {
  if (isOnline) {
    console.log('Online - starting sync');
    const result = await syncManager.syncAll();
    console.log('Sync result:', result);
  }
});
```

#### 3.2 手動同期ボタン（オプション）

```html
<!-- 手動同期ボタンを追加 -->
<button id="manual-sync-btn" onclick="triggerManualSync()">
  未同期データを送信
</button>

<script>
async function triggerManualSync() {
  const btn = document.getElementById('manual-sync-btn');
  btn.disabled = true;
  btn.textContent = '同期中...';

  try {
    const result = await syncManager.syncAll();
    alert(`${result.synced}件のデータを同期しました`);
  } catch (error) {
    alert('同期エラー: ' + error.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '未同期データを送信';
  }
}
</script>
```

## テストとデバッグ

### 1. ローカルテスト

```bash
cd /home/user/codings/pwa-warehouse-app
python3 -m http.server 8000
```

ブラウザで `http://localhost:8000/intake-delivery/` にアクセス

### 2. オフラインテスト

1. Chrome DevTools を開く
2. Network タブ → Throttling → Offline を選択
3. アプリを操作してオフライン動作を確認
4. データ入力が IndexedDB に保存されることを確認
5. Online に戻して自動同期を確認

### 3. Service Worker確認

Chrome DevTools:
- Application タブ
- Service Workers セクション
- 登録状況とキャッシュ内容を確認

## チェックリスト

### PWA要件

- [ ] HTTPS でアクセス可能
- [ ] manifest.json が正しく配置
- [ ] Service Worker が登録済み
- [ ] アイコンが設定済み（192x192, 512x512）
- [ ] オフラインでもページが表示される

### 機能要件

- [ ] ログインがオンライン/オフラインで動作
- [ ] データ入力がオフラインで可能
- [ ] IndexedDB にデータが保存される
- [ ] オンライン復帰時に自動同期
- [ ] OCR がオンライン/オフラインで動作（または適切にエラー表示）
- [ ] マスターデータがキャッシュされる
- [ ] 多言語切り替えが動作

### UI/UX

- [ ] ネットワーク状態が表示される
- [ ] 同期状態が表示される
- [ ] エラーメッセージが適切に表示
- [ ] ローディング表示が適切

### デバッグ

- [ ] コンソールエラーがない
- [ ] ネットワークエラーが適切にハンドリングされる
- [ ] データ損失がない

## トラブルシューティング

詳細は `DEPLOYMENT.md` のトラブルシューティングセクションを参照してください。

## 次のステップ

1. GASプロジェクトのAPI化
2. 本番環境へのデプロイ
3. ユーザーテストの実施
4. フィードバックに基づく改善

## サポート

問題が発生した場合は、以下を確認してください：

- `README.md` - 基本的な使用方法
- `DEPLOYMENT.md` - デプロイメント詳細
- コンソールログとDevTools

## 完成例

完全に実装されたサンプルコードは `examples/` ディレクトリを参照してください（今後追加予定）。
