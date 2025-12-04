# BVE互換性ガイド

openBVE Mobile Loader は BVE2/BVE4/BVE5/openBVE のデータをサポートします。

## サポート状況

| フォーマット | 読み込み | 自動検出 | 変換 | 状態 |
|------------|---------|---------|------|------|
| BVE2 | ✅ | ✅ | ✅ | 対応済み |
| BVE4 | ✅ | ✅ | ✅ | 対応済み |
| BVE5 | ⚠️ | ✅ | 🔄 | 部分対応 |
| openBVE | ✅ | ✅ | ✅ | 完全対応 |

- ✅ 完全対応
- ⚠️ 部分対応
- 🔄 実装中
- ❌ 未対応

## フォーマット自動検出

```csharp
using OpenBveMobile.Parsers;

// 自動検出
BveFormat format = FormatDetector.DetectRouteFormat("path/to/route.csv");

// 結果
switch (format)
{
    case BveFormat.BVE2:   // BVE Trainsim 2.x
    case BveFormat.BVE4:   // BVE Trainsim 4.x
    case BveFormat.BVE5:   // BVE Trainsim 5.x (XML)
    case BveFormat.OpenBVE: // openBVE
}
```

### 検出方法

#### BVE2
- 距離程が単独行
- シンプルなコマンド構造（CURVE, STATION等）
- ファイル拡張子: `.txt`, `.csv`

#### BVE4
- CSV形式
- `Options.`, `Route.`, `Structure.` コマンド
- 距離程とコマンドが同一行
- ファイル拡張子: `.csv`

#### BVE5
- XML形式
- `<Route>` ルート要素
- ファイル拡張子: `.xml`

#### openBVE
- BVE4ベース + 独自拡張
- `Track.SigF`, `Track.PreTrain` 等の独自コマンド
- ファイル拡張子: `.csv`

## フォーマット別対応状況

### BVE2 (BVE Trainsim 2.x)

#### 対応コマンド

##### 線形
- ✅ `CURVE radius`: 曲線
- ✅ `GRADIENT value`: 勾配
- ✅ `PITCH value`: 勾配（別名）

##### 駅
- ✅ `STATION name`: 駅設置

##### 構造物
- ✅ `GROUND index`: 地面
- ✅ `RAIL index`: レール
- ⚠️ `REPEATER`: リピーター（部分対応）

##### その他
- ✅ `LIMIT speed`: 速度制限

#### 互換性ノート

- BVE2は最も古い形式で、機能が限定的
- 複雑な構造物配置は手動変換が必要な場合あり
- 距離程の単位はメートル固定

#### サンプルBVE2ファイル

```
; BVE2 Route File
0
STATION Start Station
100
CURVE 500
200
GRADIENT 25
500
STATION Middle Station
1000
CURVE 0
GRADIENT 0
```

### BVE4 (BVE Trainsim 4.x)

#### 対応コマンド

##### Options
- ✅ `Options.UnitOfLength`: 単位長
- ✅ `Options.UnitOfSpeed`: 速度単位

##### Route
- ✅ `Route.Comment`: 説明
- ✅ `Route.Image`: サムネイル
- ✅ `Route.Gauge`: 軌間
- ✅ `Route.Elevation`: 初期標高

##### Station
- ✅ `Station`: 駅設置（全パラメータ対応）

##### Structure
- ✅ `Structure.Ground`: 地面
- ✅ `Structure.Rail`: レール
- ✅ `Structure.WallL/R`: 壁
- ✅ `Structure.DikeL/R`: 土手
- ✅ `Structure.FormL/R`: ホーム

##### Track
- ✅ `Track.Pitch`: 勾配
- ✅ `Track.Curve`: 曲線
- ✅ `Track.Turn`: カント
- ✅ `Track.Ground`: 地面配置
- ✅ `Track.FreeObj`: 自由配置
- ✅ `Track.Wall`: 壁配置
- ⚠️ `Track.Signal`: 信号（未実装）
- ⚠️ `Track.Section`: 閉塞（未実装）

#### サンプルBVE4ファイル

```csv
; BVE4 Route File
Route.Comment, Sample Route
Route.Gauge, 1.067
Options.UnitOfLength(Meter)

Structure.Ground(0), Objects/ground.csv
Structure.Rail(0), Objects/rail.b3d

0, Track.Ground(0)
1000, Station(Station1; 09.0000; 09.0100; 15; 0; 1)
2000, Track.Pitch(20)
3000, Track.Curve(400; 100)
```

### BVE5 (BVE Trainsim 5.x)

#### 対応状況

##### XML構造
- ✅ `<Route>`: ルート要素
- ✅ `<Info>`: 路線情報
- ✅ `<Structures>`: 構造物定義
- ✅ `<Tracks>`: 線形データ
- ✅ `<Stations>`: 駅情報

##### 機能
- ⚠️ 高度なグラフィックス機能（部分対応）
- ⚠️ 動的オブジェクト（未対応）
- ⚠️ スクリプト機能（未対応）

#### BVE5からの変換

BVE5の高度な機能の一部は自動変換できません。
以下のような対応が必要です：

**グラフィックス**:
- シェーダー → Unity標準シェーダーに変換
- エフェクト → 削除または簡略化

**スクリプト**:
- BVE5独自スクリプト → 手動実装

#### サンプルBVE5ファイル

```xml
<?xml version="1.0" encoding="utf-8"?>
<Route>
  <Info>
    <Name>Sample Route</Name>
    <Comment>BVE5 sample route</Comment>
    <Gauge>1.067</Gauge>
  </Info>

  <Structures>
    <Ground Key="0" FilePath="Objects/ground.b3d"/>
  </Structures>

  <Tracks>
    <Ground Distance="0" Key="0"/>
    <Curve Distance="1000" Radius="500" Cant="100"/>
  </Tracks>

  <Stations>
    <Station Distance="1000" Name="Station1" Doors="1"/>
  </Stations>
</Route>
```

### openBVE

#### 完全互換

openBVEのほぼすべての機能に対応：
- ✅ すべてのBVE4コマンド
- ✅ openBVE独自拡張
- ✅ B3Dモデルフォーマット
- ✅ CSVオブジェクトフォーマット

#### openBVE独自機能

- ✅ `Track.Back`: 背景画像
- ⚠️ `Track.SigF`: 信号（未実装）
- ⚠️ `Track.PreTrain`: 先行列車（未実装）
- ⚠️ `Route.DynamicLight`: 動的照明（未実装）

## 統合ローダーの使用

### 基本的な使い方

```csharp
using OpenBveMobile.Loaders;

// UnifiedRouteLoaderをシーンに配置
UnifiedRouteLoader loader = GetComponent<UnifiedRouteLoader>();

// 自動検出してロード
RouteData data = loader.LoadRoute("path/to/route.csv");

// フォーマット情報を取得
string info = loader.GetConversionInfo("path/to/route.csv");
Debug.Log(info);
// Output:
// Format: BVE Trainsim 4.x (Standard CSV format)
// Compatible: Yes
```

### フォーマットを強制指定

```csharp
// BVE2として強制的に読み込む
loader.SetForcedFormat(BveFormat.BVE2);
RouteData data = loader.LoadRoute("path/to/route.txt");

// 自動検出に戻す
loader.EnableAutoDetect();
```

## データ変換のベストプラクティス

### BVE2 → BVE4/openBVE

手動変換が推奨される箇所：
1. **構造物定義**: BVE2の簡易定義 → BVE4の詳細定義
2. **駅パラメータ**: BVE2の最小限 → BVE4の詳細設定
3. **距離間隔**: BVE2の固定間隔 → BVE4の自由配置

### BVE5 → BVE4/openBVE

自動変換される内容：
1. ✅ 基本的な線形データ
2. ✅ 駅情報
3. ✅ 構造物配置

手動対応が必要：
1. ⚠️ 高度なグラフィックス
2. ⚠️ 動的オブジェクト
3. ⚠️ スクリプト機能

## トラブルシューティング

### 読み込めない場合

1. **フォーマット確認**
   ```csharp
   BveFormat format = FormatDetector.DetectRouteFormat(filePath);
   Debug.Log($"Detected: {FormatDetector.GetFormatInfo(format)}");
   ```

2. **エンコーディング確認**
   - Shift-JIS推奨
   - UTF-8も対応

3. **パス区切り文字**
   - Windows: `\` または `/`
   - Unity: `/` 推奨

### 一部機能が動作しない

**信号・閉塞**:
- 現在未実装
- 今後のアップデートで対応予定

**動的オブジェクト**:
- BVE5の高度な機能
- 静的オブジェクトに変換して配置

**スクリプト**:
- BVE5独自機能
- C#で再実装が必要

## 互換性チェックリスト

路線データを移植する際のチェックリスト：

- [ ] フォーマット自動検出が正しく動作
- [ ] 駅がすべて配置されている
- [ ] 線形（曲線・勾配）が正しい
- [ ] 構造物が表示される
- [ ] テクスチャが正しく適用される
- [ ] サウンドが再生される
- [ ] 速度制限が機能する（表示のみ）

## 参考資料

- [openBVE公式ドキュメント](http://openbve-project.net/documentation.html)
- [BVE Trainsim Wiki](http://bvets.net/)
- BVE5公式サイト（日本語）

## 今後の予定

- ✅ BVE2/4/openBVE完全対応
- 🔄 BVE5完全対応
- 📋 信号システム実装
- 📋 ATS/ATC実装
- 📋 動的オブジェクト対応
