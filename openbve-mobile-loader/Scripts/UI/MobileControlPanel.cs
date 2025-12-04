using UnityEngine;
using UnityEngine.UI;
using OpenBveMobile.Controllers;

namespace OpenBveMobile.UI
{
    /// <summary>
    /// モバイル向け操作パネルUI
    /// </summary>
    public class MobileControlPanel : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private TrainController trainController;

        [Header("UI Elements")]
        [SerializeField] private Text speedText;
        [SerializeField] private Text positionText;
        [SerializeField] private Text powerNotchText;
        [SerializeField] private Text brakeNotchText;
        [SerializeField] private Slider speedSlider;

        [Header("Buttons")]
        [SerializeField] private Button powerUpButton;
        [SerializeField] private Button powerDownButton;
        [SerializeField] private Button brakeUpButton;
        [SerializeField] private Button brakeDownButton;
        [SerializeField] private Button emergencyBrakeButton;
        [SerializeField] private Button reverserButton;
        [SerializeField] private Button hornButton;
        [SerializeField] private Button bellButton;

        private void Start()
        {
            // ボタンイベント設定
            if (powerUpButton != null)
                powerUpButton.onClick.AddListener(OnPowerUp);

            if (powerDownButton != null)
                powerDownButton.onClick.AddListener(OnPowerDown);

            if (brakeUpButton != null)
                brakeUpButton.onClick.AddListener(OnBrakeUp);

            if (brakeDownButton != null)
                brakeDownButton.onClick.AddListener(OnBrakeDown);

            if (emergencyBrakeButton != null)
                emergencyBrakeButton.onClick.AddListener(OnEmergencyBrake);

            if (reverserButton != null)
                reverserButton.onClick.AddListener(OnReverser);

            if (hornButton != null)
                hornButton.onClick.AddListener(OnHorn);

            if (bellButton != null)
                bellButton.onClick.AddListener(OnBell);

            // TrainControllerのイベント購読
            if (trainController != null)
            {
                trainController.OnSpeedChanged += UpdateSpeedDisplay;
                trainController.OnPositionChanged += UpdatePositionDisplay;
                trainController.OnPowerNotchChanged += UpdatePowerNotchDisplay;
                trainController.OnBrakeNotchChanged += UpdateBrakeNotchDisplay;
            }
        }

        private void Update()
        {
            // リアルタイム更新
            if (trainController != null)
            {
                UpdateSpeedDisplay(trainController.GetSpeed());
                UpdatePositionDisplay(trainController.GetPosition());
            }
        }

        // ボタンイベントハンドラ

        private void OnPowerUp()
        {
            if (trainController != null)
                trainController.IncreasePowerNotch();
        }

        private void OnPowerDown()
        {
            if (trainController != null)
                trainController.DecreasePowerNotch();
        }

        private void OnBrakeUp()
        {
            if (trainController != null)
                trainController.IncreaseBrakeNotch();
        }

        private void OnBrakeDown()
        {
            if (trainController != null)
                trainController.DecreaseBrakeNotch();
        }

        private void OnEmergencyBrake()
        {
            if (trainController != null)
                trainController.ApplyEmergencyBrake();
        }

        private void OnReverser()
        {
            if (trainController != null)
                trainController.ToggleReverser();
        }

        private void OnHorn()
        {
            if (trainController != null)
                trainController.BlowHorn();
        }

        private void OnBell()
        {
            if (trainController != null)
                trainController.RingBell();
        }

        // UI更新メソッド

        private void UpdateSpeedDisplay(float speed)
        {
            float speedKmh = speed * 3.6f;

            if (speedText != null)
                speedText.text = $"{speedKmh:F1} km/h";

            if (speedSlider != null)
                speedSlider.value = speedKmh / 120f; // 120km/hを最大として正規化
        }

        private void UpdatePositionDisplay(float position)
        {
            if (positionText != null)
            {
                float positionKm = position / 1000f;
                positionText.text = $"{positionKm:F3} km";
            }
        }

        private void UpdatePowerNotchDisplay(int notch)
        {
            if (powerNotchText != null)
                powerNotchText.text = $"P{notch}";
        }

        private void UpdateBrakeNotchDisplay(int notch)
        {
            if (brakeNotchText != null)
            {
                if (notch > 8)
                    brakeNotchText.text = "EB";
                else
                    brakeNotchText.text = $"B{notch}";
            }
        }

        /// <summary>
        /// TrainControllerを設定
        /// </summary>
        public void SetTrainController(TrainController controller)
        {
            // 既存のイベント購読を解除
            if (trainController != null)
            {
                trainController.OnSpeedChanged -= UpdateSpeedDisplay;
                trainController.OnPositionChanged -= UpdatePositionDisplay;
                trainController.OnPowerNotchChanged -= UpdatePowerNotchDisplay;
                trainController.OnBrakeNotchChanged -= UpdateBrakeNotchDisplay;
            }

            trainController = controller;

            // 新しいイベント購読
            if (trainController != null)
            {
                trainController.OnSpeedChanged += UpdateSpeedDisplay;
                trainController.OnPositionChanged += UpdatePositionDisplay;
                trainController.OnPowerNotchChanged += UpdatePowerNotchDisplay;
                trainController.OnBrakeNotchChanged += UpdateBrakeNotchDisplay;
            }
        }
    }
}
