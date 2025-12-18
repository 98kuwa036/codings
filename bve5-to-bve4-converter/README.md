# BVE5 to BVE4 Converter

BVE Trainsim 5 のデータを BVE Trainsim 4 形式に変換するツールです。

## 機能

- **BVE5専用構文の削除**: BVE4で使用できない構文を自動的に削除します
- **構文の変換**: BVE5で変更された構文をBVE4形式に戻します
- **変数の展開**: BVE5の変数定義を展開します
- **エンコーディング変換**: UTF-8からShift_JISへの変換

## 変換内容

### 削除される構文（BVE5専用）

| 構文 | 説明 |
|------|------|
| `Repeater[].Begin()` | リピーター（繰り返し配置） |
| `Repeater[].End()` | リピーター終了 |
| `$変数名 = 値` | 変数定義 |
| `include 'ファイル'` | ファイルインクルード |
| `Section.SetSpeedLimit()` | セクション速度制限 |
| `SpeedLimit.SetSignal()` | 信号速度制限 |
| `Irregularity.*` | 軌道狂い |
| `Adhesion.*` | 粘着係数 |
| `Sound3D.*` | 3Dサウンド |
| `RollingNoise.*` | 転動音 |
| `FlangeNoise.*` | フランジ音 |
| `JointNoise.*` | ジョイント音 |
| `Train.SetTrack()` | 他列車のトラック設定 |
| `Background.Change()` | 背景変更（BVE5拡張） |

### 変換される構文

| BVE5 | BVE4 |
|------|------|
| `BveTs Map 2.xx` | `BveTs Map 1.00` |
| `Structure.Load(key, path)` | `Structure[key].Load(path)` |
| `Signal.Load(key, path)` | `Signal[key].Load(path)` |
| `Sound.Load(key, path)` | `Sound[key].Load(path)` |
| `Fog.Interpolate(d, r, g, b)` | `Legacy.Fog(0, d, r, g, b)` |
| `Fog.Set(d, r, g, b)` | `Legacy.Fog(0, d, r, g, b)` |
| `CabIlluminance.Interpolate(v)` | `Legacy.CabIlluminance(v)` |
| `Pitch.Interpolate(v)` | `Legacy.Pitch(v)` |
| `Turn.Interpolate(v)` | `Legacy.Turn(v)` |
| `Curve.Interpolate(r, c)` | `Curve.BeginTransition(); Curve.Begin(r, c)` |

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/98kuwa036/codings.git
cd codings/bve5-to-bve4-converter

# 依存関係なし（Python標準ライブラリのみ使用）
# Python 3.7以上が必要です
```

## 使い方

### 単一ファイルの変換

```bash
# 基本的な使い方（出力ファイル名は自動生成）
python src/cli.py route.txt

# 出力ファイル名を指定
python src/cli.py route.txt -o route_bve4.txt

# 詳細モード（変換内容を表示）
python src/cli.py route.txt -v
```

### ディレクトリの一括変換

```bash
# ディレクトリ内のファイルを変換
python src/cli.py ./bve5_data/ -d

# サブディレクトリも含めて再帰的に変換
python src/cli.py ./bve5_data/ -d -r

# 出力ディレクトリを指定
python src/cli.py ./bve5_data/ -d --output-dir ./bve4_data/
```

### オプション

| オプション | 説明 |
|------------|------|
| `-o, --output` | 出力ファイルパス |
| `-d, --directory` | ディレクトリモード |
| `-r, --recursive` | 再帰的に処理 |
| `-v, --verbose` | 詳細出力 |
| `--output-dir` | 出力ディレクトリ |
| `--version` | バージョン表示 |

## 対応ファイル形式

- マップファイル (`.txt`, `.map`)
- ストラクチャーリスト (`.csv`)
- 駅リスト (`.csv`)

## サンプル

### 変換前（BVE5形式）

```
BveTs Map 2.02

// 変数定義
$ballast = 'structures/ballast.csv';
$distance = 1000;

0;
    Structure.Load('ballast', $ballast);
    Repeater['rep1'].Begin(0, 'Rail1', 'ballast', 0, 0, 0, 0, 0, 0, 0, 25);

$distance;
    Fog.Set(500, 200, 200, 200);
    Curve.Interpolate(400, 0.105);
```

### 変換後（BVE4形式）

```
BveTs Map 1.00

// 変数定義


0;
    Structure['ballast'].Load('structures/ballast.csv');


1000;
    Legacy.Fog(0, 500, 200, 200, 200);
    Curve.BeginTransition();
Curve.Begin(400, 0.105);
```

## Pythonからの使用

```python
from src.converter import BVE5ToBVE4Converter

# コンバーターを初期化
converter = BVE5ToBVE4Converter()

# 文字列を変換
content = """BveTs Map 2.02
0;
    Structure.Load('test', 'test.csv');
"""
converted, result = converter.convert_map_file(content)
print(converted)
print(f"削除された行: {result.removed_lines}")

# ファイルを変換
result = converter.convert_file('input.txt', 'output.txt')
if result.success:
    print("変換成功")
else:
    print("エラー:", result.errors)
```

## 注意事項

1. **バックアップ**: 変換前にオリジナルファイルのバックアップを取ることをお勧めします
2. **手動調整**: 自動変換後、手動での調整が必要な場合があります
3. **動作確認**: 変換後のデータはBVE4で動作確認してください
4. **文字化け**: 特殊文字が含まれる場合、文字化けが発生する可能性があります

## 制限事項

- `include`で読み込まれるファイルの内容は展開されません（別途変換が必要）
- 複雑な変数式は正しく展開されない場合があります
- BVE5固有のオブジェクト（3Dモデル等）は別途対応が必要です

## ライセンス

MIT License

## 更新履歴

### v1.0.0
- 初回リリース
- マップファイル変換対応
- ストラクチャーリスト変換対応
- 駅リスト変換対応
