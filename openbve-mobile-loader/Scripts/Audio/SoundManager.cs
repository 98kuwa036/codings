using UnityEngine;
using System.Collections.Generic;
using System.IO;

namespace OpenBveMobile.Audio
{
    /// <summary>
    /// サウンド管理システム
    /// WAV/MP3/OGG対応、3Dオーディオ対応
    /// </summary>
    public class SoundManager : MonoBehaviour
    {
        private static SoundManager instance;
        public static SoundManager Instance
        {
            get
            {
                if (instance == null)
                {
                    GameObject obj = new GameObject("SoundManager");
                    instance = obj.AddComponent<SoundManager>();
                    DontDestroyOnLoad(obj);
                }
                return instance;
            }
        }

        [Header("Settings")]
        [SerializeField] [Range(0f, 1f)] private float masterVolume = 1.0f;
        [SerializeField] [Range(0f, 1f)] private float trainVolume = 1.0f;
        [SerializeField] [Range(0f, 1f)] private float environmentVolume = 0.8f;
        [SerializeField] [Range(0f, 1f)] private float uiVolume = 0.7f;

        // サウンドキャッシュ
        private Dictionary<string, AudioClip> audioCache = new Dictionary<string, AudioClip>();

        // オーディオソースプール
        private List<AudioSource> audioSourcePool = new List<AudioSource>();
        private const int POOL_SIZE = 16;

        private void Awake()
        {
            if (instance == null)
            {
                instance = this;
                DontDestroyOnLoad(gameObject);
                InitializeAudioSourcePool();
            }
            else if (instance != this)
            {
                Destroy(gameObject);
            }
        }

        /// <summary>
        /// オーディオソースプールを初期化
        /// </summary>
        private void InitializeAudioSourcePool()
        {
            for (int i = 0; i < POOL_SIZE; i++)
            {
                GameObject audioObj = new GameObject($"AudioSource_{i}");
                audioObj.transform.SetParent(transform);
                AudioSource source = audioObj.AddComponent<AudioSource>();
                source.playOnAwake = false;
                audioSourcePool.Add(source);
            }

            Debug.Log($"[SoundManager] Initialized with {POOL_SIZE} audio sources");
        }

        /// <summary>
        /// サウンドファイルをロード
        /// </summary>
        public AudioClip LoadSound(string filePath)
        {
            // キャッシュチェック
            if (audioCache.ContainsKey(filePath))
            {
                return audioCache[filePath];
            }

            if (!File.Exists(filePath))
            {
                Debug.LogWarning($"[SoundManager] File not found: {filePath}");
                return null;
            }

            string extension = Path.GetExtension(filePath).ToLowerInvariant();

            try
            {
                AudioClip clip = null;

                switch (extension)
                {
                    case ".wav":
                        clip = LoadWav(filePath);
                        break;

                    case ".mp3":
                    case ".ogg":
                        // Unity標準のロード（ランタイムでは制限あり）
                        Debug.LogWarning($"[SoundManager] {extension} requires pre-import in Unity");
                        break;

                    default:
                        Debug.LogWarning($"[SoundManager] Unsupported audio format: {extension}");
                        break;
                }

                if (clip != null)
                {
                    audioCache[filePath] = clip;
                    Debug.Log($"[SoundManager] Loaded: {Path.GetFileName(filePath)}");
                }

                return clip;
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[SoundManager] Failed to load {filePath}: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// WAVファイルをロード（ランタイム対応）
        /// </summary>
        private AudioClip LoadWav(string filePath)
        {
            byte[] fileBytes = File.ReadAllBytes(filePath);
            return WavUtility.ToAudioClip(fileBytes, Path.GetFileNameWithoutExtension(filePath));
        }

        /// <summary>
        /// サウンドを再生（2D）
        /// </summary>
        public AudioSource PlaySound(AudioClip clip, float volume = 1.0f, bool loop = false)
        {
            if (clip == null) return null;

            AudioSource source = GetAvailableAudioSource();
            if (source == null) return null;

            source.clip = clip;
            source.volume = volume * masterVolume;
            source.loop = loop;
            source.spatialBlend = 0f; // 2D
            source.Play();

            return source;
        }

        /// <summary>
        /// サウンドを再生（3D位置指定）
        /// </summary>
        public AudioSource PlaySound3D(AudioClip clip, Vector3 position, float volume = 1.0f, bool loop = false, float minDistance = 1f, float maxDistance = 50f)
        {
            if (clip == null) return null;

            AudioSource source = GetAvailableAudioSource();
            if (source == null) return null;

            source.transform.position = position;
            source.clip = clip;
            source.volume = volume * masterVolume;
            source.loop = loop;
            source.spatialBlend = 1f; // 3D
            source.minDistance = minDistance;
            source.maxDistance = maxDistance;
            source.rolloffMode = AudioRolloffMode.Linear;
            source.Play();

            return source;
        }

        /// <summary>
        /// サウンドを再生（ファイルパス指定）
        /// </summary>
        public AudioSource PlaySoundFromFile(string filePath, float volume = 1.0f, bool loop = false)
        {
            AudioClip clip = LoadSound(filePath);
            return PlaySound(clip, volume, loop);
        }

        /// <summary>
        /// サウンドを再生（3D、ファイルパス指定）
        /// </summary>
        public AudioSource PlaySoundFromFile3D(string filePath, Vector3 position, float volume = 1.0f, bool loop = false)
        {
            AudioClip clip = LoadSound(filePath);
            return PlaySound3D(clip, position, volume, loop);
        }

        /// <summary>
        /// 利用可能なオーディオソースを取得
        /// </summary>
        private AudioSource GetAvailableAudioSource()
        {
            // 再生していないソースを探す
            foreach (var source in audioSourcePool)
            {
                if (!source.isPlaying)
                {
                    return source;
                }
            }

            // 全て使用中の場合は最も古いものを使う
            Debug.LogWarning("[SoundManager] All audio sources in use, recycling oldest");
            return audioSourcePool[0];
        }

        /// <summary>
        /// すべてのサウンドを停止
        /// </summary>
        public void StopAllSounds()
        {
            foreach (var source in audioSourcePool)
            {
                source.Stop();
            }
        }

        /// <summary>
        /// 音量設定
        /// </summary>
        public void SetMasterVolume(float volume)
        {
            masterVolume = Mathf.Clamp01(volume);
        }

        public void SetTrainVolume(float volume)
        {
            trainVolume = Mathf.Clamp01(volume);
        }

        public void SetEnvironmentVolume(float volume)
        {
            environmentVolume = Mathf.Clamp01(volume);
        }

        // ゲッター
        public float GetMasterVolume() => masterVolume;
        public float GetTrainVolume() => trainVolume;
        public float GetEnvironmentVolume() => environmentVolume;
        public float GetUIVolume() => uiVolume;
    }

    /// <summary>
    /// WAVファイル読み込みユーティリティ
    /// </summary>
    public static class WavUtility
    {
        public static AudioClip ToAudioClip(byte[] wavBytes, string name = "wav")
        {
            // WAVヘッダー解析
            int headerOffset = 12; // RIFF header
            int subchunk1 = System.BitConverter.ToInt32(wavBytes, 16);
            int audioFormat = System.BitConverter.ToInt16(wavBytes, 20);

            // サポートされているのはPCM (1)のみ
            if (audioFormat != 1)
            {
                Debug.LogError($"[WavUtility] Unsupported audio format: {audioFormat}");
                return null;
            }

            int channels = System.BitConverter.ToInt16(wavBytes, 22);
            int sampleRate = System.BitConverter.ToInt32(wavBytes, 24);
            int bitDepth = System.BitConverter.ToInt16(wavBytes, 34);

            int dataOffset = 36 + subchunk1 - 16;

            // "data" チャンクを探す
            while (dataOffset < wavBytes.Length - 8)
            {
                string chunkId = System.Text.Encoding.ASCII.GetString(wavBytes, dataOffset, 4);
                int chunkSize = System.BitConverter.ToInt32(wavBytes, dataOffset + 4);

                if (chunkId == "data")
                {
                    dataOffset += 8;
                    break;
                }

                dataOffset += 8 + chunkSize;
            }

            if (dataOffset >= wavBytes.Length)
            {
                Debug.LogError("[WavUtility] Could not find data chunk");
                return null;
            }

            // サンプルデータを抽出
            int sampleCount = (wavBytes.Length - dataOffset) / (bitDepth / 8) / channels;
            float[] samples = new float[sampleCount * channels];

            if (bitDepth == 16)
            {
                for (int i = 0; i < sampleCount * channels; i++)
                {
                    short sample = System.BitConverter.ToInt16(wavBytes, dataOffset + i * 2);
                    samples[i] = sample / 32768f;
                }
            }
            else if (bitDepth == 8)
            {
                for (int i = 0; i < sampleCount * channels; i++)
                {
                    byte sample = wavBytes[dataOffset + i];
                    samples[i] = (sample - 128) / 128f;
                }
            }

            // AudioClip作成
            AudioClip audioClip = AudioClip.Create(name, sampleCount, channels, sampleRate, false);
            audioClip.SetData(samples, 0);

            Debug.Log($"[WavUtility] Loaded WAV: {name} ({sampleRate}Hz, {channels}ch, {bitDepth}bit)");
            return audioClip;
        }
    }
}
