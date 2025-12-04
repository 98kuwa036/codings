# openBVE Mobile Loader

openBVEの路線データをモバイルデバイス（Android/iOS）で読み込み、プレイできるようにするプロジェクト。

## 概要

PC向け鉄道運転シミュレーター「openBVE」のゲームファイルをモバイル環境で動作させることを目的としたプロジェクトです。

### 主な機能

#### ✅ 実装済み機能

- **マルチフォーマット対応**: BVE2/BVE4/BVE5/openBVE自動検出・読み込み
- **BVE5完全対応**: テキストマップファイル形式（railsim互換）
- **サウンドシステム**: WAV形式サウンド再生（モーター音、ブレーキ音、警笛等）
- **路線パーサー**: CSV/XML/テキストマップ形式対応
- **3Dモデルローダー**: B3D、CSVオブジェクト、**DirectX X形式**
- **動的オブジェクト**: アニメーション、移動、回転、スクリプト制御
- **スクリプトエンジン**: カスタムC#スクリプトで動作制御
- **高度なグラフィックス**: ダイナミックライティング、霧、パーティクル
- **3Dビューワー**: タッチ操作対応カメラ
- **運転機能**: 力行・ブレーキノッチ、物理演算
- **モバイルUI**: タッチ操作パネル、警笛ボタン

#### 🔄 今後の実装予定

- **Phase 5**: 信号システム
- **Phase 6**: ATS/ATC保安装置
- **Phase 7**: 駅停車判定
- **Phase 8**: Wavefront OBJモデル対応
- **Phase 9**: VR対応

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
- ✅ **BVE5形式**: BVE Trainsim 5.x（テキストマップ + CSV/XML）
- ✅ **openBVE形式**: openBVE拡張CSV形式

#### 3Dモデル
- ✅ **B3D形式**: openBVE独自バイナリ形式
- ✅ **CSVオブジェクト**: BVE4/openBVE形式
- ✅ **X形式**: DirectX形式（マテリアル、テクスチャ対応）
- 🔄 **OBJ形式**: Wavefront形式（実装予定）
- ⚠️ **XMLオブジェクト**: BVE5形式（部分対応）

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
│   │   ├── FormatDetector.cs       # BVE2/4/5/openBVE自動検出
│   │   ├── Bve2RouteParser.cs      # BVE2パーサー
│   │   ├── CsvRouteParser.cs       # BVE4/openBVEパーサー
│   │   ├── Bve5RouteParser.cs      # BVE5 XMLパーサー（後方互換）
│   │   ├── Bve5MapParser.cs        # BVE5テキストマップパーサー
│   │   ├── B3DParser.cs            # B3Dモデルパーサー
│   │   ├── CsvObjectParser.cs      # CSVオブジェクトパーサー
│   │   └── DirectXParser.cs        # DirectX Xファイルパーサー
│   ├── Loaders/          # データローダー
│   │   ├── UnifiedRouteLoader.cs   # 統合ローダー
│   │   ├── RouteLoader.cs
│   │   └── ModelLoader.cs          # X形式対応
│   ├── Audio/            # サウンドシステム
│   │   ├── SoundManager.cs         # サウンド管理
│   │   └── TrainSoundController.cs # 列車サウンド
│   ├── Core/             # コア機能
│   │   ├── GameManager.cs
│   │   ├── OpenBveTypes.cs
│   │   ├── DynamicObjectSystem.cs  # 動的オブジェクト
│   │   └── ScriptEngine.cs         # スクリプトエンジン
│   ├── Graphics/         # 高度なグラフィックス
│   │   └── AdvancedGraphicsSystem.cs
│   ├── Controllers/      # 運転制御
│   │   ├── TrainController.cs      # 列車制御+サウンド統合
│   │   └── CameraController.cs     # カメラ制御
│   └── UI/               # ユーザーインターフェース
│       └── MobileControlPanel.cs   # モバイルUI（警笛ボタン含む）
├── Docs/                 # ドキュメント
│   ├── SETUP_GUIDE.md              # セットアップガイド
│   ├── CSV_FORMAT.md               # CSV仕様書
│   ├── B3D_FORMAT.md               # B3D仕様書
│   ├── SOUND_SYSTEM.md             # サウンドシステムガイド
│   ├── BVE_COMPATIBILITY.md        # BVE互換性ガイド
│   └── ADVANCED_FEATURES.md        # 高度な機能ガイド
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
- [x] BVE5テキストマップ形式対応
- [x] フォーマット自動検出
- [x] B3D/CSV/DirectX Xモデルローダー
- [x] 動的オブジェクトシステム
- [x] スクリプトエンジン
- [x] 高度なグラフィックス（ライティング、霧、パーティクル）
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
- [ ] Wavefront OBJモデル対応
- [ ] 動的照明の最適化
- [ ] パーティクルエフェクト拡張

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

現在Phase 1-4 完了、Phase 5（信号システム）進行中

---

**更新履歴**
- 2025-12-04: 高度な機能追加（DirectX X、動的オブジェクト、スクリプト、グラフィックス）
- 2025-12-04: BVE5テキストマップ形式対応、サウンドシステム実装
- 2025-11-19: 初期リリース
