using UnityEngine;

namespace OpenBveMobile.Controllers
{
    /// <summary>
    /// モバイル対応カメラコントローラー
    /// タッチ操作で視点移動、列車追従機能
    /// </summary>
    public class CameraController : MonoBehaviour
    {
        [Header("Camera Settings")]
        [SerializeField] private float moveSpeed = 50f;
        [SerializeField] private float rotationSpeed = 100f;
        [SerializeField] private float zoomSpeed = 50f;
        [SerializeField] private float minHeight = 0.5f;
        [SerializeField] private float maxHeight = 100f;

        [Header("Touch Settings")]
        [SerializeField] private float touchSensitivity = 0.5f;
        [SerializeField] private float pinchZoomSpeed = 0.1f;

        [Header("Follow Settings")]
        [SerializeField] private Transform targetToFollow;
        [SerializeField] private Vector3 followOffset = new Vector3(0, 2, -5);
        [SerializeField] private bool isFollowing = true;

        private Camera mainCamera;
        private Vector2 lastTouchPosition;
        private float lastPinchDistance;

        // カメラモード
        public enum CameraMode
        {
            Free,           // 自由視点
            FollowTrain,    // 列車追従
            CabView,        // 運転台視点
            ExteriorView    // 外部視点
        }

        [SerializeField] private CameraMode currentMode = CameraMode.FollowTrain;

        private void Awake()
        {
            mainCamera = GetComponent<Camera>();
            if (mainCamera == null)
            {
                mainCamera = Camera.main;
            }
        }

        private void Update()
        {
            HandleInput();

            if (currentMode == CameraMode.FollowTrain && targetToFollow != null)
            {
                FollowTarget();
            }
        }

        /// <summary>
        /// 入力処理
        /// </summary>
        private void HandleInput()
        {
            // モバイルタッチ入力
            if (Input.touchCount > 0)
            {
                HandleTouchInput();
            }
            // PC向けキーボード/マウス入力
            else
            {
                HandleKeyboardMouseInput();
            }
        }

        /// <summary>
        /// タッチ入力処理
        /// </summary>
        private void HandleTouchInput()
        {
            // 1本指：カメラ回転
            if (Input.touchCount == 1)
            {
                Touch touch = Input.GetTouch(0);

                if (touch.phase == TouchPhase.Moved)
                {
                    Vector2 delta = touch.deltaPosition * touchSensitivity;

                    // カメラ回転
                    transform.Rotate(Vector3.up, delta.x * rotationSpeed * Time.deltaTime, Space.World);
                    transform.Rotate(Vector3.right, -delta.y * rotationSpeed * Time.deltaTime, Space.Self);

                    // ピッチ角度を制限
                    Vector3 euler = transform.eulerAngles;
                    euler.z = 0;
                    if (euler.x > 180)
                        euler.x = Mathf.Max(euler.x, 270);
                    else
                        euler.x = Mathf.Min(euler.x, 90);
                    transform.eulerAngles = euler;
                }
            }
            // 2本指：ピンチズーム
            else if (Input.touchCount == 2)
            {
                Touch touch0 = Input.GetTouch(0);
                Touch touch1 = Input.GetTouch(1);

                if (touch0.phase == TouchPhase.Moved || touch1.phase == TouchPhase.Moved)
                {
                    float currentDistance = Vector2.Distance(touch0.position, touch1.position);

                    if (lastPinchDistance > 0)
                    {
                        float delta = currentDistance - lastPinchDistance;
                        float zoomAmount = delta * pinchZoomSpeed * Time.deltaTime;

                        // カメラを前後移動
                        transform.Translate(Vector3.forward * zoomAmount, Space.Self);

                        // 高さ制限
                        Vector3 pos = transform.position;
                        pos.y = Mathf.Clamp(pos.y, minHeight, maxHeight);
                        transform.position = pos;
                    }

                    lastPinchDistance = currentDistance;
                }
            }
            else
            {
                lastPinchDistance = 0;
            }
        }

        /// <summary>
        /// キーボード/マウス入力処理（PC向け）
        /// </summary>
        private void HandleKeyboardMouseInput()
        {
            // WASDでカメラ移動
            float horizontal = Input.GetAxis("Horizontal");
            float vertical = Input.GetAxis("Vertical");

            Vector3 moveDirection = (transform.right * horizontal + transform.forward * vertical).normalized;
            transform.position += moveDirection * moveSpeed * Time.deltaTime;

            // QEで上下移動
            if (Input.GetKey(KeyCode.Q))
                transform.position += Vector3.down * moveSpeed * Time.deltaTime;
            if (Input.GetKey(KeyCode.E))
                transform.position += Vector3.up * moveSpeed * Time.deltaTime;

            // 高さ制限
            Vector3 pos = transform.position;
            pos.y = Mathf.Clamp(pos.y, minHeight, maxHeight);
            transform.position = pos;

            // 右クリックでカメラ回転
            if (Input.GetMouseButton(1))
            {
                float mouseX = Input.GetAxis("Mouse X");
                float mouseY = Input.GetAxis("Mouse Y");

                transform.Rotate(Vector3.up, mouseX * rotationSpeed * Time.deltaTime, Space.World);
                transform.Rotate(Vector3.right, -mouseY * rotationSpeed * Time.deltaTime, Space.Self);
            }

            // マウスホイールでズーム
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (scroll != 0)
            {
                transform.Translate(Vector3.forward * scroll * zoomSpeed, Space.Self);
            }

            // カメラモード切り替え
            if (Input.GetKeyDown(KeyCode.C))
            {
                CycleCamera();
            }

            // フォローモード切り替え
            if (Input.GetKeyDown(KeyCode.F))
            {
                isFollowing = !isFollowing;
                Debug.Log($"[CameraController] Follow mode: {isFollowing}");
            }
        }

        /// <summary>
        /// ターゲットを追従
        /// </summary>
        private void FollowTarget()
        {
            if (targetToFollow == null || !isFollowing)
                return;

            Vector3 targetPosition = targetToFollow.position + followOffset;
            transform.position = Vector3.Lerp(transform.position, targetPosition, Time.deltaTime * 5f);

            // ターゲットを見る
            Vector3 lookDirection = targetToFollow.position - transform.position;
            if (lookDirection != Vector3.zero)
            {
                Quaternion targetRotation = Quaternion.LookRotation(lookDirection);
                transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * 5f);
            }
        }

        /// <summary>
        /// カメラモードを切り替え
        /// </summary>
        public void CycleCamera()
        {
            int nextMode = ((int)currentMode + 1) % System.Enum.GetValues(typeof(CameraMode)).Length;
            SetCameraMode((CameraMode)nextMode);
        }

        /// <summary>
        /// カメラモードを設定
        /// </summary>
        public void SetCameraMode(CameraMode mode)
        {
            currentMode = mode;
            Debug.Log($"[CameraController] Camera mode: {mode}");

            switch (mode)
            {
                case CameraMode.Free:
                    isFollowing = false;
                    break;

                case CameraMode.FollowTrain:
                    isFollowing = true;
                    followOffset = new Vector3(0, 2, -5);
                    break;

                case CameraMode.CabView:
                    isFollowing = true;
                    followOffset = new Vector3(0, 1.5f, 0);
                    break;

                case CameraMode.ExteriorView:
                    isFollowing = true;
                    followOffset = new Vector3(3, 2, -3);
                    break;
            }
        }

        /// <summary>
        /// 追従ターゲットを設定
        /// </summary>
        public void SetFollowTarget(Transform target)
        {
            targetToFollow = target;
            Debug.Log($"[CameraController] Follow target set: {target.name}");
        }

        /// <summary>
        /// 追従オフセットを設定
        /// </summary>
        public void SetFollowOffset(Vector3 offset)
        {
            followOffset = offset;
        }
    }
}
