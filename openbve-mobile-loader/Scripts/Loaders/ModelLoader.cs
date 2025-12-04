using UnityEngine;
using System.IO;
using OpenBveMobile.Parsers;

namespace OpenBveMobile.Loaders
{
    /// <summary>
    /// 3Dモデルをロードするクラス
    /// B3D、CSVオブジェクト、X（DirectX）等に対応
    /// </summary>
    public class ModelLoader : MonoBehaviour
    {
        private B3DParser b3dParser;
        private CsvObjectParser csvObjectParser;

        private void Awake()
        {
            b3dParser = new B3DParser();
            csvObjectParser = new CsvObjectParser();
        }

        /// <summary>
        /// モデルファイルをロード
        /// </summary>
        public GameObject LoadModel(string filePath, Material defaultMaterial)
        {
            if (!File.Exists(filePath))
            {
                Debug.LogWarning($"[ModelLoader] File not found: {filePath}");
                return CreatePlaceholder(Path.GetFileName(filePath));
            }

            string extension = Path.GetExtension(filePath).ToLowerInvariant();

            try
            {
                switch (extension)
                {
                    case ".b3d":
                        return LoadB3D(filePath, defaultMaterial);

                    case ".csv":
                        return LoadCsvObject(filePath, defaultMaterial);

                    case ".x":
                        return LoadDirectX(filePath, defaultMaterial);

                    case ".obj":
                        return LoadWavefrontObj(filePath, defaultMaterial);

                    default:
                        Debug.LogWarning($"[ModelLoader] Unsupported format: {extension}");
                        return CreatePlaceholder(Path.GetFileName(filePath));
                }
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[ModelLoader] Failed to load {filePath}: {ex.Message}");
                return CreatePlaceholder(Path.GetFileName(filePath));
            }
        }

        /// <summary>
        /// B3Dファイルをロード
        /// </summary>
        private GameObject LoadB3D(string filePath, Material material)
        {
            Debug.Log($"[ModelLoader] Loading B3D: {filePath}");

            var b3dModel = b3dParser.Parse(filePath);
            var mesh = b3dParser.ConvertToMesh(b3dModel);

            GameObject obj = CreateGameObjectFromMesh(mesh, material);
            obj.name = Path.GetFileNameWithoutExtension(filePath);

            // テクスチャがある場合は適用
            if (!string.IsNullOrEmpty(b3dModel.TexturePath))
            {
                ApplyTexture(obj, b3dModel.TexturePath);
            }

            return obj;
        }

        /// <summary>
        /// CSVオブジェクトをロード
        /// </summary>
        private GameObject LoadCsvObject(string filePath, Material material)
        {
            Debug.Log($"[ModelLoader] Loading CSV Object: {filePath}");

            var csvObject = csvObjectParser.Parse(filePath);
            var mesh = csvObjectParser.ConvertToMesh(csvObject);

            GameObject obj = CreateGameObjectFromMesh(mesh, material);
            obj.name = Path.GetFileNameWithoutExtension(filePath);

            // 色設定
            var renderer = obj.GetComponent<MeshRenderer>();
            if (renderer != null && renderer.material != null)
            {
                renderer.material.color = new Color(
                    csvObject.Color.r / 255f,
                    csvObject.Color.g / 255f,
                    csvObject.Color.b / 255f,
                    csvObject.Color.a / 255f
                );
            }

            // テクスチャがある場合は適用
            if (!string.IsNullOrEmpty(csvObject.TexturePath))
            {
                ApplyTexture(obj, csvObject.TexturePath);
            }

            return obj;
        }

        /// <summary>
        /// DirectX Xフォーマットをロード（未実装）
        /// </summary>
        private GameObject LoadDirectX(string filePath, Material material)
        {
            Debug.LogWarning("[ModelLoader] DirectX .X format not yet implemented");
            return CreatePlaceholder(Path.GetFileName(filePath));
        }

        /// <summary>
        /// Wavefront OBJをロード（未実装）
        /// </summary>
        private GameObject LoadWavefrontObj(string filePath, Material material)
        {
            Debug.LogWarning("[ModelLoader] Wavefront .OBJ format not yet implemented");
            return CreatePlaceholder(Path.GetFileName(filePath));
        }

        /// <summary>
        /// メッシュからGameObjectを作成
        /// </summary>
        private GameObject CreateGameObjectFromMesh(Mesh mesh, Material material)
        {
            GameObject obj = new GameObject("Model");

            MeshFilter meshFilter = obj.AddComponent<MeshFilter>();
            meshFilter.mesh = mesh;

            MeshRenderer renderer = obj.AddComponent<MeshRenderer>();
            renderer.material = material != null ? material : new Material(Shader.Find("Standard"));

            return obj;
        }

        /// <summary>
        /// テクスチャを適用
        /// </summary>
        private void ApplyTexture(GameObject obj, string texturePath)
        {
            if (!File.Exists(texturePath))
            {
                Debug.LogWarning($"[ModelLoader] Texture not found: {texturePath}");
                return;
            }

            try
            {
                byte[] textureData = File.ReadAllBytes(texturePath);
                Texture2D texture = new Texture2D(2, 2);

                if (texture.LoadImage(textureData))
                {
                    var renderer = obj.GetComponent<MeshRenderer>();
                    if (renderer != null && renderer.material != null)
                    {
                        renderer.material.mainTexture = texture;
                        Debug.Log($"[ModelLoader] Texture applied: {texturePath}");
                    }
                }
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[ModelLoader] Failed to load texture {texturePath}: {ex.Message}");
            }
        }

        /// <summary>
        /// プレースホルダー（仮モデル）を作成
        /// </summary>
        private GameObject CreatePlaceholder(string name)
        {
            GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            obj.name = $"Placeholder_{name}";

            var renderer = obj.GetComponent<MeshRenderer>();
            if (renderer != null)
            {
                renderer.material.color = new Color(1f, 0f, 1f, 0.5f); // マゼンタ色
            }

            return obj;
        }
    }
}
