using UnityEngine;
using System.Collections.Generic;
using System.IO;
using OpenBveMobile.Core;
using OpenBveMobile.Parsers;

namespace OpenBveMobile.Loaders
{
    /// <summary>
    /// 路線データをUnityシーンにロードするクラス
    /// </summary>
    public class RouteLoader : MonoBehaviour
    {
        [Header("Route Settings")]
        [SerializeField] private string routeFilePath;

        [Header("References")]
        [SerializeField] private Transform worldRoot;
        [SerializeField] private Material defaultMaterial;

        private RouteData routeData;
        private CsvRouteParser routeParser;
        private ModelLoader modelLoader;

        private void Awake()
        {
            routeParser = new CsvRouteParser();
            modelLoader = GetComponent<ModelLoader>();

            if (worldRoot == null)
            {
                worldRoot = new GameObject("RouteWorld").transform;
            }
        }

        /// <summary>
        /// 路線をロード
        /// </summary>
        public void LoadRoute(string filePath)
        {
            routeFilePath = filePath;

            try
            {
                Debug.Log($"[RouteLoader] Loading route: {filePath}");

                // CSVファイルを解析
                routeData = routeParser.Parse(filePath);

                // 路線環境をセットアップ
                SetupEnvironment();

                // オブジェクトを配置
                PlaceObjects();

                // 駅情報を表示
                LogStations();

                Debug.Log("[RouteLoader] Route loaded successfully!");
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[RouteLoader] Failed to load route: {ex.Message}\n{ex.StackTrace}");
            }
        }

        /// <summary>
        /// 環境設定（背景、霧等）
        /// </summary>
        private void SetupEnvironment()
        {
            // 背景設定
            if (routeData.Background != null && !string.IsNullOrEmpty(routeData.Background.ImagePath))
            {
                Debug.Log($"[RouteLoader] Setting background: {routeData.Background.ImagePath}");
                // 背景テクスチャの読み込み（実装予定）
            }

            // 軌間情報
            Debug.Log($"[RouteLoader] Track gauge: {routeData.Gauge}m");
        }

        /// <summary>
        /// オブジェクトを配置
        /// </summary>
        private void PlaceObjects()
        {
            Debug.Log($"[RouteLoader] Placing {routeData.Objects.Count} objects...");

            foreach (var obj in routeData.Objects)
            {
                PlaceObject(obj);
            }
        }

        /// <summary>
        /// 個別オブジェクトを配置
        /// </summary>
        private void PlaceObject(PlacedObject obj)
        {
            // 構造物定義を取得
            if (!routeData.Structures.TryGetValue(obj.StructureKey, out StructureData structure))
            {
                Debug.LogWarning($"[RouteLoader] Structure not found: {obj.StructureKey}");
                return;
            }

            // モデルがまだロードされていない場合はロード
            if (structure.LoadedModel == null && !string.IsNullOrEmpty(structure.ModelPath))
            {
                structure.LoadedModel = modelLoader.LoadModel(structure.ModelPath, defaultMaterial);
            }

            if (structure.LoadedModel != null)
            {
                // インスタンスを作成
                GameObject instance = Instantiate(structure.LoadedModel, worldRoot);

                // 位置を設定（Z軸が進行方向）
                Vector3 position = new Vector3(obj.Offset.x, obj.Offset.y, obj.Position.Meters);
                instance.transform.position = position;

                // 回転を設定
                instance.transform.rotation = Quaternion.Euler(0, obj.RotationY, obj.Tilt);

                instance.name = $"{obj.StructureKey}_{obj.Position.Meters:F0}m";
                obj.Instance = instance;
            }
        }

        /// <summary>
        /// 駅情報をログ出力
        /// </summary>
        private void LogStations()
        {
            Debug.Log($"[RouteLoader] Stations: {routeData.Stations.Count}");
            foreach (var station in routeData.Stations)
            {
                Debug.Log($"  - {station.Name} at {station.Position.Meters}m");
            }
        }

        /// <summary>
        /// ロードされた路線データを取得
        /// </summary>
        public RouteData GetRouteData()
        {
            return routeData;
        }
    }
}
