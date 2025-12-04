using UnityEngine;
using OpenBveMobile.Audio;

namespace OpenBveMobile.Controllers
{
    /// <summary>
    /// 列車コントローラー
    /// 基本的な運転操作（加速/減速）とシミュレーション
    /// </summary>
    public class TrainController : MonoBehaviour
    {
        [Header("Sound")]
        [SerializeField] private TrainSoundController soundController;
        [Header("Train Parameters")]
        [SerializeField] private float mass = 40000f; // 質量（kg）
        [SerializeField] private float maxAcceleration = 1.0f; // 最大加速度（m/s²）
        [SerializeField] private float maxBrakeDeceleration = 3.0f; // 最大減速度（m/s²）
        [SerializeField] private float maxSpeed = 120f / 3.6f; // 最高速度（m/s）

        [Header("Control Settings")]
        [SerializeField] private int notchCount = 5; // ノッチ段数
        [SerializeField] private int brakeNotchCount = 8; // ブレーキノッチ段数

        [Header("Current State")]
        [SerializeField] private float currentSpeed = 0f; // 現在速度（m/s）
        [SerializeField] private float currentPosition = 0f; // 現在位置（m）
        [SerializeField] private int powerNotch = 0; // 力行ノッチ
        [SerializeField] private int brakeNotch = brakeNotchCount; // ブレーキノッチ（初期値：常用最大）
        [SerializeField] private bool reverserForward = true; // レバーサー（前進/後進）

        // 物理演算
        private float resistance = 0f; // 走行抵抗
        private float gradient = 0f; // 勾配（パーミル）

        // イベント
        public System.Action<float> OnSpeedChanged;
        public System.Action<float> OnPositionChanged;
        public System.Action<int> OnPowerNotchChanged;
        public System.Action<int> OnBrakeNotchChanged;

        private void Start()
        {
            // 初期状態
            currentSpeed = 0f;
            currentPosition = 0f;
            powerNotch = 0;
            brakeNotch = brakeNotchCount; // フルブレーキでスタート

            // サウンドコントローラー取得
            if (soundController == null)
            {
                soundController = GetComponent<TrainSoundController>();
            }
        }

        private void Update()
        {
            // 物理演算
            UpdatePhysics();

            // 位置更新
            currentPosition += currentSpeed * Time.deltaTime;

            // オブジェクトを移動
            transform.position = new Vector3(0, 0, currentPosition);

            // イベント発火
            OnPositionChanged?.Invoke(currentPosition);
        }

        /// <summary>
        /// 物理演算
        /// </summary>
        private void UpdatePhysics()
        {
            // 加速度計算
            float acceleration = CalculateAcceleration();

            // 速度更新
            float oldSpeed = currentSpeed;
            currentSpeed += acceleration * Time.deltaTime;

            // 速度制限
            currentSpeed = Mathf.Clamp(currentSpeed, 0f, maxSpeed);

            // 速度が変化した場合イベント発火
            if (Mathf.Abs(currentSpeed - oldSpeed) > 0.01f)
            {
                OnSpeedChanged?.Invoke(currentSpeed);
            }
        }

        /// <summary>
        /// 加速度を計算
        /// </summary>
        private float CalculateAcceleration()
        {
            float totalAcceleration = 0f;

            // 力行による加速
            if (powerNotch > 0 && brakeNotch == 0)
            {
                float powerRatio = (float)powerNotch / notchCount;
                totalAcceleration += maxAcceleration * powerRatio;
            }

            // ブレーキによる減速
            if (brakeNotch > 0)
            {
                float brakeRatio = (float)brakeNotch / brakeNotchCount;
                totalAcceleration -= maxBrakeDeceleration * brakeRatio;
            }

            // 走行抵抗（速度に比例）
            resistance = CalculateRunningResistance();
            totalAcceleration -= resistance;

            // 勾配抵抗
            float gradientResistance = gradient * 0.00981f; // パーミルをm/s²に変換
            totalAcceleration -= gradientResistance;

            return totalAcceleration;
        }

        /// <summary>
        /// 走行抵抗を計算（簡易版）
        /// </summary>
        private float CalculateRunningResistance()
        {
            // デービス式の簡易版：R = a + bv + cv²
            float a = 0.005f;
            float b = 0.0001f;
            float c = 0.00005f;

            float v_kmh = currentSpeed * 3.6f;
            return a + b * v_kmh + c * v_kmh * v_kmh;
        }

        // 操作メソッド

        /// <summary>
        /// 力行ノッチを上げる
        /// </summary>
        public void IncreasePowerNotch()
        {
            if (brakeNotch == 0 && powerNotch < notchCount)
            {
                powerNotch++;
                OnPowerNotchChanged?.Invoke(powerNotch);
                Debug.Log($"[TrainController] Power notch: {powerNotch}");
            }
            else if (brakeNotch > 0)
            {
                Debug.Log("[TrainController] Release brake first");
            }
        }

        /// <summary>
        /// 警笛を鳴らす
        /// </summary>
        public void BlowHorn()
        {
            soundController?.PlayHorn();
        }

        /// <summary>
        /// ベルを鳴らす
        /// </summary>
        public void RingBell()
        {
            soundController?.PlayBell();
        }

        /// <summary>
        /// 力行ノッチを下げる
        /// </summary>
        public void DecreasePowerNotch()
        {
            if (powerNotch > 0)
            {
                powerNotch--;
                OnPowerNotchChanged?.Invoke(powerNotch);
                Debug.Log($"[TrainController] Power notch: {powerNotch}");
            }
        }

        /// <summary>
        /// ブレーキノッチを上げる（強める）
        /// </summary>
        public void IncreaseBrakeNotch()
        {
            if (brakeNotch < brakeNotchCount)
            {
                brakeNotch++;
                powerNotch = 0; // 力行を切る
                OnBrakeNotchChanged?.Invoke(brakeNotch);
                soundController?.PlayBrakeSound(false);
                Debug.Log($"[TrainController] Brake notch: {brakeNotch}");
            }
        }

        /// <summary>
        /// ブレーキノッチを下げる（緩める）
        /// </summary>
        public void DecreaseBrakeNotch()
        {
            if (brakeNotch > 0)
            {
                brakeNotch--;
                OnBrakeNotchChanged?.Invoke(brakeNotch);
                soundController?.PlayBrakeReleaseSound();
                Debug.Log($"[TrainController] Brake notch: {brakeNotch}");
            }
        }

        /// <summary>
        /// 緊急ブレーキ
        /// </summary>
        public void ApplyEmergencyBrake()
        {
            brakeNotch = brakeNotchCount + 1; // 非常ブレーキ
            powerNotch = 0;
            soundController?.PlayBrakeSound(true);
            Debug.Log("[TrainController] Emergency brake applied!");
        }

        /// <summary>
        /// レバーサー切り替え
        /// </summary>
        public void ToggleReverser()
        {
            if (currentSpeed < 0.1f)
            {
                reverserForward = !reverserForward;
                Debug.Log($"[TrainController] Reverser: {(reverserForward ? "Forward" : "Backward")}");
            }
            else
            {
                Debug.Log("[TrainController] Stop the train before changing reverser");
            }
        }

        // ゲッター

        public float GetSpeed() => currentSpeed;
        public float GetSpeedKmh() => currentSpeed * 3.6f;
        public float GetPosition() => currentPosition;
        public int GetPowerNotch() => powerNotch;
        public int GetBrakeNotch() => brakeNotch;
        public bool IsForward() => reverserForward;

        /// <summary>
        /// 勾配を設定
        /// </summary>
        public void SetGradient(float gradientPermil)
        {
            gradient = gradientPermil;
        }

        /// <summary>
        /// 速度制限を設定
        /// </summary>
        public void SetSpeedLimit(float limitKmh)
        {
            maxSpeed = limitKmh / 3.6f;
        }
    }
}
