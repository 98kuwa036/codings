using UnityEngine;
using System.IO;
using OpenBveMobile.Core;
using OpenBveMobile.Parsers;

namespace OpenBveMobile.Loaders
{
    /// <summary>
    /// 統合路線ローダー
    /// BVE2/4/5/openBVEすべてのフォーマットを自動検出して読み込む
    /// </summary>
    public class UnifiedRouteLoader : MonoBehaviour
    {
        [Header("Settings")]
        [SerializeField] private bool autoDetectFormat = true;
        [SerializeField] private BveFormat forcedFormat = BveFormat.Unknown;

        [Header("References")]
        [SerializeField] private Transform worldRoot;
        [SerializeField] private Material defaultMaterial;

        private RouteData routeData;
        private ModelLoader modelLoader;

        // パーサー
        private Bve2RouteParser bve2Parser;
        private CsvRouteParser bve4Parser;
        private Bve5RouteParser bve5Parser;

        private void Awake()
        {
            // パーサー初期化
            bve2Parser = new Bve2RouteParser();
            bve4Parser = new CsvRouteParser();
            bve5Parser = new Bve5RouteParser();

            modelLoader = GetComponent<ModelLoader>();
            if (modelLoader == null)
            {
                modelLoader = gameObject.AddComponent<ModelLoader>();
            }

            if (worldRoot == null)
            {
                worldRoot = new GameObject("RouteWorld").transform;
            }
        }

        /// <summary>
        /// 路線を自動検出してロード
        /// </summary>
        public RouteData LoadRoute(string filePath)
        {
            if (!File.Exists(filePath))
            {
                Debug.LogError($"[UnifiedRouteLoader] File not found: {filePath}");
                return null;
            }

            // フォーマット検出
            BveFormat format = forcedFormat;
            if (autoDetectFormat || format == BveFormat.Unknown)
            {
                format = FormatDetector.DetectRouteFormat(filePath);
                Debug.Log($"[UnifiedRouteLoader] Detected format: {FormatDetector.GetFormatInfo(format)}");
            }

            // フォーマットに応じて適切なパーサーを選択
            try
            {
                switch (format)
                {
                    case BveFormat.BVE2:
                        routeData = bve2Parser.Parse(filePath);
                        break;

                    case BveFormat.BVE4:
                    case BveFormat.OpenBVE:
                        routeData = bve4Parser.Parse(filePath);
                        break;

                    case BveFormat.BVE5:
                        routeData = bve5Parser.Parse(filePath);
                        break;

                    default:
                        Debug.LogError($"[UnifiedRouteLoader] Unsupported format: {format}");
                        return null;
                }

                if (routeData != null)
                {
                    // データをUnityシーンに展開
                    BuildRouteInScene();
                    Debug.Log("[UnifiedRouteLoader] Route loaded and built successfully!");
                }

                return routeData;
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[UnifiedRouteLoader] Failed to load route: {ex.Message}\n{ex.StackTrace}");
                return null;
            }
        }

        /// <summary>
        /// 路線データをUnityシーンに構築
        /// </summary>
        private void BuildRouteInScene()
        {
            Debug.Log($"[UnifiedRouteLoader] Building route in scene...");

            // オブジェクト配置
            foreach (var obj in routeData.Objects)
            {
                PlaceObject(obj);
            }

            // 駅マーカー配置（デバッグ用）
            foreach (var station in routeData.Stations)
            {
                PlaceStationMarker(station);
            }

            Debug.Log($"[UnifiedRouteLoader] Placed {routeData.Objects.Count} objects and {routeData.Stations.Count} stations");
        }

        /// <summary>
        /// オブジェクトを配置
        /// </summary>
        private void PlaceObject(PlacedObject obj)
        {
            if (!routeData.Structures.TryGetValue(obj.StructureKey, out StructureData structure))
            {
                return;
            }

            // モデルロード（キャッシュ対応）
            if (structure.LoadedModel == null && !string.IsNullOrEmpty(structure.ModelPath))
            {
                structure.LoadedModel = modelLoader.LoadModel(structure.ModelPath, defaultMaterial);
            }

            if (structure.LoadedModel != null)
            {
                GameObject instance = Instantiate(structure.LoadedModel, worldRoot);
                Vector3 position = new Vector3(obj.Offset.x, obj.Offset.y, obj.Position.Meters);
                instance.transform.position = position;
                instance.transform.rotation = Quaternion.Euler(0, obj.RotationY, obj.Tilt);
                instance.name = $"{obj.StructureKey}_{obj.Position.Meters:F0}m";
                obj.Instance = instance;
            }
        }

        /// <summary>
        /// 駅マーカーを配置（デバッグ用）
        /// </summary>
        private void PlaceStationMarker(StationData station)
        {
            GameObject marker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            marker.transform.SetParent(worldRoot);
            marker.transform.position = new Vector3(0, 0.5f, station.Position.Meters);
            marker.transform.localScale = new Vector3(2f, 5f, 2f);
            marker.name = $"Station_{station.Name}";

            // マーカーの色を設定
            var renderer = marker.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.material.color = new Color(1f, 1f, 0f, 0.7f); // 黄色半透明
            }

            // 駅名表示用テキスト（オプション）
            GameObject textObj = new GameObject($"StationText_{station.Name}");
            textObj.transform.SetParent(marker.transform);
            textObj.transform.localPosition = Vector3.up * 3f;

            Debug.Log($"[UnifiedRouteLoader] Station marker: {station.Name} at {station.Position.Meters}m");
        }

        /// <summary>
        /// フォーマット変換情報を取得
        /// </summary>
        public string GetConversionInfo(string filePath)
        {
            BveFormat format = FormatDetector.DetectRouteFormat(filePath);
            string info = FormatDetector.GetFormatInfo(format);
            bool compatible = FormatDetector.IsCompatible(format);

            return $"Format: {info}\nCompatible: {(compatible ? "Yes" : "Partial/No")}";
        }

        /// <summary>
        /// ロードされた路線データを取得
        /// </summary>
        public RouteData GetRouteData() => routeData;

        /// <summary>
        /// フォーマットを強制設定
        /// </summary>
        public void SetForcedFormat(BveFormat format)
        {
            forcedFormat = format;
            autoDetectFormat = false;
        }

        /// <summary>
        /// 自動検出を有効化
        /// </summary>
        public void EnableAutoDetect()
        {
            autoDetectFormat = true;
        }
    }
}
