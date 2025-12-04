using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace OpenBveMobile.Parsers
{
    /// <summary>
    /// openBVE CSVオブジェクトファイルパーサー
    /// CSVフォーマットで定義された3Dオブジェクトを解析
    /// </summary>
    public class CsvObjectParser
    {
        public class CsvObject
        {
            public List<Vector3> Vertices = new List<Vector3>();
            public List<Vector3> Normals = new List<Vector3>();
            public List<Vector2> UVs = new List<Vector2>();
            public List<Color32> Colors = new List<Color32>();
            public List<Face> Faces = new List<Face>();
            public string TexturePath;
            public Color32 Color = new Color32(255, 255, 255, 255);
            public bool EmissiveColor;
            public Color32 EmissiveColorValue;
            public bool TransparentColor;
            public Color32 TransparentColorValue;
        }

        public class Face
        {
            public int[] VertexIndices;
            public bool TwoSided = false;
        }

        private string objectDirectory;

        /// <summary>
        /// CSVオブジェクトファイルを解析
        /// </summary>
        public CsvObject Parse(string filePath)
        {
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"CSV object file not found: {filePath}");
            }

            objectDirectory = Path.GetDirectoryName(filePath);
            Debug.Log($"[CsvObjectParser] Parsing: {filePath}");

            var csvObject = new CsvObject();

            try
            {
                string[] lines = File.ReadAllLines(filePath, Encoding.UTF8);

                foreach (string rawLine in lines)
                {
                    string line = rawLine.Trim();

                    // コメント除去
                    int commentIndex = line.IndexOf(';');
                    if (commentIndex >= 0)
                    {
                        line = line.Substring(0, commentIndex).Trim();
                    }

                    if (string.IsNullOrEmpty(line))
                        continue;

                    ParseCommand(line, csvObject);
                }

                Debug.Log($"[CsvObjectParser] Loaded: {csvObject.Vertices.Count} vertices, {csvObject.Faces.Count} faces");
                return csvObject;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[CsvObjectParser] Parse error: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// コマンドを解析
        /// </summary>
        private void ParseCommand(string line, CsvObject csvObject)
        {
            // コマンドと引数を分離
            int parenIndex = line.IndexOf('(');
            if (parenIndex < 0)
                return;

            string command = line.Substring(0, parenIndex).Trim().ToLowerInvariant();
            string arguments = line.Substring(parenIndex + 1).TrimEnd(')').Trim();
            string[] args = SplitArguments(arguments);

            switch (command)
            {
                case "createvertex":
                case "vertex":
                    ParseVertex(args, csvObject);
                    break;

                case "addface":
                case "face":
                case "face2":
                    ParseFace(args, csvObject, command == "face2");
                    break;

                case "setcolor":
                case "color":
                    ParseColor(args, csvObject);
                    break;

                case "loadtexture":
                case "texture":
                    ParseTexture(args, csvObject);
                    break;

                case "setemissivecolor":
                    ParseEmissiveColor(args, csvObject);
                    break;

                case "settransparentcolor":
                    ParseTransparentColor(args, csvObject);
                    break;

                case "translate":
                case "rotate":
                case "scale":
                    // 変形コマンド（後で実装）
                    break;

                default:
                    // Debug.Log($"[CsvObjectParser] Unknown command: {command}");
                    break;
            }
        }

        /// <summary>
        /// 頂点を解析
        /// 形式: CreateVertex(vX, vY, vZ, nX, nY, nZ)
        /// </summary>
        private void ParseVertex(string[] args, CsvObject csvObject)
        {
            if (args.Length < 3)
                return;

            try
            {
                float x = ParseFloat(args[0]);
                float y = ParseFloat(args[1]);
                float z = ParseFloat(args[2]);
                csvObject.Vertices.Add(new Vector3(x, y, z));

                // 法線
                if (args.Length >= 6)
                {
                    float nx = ParseFloat(args[3]);
                    float ny = ParseFloat(args[4]);
                    float nz = ParseFloat(args[5]);
                    csvObject.Normals.Add(new Vector3(nx, ny, nz));
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[CsvObjectParser] Vertex parse error: {ex.Message}");
            }
        }

        /// <summary>
        /// 面を解析
        /// 形式: AddFace(v0, v1, v2, ..., vN)
        /// Face2は両面レンダリング
        /// </summary>
        private void ParseFace(string[] args, CsvObject csvObject, bool twoSided)
        {
            if (args.Length < 3)
                return;

            try
            {
                var face = new Face
                {
                    TwoSided = twoSided
                };

                List<int> indices = new List<int>();
                foreach (string arg in args)
                {
                    if (int.TryParse(arg, out int index))
                    {
                        indices.Add(index);
                    }
                }

                face.VertexIndices = indices.ToArray();
                csvObject.Faces.Add(face);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[CsvObjectParser] Face parse error: {ex.Message}");
            }
        }

        /// <summary>
        /// 色を解析
        /// 形式: SetColor(r, g, b, a)
        /// </summary>
        private void ParseColor(string[] args, CsvObject csvObject)
        {
            if (args.Length < 3)
                return;

            try
            {
                byte r = (byte)Mathf.Clamp(ParseInt(args[0]), 0, 255);
                byte g = (byte)Mathf.Clamp(ParseInt(args[1]), 0, 255);
                byte b = (byte)Mathf.Clamp(ParseInt(args[2]), 0, 255);
                byte a = args.Length > 3 ? (byte)Mathf.Clamp(ParseInt(args[3]), 0, 255) : (byte)255;

                csvObject.Color = new Color32(r, g, b, a);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[CsvObjectParser] Color parse error: {ex.Message}");
            }
        }

        /// <summary>
        /// テクスチャを解析
        /// 形式: LoadTexture(DayTexture, texture.png)
        /// </summary>
        private void ParseTexture(string[] args, CsvObject csvObject)
        {
            if (args.Length < 2)
                return;

            string texturePath = args[1].Trim();
            csvObject.TexturePath = Path.Combine(objectDirectory, texturePath);
            Debug.Log($"[CsvObjectParser] Texture: {csvObject.TexturePath}");
        }

        /// <summary>
        /// エミッシブカラーを解析
        /// </summary>
        private void ParseEmissiveColor(string[] args, CsvObject csvObject)
        {
            if (args.Length < 3)
                return;

            try
            {
                byte r = (byte)Mathf.Clamp(ParseInt(args[0]), 0, 255);
                byte g = (byte)Mathf.Clamp(ParseInt(args[1]), 0, 255);
                byte b = (byte)Mathf.Clamp(ParseInt(args[2]), 0, 255);

                csvObject.EmissiveColor = true;
                csvObject.EmissiveColorValue = new Color32(r, g, b, 255);
            }
            catch { }
        }

        /// <summary>
        /// 透明色を解析
        /// </summary>
        private void ParseTransparentColor(string[] args, CsvObject csvObject)
        {
            if (args.Length < 3)
                return;

            try
            {
                byte r = (byte)Mathf.Clamp(ParseInt(args[0]), 0, 255);
                byte g = (byte)Mathf.Clamp(ParseInt(args[1]), 0, 255);
                byte b = (byte)Mathf.Clamp(ParseInt(args[2]), 0, 255);

                csvObject.TransparentColor = true;
                csvObject.TransparentColorValue = new Color32(r, g, b, 255);
            }
            catch { }
        }

        /// <summary>
        /// Unityメッシュに変換
        /// </summary>
        public Mesh ConvertToMesh(CsvObject csvObject)
        {
            Mesh mesh = new Mesh();

            mesh.vertices = csvObject.Vertices.ToArray();

            if (csvObject.Normals.Count == csvObject.Vertices.Count)
            {
                mesh.normals = csvObject.Normals.ToArray();
            }

            if (csvObject.UVs.Count == csvObject.Vertices.Count)
            {
                mesh.uv = csvObject.UVs.ToArray();
            }

            // 面データを三角形インデックスに変換
            List<int> triangles = new List<int>();
            foreach (var face in csvObject.Faces)
            {
                if (face.VertexIndices.Length == 3)
                {
                    triangles.Add(face.VertexIndices[0]);
                    triangles.Add(face.VertexIndices[1]);
                    triangles.Add(face.VertexIndices[2]);
                }
                else if (face.VertexIndices.Length >= 4)
                {
                    // N角形を三角形に分割（ファン方式）
                    for (int i = 1; i < face.VertexIndices.Length - 1; i++)
                    {
                        triangles.Add(face.VertexIndices[0]);
                        triangles.Add(face.VertexIndices[i]);
                        triangles.Add(face.VertexIndices[i + 1]);
                    }
                }

                // 両面レンダリングの場合は裏面も追加
                if (face.TwoSided && face.VertexIndices.Length >= 3)
                {
                    if (face.VertexIndices.Length == 3)
                    {
                        triangles.Add(face.VertexIndices[2]);
                        triangles.Add(face.VertexIndices[1]);
                        triangles.Add(face.VertexIndices[0]);
                    }
                    else if (face.VertexIndices.Length >= 4)
                    {
                        for (int i = 1; i < face.VertexIndices.Length - 1; i++)
                        {
                            triangles.Add(face.VertexIndices[i + 1]);
                            triangles.Add(face.VertexIndices[i]);
                            triangles.Add(face.VertexIndices[0]);
                        }
                    }
                }
            }

            mesh.triangles = triangles.ToArray();

            // 法線が無い場合は自動計算
            if (csvObject.Normals.Count == 0)
            {
                mesh.RecalculateNormals();
            }

            mesh.RecalculateBounds();
            return mesh;
        }

        // ヘルパーメソッド
        private string[] SplitArguments(string arguments)
        {
            if (string.IsNullOrEmpty(arguments))
                return new string[0];

            char separator = arguments.Contains(";") ? ';' : ',';
            string[] parts = arguments.Split(separator);

            for (int i = 0; i < parts.Length; i++)
            {
                parts[i] = parts[i].Trim();
            }

            return parts;
        }

        private float ParseFloat(string value)
        {
            if (float.TryParse(value, out float result))
                return result;
            return 0f;
        }

        private int ParseInt(string value)
        {
            if (int.TryParse(value, out int result))
                return result;
            return 0;
        }
    }
}
