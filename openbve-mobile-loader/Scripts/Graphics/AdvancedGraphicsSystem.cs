using UnityEngine;
using System.Collections.Generic;

namespace OpenBveMobile.Graphics
{
    /// <summary>
    /// 高度なグラフィックスシステム
    /// シェーダー、ライティング、パーティクルエフェクト
    /// </summary>
    public class AdvancedGraphicsSystem : MonoBehaviour
    {
        [Header("Graphics Quality")]
        [SerializeField] private GraphicsQuality quality = GraphicsQuality.High;

        [Header("Lighting")]
        [SerializeField] private bool dynamicLighting = true;
        [SerializeField] private Color ambientColor = new Color(0.3f, 0.3f, 0.4f);
        [SerializeField] private Light mainDirectionalLight;

        [Header("Post Processing")]
        [SerializeField] private bool enableFog = true;
        [SerializeField] private Color fogColor = Color.gray;
        [SerializeField] private float fogDensity = 0.01f;

        [Header("Effects")]
        [SerializeField] private bool enableParticles = true;
        [SerializeField] private GameObject rainPrefab;
        [SerializeField] private GameObject snowPrefab;

        // シェーダー管理
        private Dictionary<string, Shader> customShaders = new Dictionary<string, Shader>();
        private Dictionary<string, Material> materialCache = new Dictionary<string, Material>();

        // パーティクル管理
        private List<ParticleSystem> activeParticles = new List<ParticleSystem>();

        public enum GraphicsQuality
        {
            Low,
            Medium,
            High,
            Ultra
        }

        private void Start()
        {
            InitializeGraphics();
            LoadCustomShaders();
            SetupLighting();
            SetupFog();
        }

        /// <summary>
        /// グラフィックスを初期化
        /// </summary>
        private void InitializeGraphics()
        {
            ApplyQualitySettings();

            // メインライトがない場合は作成
            if (mainDirectionalLight == null)
            {
                GameObject lightObj = new GameObject("Main Directional Light");
                mainDirectionalLight = lightObj.AddComponent<Light>();
                mainDirectionalLight.type = LightType.Directional;
                mainDirectionalLight.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            }

            Debug.Log($"[AdvancedGraphicsSystem] Initialized ({quality})");
        }

        /// <summary>
        /// 品質設定を適用
        /// </summary>
        private void ApplyQualitySettings()
        {
            switch (quality)
            {
                case GraphicsQuality.Low:
                    QualitySettings.SetQualityLevel(0);
                    QualitySettings.shadows = ShadowQuality.Disable;
                    break;

                case GraphicsQuality.Medium:
                    QualitySettings.SetQualityLevel(2);
                    QualitySettings.shadows = ShadowQuality.HardOnly;
                    break;

                case GraphicsQuality.High:
                    QualitySettings.SetQualityLevel(4);
                    QualitySettings.shadows = ShadowQuality.All;
                    break;

                case GraphicsQuality.Ultra:
                    QualitySettings.SetQualityLevel(5);
                    QualitySettings.shadows = ShadowQuality.All;
                    QualitySettings.shadowResolution = ShadowResolution.VeryHigh;
                    break;
            }
        }

        /// <summary>
        /// カスタムシェーダーを読み込み
        /// </summary>
        private void LoadCustomShaders()
        {
            // Unityビルトインシェーダー
            customShaders["Standard"] = Shader.Find("Standard");
            customShaders["Unlit"] = Shader.Find("Unlit/Texture");
            customShaders["Transparent"] = Shader.Find("Transparent/Diffuse");

            // カスタムシェーダー（Resources/Shadersから読み込み）
            Shader[] customShaderAssets = Resources.LoadAll<Shader>("Shaders");
            foreach (var shader in customShaderAssets)
            {
                customShaders[shader.name] = shader;
                Debug.Log($"[AdvancedGraphicsSystem] Loaded shader: {shader.name}");
            }
        }

        /// <summary>
        /// ライティングをセットアップ
        /// </summary>
        private void SetupLighting()
        {
            if (dynamicLighting)
            {
                RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
                RenderSettings.ambientLight = ambientColor;

                if (mainDirectionalLight != null)
                {
                    mainDirectionalLight.intensity = 1.0f;
                    mainDirectionalLight.color = Color.white;
                    mainDirectionalLight.shadows = quality >= GraphicsQuality.Medium ? LightShadows.Soft : LightShadows.None;
                }
            }
        }

        /// <summary>
        /// 霧をセットアップ
        /// </summary>
        private void SetupFog()
        {
            RenderSettings.fog = enableFog;
            if (enableFog)
            {
                RenderSettings.fogColor = fogColor;
                RenderSettings.fogMode = FogMode.Exponential;
                RenderSettings.fogDensity = fogDensity;
            }
        }

        /// <summary>
        /// マテリアルを作成（キャッシュ付き）
        /// </summary>
        public Material CreateMaterial(string shaderName, Color color, Texture2D texture = null, bool emissive = false)
        {
            string cacheKey = $"{shaderName}_{color}_{(texture != null ? texture.name : "notex")}_{emissive}";

            if (materialCache.TryGetValue(cacheKey, out Material cachedMaterial))
            {
                return cachedMaterial;
            }

            Shader shader = GetShader(shaderName);
            Material material = new Material(shader);

            // 基本設定
            material.color = color;

            if (texture != null)
            {
                material.mainTexture = texture;
            }

            // エミッシブ（発光）
            if (emissive && shader.name == "Standard")
            {
                material.EnableKeyword("_EMISSION");
                material.SetColor("_EmissionColor", color);
            }

            materialCache[cacheKey] = material;
            return material;
        }

        /// <summary>
        /// シェーダーを取得
        /// </summary>
        public Shader GetShader(string name)
        {
            if (customShaders.TryGetValue(name, out Shader shader))
            {
                return shader;
            }

            // デフォルトはStandard
            return Shader.Find("Standard");
        }

        /// <summary>
        /// 時刻に応じてライティングを更新
        /// </summary>
        public void SetTimeOfDay(float hours)
        {
            if (!dynamicLighting || mainDirectionalLight == null)
                return;

            // 0-24時間を角度に変換
            float angle = (hours / 24f) * 360f - 90f;

            // ライトの回転
            mainDirectionalLight.transform.rotation = Quaternion.Euler(angle, -30f, 0f);

            // 時刻に応じた色と強度
            if (hours >= 6f && hours < 8f)
            {
                // 日の出
                float t = (hours - 6f) / 2f;
                mainDirectionalLight.color = Color.Lerp(new Color(1f, 0.6f, 0.4f), Color.white, t);
                mainDirectionalLight.intensity = Mathf.Lerp(0.3f, 1.0f, t);
            }
            else if (hours >= 18f && hours < 20f)
            {
                // 日没
                float t = (hours - 18f) / 2f;
                mainDirectionalLight.color = Color.Lerp(Color.white, new Color(1f, 0.5f, 0.3f), t);
                mainDirectionalLight.intensity = Mathf.Lerp(1.0f, 0.2f, t);
            }
            else if (hours >= 20f || hours < 6f)
            {
                // 夜
                mainDirectionalLight.color = new Color(0.5f, 0.5f, 0.7f);
                mainDirectionalLight.intensity = 0.1f;
            }
            else
            {
                // 昼
                mainDirectionalLight.color = Color.white;
                mainDirectionalLight.intensity = 1.0f;
            }

            // アンビエントライトも調整
            RenderSettings.ambientLight = mainDirectionalLight.color * 0.3f;
        }

        /// <summary>
        /// 雨エフェクトを開始
        /// </summary>
        public void StartRain(float intensity = 1.0f)
        {
            if (!enableParticles || rainPrefab == null)
                return;

            GameObject rainObj = Instantiate(rainPrefab, Vector3.zero, Quaternion.identity);
            ParticleSystem ps = rainObj.GetComponent<ParticleSystem>();

            if (ps != null)
            {
                var emission = ps.emission;
                emission.rateOverTime = 100 * intensity;
                activeParticles.Add(ps);

                Debug.Log($"[AdvancedGraphicsSystem] Started rain (intensity: {intensity})");
            }
        }

        /// <summary>
        /// 雪エフェクトを開始
        /// </summary>
        public void StartSnow(float intensity = 1.0f)
        {
            if (!enableParticles || snowPrefab == null)
                return;

            GameObject snowObj = Instantiate(snowPrefab, Vector3.zero, Quaternion.identity);
            ParticleSystem ps = snowObj.GetComponent<ParticleSystem>();

            if (ps != null)
            {
                var emission = ps.emission;
                emission.rateOverTime = 50 * intensity;
                activeParticles.Add(ps);

                Debug.Log($"[AdvancedGraphicsSystem] Started snow (intensity: {intensity})");
            }
        }

        /// <summary>
        /// すべてのパーティクルエフェクトを停止
        /// </summary>
        public void StopAllEffects()
        {
            foreach (var ps in activeParticles)
            {
                if (ps != null)
                {
                    ps.Stop();
                    Destroy(ps.gameObject, 5f);
                }
            }

            activeParticles.Clear();
        }

        /// <summary>
        /// 霧の設定を変更
        /// </summary>
        public void SetFog(bool enabled, Color color, float density)
        {
            enableFog = enabled;
            fogColor = color;
            fogDensity = density;
            SetupFog();
        }

        /// <summary>
        /// グラフィックス品質を変更
        /// </summary>
        public void SetQuality(GraphicsQuality newQuality)
        {
            quality = newQuality;
            ApplyQualitySettings();
            SetupLighting();

            Debug.Log($"[AdvancedGraphicsSystem] Quality changed to: {quality}");
        }

        /// <summary>
        /// パーティクルエフェクトを作成
        /// </summary>
        public ParticleSystem CreateParticleEffect(Vector3 position, Color color, float size = 1.0f, float lifetime = 2.0f)
        {
            GameObject effectObj = new GameObject("ParticleEffect");
            effectObj.transform.position = position;

            ParticleSystem ps = effectObj.AddComponent<ParticleSystem>();

            var main = ps.main;
            main.startColor = color;
            main.startSize = size;
            main.startLifetime = lifetime;

            activeParticles.Add(ps);

            return ps;
        }
    }
}
