using UnityEngine;
using System.Collections.Generic;

namespace OpenBveMobile.Core
{
    /// <summary>
    /// 動的オブジェクトの種類
    /// </summary>
    public enum DynamicObjectType
    {
        Static,          // 静的（動かない）
        Animated,        // アニメーション
        Translating,     // 移動
        Rotating,        // 回転
        Scripted         // スクリプト制御
    }

    /// <summary>
    /// 動的オブジェクトの定義
    /// </summary>
    [System.Serializable]
    public class DynamicObjectDefinition
    {
        public string ObjectKey;
        public DynamicObjectType Type = DynamicObjectType.Static;

        // アニメーション設定
        public string AnimationName;
        public float AnimationSpeed = 1.0f;
        public bool AnimationLoop = true;

        // 移動設定
        public Vector3 TranslateDirection = Vector3.forward;
        public float TranslateSpeed = 1.0f;
        public float TranslateDistance = 10f;
        public bool TranslatePingPong = true;

        // 回転設定
        public Vector3 RotationAxis = Vector3.up;
        public float RotationSpeed = 30f; // 度/秒

        // スクリプト設定
        public string ScriptName;
    }

    /// <summary>
    /// 動的オブジェクトシステム
    /// アニメーション、移動、回転、スクリプト制御に対応
    /// </summary>
    public class DynamicObjectSystem : MonoBehaviour
    {
        [Header("Settings")]
        [SerializeField] private bool enableDynamicObjects = true;

        // 動的オブジェクト管理
        private Dictionary<string, DynamicObjectDefinition> definitions = new Dictionary<string, DynamicObjectDefinition>();
        private List<DynamicObjectInstance> instances = new List<DynamicObjectInstance>();

        private class DynamicObjectInstance
        {
            public GameObject GameObject;
            public DynamicObjectDefinition Definition;
            public Animator Animator;
            public float TimeElapsed;
            public Vector3 InitialPosition;
            public Quaternion InitialRotation;
            public bool MovingForward = true;
        }

        private void Update()
        {
            if (!enableDynamicObjects) return;

            foreach (var instance in instances)
            {
                UpdateDynamicObject(instance);
            }
        }

        /// <summary>
        /// 動的オブジェクト定義を登録
        /// </summary>
        public void RegisterDefinition(string key, DynamicObjectDefinition definition)
        {
            definitions[key] = definition;
            Debug.Log($"[DynamicObjectSystem] Registered: {key} ({definition.Type})");
        }

        /// <summary>
        /// 動的オブジェクトを作成
        /// </summary>
        public GameObject CreateDynamicObject(string key, GameObject prefab, Vector3 position, Quaternion rotation)
        {
            if (!definitions.TryGetValue(key, out DynamicObjectDefinition definition))
            {
                // 定義がない場合は静的オブジェクトとして扱う
                return Instantiate(prefab, position, rotation);
            }

            GameObject obj = Instantiate(prefab, position, rotation);

            var instance = new DynamicObjectInstance
            {
                GameObject = obj,
                Definition = definition,
                TimeElapsed = 0f,
                InitialPosition = position,
                InitialRotation = rotation
            };

            // タイプ別の初期化
            switch (definition.Type)
            {
                case DynamicObjectType.Animated:
                    InitializeAnimated(instance);
                    break;

                case DynamicObjectType.Translating:
                case DynamicObjectType.Rotating:
                case DynamicObjectType.Scripted:
                    // 他のタイプは Update で処理
                    break;
            }

            instances.Add(instance);
            return obj;
        }

        /// <summary>
        /// アニメーション初期化
        /// </summary>
        private void InitializeAnimated(DynamicObjectInstance instance)
        {
            instance.Animator = instance.GameObject.GetComponent<Animator>();

            if (instance.Animator == null)
            {
                instance.Animator = instance.GameObject.AddComponent<Animator>();
            }

            // アニメーションコントローラーがある場合は再生
            if (!string.IsNullOrEmpty(instance.Definition.AnimationName))
            {
                instance.Animator.speed = instance.Definition.AnimationSpeed;
                // Unity Animator 使用
            }
        }

        /// <summary>
        /// 動的オブジェクトを更新
        /// </summary>
        private void UpdateDynamicObject(DynamicObjectInstance instance)
        {
            if (instance.GameObject == null) return;

            instance.TimeElapsed += Time.deltaTime;

            switch (instance.Definition.Type)
            {
                case DynamicObjectType.Animated:
                    UpdateAnimated(instance);
                    break;

                case DynamicObjectType.Translating:
                    UpdateTranslating(instance);
                    break;

                case DynamicObjectType.Rotating:
                    UpdateRotating(instance);
                    break;

                case DynamicObjectType.Scripted:
                    UpdateScripted(instance);
                    break;
            }
        }

        /// <summary>
        /// アニメーション更新
        /// </summary>
        private void UpdateAnimated(DynamicObjectInstance instance)
        {
            // Animatorコンポーネントが自動的に処理
            if (instance.Animator != null && !instance.Definition.AnimationLoop)
            {
                // ループしない場合、終了チェック
                AnimatorStateInfo stateInfo = instance.Animator.GetCurrentAnimatorStateInfo(0);
                if (stateInfo.normalizedTime >= 1.0f)
                {
                    instance.Animator.speed = 0f;
                }
            }
        }

        /// <summary>
        /// 移動更新
        /// </summary>
        private void UpdateTranslating(DynamicObjectInstance instance)
        {
            var def = instance.Definition;

            // 移動距離を計算
            float totalDistance = def.TranslateDistance;
            float currentDistance = (instance.TimeElapsed * def.TranslateSpeed) % (totalDistance * 2);

            if (def.TranslatePingPong)
            {
                // 往復運動
                if (currentDistance > totalDistance)
                {
                    currentDistance = totalDistance * 2 - currentDistance;
                }
            }
            else
            {
                // 一方向ループ
                currentDistance = currentDistance % totalDistance;
            }

            Vector3 offset = def.TranslateDirection.normalized * currentDistance;
            instance.GameObject.transform.position = instance.InitialPosition + offset;
        }

        /// <summary>
        /// 回転更新
        /// </summary>
        private void UpdateRotating(DynamicObjectInstance instance)
        {
            var def = instance.Definition;

            // 回転角度を計算
            float rotationAngle = instance.TimeElapsed * def.RotationSpeed;
            Quaternion rotation = Quaternion.AngleAxis(rotationAngle, def.RotationAxis);

            instance.GameObject.transform.rotation = instance.InitialRotation * rotation;
        }

        /// <summary>
        /// スクリプト制御更新
        /// </summary>
        private void UpdateScripted(DynamicObjectInstance instance)
        {
            // スクリプトエンジンで処理
            if (!string.IsNullOrEmpty(instance.Definition.ScriptName))
            {
                var scriptEngine = GetComponent<ScriptEngine>();
                if (scriptEngine != null)
                {
                    scriptEngine.ExecuteObjectScript(instance.Definition.ScriptName, instance.GameObject, instance.TimeElapsed);
                }
            }
        }

        /// <summary>
        /// すべての動的オブジェクトをクリア
        /// </summary>
        public void ClearAll()
        {
            foreach (var instance in instances)
            {
                if (instance.GameObject != null)
                {
                    Destroy(instance.GameObject);
                }
            }

            instances.Clear();
            Debug.Log("[DynamicObjectSystem] Cleared all dynamic objects");
        }

        /// <summary>
        /// 動的オブジェクトの一時停止/再開
        /// </summary>
        public void SetPaused(bool paused)
        {
            enableDynamicObjects = !paused;

            foreach (var instance in instances)
            {
                if (instance.Animator != null)
                {
                    instance.Animator.speed = paused ? 0f : instance.Definition.AnimationSpeed;
                }
            }
        }

        /// <summary>
        /// 統計情報を取得
        /// </summary>
        public string GetStats()
        {
            return $"Dynamic Objects: {instances.Count} active, {definitions.Count} definitions";
        }
    }
}
