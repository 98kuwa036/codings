# openBVE Mobile Loader

openBVEの路線データをモバイルデバイス（Android/iOS）で読み込み、プレイできるようにするプロジェクト。

## 概要

PC向け鉄道運転シミュレーター「openBVE」のゲームファイルをモバイル環境で動作させることを目的としたプロジェクトです。

### 主な機能

#### ✅ 実装済み機能

- **マルチフォーマット対応**: BVE2/BVE4/BVE5/openBVE自動検出・読み込み
- **サウンドシステム**: WAV形式サウンド再生（モーター音、ブレーキ音、警笛等）
- **路線パーサー**: CSV/XML形式対応
- **3Dモデルローダー**: B3D、CSVオブジェクト
- **3Dビューワー**: タッチ操作対応カメラ
- **運転機能**: 力行・ブレーキノッチ、物理演算
- **モバイルUI**: タッチ操作パネル、警笛ボタン

#### 🔄 今後の実装予定

- **Phase 5**: 信号システム
- **Phase 6**: ATS/ATC保安装置
- **Phase 7**: 駅停車判定
- **Phase 8**: DirectX (.x) モデル対応

## 技術スタック

- **エンジン**: Unity 2021.3 LTS以降推奨
- **言語**: C#
- **対応プラットフォーム**: Android、iOS
- **3Dレンダリング**: Unity標準レンダリングパイプライン
- **オーディオ**: Unity AudioSource（WAV形式対応）

## BVE/openBVEファイル形式対応

### 対応フォーマット

#### 路線データ
- ✅ **BVE2形式**: BVE Trainsim 2.x（レガシー形式）
- ✅ **BVE4形式**: BVE Trainsim 4.x（標準CSV形式）
- ⚠️ **BVE5形式**: BVE Trainsim 5.x（XML形式、部分対応）
- ✅ **openBVE形式**: openBVE拡張CSV形式

#### 3Dモデル
- ✅ **B3D形式**: openBVE独自バイナリ形式
- ✅ **CSVオブジェクト**: BVE4/openBVE形式
- 🔄 **X形式**: DirectX形式（実装予定）
- 🔄 **OBJ形式**: Wavefront形式（実装予定）

#### テクスチャ
- ✅ **PNG**: 推奨形式
- ✅ **BMP**: 対応
- ✅ **JPG**: 対応

#### サウンド
- ✅ **WAV**: PCM 8/16bit（完全対応、推奨）
- ⚠️ **MP3**: Unity事前インポート必要
- ⚠️ **OGG**: Unity事前インポート必要

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

3. **シーンセットアップ**
   - 詳細は `Docs/SETUP_GUIDE.md` 参照

4. **サウンドデータ配置**
   - WAV形式のサウンドファイルを準備
   - 詳細は `Docs/SOUND_SYSTEM.md` 参照

5. **ビルド設定**
   - Android: File > Build Settings > Android
   - iOS: File > Build Settings > iOS

### 開発ロードマップ

#### Phase 1-4: 基本機能 ✅ 完了
- [x] プロジェクト構造作成
- [x] BVE2/4/5/openBVEパーサー
- [x] フォーマット自動検出
- [x] B3D/CSVモデルローダー
- [x] 3Dビューワー（タッチ対応カメラ）
- [x] 列車物理演算
- [x] サウンドシステム（WAV対応）
- [x] モバイルUI

#### Phase 5: 信号・閉塞システム 🔄 進行中
- [ ] 信号機配置
- [ ] 閉塞区間管理
- [ ] 信号現示制御

#### Phase 6: 保安装置 📋 計画中
- [ ] ATS-P/ATS-SN
- [ ] ATC
- [ ] 地上子システム

#### Phase 7: 駅機能拡張 📋 計画中
- [ ] 正確な停止位置判定
- [ ] ドア開閉制御
- [ ] 時刻表管理

#### Phase 8: グラフィックス強化 📋 計画中
- [ ] DirectX (.x) モデル対応
- [ ] 動的照明
- [ ] パーティクルエフェクト

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
