using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Globalization;

namespace OpenBveMobile.Parsers
{
    /// <summary>
    /// DirectX Xファイルパーサー
    /// テキスト形式のDirectX .xファイルに対応
    /// </summary>
    public class DirectXParser
    {
        public class XModel
        {
            public List<Vector3> Vertices = new List<Vector3>();
            public List<Vector3> Normals = new List<Vector3>();
            public List<Vector2> UVs = new List<Vector2>();
            public List<Color32> Colors = new List<Color32>();
            public List<XFace> Faces = new List<XFace>();
            public List<XMaterial> Materials = new List<XMaterial>();
            public string TexturePath;
        }

        public class XFace
        {
            public int[] Indices;
            public int MaterialIndex = 0;
        }

        public class XMaterial
        {
            public Color DiffuseColor = Color.white;
            public Color SpecularColor = Color.white;
            public Color EmissiveColor = Color.black;
            public float SpecularPower = 0f;
            public string TextureFilename;
        }

        /// <summary>
        /// DirectX Xファイルを解析
        /// </summary>
        public XModel Parse(string filePath)
        {
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"DirectX X file not found: {filePath}");
            }

            Debug.Log($"[DirectXParser] Parsing: {filePath}");

            string content = File.ReadAllText(filePath, Encoding.UTF8);

            // バイナリ形式チェック
            if (content.StartsWith("xof 0303bin"))
            {
                Debug.LogError("[DirectXParser] Binary X files not supported. Please use text format.");
                return null;
            }

            // テキスト形式のみ対応
            if (!content.StartsWith("xof "))
            {
                Debug.LogError("[DirectXParser] Invalid X file format");
                return null;
            }

            var model = new XModel();

            try
            {
                // テンプレート定義を除去
                content = RemoveTemplates(content);

                // メッシュデータを解析
                ParseMesh(content, model, Path.GetDirectoryName(filePath));

                // マテリアル解析
                ParseMaterials(content, model, Path.GetDirectoryName(filePath));

                Debug.Log($"[DirectXParser] Loaded: {model.Vertices.Count} vertices, {model.Faces.Count} faces, {model.Materials.Count} materials");
                return model;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[DirectXParser] Parse error: {ex.Message}\n{ex.StackTrace}");
                return null;
            }
        }

        /// <summary>
        /// テンプレート定義を除去
        /// </summary>
        private string RemoveTemplates(string content)
        {
            // "template " から次の "}" までを削除
            while (true)
            {
                int templateStart = content.IndexOf("template ");
                if (templateStart < 0) break;

                int braceCount = 0;
                int i = templateStart;
                bool inTemplate = false;

                while (i < content.Length)
                {
                    if (content[i] == '{')
                    {
                        braceCount++;
                        inTemplate = true;
                    }
                    else if (content[i] == '}')
                    {
                        braceCount--;
                        if (inTemplate && braceCount == 0)
                        {
                            content = content.Remove(templateStart, i - templateStart + 1);
                            break;
                        }
                    }
                    i++;
                }

                if (i >= content.Length) break;
            }

            return content;
        }

        /// <summary>
        /// メッシュデータを解析
        /// </summary>
        private void ParseMesh(string content, XModel model, string directory)
        {
            // "Mesh {" を探す
            int meshStart = content.IndexOf("Mesh ");
            if (meshStart < 0)
            {
                meshStart = content.IndexOf("Mesh{");
            }

            if (meshStart < 0)
            {
                Debug.LogWarning("[DirectXParser] No Mesh found");
                return;
            }

            // メッシュブロックを抽出
            string meshBlock = ExtractBlock(content, meshStart);

            // 頂点数を取得
            var numbers = ExtractNumbers(meshBlock);
            if (numbers.Count == 0) return;

            int vertexCount = (int)numbers[0];
            int numberIndex = 1;

            // 頂点データ読み込み
            for (int i = 0; i < vertexCount && numberIndex + 2 < numbers.Count; i++)
            {
                float x = numbers[numberIndex++];
                float y = numbers[numberIndex++];
                float z = numbers[numberIndex++];

                // DirectXは左手座標系、Unityは左手座標系なので変換不要
                // ただし、軸の向きは調整が必要な場合がある
                model.Vertices.Add(new Vector3(-x, y, z)); // X軸反転でUnity座標系に
            }

            // 面数を取得
            if (numberIndex >= numbers.Count) return;
            int faceCount = (int)numbers[numberIndex++];

            // 面データ読み込み
            for (int i = 0; i < faceCount; i++)
            {
                if (numberIndex >= numbers.Count) break;

                int indexCount = (int)numbers[numberIndex++];
                var face = new XFace();
                face.Indices = new int[indexCount];

                for (int j = 0; j < indexCount && numberIndex < numbers.Count; j++)
                {
                    face.Indices[j] = (int)numbers[numberIndex++];
                }

                model.Faces.Add(face);
            }

            // MeshNormals を解析
            ParseMeshNormals(meshBlock, model);

            // MeshTextureCoords を解析
            ParseMeshTextureCoords(meshBlock, model);
        }

        /// <summary>
        /// 法線データを解析
        /// </summary>
        private void ParseMeshNormals(string meshBlock, XModel model)
        {
            int normalsStart = meshBlock.IndexOf("MeshNormals");
            if (normalsStart < 0) return;

            string normalsBlock = ExtractBlock(meshBlock, normalsStart);
            var numbers = ExtractNumbers(normalsBlock);

            if (numbers.Count == 0) return;

            int normalCount = (int)numbers[0];
            int index = 1;

            for (int i = 0; i < normalCount && index + 2 < numbers.Count; i++)
            {
                float x = numbers[index++];
                float y = numbers[index++];
                float z = numbers[index++];

                model.Normals.Add(new Vector3(-x, y, z));
            }
        }

        /// <summary>
        /// テクスチャ座標を解析
        /// </summary>
        private void ParseMeshTextureCoords(string meshBlock, XModel model)
        {
            int texStart = meshBlock.IndexOf("MeshTextureCoords");
            if (texStart < 0) return;

            string texBlock = ExtractBlock(meshBlock, texStart);
            var numbers = ExtractNumbers(texBlock);

            if (numbers.Count == 0) return;

            int uvCount = (int)numbers[0];
            int index = 1;

            for (int i = 0; i < uvCount && index + 1 < numbers.Count; i++)
            {
                float u = numbers[index++];
                float v = numbers[index++];

                model.UVs.Add(new Vector2(u, 1.0f - v)); // V座標反転
            }
        }

        /// <summary>
        /// マテリアルを解析
        /// </summary>
        private void ParseMaterials(string content, XModel model, string directory)
        {
            int materialStart = 0;

            while (true)
            {
                materialStart = content.IndexOf("Material ", materialStart);
                if (materialStart < 0) break;

                string materialBlock = ExtractBlock(content, materialStart);
                var material = ParseMaterial(materialBlock, directory);

                if (material != null)
                {
                    model.Materials.Add(material);
                }

                materialStart++;
            }
        }

        /// <summary>
        /// 個別マテリアルを解析
        /// </summary>
        private XMaterial ParseMaterial(string materialBlock, string directory)
        {
            var material = new XMaterial();
            var numbers = ExtractNumbers(materialBlock);

            if (numbers.Count >= 4)
            {
                // Diffuse color (RGBA)
                material.DiffuseColor = new Color(numbers[0], numbers[1], numbers[2], numbers[3]);
            }

            if (numbers.Count >= 5)
            {
                material.SpecularPower = numbers[4];
            }

            if (numbers.Count >= 8)
            {
                // Specular color (RGB)
                material.SpecularColor = new Color(numbers[5], numbers[6], numbers[7]);
            }

            if (numbers.Count >= 11)
            {
                // Emissive color (RGB)
                material.EmissiveColor = new Color(numbers[8], numbers[9], numbers[10]);
            }

            // TextureFilename を探す
            int texStart = materialBlock.IndexOf("TextureFilename");
            if (texStart >= 0)
            {
                int quoteStart = materialBlock.IndexOf("\"", texStart);
                int quoteEnd = materialBlock.IndexOf("\"", quoteStart + 1);

                if (quoteStart >= 0 && quoteEnd > quoteStart)
                {
                    string filename = materialBlock.Substring(quoteStart + 1, quoteEnd - quoteStart - 1);
                    material.TextureFilename = Path.Combine(directory, filename);
                }
            }

            return material;
        }

        /// <summary>
        /// ブロック（{ }）を抽出
        /// </summary>
        private string ExtractBlock(string content, int startIndex)
        {
            int braceStart = content.IndexOf('{', startIndex);
            if (braceStart < 0) return "";

            int braceCount = 1;
            int i = braceStart + 1;

            while (i < content.Length && braceCount > 0)
            {
                if (content[i] == '{') braceCount++;
                else if (content[i] == '}') braceCount--;
                i++;
            }

            return content.Substring(braceStart, i - braceStart);
        }

        /// <summary>
        /// 数値を抽出
        /// </summary>
        private List<float> ExtractNumbers(string text)
        {
            var numbers = new List<float>();

            // セミコロンとカンマを区切り文字として数値を抽出
            string[] tokens = text.Split(new[] { ' ', '\t', '\n', '\r', ';', ',', '{', '}' }, StringSplitOptions.RemoveEmptyEntries);

            foreach (string token in tokens)
            {
                if (float.TryParse(token, NumberStyles.Float, CultureInfo.InvariantCulture, out float number))
                {
                    numbers.Add(number);
                }
            }

            return numbers;
        }

        /// <summary>
        /// Unityメッシュに変換
        /// </summary>
        public Mesh ConvertToMesh(XModel xModel)
        {
            Mesh mesh = new Mesh();

            mesh.vertices = xModel.Vertices.ToArray();

            if (xModel.Normals.Count == xModel.Vertices.Count)
            {
                mesh.normals = xModel.Normals.ToArray();
            }

            if (xModel.UVs.Count == xModel.Vertices.Count)
            {
                mesh.uv = xModel.UVs.ToArray();
            }

            // 面データを三角形に変換
            List<int> triangles = new List<int>();

            foreach (var face in xModel.Faces)
            {
                if (face.Indices.Length == 3)
                {
                    // 三角形（巻き順を反転）
                    triangles.Add(face.Indices[0]);
                    triangles.Add(face.Indices[2]);
                    triangles.Add(face.Indices[1]);
                }
                else if (face.Indices.Length >= 4)
                {
                    // 四角形以上をファン方式で三角形分割
                    for (int i = 1; i < face.Indices.Length - 1; i++)
                    {
                        triangles.Add(face.Indices[0]);
                        triangles.Add(face.Indices[i + 1]);
                        triangles.Add(face.Indices[i]);
                    }
                }
            }

            mesh.triangles = triangles.ToArray();

            if (xModel.Normals.Count == 0)
            {
                mesh.RecalculateNormals();
            }

            mesh.RecalculateBounds();
            return mesh;
        }
    }
}
