using UnityEngine;
using System.IO;
using System.Collections.Generic;
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

                    case ".xml":
                        // BVE5 XMLオブジェクト
                        Debug.LogWarning("[ModelLoader] BVE5 XML objects not yet implemented");
                        return CreatePlaceholder(Path.GetFileName(filePath));

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
        /// DirectX Xフォーマットをロード
        /// </summary>
        private GameObject LoadDirectX(string filePath, Material material)
        {
            Debug.Log($"[ModelLoader] Loading DirectX X: {filePath}");

            var xParser = new DirectXParser();
            var xModel = xParser.Parse(filePath);

            if (xModel == null)
            {
                return CreatePlaceholder(Path.GetFileName(filePath));
            }

            var mesh = xParser.ConvertToMesh(xModel);
            GameObject obj = CreateGameObjectFromMesh(mesh, material);
            obj.name = Path.GetFileNameWithoutExtension(filePath);

            // マテリアル適用
            if (xModel.Materials.Count > 0)
            {
                ApplyXMaterials(obj, xModel.Materials);
            }

            // テクスチャがある場合は適用
            if (!string.IsNullOrEmpty(xModel.TexturePath))
            {
                ApplyTexture(obj, xModel.TexturePath);
            }
            else if (xModel.Materials.Count > 0 && !string.IsNullOrEmpty(xModel.Materials[0].TextureFilename))
            {
                ApplyTexture(obj, xModel.Materials[0].TextureFilename);
            }

            return obj;
        }

        /// <summary>
        /// DirectX マテリアルを適用
        /// </summary>
        private void ApplyXMaterials(GameObject obj, List<DirectXParser.XMaterial> materials)
        {
            var renderer = obj.GetComponent<MeshRenderer>();
            if (renderer == null || materials.Count == 0) return;

            var material = materials[0]; // 最初のマテリアルを使用

            // マテリアル作成
            Material unityMat = new Material(Shader.Find("Standard"));
            unityMat.color = material.DiffuseColor;

            // スペキュラー
            unityMat.SetFloat("_Glossiness", material.SpecularPower / 100f);
            unityMat.SetColor("_SpecColor", material.SpecularColor);

            // エミッシブ
            if (material.EmissiveColor != Color.black)
            {
                unityMat.EnableKeyword("_EMISSION");
                unityMat.SetColor("_EmissionColor", material.EmissiveColor);
            }

            renderer.material = unityMat;
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
