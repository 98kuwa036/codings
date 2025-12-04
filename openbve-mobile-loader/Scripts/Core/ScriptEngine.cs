using UnityEngine;
using System;
using System.Collections.Generic;
using System.Reflection;

namespace OpenBveMobile.Core
{
    /// <summary>
    /// カスタムスクリプトエンジン
    /// オブジェクトの動作をC#スクリプトで制御
    /// </summary>
    public class ScriptEngine : MonoBehaviour
    {
        [Header("Settings")]
        [SerializeField] private bool enableScripts = true;

        // スクリプト管理
        private Dictionary<string, IObjectScript> scripts = new Dictionary<string, IObjectScript>();
        private Dictionary<string, ScriptContext> contexts = new Dictionary<string, ScriptContext>();

        /// <summary>
        /// スクリプトコンテキスト（変数保存用）
        /// </summary>
        public class ScriptContext
        {
            public Dictionary<string, object> Variables = new Dictionary<string, object>();
            public float TimeElapsed = 0f;
        }

        private void Awake()
        {
            // ビルトインスクリプトを登録
            RegisterBuiltInScripts();
        }

        /// <summary>
        /// ビルトインスクリプトを登録
        /// </summary>
        private void RegisterBuiltInScripts()
        {
            RegisterScript("rotate_y", new RotateYScript());
            RegisterScript("bounce", new BounceScript());
            RegisterScript("flash", new FlashScript());
            RegisterScript("door_open_close", new DoorOpenCloseScript());

            Debug.Log($"[ScriptEngine] Registered {scripts.Count} built-in scripts");
        }

        /// <summary>
        /// スクリプトを登録
        /// </summary>
        public void RegisterScript(string name, IObjectScript script)
        {
            scripts[name] = script;
            contexts[name] = new ScriptContext();
        }

        /// <summary>
        /// オブジェクトスクリプトを実行
        /// </summary>
        public void ExecuteObjectScript(string scriptName, GameObject obj, float timeElapsed)
        {
            if (!enableScripts) return;

            if (!scripts.TryGetValue(scriptName, out IObjectScript script))
            {
                Debug.LogWarning($"[ScriptEngine] Script not found: {scriptName}");
                return;
            }

            if (!contexts.TryGetValue(scriptName, out ScriptContext context))
            {
                context = new ScriptContext();
                contexts[scriptName] = context;
            }

            context.TimeElapsed = timeElapsed;

            try
            {
                script.Execute(obj, context);
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ScriptEngine] Script error ({scriptName}): {ex.Message}");
            }
        }

        /// <summary>
        /// 列車スクリプトを実行
        /// </summary>
        public void ExecuteTrainScript(string scriptName, GameObject train, float speed, float position)
        {
            if (!enableScripts) return;

            if (!scripts.TryGetValue(scriptName, out IObjectScript script))
                return;

            if (!contexts.TryGetValue(scriptName, out ScriptContext context))
            {
                context = new ScriptContext();
                contexts[scriptName] = context;
            }

            context.Variables["speed"] = speed;
            context.Variables["position"] = position;

            try
            {
                script.Execute(train, context);
            }
            catch (Exception ex)
            {
                Debug.LogError($"[ScriptEngine] Train script error ({scriptName}): {ex.Message}");
            }
        }

        /// <summary>
        /// 全スクリプトをクリア
        /// </summary>
        public void ClearAllScripts()
        {
            contexts.Clear();
            Debug.Log("[ScriptEngine] Cleared all script contexts");
        }
    }

    /// <summary>
    /// オブジェクトスクリプトインターフェース
    /// </summary>
    public interface IObjectScript
    {
        void Execute(GameObject obj, ScriptEngine.ScriptContext context);
    }

    /// <summary>
    /// Y軸回転スクリプト
    /// </summary>
    public class RotateYScript : IObjectScript
    {
        public void Execute(GameObject obj, ScriptEngine.ScriptContext context)
        {
            float speed = context.Variables.ContainsKey("speed") ? (float)context.Variables["speed"] : 30f;
            obj.transform.Rotate(Vector3.up, speed * Time.deltaTime);
        }
    }

    /// <summary>
    /// バウンススクリプト（上下運動）
    /// </summary>
    public class BounceScript : IObjectScript
    {
        public void Execute(GameObject obj, ScriptEngine.ScriptContext context)
        {
            if (!context.Variables.ContainsKey("initialY"))
            {
                context.Variables["initialY"] = obj.transform.position.y;
            }

            float initialY = (float)context.Variables["initialY"];
            float amplitude = context.Variables.ContainsKey("amplitude") ? (float)context.Variables["amplitude"] : 1f;
            float frequency = context.Variables.ContainsKey("frequency") ? (float)context.Variables["frequency"] : 1f;

            float newY = initialY + Mathf.Sin(context.TimeElapsed * frequency * Mathf.PI * 2) * amplitude;

            Vector3 pos = obj.transform.position;
            pos.y = newY;
            obj.transform.position = pos;
        }
    }

    /// <summary>
    /// 点滅スクリプト
    /// </summary>
    public class FlashScript : IObjectScript
    {
        public void Execute(GameObject obj, ScriptEngine.ScriptContext context)
        {
            float interval = context.Variables.ContainsKey("interval") ? (float)context.Variables["interval"] : 1f;

            bool visible = (Mathf.Floor(context.TimeElapsed / interval) % 2) == 0;

            var renderer = obj.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.enabled = visible;
            }
        }
    }

    /// <summary>
    /// ドア開閉スクリプト
    /// </summary>
    public class DoorOpenCloseScript : IObjectScript
    {
        public void Execute(GameObject obj, ScriptEngine.ScriptContext context)
        {
            // ドア開閉状態を取得
            bool isOpen = context.Variables.ContainsKey("door_open") && (bool)context.Variables["door_open"];

            if (!context.Variables.ContainsKey("initialX"))
            {
                context.Variables["initialX"] = obj.transform.localPosition.x;
            }

            float initialX = (float)context.Variables["initialX"];
            float openDistance = context.Variables.ContainsKey("open_distance") ? (float)context.Variables["open_distance"] : 1.5f;
            float speed = context.Variables.ContainsKey("speed") ? (float)context.Variables["speed"] : 2f;

            // 目標位置
            float targetX = isOpen ? initialX + openDistance : initialX;

            // スムーズに移動
            Vector3 pos = obj.transform.localPosition;
            pos.x = Mathf.Lerp(pos.x, targetX, Time.deltaTime * speed);
            obj.transform.localPosition = pos;
        }
    }

    /// <summary>
    /// カスタムスクリプトローダー
    /// 外部テキストファイルからスクリプトを読み込む
    /// </summary>
    public class CustomScriptLoader
    {
        /// <summary>
        /// シンプルなスクリプト言語を解析
        /// 形式例：
        /// rotate y 30
        /// translate 0 1 0 speed=2
        /// scale 1.5
        /// </summary>
        public static IObjectScript ParseScript(string scriptText)
        {
            // 簡易的なスクリプト言語パーサー
            var script = new CompositeScript();

            string[] lines = scriptText.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);

            foreach (string line in lines)
            {
                string trimmed = line.Trim();

                if (trimmed.StartsWith("//") || trimmed.StartsWith(";"))
                    continue; // コメント

                if (trimmed.StartsWith("rotate"))
                {
                    // rotate y 30
                    string[] parts = trimmed.Split(' ');
                    if (parts.Length >= 3)
                    {
                        script.AddAction(new RotateYScript());
                    }
                }
                else if (trimmed.StartsWith("bounce"))
                {
                    script.AddAction(new BounceScript());
                }
                else if (trimmed.StartsWith("flash"))
                {
                    script.AddAction(new FlashScript());
                }
            }

            return script;
        }
    }

    /// <summary>
    /// 複合スクリプト（複数のスクリプトを組み合わせ）
    /// </summary>
    public class CompositeScript : IObjectScript
    {
        private List<IObjectScript> actions = new List<IObjectScript>();

        public void AddAction(IObjectScript action)
        {
            actions.Add(action);
        }

        public void Execute(GameObject obj, ScriptEngine.ScriptContext context)
        {
            foreach (var action in actions)
            {
                action.Execute(obj, context);
            }
        }
    }
}
