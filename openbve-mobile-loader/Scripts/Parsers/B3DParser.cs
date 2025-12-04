using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace OpenBveMobile.Parsers
{
    /// <summary>
    /// openBVE B3D (Binary 3D) ファイルパーサー
    /// B3DはopenBVE独自の3Dモデルフォーマット
    /// </summary>
    public class B3DParser
    {
        public class B3DModel
        {
            public List<Vector3> Vertices = new List<Vector3>();
            public List<Vector3> Normals = new List<Vector3>();
            public List<Vector2> UVs = new List<Vector2>();
            public List<Color32> Colors = new List<Color32>();
            public List<Face> Faces = new List<Face>();
            public string TexturePath;
            public bool EmissiveColor;
            public Color32 EmissiveColorValue;
        }

        public class Face
        {
            public int[] VertexIndices;
            public bool IsQuad => VertexIndices.Length == 4;
        }

        /// <summary>
        /// B3Dファイルを解析
        /// </summary>
        public B3DModel Parse(string filePath)
        {
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"B3D file not found: {filePath}");
            }

            Debug.Log($"[B3DParser] Parsing: {filePath}");

            using (FileStream fs = new FileStream(filePath, FileMode.Open, FileAccess.Read))
            using (BinaryReader reader = new BinaryReader(fs))
            {
                return ParseB3D(reader, Path.GetDirectoryName(filePath));
            }
        }

        private B3DModel ParseB3D(BinaryReader reader, string directory)
        {
            var model = new B3DModel();

            try
            {
                // B3Dファイルヘッダーチェック（簡易版）
                // 実際のB3Dフォーマットはテキストベースのセクション構造

                // B3Dはテキストとバイナリ混在形式
                // とりあえずバイナリ読み込みを実装
                // 注：実際のB3Dは複雑なので、基本構造のみ実装

                string header = ReadString(reader);
                if (!header.Contains("B3D") && !header.Contains("[MeshBuilder]"))
                {
                    Debug.LogWarning("[B3DParser] Invalid B3D header, attempting to parse anyway");
                }

                // セクション読み込み
                while (reader.BaseStream.Position < reader.BaseStream.Length)
                {
                    string line = ReadLine(reader);
                    if (string.IsNullOrEmpty(line))
                        continue;

                    line = line.Trim();

                    if (line.StartsWith("[MeshBuilder]", StringComparison.OrdinalIgnoreCase))
                    {
                        ParseMeshBuilder(reader, model);
                    }
                    else if (line.StartsWith("Vertex", StringComparison.OrdinalIgnoreCase))
                    {
                        ParseVertex(line, model);
                    }
                    else if (line.StartsWith("Face", StringComparison.OrdinalIgnoreCase))
                    {
                        ParseFace(line, model);
                    }
                    else if (line.StartsWith("SetTexture", StringComparison.OrdinalIgnoreCase))
                    {
                        ParseTexture(line, model, directory);
                    }
                    else if (line.StartsWith("SetEmissiveColor", StringComparison.OrdinalIgnoreCase))
                    {
                        ParseEmissiveColor(line, model);
                    }
                }

                Debug.Log($"[B3DParser] Loaded: {model.Vertices.Count} vertices, {model.Faces.Count} faces");
                return model;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[B3DParser] Parse error: {ex.Message}");
                throw;
            }
        }

        private void ParseMeshBuilder(BinaryReader reader, B3DModel model)
        {
            // MeshBuilderセクションの処理
            // 実装はコマンドに応じて分岐
        }

        /// <summary>
        /// 頂点コマンドを解析
        /// 形式: Vertex vX, vY, vZ, nX, nY, nZ
        /// </summary>
        private void ParseVertex(string line, B3DModel model)
        {
            string[] parts = line.Split(new[] { ' ', ',' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 4) // 最低でも Vertex x y z
                return;

            try
            {
                float x = float.Parse(parts[1]);
                float y = float.Parse(parts[2]);
                float z = float.Parse(parts[3]);
                model.Vertices.Add(new Vector3(x, y, z));

                // 法線がある場合
                if (parts.Length >= 7)
                {
                    float nx = float.Parse(parts[4]);
                    float ny = float.Parse(parts[5]);
                    float nz = float.Parse(parts[6]);
                    model.Normals.Add(new Vector3(nx, ny, nz));
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[B3DParser] Vertex parse error: {ex.Message}");
            }
        }

        /// <summary>
        /// 面コマンドを解析
        /// 形式: Face v0, v1, v2 または Face v0, v1, v2, v3
        /// </summary>
        private void ParseFace(string line, B3DModel model)
        {
            string[] parts = line.Split(new[] { ' ', ',' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 4) // Face + 最低3頂点
                return;

            try
            {
                var face = new Face();
                var indices = new List<int>();

                for (int i = 1; i < parts.Length; i++)
                {
                    if (int.TryParse(parts[i], out int index))
                    {
                        indices.Add(index);
                    }
                }

                face.VertexIndices = indices.ToArray();
                model.Faces.Add(face);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[B3DParser] Face parse error: {ex.Message}");
            }
        }

        /// <summary>
        /// テクスチャコマンドを解析
        /// 形式: SetTexture DayTexture, texture.png
        /// </summary>
        private void ParseTexture(string line, B3DModel model, string directory)
        {
            // SetTexture の後のファイル名を抽出
            int commaIndex = line.IndexOf(',');
            if (commaIndex > 0)
            {
                string textureName = line.Substring(commaIndex + 1).Trim();
                model.TexturePath = Path.Combine(directory, textureName);
                Debug.Log($"[B3DParser] Texture: {model.TexturePath}");
            }
        }

        /// <summary>
        /// エミッシブカラーを解析
        /// 形式: SetEmissiveColor r, g, b
        /// </summary>
        private void ParseEmissiveColor(string line, B3DModel model)
        {
            string[] parts = line.Split(new[] { ' ', ',' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length >= 4)
            {
                try
                {
                    byte r = byte.Parse(parts[1]);
                    byte g = byte.Parse(parts[2]);
                    byte b = byte.Parse(parts[3]);
                    model.EmissiveColor = true;
                    model.EmissiveColorValue = new Color32(r, g, b, 255);
                }
                catch { }
            }
        }

        /// <summary>
        /// Unityメッシュに変換
        /// </summary>
        public Mesh ConvertToMesh(B3DModel b3dModel)
        {
            Mesh mesh = new Mesh();

            // 頂点データ設定
            mesh.vertices = b3dModel.Vertices.ToArray();

            if (b3dModel.Normals.Count == b3dModel.Vertices.Count)
            {
                mesh.normals = b3dModel.Normals.ToArray();
            }

            if (b3dModel.UVs.Count == b3dModel.Vertices.Count)
            {
                mesh.uv = b3dModel.UVs.ToArray();
            }

            if (b3dModel.Colors.Count == b3dModel.Vertices.Count)
            {
                mesh.colors32 = b3dModel.Colors.ToArray();
            }

            // 面データを三角形インデックスに変換
            List<int> triangles = new List<int>();
            foreach (var face in b3dModel.Faces)
            {
                if (face.VertexIndices.Length == 3)
                {
                    // 三角形
                    triangles.Add(face.VertexIndices[0]);
                    triangles.Add(face.VertexIndices[1]);
                    triangles.Add(face.VertexIndices[2]);
                }
                else if (face.VertexIndices.Length == 4)
                {
                    // 四角形を2つの三角形に分割
                    triangles.Add(face.VertexIndices[0]);
                    triangles.Add(face.VertexIndices[1]);
                    triangles.Add(face.VertexIndices[2]);

                    triangles.Add(face.VertexIndices[0]);
                    triangles.Add(face.VertexIndices[2]);
                    triangles.Add(face.VertexIndices[3]);
                }
            }

            mesh.triangles = triangles.ToArray();

            // 法線が無い場合は自動計算
            if (b3dModel.Normals.Count == 0)
            {
                mesh.RecalculateNormals();
            }

            mesh.RecalculateBounds();
            return mesh;
        }

        // ヘルパーメソッド
        private string ReadString(BinaryReader reader)
        {
            List<byte> bytes = new List<byte>();
            byte b;
            while ((b = reader.ReadByte()) != 0 && reader.BaseStream.Position < reader.BaseStream.Length)
            {
                bytes.Add(b);
            }
            return Encoding.ASCII.GetString(bytes.ToArray());
        }

        private string ReadLine(BinaryReader reader)
        {
            List<byte> bytes = new List<byte>();
            byte b;
            while (reader.BaseStream.Position < reader.BaseStream.Length)
            {
                b = reader.ReadByte();
                if (b == '\n' || b == '\r')
                {
                    // 改行スキップ
                    if (b == '\r' && reader.BaseStream.Position < reader.BaseStream.Length)
                    {
                        byte next = reader.ReadByte();
                        if (next != '\n')
                        {
                            reader.BaseStream.Position--;
                        }
                    }
                    break;
                }
                bytes.Add(b);
            }
            return Encoding.UTF8.GetString(bytes.ToArray());
        }
    }
}
