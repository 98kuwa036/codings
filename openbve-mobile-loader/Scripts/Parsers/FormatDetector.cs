using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;

namespace OpenBveMobile.Parsers
{
    /// <summary>
    /// BVEフォーマット種別
    /// </summary>
    public enum BveFormat
    {
        Unknown,
        BVE2,       // BVE Trainsim 2.x
        BVE4,       // BVE Trainsim 4.x
        BVE5,       // BVE Trainsim 5.x
        OpenBVE     // openBVE
    }

    /// <summary>
    /// BVEフォーマット自動検出クラス
    /// ファイルの内容を解析してBVE2/4/5/openBVEを判別
    /// </summary>
    public static class FormatDetector
    {
        /// <summary>
        /// 路線ファイルのフォーマットを検出
        /// </summary>
        public static BveFormat DetectRouteFormat(string filePath)
        {
            if (!File.Exists(filePath))
            {
                Debug.LogError($"[FormatDetector] File not found: {filePath}");
                return BveFormat.Unknown;
            }

            string extension = Path.GetExtension(filePath).ToLowerInvariant();

            // 拡張子による判定
            if (extension == ".xml")
            {
                return BveFormat.BVE5; // BVE5はXML形式
            }

            // ファイル内容を読み込んで判定
            try
            {
                string[] lines = ReadFileLines(filePath, 50); // 最初の50行で判定

                // BVE5のXMLチェック
                if (ContainsPattern(lines, @"<\?xml"))
                {
                    return BveFormat.BVE5;
                }

                // BVE4/openBVEの特徴的なコマンドをチェック
                if (ContainsPattern(lines, @"Options\.") ||
                    ContainsPattern(lines, @"Route\.") ||
                    ContainsPattern(lines, @"Structure\."))
                {
                    // openBVE独自コマンドがあるかチェック
                    if (ContainsPattern(lines, @"Track\.SigF") ||
                        ContainsPattern(lines, @"Track\.PreTrain") ||
                        ContainsPattern(lines, @"Route\.DynamicLight"))
                    {
                        return BveFormat.OpenBVE;
                    }
                    return BveFormat.BVE4;
                }

                // BVE2の特徴をチェック（距離程が単独行）
                if (ContainsPattern(lines, @"^\d+\s*$"))
                {
                    // BVE2は距離程とコマンドが別行
                    return BveFormat.BVE2;
                }

                // デフォルトはBVE4/openBVE互換として扱う
                Debug.LogWarning("[FormatDetector] Could not determine format, assuming BVE4/openBVE");
                return BveFormat.BVE4;
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[FormatDetector] Error detecting format: {ex.Message}");
                return BveFormat.Unknown;
            }
        }

        /// <summary>
        /// 車両ファイルのフォーマットを検出
        /// </summary>
        public static BveFormat DetectTrainFormat(string directoryPath)
        {
            if (!Directory.Exists(directoryPath))
            {
                Debug.LogError($"[FormatDetector] Directory not found: {directoryPath}");
                return BveFormat.Unknown;
            }

            // BVE5: vehicle.xml が存在
            if (File.Exists(Path.Combine(directoryPath, "vehicle.xml")))
            {
                return BveFormat.BVE5;
            }

            // BVE4/openBVE: train.dat が存在
            if (File.Exists(Path.Combine(directoryPath, "train.dat")))
            {
                // 内容でBVE4/openBVEを判別
                string trainDat = Path.Combine(directoryPath, "train.dat");
                string[] lines = ReadFileLines(trainDat, 30);

                // openBVE独自パラメータをチェック
                if (ContainsPattern(lines, @"BVE\s*=\s*\d+\.\d+"))
                {
                    return BveFormat.OpenBVE;
                }

                return BveFormat.BVE4;
            }

            // BVE2: train.txt が存在
            if (File.Exists(Path.Combine(directoryPath, "train.txt")))
            {
                return BveFormat.BVE2;
            }

            Debug.LogWarning("[FormatDetector] Could not determine train format");
            return BveFormat.Unknown;
        }

        /// <summary>
        /// オブジェクトファイルのフォーマットを検出
        /// </summary>
        public static string DetectObjectFormat(string filePath)
        {
            string extension = Path.GetExtension(filePath).ToLowerInvariant();

            switch (extension)
            {
                case ".b3d":
                    return "B3D"; // openBVE独自

                case ".csv":
                    // CSVの種類を判別
                    if (File.Exists(filePath))
                    {
                        string[] lines = ReadFileLines(filePath, 10);
                        if (ContainsPattern(lines, @"CreateMeshBuilder|AddVertex|AddFace"))
                        {
                            return "CSV_OBJECT"; // BVE4/openBVE
                        }
                    }
                    return "CSV_ROUTE"; // デフォルトは路線CSV

                case ".x":
                    return "DIRECTX"; // DirectX形式

                case ".obj":
                    return "WAVEFRONT"; // Wavefront OBJ

                case ".xml":
                    return "BVE5_XML"; // BVE5独自

                default:
                    return "UNKNOWN";
            }
        }

        /// <summary>
        /// ファイルの最初のN行を読み込み
        /// </summary>
        private static string[] ReadFileLines(string filePath, int maxLines)
        {
            try
            {
                // エンコーディング自動判定
                Encoding encoding = DetectEncoding(filePath);

                var lines = new System.Collections.Generic.List<string>();
                using (StreamReader reader = new StreamReader(filePath, encoding))
                {
                    int count = 0;
                    string line;
                    while ((line = reader.ReadLine()) != null && count < maxLines)
                    {
                        lines.Add(line);
                        count++;
                    }
                }
                return lines.ToArray();
            }
            catch
            {
                return new string[0];
            }
        }

        /// <summary>
        /// パターンが存在するかチェック
        /// </summary>
        private static bool ContainsPattern(string[] lines, string pattern)
        {
            Regex regex = new Regex(pattern, RegexOptions.IgnoreCase);

            foreach (string line in lines)
            {
                if (regex.IsMatch(line))
                {
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// エンコーディングを検出
        /// </summary>
        private static Encoding DetectEncoding(string filePath)
        {
            // BOMチェック
            byte[] bom = new byte[4];
            using (FileStream fs = new FileStream(filePath, FileMode.Open, FileAccess.Read))
            {
                fs.Read(bom, 0, 4);
            }

            // UTF-8 BOM
            if (bom[0] == 0xEF && bom[1] == 0xBB && bom[2] == 0xBF)
                return Encoding.UTF8;

            // UTF-16 LE BOM
            if (bom[0] == 0xFF && bom[1] == 0xFE)
                return Encoding.Unicode;

            // UTF-16 BE BOM
            if (bom[0] == 0xFE && bom[1] == 0xFF)
                return Encoding.BigEndianUnicode;

            // BOMなし：Shift-JISまたはUTF-8
            // 日本のBVEデータは主にShift-JIS
            try
            {
                return Encoding.GetEncoding("shift_jis");
            }
            catch
            {
                return Encoding.UTF8;
            }
        }

        /// <summary>
        /// フォーマット情報を取得
        /// </summary>
        public static string GetFormatInfo(BveFormat format)
        {
            switch (format)
            {
                case BveFormat.BVE2:
                    return "BVE Trainsim 2.x (Legacy format)";
                case BveFormat.BVE4:
                    return "BVE Trainsim 4.x (Standard CSV format)";
                case BveFormat.BVE5:
                    return "BVE Trainsim 5.x (XML/Modern format)";
                case BveFormat.OpenBVE:
                    return "openBVE (Extended CSV format)";
                default:
                    return "Unknown format";
            }
        }

        /// <summary>
        /// 互換性チェック
        /// </summary>
        public static bool IsCompatible(BveFormat format)
        {
            switch (format)
            {
                case BveFormat.BVE2:
                case BveFormat.BVE4:
                case BveFormat.OpenBVE:
                    return true;  // 現在対応済み

                case BveFormat.BVE5:
                    return false; // 部分的対応（今後実装）

                default:
                    return false;
            }
        }
    }
}
