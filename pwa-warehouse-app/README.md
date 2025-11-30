# 倉庫管理PWAアプリケーション

完全オフライン対応の倉庫管理システム

## 概要

このプロジェクトは、既存のGoogle Apps Script (GAS)ベースの倉庫管理システムをProgressive Web App (PWA)化したものです。

### 主な機能

- **完全オフライン対応**: インターネット接続がなくても動作
- **自動データ同期**: オンライン復帰時に自動的にサーバーと同期
- **オフラインOCR**: Tesseract.jsによる日本語OCR機能（オンライン時はGoogle Vision API優先）
- **多言語対応**: 日本語、英語、インドネシア語
- **Last-Write-Wins**: タイムスタンプベースの競合解決

## プロジェクト構造

```
pwa-warehouse-app/
├── intake-delivery/          # 入出庫記録アプリ
│   ├── index.html           # メインHTML
│   ├── manifest.json        # PWAマニフェスト
│   ├── sw.js                # Service Worker
│   ├── js/                  # アプリ固有JavaScript
│   ├── css/                 # スタイルシート
│   └── icons/               # アプリアイコン
│
├── login/                    # ログインアプリ
│   ├── index.html
│   ├── manifest.json
│   ├── sw.js
│   ├── js/
│   ├── css/
│   └── icons/
│
└── shared/                   # 共有リソース
    ├── js/
    │   ├── offline-db.js    # IndexedDB管理
    │   ├── network-status.js # ネットワーク状態監視
    │   ├── sync-manager.js   # データ同期
    │   └── ocr-helper.js     # OCR機能
    ├── css/                 # 共有スタイル
    └── icons/               # 共有アイコン
        └── warehouse-icon.svg
```

## 技術スタック

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Offline Storage**: IndexedDB
- **Service Worker**: キャッシュ管理、オフライン対応
- **OCR**: Tesseract.js (オフライン) / Google Vision API (オンライン)
- **Backend**: Google Apps Script (同期用)

## セットアップ

### 1. ファイル配置

プロジェクトファイルを適切なディレクトリに配置してください。

### 2. Service Worker登録

各アプリのHTMLファイルにService Worker登録コードが含まれています。

### 3. Tesseract.js読み込み

入出庫記録アプリでOCR機能を使用する場合、Tesseract.jsをCDN経由で読み込みます：

```html
<script src="https://cdn.jsdelivr.net/npm/tesseract.js@4/dist/tesseract.min.js"></script>
```

### 4. GAS連携設定

`sync-manager.js`でGASのエンドポイントを設定：

```javascript
syncManager.updateApiConfig({
  baseUrl: 'https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec',
  endpoints: {
    register: '/register',
    masterData: '/master-data'
  }
});
```

## オフライン動作

### データ保存

- 入出庫記録はIndexedDBに保存
- マスターデータ（品目リストなど）もキャッシュ
- ユーザー認証情報も一時保存

### 同期戦略

1. **オンライン時**: 即座にサーバーへ送信
2. **オフライン時**: IndexedDBに保存
3. **オンライン復帰時**: 自動的に未同期データを送信

### 競合解決

Last-Write-Wins戦略を採用：
- タイムスタンプが新しいデータを優先
- 競合発生時は最終書き込み時刻で自動解決

## 使用方法

### アプリのインストール

1. PWA対応ブラウザでアクセス
2. アドレスバーのインストールアイコンをクリック
3. ホーム画面に追加

### オフラインでの使用

1. 一度オンラインでアクセスしてキャッシュ
2. 以降はオフラインでも使用可能
3. データ入力は通常通り実行
4. オンライン復帰時に自動同期

### OCR機能

- **オンライン時**: Google Vision API（高精度）
- **オフライン時**: Tesseract.js（日本語対応）
- 自動的に使用可能な方を選択

## ブラウザ対応

- Chrome 67+
- Firefox 63+
- Safari 11.1+
- Edge 79+

## セキュリティ

- HTTPS必須（PWA要件）
- パスワードは平文保存しない
- 認証トークンの適切な管理

## デバッグ

### Service Workerの確認

Chrome DevTools:
1. Application タブ
2. Service Workers セクション
3. 登録状況とキャッシュを確認

### IndexedDBの確認

Chrome DevTools:
1. Application タブ
2. Storage > IndexedDB
3. WarehouseDB を確認

### ネットワーク状態テスト

Chrome DevTools:
1. Network タブ
2. Throttling で「Offline」を選択
3. オフライン動作をテスト

## トラブルシューティング

### Service Workerが登録されない

- HTTPSで実行されているか確認
- ブラウザがService Workerをサポートしているか確認
- コンソールでエラーメッセージを確認

### データが同期されない

- ネットワーク接続を確認
- 同期キューにデータがあるか確認（IndexedDB）
- コンソールで同期エラーを確認

### OCRが動作しない

- Tesseract.jsがロードされているか確認
- 画像フォーマットが対応しているか確認
- ファイルサイズが適切か確認（10MB以下推奨）

## ライセンス

MIT License

## クレジット

- Tesseract.js: Apache License 2.0
- Original GAS Application: Gemini, ChatGPT, Claude collaboration
