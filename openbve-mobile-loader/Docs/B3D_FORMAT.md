# B3D (Binary 3D) フォーマット仕様

openBVE独自の3Dモデルフォーマット「B3D」について説明します。

## 概要

B3Dは、openBVEで使用される3Dモデルフォーマットです。
テキストベースのコマンド構造を持ち、頂点・面・テクスチャ等の情報を記述します。

## 基本構造

```
[MeshBuilder]
; コメント行

CreateMeshBuilder
Vertex vX, vY, vZ, nX, nY, nZ
AddFace v0, v1, v2
...
```

## コマンド一覧

### MeshBuilderセクション

#### [MeshBuilder]
メッシュビルダーセクションの開始

```
[MeshBuilder]
```

#### CreateMeshBuilder
新しいメッシュを作成

```
CreateMeshBuilder
```

### 頂点定義

#### Vertex
頂点を追加

```
Vertex vX, vY, vZ
Vertex vX, vY, vZ, nX, nY, nZ
```

引数：
- **vX, vY, vZ**: 頂点座標（メートル単位）
- **nX, nY, nZ**: 法線ベクトル（省略可）

例：
```
Vertex 0, 0, 0
Vertex 1, 0, 0, 0, 1, 0
Vertex 1, 1, 0, 0, 1, 0
Vertex 0, 1, 0, 0, 1, 0
```

### 面定義

#### AddFace / Face
面を追加

```
AddFace v0, v1, v2
AddFace v0, v1, v2, v3
```

引数：
- **v0, v1, v2, ...**: 頂点インデックス（0から開始）

三角形または四角形を定義できます。

例：
```
; 三角形
AddFace 0, 1, 2

; 四角形
AddFace 0, 1, 2, 3
```

#### AddFace2 / Face2
両面レンダリングの面を追加

```
AddFace2 v0, v1, v2
```

裏面も表示されます（フェンス等に使用）。

### テクスチャ

#### SetTexture / LoadTexture
テクスチャを設定

```
SetTexture DayTexture, ファイル名
```

引数：
- **DayTexture**: 昼間用テクスチャ
- **NightTexture**: 夜間用テクスチャ（未実装）

例：
```
SetTexture DayTexture, texture.png
```

#### Coordinates
テクスチャ座標を設定

```
Coordinates 頂点番号, u, v
```

引数：
- **頂点番号**: 対象の頂点インデックス
- **u, v**: テクスチャ座標（0.0～1.0）

例：
```
Coordinates 0, 0, 0
Coordinates 1, 1, 0
Coordinates 2, 1, 1
Coordinates 3, 0, 1
```

### 色設定

#### SetColor
オブジェクトの色を設定

```
SetColor r, g, b, a
```

引数：
- **r, g, b**: RGB値（0～255）
- **a**: アルファ値（0～255、省略可）

例：
```
SetColor 255, 255, 255, 255  ; 白色
SetColor 128, 128, 128        ; グレー
```

#### SetEmissiveColor
発光色を設定

```
SetEmissiveColor r, g, b
```

自己発光するオブジェクト（ライト等）に使用。

例：
```
SetEmissiveColor 255, 255, 0  ; 黄色の発光
```

#### SetTransparentColor
透明色を設定

```
SetTransparentColor r, g, b
```

指定した色を透明にします。

### 変形コマンド

#### Translate
移動

```
Translate x, y, z
```

#### Rotate
回転

```
Rotate x, y, z, angle
```

引数：
- **x, y, z**: 回転軸
- **angle**: 回転角度（度）

例：
```
Rotate 0, 1, 0, 90  ; Y軸周りに90度回転
```

#### Scale
スケール

```
Scale x, y, z
```

例：
```
Scale 2, 2, 2  ; 2倍に拡大
```

## サンプルB3Dファイル

### 例1: シンプルな箱

```
[MeshBuilder]
CreateMeshBuilder

; 頂点定義（立方体）
Vertex -1, 0, -1
Vertex 1, 0, -1
Vertex 1, 0, 1
Vertex -1, 0, 1
Vertex -1, 2, -1
Vertex 1, 2, -1
Vertex 1, 2, 1
Vertex -1, 2, 1

; 面定義
; 底面
AddFace 0, 1, 2, 3

; 前面
AddFace 0, 4, 5, 1

; 右面
AddFace 1, 5, 6, 2

; 背面
AddFace 2, 6, 7, 3

; 左面
AddFace 3, 7, 4, 0

; 上面
AddFace 4, 7, 6, 5

; 色設定
SetColor 200, 200, 200
```

### 例2: テクスチャ付き壁

```
[MeshBuilder]
CreateMeshBuilder

; 頂点
Vertex 0, 0, 0
Vertex 10, 0, 0
Vertex 10, 3, 0
Vertex 0, 3, 0

; テクスチャ座標
Coordinates 0, 0, 0
Coordinates 1, 1, 0
Coordinates 2, 1, 1
Coordinates 3, 0, 1

; 面
AddFace 0, 1, 2, 3

; テクスチャ
SetTexture DayTexture, wall_texture.png
```

### 例3: 発光する信号機

```
[MeshBuilder]
CreateMeshBuilder

; 信号本体
Vertex -0.2, 0, 0
Vertex 0.2, 0, 0
Vertex 0.2, 0.5, 0
Vertex -0.2, 0.5, 0

AddFace 0, 1, 2, 3
SetColor 50, 50, 50

; 信号灯
Vertex -0.1, 0.2, 0.01
Vertex 0.1, 0.2, 0.01
Vertex 0.1, 0.3, 0.01
Vertex -0.1, 0.3, 0.01

AddFace 4, 5, 6, 7
SetEmissiveColor 255, 0, 0  ; 赤色発光
```

## 座標系

openBVEの座標系：
- **X軸**: 右方向が正
- **Y軸**: 上方向が正
- **Z軸**: 進行方向が正（手前から奥）

Unityの座標系と一致しているため、変換不要です。

## 実装状況

### ✅ 実装済み

- [MeshBuilder]
- Vertex（頂点定義）
- Face / AddFace（面定義）
- SetTexture（テクスチャ）
- SetColor（色設定）
- SetEmissiveColor（発光色）

### ⏳ 未実装（今後対応予定）

- Face2 / AddFace2（両面レンダリング）
- Coordinates（テクスチャ座標詳細設定）
- SetTransparentColor（透明色）
- Translate, Rotate, Scale（変形コマンド）
- GenerateNormals（法線自動生成）
- SetBlendMode（ブレンドモード）
- NightTexture（夜間テクスチャ）

## 注意事項

1. **頂点順序**: 反時計回りが表面
2. **法線**: 指定しない場合は自動計算
3. **テクスチャ**: PNG, BMP, JPGに対応
4. **エンコーディング**: UTF-8またはShift-JIS

## 参考

- [openBVE Object Formats](http://openbve-project.net/documentation/HTML/object_native.html)
- [BVE Trainsim Wiki](http://bvets.net/)
