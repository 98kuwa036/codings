using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using OpenBveMobile.Core;

namespace OpenBveMobile.Parsers
{
    /// <summary>
    /// BVE5形式のマップファイルパーサー（修正版）
    /// テキストマップファイル + CSV/オブジェクトファイル参照方式
    /// </summary>
    public class Bve5MapParser
    {
        private RouteData routeData;
        private string mapDirectory;
        private float currentDistance = 0f;

        // BVE5設定
        private Dictionary<string, string> structurePaths = new Dictionary<string, string>();
        private Dictionary<string, string> stationPaths = new Dictionary<string, string>();
        private Dictionary<string, string> signalPaths = new Dictionary<string, string>();
        private Dictionary<string, string> soundPaths = new Dictionary<string, string>();

        /// <summary>
        /// BVE5マップファイルを解析
        /// </summary>
        public RouteData Parse(string filePath)
        {
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"BVE5 map file not found: {filePath}");
            }

            routeData = new RouteData();
            mapDirectory = Path.GetDirectoryName(filePath);

            Debug.Log($"[Bve5MapParser] Starting parse: {filePath}");

            try
            {
                Encoding encoding = DetectEncoding(filePath);
                string[] lines = File.ReadAllLines(filePath, encoding);
                ParseLines(lines);

                Debug.Log($"[Bve5MapParser] Parse completed. Stations: {routeData.Stations.Count}");
                return routeData;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[Bve5MapParser] Parse error: {ex.Message}\n{ex.StackTrace}");
                throw;
            }
        }

        /// <summary>
        /// 行ごとに解析
        /// </summary>
        private void ParseLines(string[] lines)
        {
            for (int i = 0; i < lines.Length; i++)
            {
                string line = lines[i].Trim();

                // コメント除去
                int commentIndex = line.IndexOf(';');
                if (commentIndex < 0)
                    commentIndex = line.IndexOf("//");

                if (commentIndex >= 0)
                {
                    line = line.Substring(0, commentIndex).Trim();
                }

                if (string.IsNullOrEmpty(line))
                    continue;

                try
                {
                    ParseLine(line, i + 1);
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"[Bve5MapParser] Line {i + 1} parse error: {ex.Message}\nLine: {line}");
                }
            }
        }

        /// <summary>
        /// 1行を解析
        /// </summary>
        private void ParseLine(string line, int lineNumber)
        {
            // BVE5は距離程とコマンドが同一行
            // 形式: "距離程;コマンド(引数)" または "コマンド(引数)"

            // 距離程の検出
            string[] distanceSplit = line.Split(new[] { ';' }, 2);
            if (distanceSplit.Length == 2 && float.TryParse(distanceSplit[0].Trim(), out float distance))
            {
                currentDistance = distance;
                line = distanceSplit[1].Trim();
            }

            // コマンド解析
            ParseCommand(line);
        }

        /// <summary>
        /// コマンドを解析
        /// </summary>
        private void ParseCommand(string line)
        {
            // コマンドと引数を分離
            int parenIndex = line.IndexOf('(');
            if (parenIndex < 0)
                return;

            string command = line.Substring(0, parenIndex).Trim();
            string arguments = line.Substring(parenIndex + 1).TrimEnd(')').Trim();
            string[] args = SplitArguments(arguments);

            // コマンド正規化
            string normalizedCommand = command.ToLowerInvariant().Replace('.', '_');

            switch (normalizedCommand)
            {
                // ファイル読み込み系コマンド
                case "bveats_map_load":
                case "map_load":
                    LoadMapFile(args);
                    break;

                case "structure_load":
                    LoadStructureDefinition(args);
                    break;

                case "station_load":
                    LoadStationDefinition(args);
                    break;

                case "signal_load":
                    LoadSignalDefinition(args);
                    break;

                case "sound_load":
                    LoadSoundDefinition(args);
                    break;

                // 路線情報
                case "route_comment":
                    routeData.Comment = arguments;
                    break;

                case "route_gauge":
                    routeData.Gauge = ParseFloat(args, 0, 1.435f);
                    break;

                // 線形
                case "curve_setgauge":
                case "curve":
                    ParseCurve(args);
                    break;

                case "gradient_begintransition":
                case "gradient":
                    ParseGradient(args);
                    break;

                // 構造物配置
                case "structure_put":
                case "structure_put0":
                    ParseStructurePlacement(args);
                    break;

                case "structure_putbetween":
                    ParseStructurePutBetween(args);
                    break;

                // 駅
                case "station_put":
                    ParseStationPlacement(args);
                    break;

                // その他のBVE5コマンド
                default:
                    // 未実装のコマンドは警告のみ
                    // Debug.LogWarning($"[Bve5MapParser] Unhandled command: {command}");
                    break;
            }
        }

        /// <summary>
        /// マップファイルを読み込み（入れ子対応）
        /// </summary>
        private void LoadMapFile(string[] args)
        {
            if (args.Length < 1) return;

            string mapPath = GetFullPath(args[0]);
            if (File.Exists(mapPath))
            {
                Debug.Log($"[Bve5MapParser] Loading nested map: {mapPath}");

                // 入れ子のマップファイルを解析
                string[] lines = File.ReadAllLines(mapPath);
                ParseLines(lines);
            }
        }

        /// <summary>
        /// 構造物定義ファイルを読み込み
        /// </summary>
        private void LoadStructureDefinition(string[] args)
        {
            if (args.Length < 2) return;

            string key = args[0];
            string filePath = GetFullPath(args[1]);

            structurePaths[key] = filePath;

            var structure = new StructureData
            {
                Key = key,
                ModelPath = filePath
            };

            routeData.Structures[key] = structure;
            Debug.Log($"[Bve5MapParser] Structure loaded: {key} -> {filePath}");
        }

        /// <summary>
        /// 駅定義ファイルを読み込み
        /// </summary>
        private void LoadStationDefinition(string[] args)
        {
            if (args.Length < 2) return;

            string key = args[0];
            string filePath = GetFullPath(args[1]);

            stationPaths[key] = filePath;
            Debug.Log($"[Bve5MapParser] Station definition loaded: {key} -> {filePath}");
        }

        /// <summary>
        /// 信号定義ファイルを読み込み
        /// </summary>
        private void LoadSignalDefinition(string[] args)
        {
            if (args.Length < 2) return;

            string key = args[0];
            string filePath = GetFullPath(args[1]);

            signalPaths[key] = filePath;
            Debug.Log($"[Bve5MapParser] Signal definition loaded: {key}");
        }

        /// <summary>
        /// サウンド定義を読み込み
        /// </summary>
        private void LoadSoundDefinition(string[] args)
        {
            if (args.Length < 2) return;

            string key = args[0];
            string filePath = GetFullPath(args[1]);

            soundPaths[key] = filePath;
            Debug.Log($"[Bve5MapParser] Sound loaded: {key}");
        }

        /// <summary>
        /// 曲線を解析
        /// </summary>
        private void ParseCurve(string[] args)
        {
            if (args.Length < 1) return;

            float radius = ParseFloat(args[0]);
            float cant = args.Length > 1 ? ParseFloat(args[1]) : 0;

            var geometry = new TrackGeometry
            {
                StartPosition = currentDistance,
                Radius = radius,
                Gradient = 0
            };

            routeData.Geometries.Add(geometry);
        }

        /// <summary>
        /// 勾配を解析
        /// </summary>
        private void ParseGradient(string[] args)
        {
            if (args.Length < 1) return;

            float gradient = ParseFloat(args[0]);

            var geometry = new TrackGeometry
            {
                StartPosition = currentDistance,
                Gradient = gradient,
                Radius = 0
            };

            routeData.Geometries.Add(geometry);
        }

        /// <summary>
        /// 構造物配置
        /// </summary>
        private void ParseStructurePlacement(string[] args)
        {
            if (args.Length < 1) return;

            string key = args[0];
            float x = args.Length > 1 ? ParseFloat(args[1]) : 0;
            float y = args.Length > 2 ? ParseFloat(args[2]) : 0;
            float yaw = args.Length > 3 ? ParseFloat(args[3]) : 0;

            var obj = new PlacedObject
            {
                Position = currentDistance,
                StructureKey = key,
                RailIndex = 0,
                Offset = new Vector3(x, y, 0),
                RotationY = yaw
            };

            routeData.Objects.Add(obj);
        }

        /// <summary>
        /// 構造物を区間配置（繰り返し）
        /// </summary>
        private void ParseStructurePutBetween(string[] args)
        {
            if (args.Length < 3) return;

            string key = args[0];
            float startDist = ParseFloat(args[1]);
            float endDist = ParseFloat(args[2]);
            float interval = args.Length > 3 ? ParseFloat(args[3]) : 25f;

            // 指定区間に繰り返し配置
            for (float dist = startDist; dist <= endDist; dist += interval)
            {
                var obj = new PlacedObject
                {
                    Position = dist,
                    StructureKey = key,
                    RailIndex = 0
                };

                routeData.Objects.Add(obj);
            }

            Debug.Log($"[Bve5MapParser] Structure repeated: {key} from {startDist}m to {endDist}m");
        }

        /// <summary>
        /// 駅配置
        /// </summary>
        private void ParseStationPlacement(string[] args)
        {
            if (args.Length < 1) return;

            string stationKey = args[0];
            string stationName = args.Length > 1 ? args[1] : stationKey;

            var station = new StationData
            {
                Position = currentDistance,
                Name = stationName,
                ArrivalTime = -1,
                DepartureTime = -1,
                StopDuration = 15f,
                Doors = 1
            };

            routeData.Stations.Add(station);
            Debug.Log($"[Bve5MapParser] Station: {stationName} at {currentDistance}m");
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

        private float ParseFloat(string[] args, int index, float defaultValue = 0f)
        {
            if (args.Length <= index || string.IsNullOrEmpty(args[index]))
                return defaultValue;

            return ParseFloat(args[index], defaultValue);
        }

        private float ParseFloat(string value, float defaultValue = 0f)
        {
            if (float.TryParse(value, out float result))
                return result;
            return defaultValue;
        }

        private string GetFullPath(string relativePath)
        {
            if (string.IsNullOrEmpty(relativePath))
                return "";

            if (Path.IsPathRooted(relativePath))
                return relativePath;

            return Path.Combine(mapDirectory, relativePath);
        }

        private Encoding DetectEncoding(string filePath)
        {
            byte[] bom = new byte[4];
            using (FileStream fs = new FileStream(filePath, FileMode.Open, FileAccess.Read))
            {
                fs.Read(bom, 0, 4);
            }

            if (bom[0] == 0xEF && bom[1] == 0xBB && bom[2] == 0xBF)
                return Encoding.UTF8;

            try
            {
                return Encoding.GetEncoding("shift_jis");
            }
            catch
            {
                return Encoding.UTF8;
            }
        }
    }
}
