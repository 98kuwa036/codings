# サウンドシステムガイド

openBVE Mobile Loaderのサウンドシステムについて説明します。

## 概要

WAV形式のサウンドファイルをランタイムでロード・再生できます。
列車のモーター音、ブレーキ音、警笛、ドア開閉音などに対応。

## 対応フォーマット

### 完全対応
- **WAV**: PCM 8bit/16bit, モノラル/ステレオ
  - ランタイムロード可能
  - 最も推奨されるフォーマット

### Unity事前インポート必要
- **MP3**: Unity Editorでインポート必要
- **OGG**: Unity Editorでインポート必要

## サウンドファイル構成

### 基本的なフォルダ構造

```
Train/
├── Sound/
│   ├── motor0.wav      # モーター音（0km/h～20km/h）
│   ├── motor1.wav      # モーター音（20km/h～40km/h）
│   ├── motor2.wav      # モーター音（40km/h～60km/h）
│   ├── motor3.wav      # モーター音（60km/h～80km/h）
│   ├── motor4.wav      # モーター音（80km/h～100km/h）
│   ├── motor5.wav      # モーター音（100km/h～）
│   ├── brake.wav       # ブレーキ音
│   ├── brake_release.wav # ブレーキ緩解音
│   ├── brake_emergency.wav # 非常ブレーキ音
│   ├── run.wav         # 走行音（レール音）
│   ├── flange.wav      # フランジ音（カーブ時）
│   ├── horn.wav        # 警笛
│   ├── bell.wav        # ベル
│   ├── door_open.wav   # ドア開
│   └── door_close.wav  # ドア閉
```

## サウンドの種類

### 1. モーター音（motor0～motor9）

速度に応じて自動的に切り替わります。

```
motor0.wav: 0～20 km/h
motor1.wav: 20～40 km/h
motor2.wav: 40～60 km/h
...
```

**特徴**:
- 力行中のみ再生
- ボリューム：ノッチ数に比例
- ピッチ：速度に比例

### 2. ブレーキ音

```
brake.wav: 常用ブレーキ
brake_release.wav: ブレーキ緩解時
brake_emergency.wav: 非常ブレーキ
```

**再生タイミング**:
- ブレーキノッチを上げた時
- ブレーキを緩めた時
- 非常ブレーキボタンを押した時

### 3. 走行音

```
run.wav: レール音（ループ再生）
flange.wav: フランジ音（カーブ時）
```

**特徴**:
- 速度1km/h以上で再生開始
- ボリューム・ピッチが速度に連動

### 4. 警笛・ベル

```
horn.wav: 警笛（ホーン）
bell.wav: ベル
```

**操作方法**:
- UI上のボタンをタップ
- キーボード: H（Horn）、B（Bell）

### 5. ドア開閉音

```
door_open.wav: ドアが開く音
door_close.wav: ドアが閉まる音
```

**再生タイミング**:
- 駅停車時のドア開閉操作

## Unityでの設定方法

### 1. サウンドマネージャーの配置

```
Hierarchy:
└── SoundManager (自動生成)
```

`SoundManager` は自動的にシングルトンとして生成されます。

### 2. TrainSoundControllerの設定

```
Hierarchy:
└── Train
    └── TrainSoundController (コンポーネント)
```

**設定項目**:
- **Train Controller**: TrainControllerへの参照
- **Sound Directory**: サウンドファイルのディレクトリパス

例:
```
Sound Directory: "Assets/Trains/MyTrain/Sound"
```

### 3. 音量調整

Inspector で各音量を調整可能：
- **Master Volume**: 全体音量
- **Train Volume**: 列車音量
- **Environment Volume**: 環境音量
- **UI Volume**: UI効果音量

## スクリプトからの使用

### サウンドを再生

```csharp
using OpenBveMobile.Audio;

// 2Dサウンド再生
AudioClip clip = SoundManager.Instance.LoadSound("path/to/sound.wav");
SoundManager.Instance.PlaySound(clip, volume: 0.8f, loop: false);

// 3Dサウンド再生
SoundManager.Instance.PlaySound3D(clip, position, volume: 1.0f, loop: true);

// ファイルパスから直接再生
SoundManager.Instance.PlaySoundFromFile("path/to/sound.wav", volume: 1.0f);
```

### 列車サウンドコントロール

```csharp
using OpenBveMobile.Audio;

TrainSoundController soundController = GetComponent<TrainSoundController>();

// サウンドをロード
soundController.LoadTrainSounds("path/to/sound/directory");

// 個別再生
soundController.PlayHorn();        // 警笛
soundController.PlayBell();        // ベル
soundController.PlayBrakeSound();  // ブレーキ音
soundController.PlayDoorSound(true); // ドア開閉音
```

## パフォーマンス最適化

### オーディオソースプール

16個のAudioSourceを事前に確保し、再利用します。
同時に16個以上のサウンドが必要な場合、古いものから上書きされます。

### サウンドキャッシュ

一度ロードしたサウンドはメモリにキャッシュされ、
2回目以降は高速にアクセスできます。

### ストリーミング再生

長い環境音などはストリーミング再生を推奨：
1. Unity Editorでインポート
2. Import Settings → Load Type: "Streaming"

## トラブルシューティング

### サウンドが再生されない

1. **ファイルパスを確認**
   ```
   Debug.Log(Path.GetFullPath("Sound/motor0.wav"));
   ```

2. **WAVフォーマットを確認**
   - PCM形式か確認
   - 8bit/16bitか確認
   - 圧縮形式（ADPCM等）は非対応

3. **Consoleログを確認**
   ```
   [SoundManager] Loaded: motor0.wav
   ```

### 音が小さい/聞こえない

1. **音量設定を確認**
   - SoundManager の Master Volume
   - TrainSoundController の各音量

2. **AudioListener の確認**
   - Main Camera に AudioListener が付いているか
   - 1シーンに1つのみ

### モーター音が変化しない

1. **motor0.wav ~ motor5.wav が存在するか確認**
2. **TrainController が動作しているか確認**
3. **力行ノッチが入っているか確認**

## BVE互換性

### BVE2/4/openBVE

基本的に同じファイル名・構造で互換性があります。

### BVE5

BVE5のサウンド定義（XML形式）からの変換が必要です。
`vehicle.xml` から該当サウンドファイルを抽出してください。

## サンプルコード

### カスタムサウンド再生

```csharp
using UnityEngine;
using OpenBveMobile.Audio;

public class CustomSoundPlayer : MonoBehaviour
{
    void Start()
    {
        // サウンドをロード
        AudioClip mySound = SoundManager.Instance.LoadSound("Sounds/custom.wav");

        // 再生
        SoundManager.Instance.PlaySound(mySound, volume: 0.5f, loop: false);
    }
}
```

### 位置ベースサウンド

```csharp
// 特定位置から音を鳴らす（例：踏切）
Vector3 crossingPosition = new Vector3(100, 0, 500);
AudioClip bellSound = SoundManager.Instance.LoadSound("Sounds/crossing_bell.wav");
SoundManager.Instance.PlaySound3D(bellSound, crossingPosition, volume: 1.0f, loop: true);
```

## 推奨事項

1. **WAV形式を使用**: 最も互換性が高い
2. **適切なサンプリングレート**: 22050Hz または 44100Hz
3. **モノラル推奨**: モーター音・走行音等
4. **ステレオ可**: 環境音・BGM
5. **ファイルサイズ注意**: モバイルではメモリ制限あり

## 参考

- Unity AudioClip: https://docs.unity3d.com/ScriptReference/AudioClip.html
- Unity AudioSource: https://docs.unity3d.com/ScriptReference/AudioSource.html
