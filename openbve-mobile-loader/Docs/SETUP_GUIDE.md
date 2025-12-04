# openBVE Mobile Loader - セットアップガイド

## 必要な環境

- **Unity**: 2021.3 LTS以降推奨
- **IDE**: Visual Studio 2019以降、JetBrains Rider、またはVS Code
- **対象プラットフォーム**:
  - Android: Android SDK、JDK
  - iOS: Xcode（macOSのみ）

## プロジェクトセットアップ

### 1. Unityプロジェクトを作成

1. Unity Hubを起動
2. 「新規作成」をクリック
3. プロジェクト設定：
   - テンプレート: **3D**
   - プロジェクト名: `openBVE-Mobile`
   - 保存場所: 任意の場所

### 2. スクリプトを配置

```bash
# このリポジトリのScriptsフォルダをUnityプロジェクトにコピー
cp -r openbve-mobile-loader/Scripts/ <UnityプロジェクトPath>/Assets/Scripts/
```

または、Unityエディタ内で：
1. Assetsフォルダを右クリック → Create → Folder
2. フォルダ名を「Scripts」に変更
3. このリポジトリの`Scripts`フォルダの中身を全てコピー

### 3. 基本シーンをセットアップ

#### A. GameManagerオブジェクトを作成

1. Hierarchy → 右クリック → Create Empty
2. 名前を「GameManager」に変更
3. Inspector → Add Component → `GameManager` スクリプトをアタッチ

#### B. カメラをセットアップ

1. Main Cameraを選択
2. Inspector → Add Component → `CameraController` スクリプトをアタッチ
3. 初期位置を設定（例: Position: 0, 2, -5）

#### C. 列車オブジェクトを作成

1. Hierarchy → 右クリック → Create Empty
2. 名前を「Train」に変更
3. Inspector → Add Component → `TrainController` スクリプトをアタッチ
4. 仮の見た目として Cube を追加（Train の子オブジェクト）

#### D. RouteLoaderオブジェクトを作成

1. Hierarchy → 右クリック → Create Empty
2. 名前を「RouteLoader」に変更
3. Inspector → Add Component:
   - `RouteLoader` スクリプト
   - `ModelLoader` スクリプト

#### E. GameManagerの参照を設定

1. GameManagerオブジェクトを選択
2. Inspector で各フィールドに対応するオブジェクトをドラッグ：
   - Route Loader: RouteLoader オブジェクト
   - Train Controller: Train オブジェクト
   - Camera Controller: Main Camera

### 4. UIをセットアップ（モバイル操作用）

#### A. Canvas を作成

1. Hierarchy → 右クリック → UI → Canvas
2. Canvas の Render Mode を「Screen Space - Overlay」に設定

#### B. 操作パネルを作成

1. Canvas を右クリック → UI → Panel
2. 名前を「ControlPanel」に変更
3. Inspector → Add Component → `MobileControlPanel` スクリプトをアタッチ

#### C. ボタンを配置

以下のボタンを作成：

**力行ボタン**
- Canvas → 右クリック → UI → Button
- 名前: `PowerUpButton`
- Text: 「力行↑」
- 位置: 右下

**ブレーキボタン**
- 名前: `BrakeUpButton`
- Text: 「ブレーキ↑」
- 位置: 右下（力行ボタンの左）

**緊急ブレーキボタン**
- 名前: `EmergencyBrakeButton`
- Text: 「非常」
- 位置: 中央下
- 色: 赤

**速度計表示**
- Canvas → 右クリック → UI → Text
- 名前: `SpeedText`
- Text: 「0.0 km/h」
- 位置: 左上
- フォントサイズ: 32

#### D. MobileControlPanelの参照を設定

1. ControlPanel オブジェクトを選択
2. Inspector の MobileControlPanel コンポーネントで：
   - Train Controller: Train オブジェクト
   - 各ボタン/テキストフィールドに対応するUIオブジェクトをドラッグ

### 5. デフォルトマテリアルを作成

1. Assets フォルダで右クリック → Create → Material
2. 名前を「DefaultMaterial」に変更
3. RouteLoader の Inspector で Default Material フィールドにドラッグ

### 6. ビルド設定

#### Android向け

1. File → Build Settings
2. Platform → Android を選択
3. Switch Platform をクリック
4. Player Settings → Other Settings:
   - Package Name: `com.yourname.openbvemobile`
   - Minimum API Level: Android 7.0 (API Level 24) 以上
   - Graphics APIs: OpenGLES3, Vulkan
5. Build をクリック

#### iOS向け

1. File → Build Settings
2. Platform → iOS を選択
3. Switch Platform をクリック
4. Player Settings → Other Settings:
   - Bundle Identifier: `com.yourname.openbvemobile`
   - Target minimum iOS Version: 12.0 以上
5. Build をクリック（Xcodeプロジェクトが生成される）
6. Xcodeで開いて実機ビルド

## 路線データをロードする

### テスト用シンプル路線を作成

1. プロジェクトフォルダ内に `TestRoute` フォルダを作成
2. `route.csv` ファイルを作成：

```csv
; Test Route
Route.Comment, Test Route for openBVE Mobile
Route.Gauge, 1.067

; Station
0, Station(TestStation), 00.0000, 00.0100, 15, 0, 1

1000, Track.Pitch(0)
2000, Track.Pitch(10)
3000, Track.Pitch(0)
4000, Track.Curve(400)
5000, Track.Curve(0)
```

3. GameManager の Inspector:
   - Route File Path: TestRoute/route.csv のパス
   - Auto Load On Start: チェック

4. Play ボタンを押してテスト

## トラブルシューティング

### スクリプトエラーが出る場合

- Unity エディタで右クリック → Reimport All
- Visual Studio で Solution をクリーン・リビルド

### ボタンが反応しない

- EventSystem が存在することを確認（Canvas作成時に自動生成）
- ボタンの OnClick イベントが正しく設定されているか確認

### 路線がロードされない

- ファイルパスが正しいか確認
- Consoleウィンドウでエラーメッセージを確認
- ファイルエンコーディングをUTF-8またはShift-JISに統一

### モバイルでタッチが反応しない

- Input System が Legacy に設定されているか確認
  - Edit → Project Settings → Player → Active Input Handling: Input Manager (Old)

## 次のステップ

1. 実際のopenBVE路線データでテスト
2. 3Dモデル（B3D、CSV）の読み込みテスト
3. 高度な機能の追加（信号、駅停車判定等）
4. グラフィックスの改善

## 参考資料

- [Unity公式ドキュメント](https://docs.unity3d.com/)
- [openBVE公式サイト](http://openbve-project.net/)
- [openBVEデータ仕様書](http://openbve-project.net/documentation.html)
