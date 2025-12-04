# openBVE Mobile Loader

openBVEの路線データをモバイルデバイス（Android/iOS）で読み込み、プレイできるようにするプロジェクト。

## 概要

PC向け鉄道運転シミュレーター「openBVE」のゲームファイルをモバイル環境で動作させることを目的としたプロジェクトです。

### 主な機能（段階的実装）

- **Phase 1**: 路線ファイル（CSV）パーサー
- **Phase 2**: 3Dモデルローダー（B3D、CSVオブジェクト）
- **Phase 3**: 3Dビューワー機能
- **Phase 4**: 基本的な運転機能（アクセル/ブレーキ）
- **Phase 5**: 高度な運転機能（段階追加）

## 技術スタック

- **エンジン**: Unity 2021.3 LTS以降推奨
- **言語**: C#
- **対応プラットフォーム**: Android、iOS
- **3Dレンダリング**: Unity標準レンダリングパイプライン

## openBVEファイル形式対応

### 対応予定フォーマット

- **路線データ**: CSV形式（Track.*, Station.*等）
- **3Dモデル**:
  - B3D形式（openBVE独自）
  - CSV形式（オブジェクト定義）
  - X形式（DirectX）
  - 将来的にOBJ形式も対応予定
- **テクスチャ**: PNG、BMP、JPG
- **サウンド**: WAV、MP3

## プロジェクト構造

```
openbve-mobile-loader/
├── Scripts/
│   ├── Parsers/          # ファイルパーサー
│   │   ├── CsvRouteParser.cs
│   │   ├── B3DParser.cs
│   │   └── CsvObjectParser.cs
│   ├── Loaders/          # データローダー
│   │   ├── RouteLoader.cs
│   │   ├── ModelLoader.cs
│   │   └── TextureLoader.cs
│   ├── Core/             # コア機能
│   │   ├── TrackManager.cs
│   │   ├── ObjectManager.cs
│   │   └── WorldManager.cs
│   ├── Controllers/      # 運転制御
│   │   ├── TrainController.cs
│   │   └── PhysicsController.cs
│   └── UI/               # ユーザーインターフェース
│       ├── MainMenu.cs
│       └── ControlPanel.cs
├── Docs/                 # ドキュメント
│   ├── CSV_FORMAT.md
│   ├── B3D_FORMAT.md
│   └── DEVELOPMENT.md
├── Assets/               # アセット（テスト用）
└── README.md
```

## 開発ガイド

### 必要な環境

- Unity 2021.3 LTS以降
- Visual Studio 2019以降またはRider
- Android SDK（Android向けビルド時）
- Xcode（iOS向けビルド時、macOSのみ）

### セットアップ手順

1. **Unityプロジェクト作成**
   ```
   Unity Hubで新規3Dプロジェクトを作成
   プロジェクト名: openBVE-Mobile
   ```

2. **スクリプトの配置**
   ```
   このリポジトリのScripts/フォルダ内容を
   Unity Assets/Scripts/ にコピー
   ```

3. **ビルド設定**
   - Android: File > Build Settings > Android
   - iOS: File > Build Settings > iOS

### 開発ロードマップ

#### Phase 1: 基礎パーサー実装 ✓ 実装中
- [x] プロジェクト構造作成
- [ ] CSV路線ファイルパーサー
- [ ] 基本的なデータ構造定義

#### Phase 2: モデルローダー
- [ ] B3Dファイルパーサー
- [ ] CSVオブジェクト定義パーサー
- [ ] Unityメッシュへの変換

#### Phase 3: ビューワー
- [ ] 3D空間への配置
- [ ] カメラコントロール（タッチ対応）
- [ ] テクスチャ適用

#### Phase 4: 基本運転機能
- [ ] 列車物理演算
- [ ] アクセル/ブレーキUI
- [ ] 速度計表示

#### Phase 5: 高度な機能
- [ ] 信号システム
- [ ] 駅停車判定
- [ ] サウンド再生
- [ ] 保安装置（ATS/ATC）

## openBVE仕様書参考

- [openBVE公式ドキュメント](http://openbve-project.net/documentation.html)
- CSV Route Format
- B3D/CSV Object Format

## ライセンス

個人利用のみ。商用利用不可。

openBVEはGPL-2.0ライセンスのオープンソースソフトウェアです。
このプロジェクトもそれに準じます。

## 注意事項

- このプロジェクトは個人学習・研究目的です
- openBVE本家プロジェクトとは無関係です
- 路線データの著作権は各制作者に帰属します
- 商用利用は行わないでください

## 貢献

個人プロジェクトですが、改善提案は歓迎します。

## 開発状況

現在Phase 1を実装中
