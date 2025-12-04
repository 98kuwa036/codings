using UnityEngine;
using OpenBveMobile.Loaders;
using OpenBveMobile.Controllers;
using OpenBveMobile.UI;

namespace OpenBveMobile.Core
{
    /// <summary>
    /// ゲーム全体を管理するメインクラス
    /// </summary>
    public class GameManager : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private RouteLoader routeLoader;
        [SerializeField] private TrainController trainController;
        [SerializeField] private CameraController cameraController;
        [SerializeField] private MobileControlPanel controlPanel;

        [Header("Settings")]
        [SerializeField] private string routeFilePath;
        [SerializeField] private bool autoLoadOnStart = false;

        private static GameManager instance;

        public static GameManager Instance
        {
            get
            {
                if (instance == null)
                {
                    instance = FindObjectOfType<GameManager>();
                }
                return instance;
            }
        }

        private void Awake()
        {
            // シングルトン設定
            if (instance == null)
            {
                instance = this;
                DontDestroyOnLoad(gameObject);
            }
            else
            {
                Destroy(gameObject);
                return;
            }

            // コンポーネント取得
            if (routeLoader == null)
                routeLoader = FindObjectOfType<RouteLoader>();

            if (trainController == null)
                trainController = FindObjectOfType<TrainController>();

            if (cameraController == null)
                cameraController = FindObjectOfType<CameraController>();

            if (controlPanel == null)
                controlPanel = FindObjectOfType<MobileControlPanel>();
        }

        private void Start()
        {
            // 初期設定
            SetupReferences();

            // 自動ロード
            if (autoLoadOnStart && !string.IsNullOrEmpty(routeFilePath))
            {
                LoadRoute(routeFilePath);
            }
        }

        /// <summary>
        /// 参照を設定
        /// </summary>
        private void SetupReferences()
        {
            // カメラを列車に追従させる
            if (cameraController != null && trainController != null)
            {
                cameraController.SetFollowTarget(trainController.transform);
            }

            // UIにTrainControllerを設定
            if (controlPanel != null && trainController != null)
            {
                controlPanel.SetTrainController(trainController);
            }
        }

        /// <summary>
        /// 路線をロード
        /// </summary>
        public void LoadRoute(string filePath)
        {
            Debug.Log($"[GameManager] Loading route: {filePath}");

            if (routeLoader != null)
            {
                routeLoader.LoadRoute(filePath);
                Debug.Log("[GameManager] Route loaded successfully!");
            }
            else
            {
                Debug.LogError("[GameManager] RouteLoader not found!");
            }
        }

        /// <summary>
        /// ゲームを開始
        /// </summary>
        public void StartGame()
        {
            Debug.Log("[GameManager] Game started!");

            if (trainController != null)
            {
                // ブレーキを緩めてスタート準備
                trainController.DecreaseBrakeNotch();
            }
        }

        /// <summary>
        /// ゲームを一時停止
        /// </summary>
        public void PauseGame()
        {
            Time.timeScale = 0f;
            Debug.Log("[GameManager] Game paused");
        }

        /// <summary>
        /// ゲームを再開
        /// </summary>
        public void ResumeGame()
        {
            Time.timeScale = 1f;
            Debug.Log("[GameManager] Game resumed");
        }

        /// <summary>
        /// ゲームを終了
        /// </summary>
        public void QuitGame()
        {
            Debug.Log("[GameManager] Quitting game...");
            Application.Quit();

#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#endif
        }

        // ゲッター

        public RouteLoader GetRouteLoader() => routeLoader;
        public TrainController GetTrainController() => trainController;
        public CameraController GetCameraController() => cameraController;
    }
}
