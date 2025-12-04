using UnityEngine;
using System.Collections.Generic;
using System.IO;
using OpenBveMobile.Controllers;

namespace OpenBveMobile.Audio
{
    /// <summary>
    /// 列車サウンドコントローラー
    /// モーター音、ブレーキ音、警笛等を管理
    /// </summary>
    public class TrainSoundController : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private TrainController trainController;

        [Header("Sound Settings")]
        [SerializeField] private string soundDirectory;

        // サウンドカテゴリー
        private Dictionary<string, AudioClip> motorSounds = new Dictionary<string, AudioClip>();
        private Dictionary<string, AudioClip> brakeSounds = new Dictionary<string, AudioClip>();
        private Dictionary<string, AudioClip> runningSounds = new Dictionary<string, AudioClip>();
        private AudioClip hornSound;
        private AudioClip doorOpenSound;
        private AudioClip doorCloseSound;
        private AudioClip bellSound;

        // オーディオソース
        private AudioSource motorSource;
        private AudioSource brakeSource;
        private AudioSource runningSource;
        private AudioSource hornSource;
        private AudioSource miscSource;

        // 状態管理
        private int currentMotorIndex = 0;
        private float lastSpeed = 0f;

        private void Awake()
        {
            SetupAudioSources();
        }

        private void Start()
        {
            if (trainController == null)
            {
                trainController = GetComponent<TrainController>();
            }

            if (!string.IsNullOrEmpty(soundDirectory))
            {
                LoadTrainSounds(soundDirectory);
            }
        }

        private void Update()
        {
            if (trainController != null)
            {
                UpdateMotorSound();
                UpdateRunningSound();
            }
        }

        /// <summary>
        /// オーディオソースをセットアップ
        /// </summary>
        private void SetupAudioSources()
        {
            // モーター音用
            motorSource = gameObject.AddComponent<AudioSource>();
            motorSource.loop = true;
            motorSource.playOnAwake = false;
            motorSource.spatialBlend = 0f; // 2D

            // ブレーキ音用
            brakeSource = gameObject.AddComponent<AudioSource>();
            brakeSource.loop = false;
            brakeSource.playOnAwake = false;
            brakeSource.spatialBlend = 0f;

            // 走行音用
            runningSource = gameObject.AddComponent<AudioSource>();
            runningSource.loop = true;
            runningSource.playOnAwake = false;
            runningSource.spatialBlend = 0f;

            // 警笛用
            hornSource = gameObject.AddComponent<AudioSource>();
            hornSource.loop = false;
            hornSource.playOnAwake = false;
            hornSource.spatialBlend = 0f;

            // その他効果音用
            miscSource = gameObject.AddComponent<AudioSource>();
            miscSource.loop = false;
            miscSource.playOnAwake = false;
            miscSource.spatialBlend = 0f;

            Debug.Log("[TrainSoundController] Audio sources initialized");
        }

        /// <summary>
        /// 列車サウンドをロード
        /// </summary>
        public void LoadTrainSounds(string directory)
        {
            soundDirectory = directory;

            if (!Directory.Exists(directory))
            {
                Debug.LogWarning($"[TrainSoundController] Sound directory not found: {directory}");
                return;
            }

            Debug.Log($"[TrainSoundController] Loading sounds from: {directory}");

            // モーター音ロード（motor0.wav, motor1.wav, ...）
            for (int i = 0; i < 10; i++)
            {
                string motorPath = Path.Combine(directory, $"motor{i}.wav");
                if (File.Exists(motorPath))
                {
                    AudioClip clip = SoundManager.Instance.LoadSound(motorPath);
                    if (clip != null)
                    {
                        motorSounds[$"motor{i}"] = clip;
                    }
                }
            }

            // ブレーキ音ロード
            LoadSoundIfExists(directory, "brake.wav", clip => brakeSounds["brake"] = clip);
            LoadSoundIfExists(directory, "brake_release.wav", clip => brakeSounds["brake_release"] = clip);
            LoadSoundIfExists(directory, "brake_emergency.wav", clip => brakeSounds["brake_emergency"] = clip);

            // 走行音ロード
            LoadSoundIfExists(directory, "run.wav", clip => runningSounds["run"] = clip);
            LoadSoundIfExists(directory, "flange.wav", clip => runningSounds["flange"] = clip);

            // 警笛
            LoadSoundIfExists(directory, "horn.wav", clip => hornSound = clip);
            LoadSoundIfExists(directory, "bell.wav", clip => bellSound = clip);

            // ドア
            LoadSoundIfExists(directory, "door_open.wav", clip => doorOpenSound = clip);
            LoadSoundIfExists(directory, "door_close.wav", clip => doorCloseSound = clip);

            Debug.Log($"[TrainSoundController] Loaded {motorSounds.Count} motor sounds, " +
                     $"{brakeSounds.Count} brake sounds, {runningSounds.Count} running sounds");
        }

        /// <summary>
        /// サウンドファイルが存在すればロード
        /// </summary>
        private void LoadSoundIfExists(string directory, string fileName, System.Action<AudioClip> onLoaded)
        {
            string path = Path.Combine(directory, fileName);
            if (File.Exists(path))
            {
                AudioClip clip = SoundManager.Instance.LoadSound(path);
                if (clip != null)
                {
                    onLoaded?.Invoke(clip);
                }
            }
        }

        /// <summary>
        /// モーター音を更新（速度に応じて変化）
        /// </summary>
        private void UpdateMotorSound()
        {
            if (motorSounds.Count == 0) return;

            float speed = trainController.GetSpeedKmh();
            int powerNotch = trainController.GetPowerNotch();

            // 力行中のみモーター音を再生
            if (powerNotch > 0)
            {
                // 速度に応じてモーター音のインデックスを変更
                int targetIndex = Mathf.FloorToInt(speed / 20f); // 20km/hごとに切り替え
                targetIndex = Mathf.Clamp(targetIndex, 0, motorSounds.Count - 1);

                if (targetIndex != currentMotorIndex)
                {
                    currentMotorIndex = targetIndex;
                    string key = $"motor{currentMotorIndex}";

                    if (motorSounds.ContainsKey(key))
                    {
                        motorSource.clip = motorSounds[key];
                        motorSource.Play();
                    }
                }

                // ボリューム調整（速度とノッチに比例）
                float volume = Mathf.Lerp(0.3f, 1.0f, powerNotch / 5f);
                motorSource.volume = volume * SoundManager.Instance.GetTrainVolume();

                // ピッチ調整（速度に比例）
                motorSource.pitch = Mathf.Lerp(0.8f, 1.5f, speed / 120f);

                if (!motorSource.isPlaying)
                {
                    motorSource.Play();
                }
            }
            else
            {
                // 惰行時はフェードアウト
                if (motorSource.isPlaying)
                {
                    motorSource.volume = Mathf.Lerp(motorSource.volume, 0f, Time.deltaTime * 2f);

                    if (motorSource.volume < 0.01f)
                    {
                        motorSource.Stop();
                    }
                }
            }

            lastSpeed = speed;
        }

        /// <summary>
        /// 走行音を更新（速度に応じて変化）
        /// </summary>
        private void UpdateRunningSound()
        {
            if (!runningSounds.ContainsKey("run")) return;

            float speed = trainController.GetSpeedKmh();

            if (speed > 1f)
            {
                if (!runningSource.isPlaying)
                {
                    runningSource.clip = runningSounds["run"];
                    runningSource.Play();
                }

                // ボリュームとピッチを速度に応じて調整
                runningSource.volume = Mathf.Lerp(0.1f, 0.6f, speed / 120f) * SoundManager.Instance.GetTrainVolume();
                runningSource.pitch = Mathf.Lerp(0.7f, 1.3f, speed / 120f);
            }
            else
            {
                if (runningSource.isPlaying)
                {
                    runningSource.Stop();
                }
            }
        }

        /// <summary>
        /// ブレーキ音を再生
        /// </summary>
        public void PlayBrakeSound(bool emergency = false)
        {
            string key = emergency ? "brake_emergency" : "brake";

            if (brakeSounds.ContainsKey(key))
            {
                brakeSource.clip = brakeSounds[key];
                brakeSource.volume = SoundManager.Instance.GetTrainVolume();
                brakeSource.Play();
                Debug.Log($"[TrainSoundController] Playing {key}");
            }
        }

        /// <summary>
        /// ブレーキ緩解音を再生
        /// </summary>
        public void PlayBrakeReleaseSound()
        {
            if (brakeSounds.ContainsKey("brake_release"))
            {
                brakeSource.clip = brakeSounds["brake_release"];
                brakeSource.volume = SoundManager.Instance.GetTrainVolume();
                brakeSource.Play();
            }
        }

        /// <summary>
        /// 警笛を再生
        /// </summary>
        public void PlayHorn()
        {
            if (hornSound != null)
            {
                hornSource.clip = hornSound;
                hornSource.volume = SoundManager.Instance.GetTrainVolume();
                hornSource.Play();
                Debug.Log("[TrainSoundController] Horn!");
            }
        }

        /// <summary>
        /// ベルを再生
        /// </summary>
        public void PlayBell()
        {
            if (bellSound != null)
            {
                miscSource.clip = bellSound;
                miscSource.volume = SoundManager.Instance.GetTrainVolume();
                miscSource.Play();
            }
        }

        /// <summary>
        /// ドア開閉音を再生
        /// </summary>
        public void PlayDoorSound(bool opening)
        {
            AudioClip clip = opening ? doorOpenSound : doorCloseSound;

            if (clip != null)
            {
                miscSource.clip = clip;
                miscSource.volume = SoundManager.Instance.GetTrainVolume();
                miscSource.Play();
                Debug.Log($"[TrainSoundController] Door {(opening ? "opening" : "closing")}");
            }
        }

        /// <summary>
        /// すべてのサウンドを停止
        /// </summary>
        public void StopAllSounds()
        {
            motorSource.Stop();
            brakeSource.Stop();
            runningSource.Stop();
            hornSource.Stop();
            miscSource.Stop();
        }
    }
}
