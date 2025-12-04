# openBVE CSVフォーマット仕様

openBVE Mobile Loaderで対応しているCSVフォーマットについて説明します。

## 基本構造

```csv
距離程, コマンド(引数1, 引数2, ...)
```

- **距離程**: メートル単位の位置（省略可）
- **コマンド**: 実行する命令
- **引数**: カンマ（`,`）またはセミコロン（`;`）で区切る
- **コメント**: セミコロン（`;`）以降はコメント

## 対応コマンド一覧

### Options（オプション設定）

#### Options.UnitOfLength
単位長を設定

```csv
Options.UnitOfLength(単位名)
```

- `Meter` / `Meters`: メートル（デフォルト）
- `Kilometer` / `Kilometers`: キロメートル
- `Mile` / `Miles`: マイル
- `Yard` / `Yards`: ヤード

例：
```csv
Options.UnitOfLength(Kilometers)
```

#### Options.UnitOfSpeed
速度単位を設定（未実装）

### Route（路線情報）

#### Route.Comment
路線の説明

```csv
Route.Comment, 説明文
```

#### Route.Image
路線のサムネイル画像

```csv
Route.Image, ファイル名
```

#### Route.Gauge
軌間（ゲージ）をメートル単位で設定

```csv
Route.Gauge, 値
```

例：
```csv
Route.Gauge, 1.067  ; 狭軌（1067mm）
Route.Gauge, 1.435  ; 標準軌（1435mm）
```

#### Route.Elevation
初期標高をメートル単位で設定

```csv
Route.Elevation, 値
```

### Station（駅）

#### Station / Track.Sta
駅を設置

```csv
距離程, Station(駅名; 到着時刻; 発車時刻; 停車時間; 通過警告; ドア; 強制赤信号; 系統)
```

引数：
1. **駅名**: 駅の名前
2. **到着時刻**: HH.MMSS形式（省略可）
3. **発車時刻**: HH.MMSS形式（省略可）
4. **停車時間**: 秒単位（デフォルト15秒）
5. **通過警告**: 0=なし、1=あり
6. **ドア**: -1=左、0=なし、1=右
7. **強制赤信号**: 0=なし、1=あり
8. **系統**: ATS/ATC種別

例：
```csv
1000, Station(新宿; 09.3000; 09.3100; 30; 0; 1; 0; 0)
```

### Structure（構造物定義）

構造物（3Dモデル）を定義します。

#### Structure.Ground
地面オブジェクト

```csv
Structure.Ground(インデックス), ファイルパス
```

#### Structure.Rail
レールオブジェクト

```csv
Structure.Rail(インデックス), ファイルパス
```

#### Structure.WallL / Structure.WallR
左右の壁オブジェクト

```csv
Structure.WallL(インデックス), ファイルパス
Structure.WallR(インデックス), ファイルパス
```

#### Structure.DikeL / Structure.DikeR
左右の土手オブジェクト

```csv
Structure.DikeL(インデックス), ファイルパス
Structure.DikeR(インデックス), ファイルパス
```

例：
```csv
Structure.Ground(0), ground_grass.csv
Structure.Rail(0), rail_standard.b3d
Structure.WallL(0), wall_concrete.csv
```

### Track（線形・配置）

#### Track.Pitch
勾配を設定（パーミル）

```csv
距離程, Track.Pitch(値)
```

- 正の値：上り勾配
- 負の値：下り勾配

例：
```csv
1000, Track.Pitch(25)   ; 25パーミルの上り勾配
2000, Track.Pitch(0)    ; 平坦に戻す
```

#### Track.Curve
曲線を設定

```csv
距離程, Track.Curve(半径; カント)
```

- **半径**: メートル単位（正=右カーブ、負=左カーブ、0=直線）
- **カント**: ミリメートル単位（省略可）

例：
```csv
1000, Track.Curve(400; 100)  ; 半径400mの右カーブ、カント100mm
2000, Track.Curve(0)          ; 直線に戻す
```

#### Track.Turn
カントのみを設定

```csv
距離程, Track.Turn(値)
```

#### Track.Ground
地面オブジェクトを配置

```csv
距離程, Track.Ground(インデックス)
```

例：
```csv
0, Track.Ground(0)  ; Structure.Ground(0) で定義したオブジェクトを配置
```

#### Track.FreeObj
自由配置オブジェクト

```csv
距離程, Track.FreeObj(レール番号; オブジェクトキー; X; Y; ヨー; ピッチ; ロール)
```

引数：
1. **レール番号**: 基準となるレール（0=主レール）
2. **オブジェクトキー**: 構造物定義のキー
3. **X**: 横方向オフセット（メートル）
4. **Y**: 縦方向オフセット（メートル）
5. **ヨー**: Y軸回転（度）
6. **ピッチ**: X軸回転（度）
7. **ロール**: Z軸回転（度）

例：
```csv
1000, Track.FreeObj(0; building_1; 10; 0; 0; 0; 0)
```

#### Track.Wall
壁オブジェクトを配置

```csv
距離程, Track.Wall(レール番号; 方向; オブジェクトキー)
```

- **方向**: -1=左、1=右

#### Track.Back / Track.Background
背景画像を設定

```csv
Track.Back(ファイルパス)
```

例：
```csv
Track.Back(sky_01.png)
```

### Signal（信号）

#### Track.Signal
信号機を設置（未実装）

```csv
距離程, Track.Signal(タイプ)
```

#### Track.Section
閉塞区間を設定（未実装）

```csv
距離程, Track.Section(値)
```

### その他

#### Track.Limit
速度制限

```csv
距離程, Track.Limit(速度)
```

速度: km/h単位

例：
```csv
1000, Track.Limit(60)  ; 60km/h制限
```

#### Track.Stop
停止位置マーカー

```csv
距離程, Track.Stop(方向; 後退余裕; 前方許容; ドア)
```

#### Track.Beacon
地上子（ATS等）を設置（未実装）

```csv
距離程, Track.Beacon(タイプ; データ)
```

## 実装状況

### ✅ 実装済み

- Options.UnitOfLength
- Route.Comment, Route.Image, Route.Gauge, Route.Elevation
- Station
- Structure.Ground, Rail, WallL, WallR, DikeL, DikeR
- Track.Pitch, Track.Curve
- Track.Ground, Track.FreeObj
- Track.Background

### ⏳ 未実装（今後対応予定）

- Track.Rail, Track.RailStart, Track.RailEnd
- Track.Signal, Track.Section
- Track.Limit（制限表示のみ、実際の制限は未実装）
- Track.Beacon
- Track.Form（ホーム関連）
- Track.Fog（霧）

## サンプルCSV

```csv
; Sample Route
Route.Comment, Sample route for testing
Route.Gauge, 1.067

; Define structures
Structure.Ground(0), Objects/ground_grass.csv
Structure.Rail(0), Objects/rail_std.b3d

; Start
0, Track.Ground(0)

; Station 1
1000, Station(Test Station 1; ; ; 15; 0; 1)

; Gradient
2000, Track.Pitch(20)
3000, Track.Pitch(0)

; Curve
4000, Track.Curve(500; 80)
5000, Track.Curve(0)

; Station 2
6000, Station(Test Station 2; ; ; 15; 0; 1)
```

## 参考

- [openBVE公式ドキュメント（英語）](http://openbve-project.net/documentation.html)
- [BVE Trainsim - CSV Route Format](http://bvets.net/)
