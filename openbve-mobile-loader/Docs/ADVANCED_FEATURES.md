## 高度な機能ガイド

openBVE Mobile Loaderの高度な機能について説明します。

## 目次

1. [DirectX Xファイル対応](#directx-xファイル対応)
2. [動的オブジェクトシステム](#動的オブジェクトシステム)
3. [スクリプトエンジン](#スクリプトエンジン)
4. [高度なグラフィックス](#高度なグラフィックス)
5. [BVE5完全対応](#bve5完全対応)

---

## DirectX Xファイル対応

### 概要

DirectX .X形式の3Dモデルを完全サポート。
テキスト形式のXファイルをランタイムで読み込み、Unityメッシュに変換します。

### 対応機能

✅ **頂点データ**
- 頂点座標
- 法線
- テクスチャ座標（UV）

✅ **面データ**
- 三角形、四角形、N角形
- 自動三角形分割

✅ **マテリアル**
- Diffuse色
- Specular色
- Emissive色（発光）
- Specular Power
- テクスチャファイル

### 使用方法

```csharp
// ModelLoaderが自動的に.xファイルを検出
GameObject model = modelLoader.LoadModel("path/to/model.x", defaultMaterial);
```

### Xファイル形式

```
xof 0303txt 0032

Mesh {
  4;  // 頂点数
  0.0; 0.0; 0.0;,  // 頂点1
  1.0; 0.0; 0.0;,  // 頂点2
  1.0; 1.0; 0.0;,  // 頂点3
  0.0; 1.0; 0.0;;  // 頂点4

  1;  // 面数
  4;0,1,2,3;;  // 四角形

  MeshNormals {
    4;
    0.0; 0.0; 1.0;,
    0.0; 0.0; 1.0;,
    0.0; 0.0; 1.0;,
    0.0; 0.0; 1.0;;
    1;
    4;0,1,2,3;;
  }

  MeshTextureCoords {
    4;
    0.0; 0.0;,
    1.0; 0.0;,
    1.0; 1.0;,
    0.0; 1.0;;
  }

  MeshMaterialList {
    1; 1; 0;
    Material {
      1.0; 1.0; 1.0; 1.0;;
      50.0;
      1.0; 1.0; 1.0;;
      0.0; 0.0; 0.0;;
      TextureFilename {
        "texture.png";
      }
    }
  }
}
```

### 制限事項

- ❌ バイナリXファイル（テキスト形式のみ）
- ❌ アニメーション（今後対応予定）
- ❌ スキンメッシュ（今後対応予定）

---

## 動的オブジェクトシステム

### 概要

オブジェクトにアニメーション、移動、回転、スクリプト制御を追加。

### オブジェクトタイプ

#### 1. Static（静的）
通常の動かないオブジェクト。

#### 2. Animated（アニメーション）
Unityアニメーションコンポーネントで制御。

```csharp
var definition = new DynamicObjectDefinition
{
    Type = DynamicObjectType.Animated,
    AnimationName = "DoorOpen",
    AnimationSpeed = 1.0f,
    AnimationLoop = true
};
```

#### 3. Translating（移動）
指定方向に往復または一方向移動。

```csharp
var definition = new DynamicObjectDefinition
{
    Type = DynamicObjectType.Translating,
    TranslateDirection = Vector3.right,
    TranslateSpeed = 2.0f,
    TranslateDistance = 10f,
    TranslatePingPong = true  // 往復
};
```

#### 4. Rotating（回転）
指定軸で回転。

```csharp
var definition = new DynamicObjectDefinition
{
    Type = DynamicObjectType.Rotating,
    RotationAxis = Vector3.up,
    RotationSpeed = 30f  // 度/秒
};
```

#### 5. Scripted（スクリプト制御）
カスタムスクリプトで完全制御。

```csharp
var definition = new DynamicObjectDefinition
{
    Type = DynamicObjectType.Scripted,
    ScriptName = "custom_behavior"
};
```

### 使用方法

```csharp
// システムを取得
DynamicObjectSystem dynSystem = GetComponent<DynamicObjectSystem>();

// 定義を登録
dynSystem.RegisterDefinition("rotating_sign", rotatingDefinition);

// オブジェクトを作成
GameObject obj = dynSystem.CreateDynamicObject(
    "rotating_sign",
    prefab,
    position,
    rotation
);
```

### BVEデータでの使用

路線CSVファイルで動的オブジェクトを指定：

```csv
; 回転する看板
Structure.Object(10), rotating_sign.csv
1000, Track.FreeObj(0; 10; 5; 0; 0)
```

---

## スクリプトエンジン

### 概要

C#スクリプトでオブジェクトの動作をカスタマイズ。

### ビルトインスクリプト

#### rotate_y
Y軸回転

```csharp
context.Variables["speed"] = 45f;  // 45度/秒
scriptEngine.ExecuteObjectScript("rotate_y", obj, time);
```

#### bounce
上下バウンス

```csharp
context.Variables["amplitude"] = 0.5f;  // 振幅
context.Variables["frequency"] = 2f;    // 周波数
scriptEngine.ExecuteObjectScript("bounce", obj, time);
```

#### flash
点滅

```csharp
context.Variables["interval"] = 0.5f;  // 0.5秒ごと
scriptEngine.ExecuteObjectScript("flash", obj, time);
```

#### door_open_close
ドア開閉

```csharp
context.Variables["door_open"] = true;
context.Variables["open_distance"] = 1.5f;
context.Variables["speed"] = 2f;
scriptEngine.ExecuteObjectScript("door_open_close", obj, time);
```

### カスタムスクリプト作成

#### 方法1: C#クラス

```csharp
public class MyCustomScript : IObjectScript
{
    public void Execute(GameObject obj, ScriptEngine.ScriptContext context)
    {
        // カスタム動作
        float speed = (float)context.Variables.GetValueOrDefault("speed", 1f);
        obj.transform.Rotate(Vector3.up, speed * Time.deltaTime);
    }
}

// 登録
scriptEngine.RegisterScript("my_custom", new MyCustomScript());
```

#### 方法2: テキストスクリプト

```
// script.txt
rotate y 30
bounce amplitude=1.0 frequency=2.0
```

```csharp
// 読み込み
string scriptText = File.ReadAllText("script.txt");
IObjectScript script = CustomScriptLoader.ParseScript(scriptText);
scriptEngine.RegisterScript("from_file", script);
```

---

## 高度なグラフィックス

### 概要

高品質なビジュアル表現のための機能。

### 品質設定

```csharp
AdvancedGraphicsSystem graphics = GetComponent<AdvancedGraphicsSystem>();

// 品質レベル設定
graphics.SetQuality(GraphicsQuality.High);
```

**品質レベル**:
- `Low`: シャドウなし、低解像度
- `Medium`: ハードシャドウ
- `High`: ソフトシャドウ、高品質
- `Ultra`: 最高品質、VeryHighシャドウ

### ダイナミックライティング

時刻に応じた自動ライティング調整。

```csharp
// 時刻設定（0-24時間）
graphics.SetTimeOfDay(16.5f);  // 16:30

// 自動的にライトの色と強度が変化
// 6:00-8:00: 日の出（オレンジ）
// 18:00-20:00: 日没（オレンジ）
// 20:00-6:00: 夜（暗い青）
```

### 霧エフェクト

```csharp
graphics.SetFog(
    enabled: true,
    color: Color.gray,
    density: 0.01f
);
```

### パーティクルエフェクト

#### 雨

```csharp
graphics.StartRain(intensity: 1.0f);
```

#### 雪

```csharp
graphics.StartSnow(intensity: 0.5f);
```

#### カスタムパーティクル

```csharp
ParticleSystem ps = graphics.CreateParticleEffect(
    position: new Vector3(0, 5, 0),
    color: Color.white,
    size: 1.0f,
    lifetime: 2.0f
);
```

### カスタムシェーダー

```csharp
// カスタムマテリアル作成
Material mat = graphics.CreateMaterial(
    shaderName: "Standard",
    color: Color.white,
    texture: myTexture,
    emissive: true  // 発光
);
```

### シェーダー種類

- `Standard`: Unity標準PBRシェーダー
- `Unlit`: ライティングなし
- `Transparent`: 透明
- カスタムシェーダー（Resources/Shadersから）

---

## BVE5完全対応

### 概要

BVE5のテキストマップファイル形式を完全サポート。

### ファイル構造

```
Route/
├── map.txt          # メインマップファイル
├── Structures/
│   ├── ground.csv
│   ├── rail.x
│   └── building.b3d
├── Stations/
│   └── station1.txt
└── Sounds/
    └── ambient.wav
```

### マップファイル形式

```
; BVE5 Map File
BveAts.Map.Load('submaps/section1.txt');

Structure.Load('ground_1', 'Structures/ground.csv');
Structure.Load('building_1', 'Structures/building.x');

Station.Load('sta1', 'Stations/station1.txt');

Sound.Load('ambient', 'Sounds/ambient.wav');

0; Curve(0);
0; Gradient(0);
0; Structure.Put('ground_1');

1000; Station.Put('sta1');
1000; Structure.Put('building_1', 5, 0, 0);

2000; Curve(500, 100);
3000; Curve(0);
```

### 対応コマンド

#### ファイル読み込み
- ✅ `Map.Load`: 入れ子マップファイル
- ✅ `Structure.Load`: 構造物定義
- ✅ `Station.Load`: 駅定義
- ✅ `Signal.Load`: 信号定義
- ✅ `Sound.Load`: サウンド定義

#### 線形
- ✅ `Curve`: 曲線
- ✅ `Gradient`: 勾配
- ✅ `Curve.SetGauge`: カント付き曲線

#### 配置
- ✅ `Structure.Put`: 構造物配置
- ✅ `Structure.PutBetween`: 区間繰り返し配置
- ✅ `Station.Put`: 駅配置

### 入れ子構造

BVE5は複数のマップファイルを組み合わせ可能：

**main.txt**:
```
Map.Load('section1.txt');
Map.Load('section2.txt');
Map.Load('section3.txt');
```

**section1.txt**:
```
0; Structure.Put('ground_1');
1000; Curve(400);
```

システムが自動的に再帰読み込み。

### railsim互換性

railsim形式のコマンドも一部対応：

```
; railsim style
Object.Load(0, 'model.x');
0, Object.Put(0, 5, 0);
```

---

## パフォーマンス最適化

### 動的オブジェクト

```csharp
// 一時停止（パフォーマンス向上）
dynSystem.SetPaused(true);

// 再開
dynSystem.SetPaused(false);

// すべてクリア（メモリ解放）
dynSystem.ClearAll();
```

### グラフィックス

```csharp
// モバイル向け低品質設定
graphics.SetQuality(GraphicsQuality.Low);

// パーティクル無効化
graphics.StopAllEffects();
```

### スクリプト

```csharp
// スクリプト実行を無効化
scriptEngine.enableScripts = false;
```

---

## トラブルシューティング

### Xファイルが読み込めない

**問題**: バイナリXファイル
**解決**: テキスト形式に変換

```bash
# Blenderで変換
blender --background --python convert_x_to_text.py model.x
```

### 動的オブジェクトが動かない

**確認事項**:
1. DynamicObjectSystem が有効か
2. 定義が正しく登録されているか
3. Update が呼ばれているか

```csharp
Debug.Log(dynSystem.GetStats());
```

### スクリプトエラー

```csharp
// エラーログ確認
// Console に [ScriptEngine] Script error が表示される
```

### グラフィックスが重い

**解決策**:
1. 品質を下げる: `SetQuality(GraphicsQuality.Low)`
2. シャドウを無効化
3. パーティクルを停止
4. 霧を無効化

---

## サンプルコード

### 完全な動的オブジェクト設定

```csharp
using UnityEngine;
using OpenBveMobile.Core;

public class DynamicObjectSetup : MonoBehaviour
{
    void Start()
    {
        var dynSystem = gameObject.AddComponent<DynamicObjectSystem>();

        // 回転する風車
        var windmill = new DynamicObjectDefinition
        {
            ObjectKey = "windmill",
            Type = DynamicObjectType.Rotating,
            RotationAxis = Vector3.forward,
            RotationSpeed = 20f
        };
        dynSystem.RegisterDefinition("windmill", windmill);

        // 往復する電車
        var train = new DynamicObjectDefinition
        {
            ObjectKey = "shuttle_train",
            Type = DynamicObjectType.Translating,
            TranslateDirection = Vector3.forward,
            TranslateSpeed = 5f,
            TranslateDistance = 100f,
            TranslatePingPong = true
        };
        dynSystem.RegisterDefinition("shuttle", train);
    }
}
```

### スクリプトエンジン統合

```csharp
using UnityEngine;
using OpenBveMobile.Core;

public class ScriptSetup : MonoBehaviour
{
    void Start()
    {
        var scriptEngine = gameObject.AddComponent<ScriptEngine>();

        // カスタムスクリプト登録
        scriptEngine.RegisterScript("pulse", new PulseScript());
    }
}

public class PulseScript : IObjectScript
{
    public void Execute(GameObject obj, ScriptEngine.ScriptContext context)
    {
        float scale = 1f + Mathf.Sin(context.TimeElapsed * 2f) * 0.2f;
        obj.transform.localScale = Vector3.one * scale;
    }
}
```

---

## 参考資料

- [BVE5公式サイト](http://bvets.net/jp/)
- [DirectX X File Format](https://docs.microsoft.com/en-us/windows/win32/direct3d9/dx9-graphics-reference-x-file-format)
- [Unity Particle System](https://docs.unity3d.com/Manual/class-ParticleSystem.html)
- [Unity Shader Reference](https://docs.unity3d.com/Manual/SL-Reference.html)
