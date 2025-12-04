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
    /// openBVE CSV路線ファイルパーサー
    /// </summary>
    public class CsvRouteParser
    {
        private RouteData routeData;
        private string routeDirectory;
        private float unitOfLength = 1.0f; // デフォルト：メートル
        private float currentDistance = 0f;

        /// <summary>
        /// CSV路線ファイルを解析
        /// </summary>
        public RouteData Parse(string filePath)
        {
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"Route file not found: {filePath}");
            }

            routeData = new RouteData();
            routeDirectory = Path.GetDirectoryName(filePath);

            Debug.Log($"[CsvRouteParser] Starting parse: {filePath}");

            try
            {
                // Shift-JISまたはUTF-8で読み込み
                string[] lines = ReadFileWithEncoding(filePath);
                ParseLines(lines);

                Debug.Log($"[CsvRouteParser] Parse completed. Stations: {routeData.Stations.Count}, Objects: {routeData.Objects.Count}");
                return routeData;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[CsvRouteParser] Parse error: {ex.Message}\n{ex.StackTrace}");
                throw;
            }
        }

        /// <summary>
        /// エンコーディングを自動判定して読み込み
        /// </summary>
        private string[] ReadFileWithEncoding(string filePath)
        {
            // まずUTF-8で試行
            try
            {
                return File.ReadAllLines(filePath, Encoding.UTF8);
            }
            catch
            {
                // Shift-JISで試行
                try
                {
                    Encoding shiftJis = Encoding.GetEncoding("shift_jis");
                    return File.ReadAllLines(filePath, shiftJis);
                }
                catch
                {
                    // デフォルトエンコーディング
                    return File.ReadAllLines(filePath);
                }
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
                    Debug.LogWarning($"[CsvRouteParser] Line {i + 1} parse error: {ex.Message}\nLine: {line}");
                }
            }
        }

        /// <summary>
        /// 1行を解析
        /// </summary>
        private void ParseLine(string line, int lineNumber)
        {
            // 距離程の検出（例: "1000," で始まる）
            Match distanceMatch = Regex.Match(line, @"^([\d.]+)\s*,");
            if (distanceMatch.Success)
            {
                float distance = float.Parse(distanceMatch.Groups[1].Value);
                currentDistance = distance * unitOfLength;
                line = line.Substring(distanceMatch.Length).Trim();
            }

            // コマンドと引数を分離
            string[] parts = line.Split(new[] { '(' }, 2);
            if (parts.Length < 1)
                return;

            string command = parts[0].Trim();
            string arguments = parts.Length > 1 ? parts[1].TrimEnd(')').Trim() : "";

            ParseCommand(command, arguments);
        }

        /// <summary>
        /// コマンドを解析して実行
        /// </summary>
        private void ParseCommand(string command, string arguments)
        {
            string[] args = SplitArguments(arguments);

            // コマンドの正規化（大文字小文字を無視、ドットを統一）
            string normalizedCommand = command.ToLowerInvariant().Replace('.', '_');

            switch (normalizedCommand)
            {
                // Options
                case "options_unitoflength":
                    ParseUnitOfLength(args);
                    break;

                // Route
                case "route_comment":
                    routeData.Comment = arguments;
                    Debug.Log($"[Route] Comment: {arguments}");
                    break;
                case "route_image":
                    routeData.Image = GetFullPath(arguments);
                    break;
                case "route_gauge":
                    routeData.Gauge = ParseFloat(args, 0, 1.435f);
                    Debug.Log($"[Route] Gauge: {routeData.Gauge}m");
                    break;
                case "route_elevation":
                    routeData.InitialElevation = ParseFloat(args, 0, 0f);
                    break;

                // Station
                case "station":
                case "track_sta":
                    ParseStation(args);
                    break;

                // Structure definitions
                case "structure_ground":
                    ParseStructure("ground", args);
                    break;
                case "structure_rail":
                    ParseStructure("rail", args);
                    break;
                case "structure_walll":
                    ParseStructure("walll", args);
                    break;
                case "structure_wallr":
                    ParseStructure("wallr", args);
                    break;
                case "structure_dikel":
                    ParseStructure("dikel", args);
                    break;
                case "structure_diker":
                    ParseStructure("diker", args);
                    break;
                case "structure_forml":
                    ParseStructure("forml", args);
                    break;
                case "structure_formr":
                    ParseStructure("formr", args);
                    break;

                // Track geometry
                case "track_pitch":
                    ParsePitch(args);
                    break;
                case "track_curve":
                    ParseCurve(args);
                    break;
                case "track_turn":
                    ParseTurn(args);
                    break;

                // Objects
                case "track_ground":
                    ParseTrackGround(args);
                    break;
                case "track_freeobj":
                    ParseFreeObj(args);
                    break;
                case "track_wall":
                    ParseWall(args);
                    break;

                // Background
                case "track_back":
                case "track_background":
                    ParseBackground(args);
                    break;

                // その他のコマンドは現在未実装
                default:
                    // Debug.Log($"[CsvRouteParser] Unhandled command: {command}");
                    break;
            }
        }

        /// <summary>
        /// 引数を分割（カンマ区切り、セミコロン区切り対応）
        /// </summary>
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

        /// <summary>
        /// 単位長を解析
        /// </summary>
        private void ParseUnitOfLength(string[] args)
        {
            if (args.Length > 0)
            {
                string unit = args[0].ToLowerInvariant();
                switch (unit)
                {
                    case "kilometer":
                    case "kilometers":
                        unitOfLength = 1000f;
                        break;
                    case "meter":
                    case "meters":
                        unitOfLength = 1f;
                        break;
                    case "mile":
                    case "miles":
                        unitOfLength = 1609.34f;
                        break;
                    case "yard":
                    case "yards":
                        unitOfLength = 0.9144f;
                        break;
                    default:
                        Debug.LogWarning($"[CsvRouteParser] Unknown unit of length: {unit}");
                        break;
                }
                Debug.Log($"[Options] Unit of Length: {unit} ({unitOfLength}m)");
            }
        }

        /// <summary>
        /// 駅情報を解析
        /// </summary>
        private void ParseStation(string[] args)
        {
            var station = new StationData
            {
                Position = currentDistance,
                Name = args.Length > 0 ? args[0] : "Unnamed Station",
                ArrivalTime = args.Length > 1 ? ParseTime(args[1]) : -1,
                DepartureTime = args.Length > 2 ? ParseTime(args[2]) : -1,
                StopDuration = args.Length > 3 ? ParseFloat(args[3]) : 15f,
                PassAlarm = args.Length > 4 ? ParseInt(args[4]) : 0,
                Doors = args.Length > 5 ? ParseInt(args[5]) : 0,
                ForcedRedSignal = args.Length > 6 && ParseInt(args[6]) == 1,
                System = args.Length > 7 ? ParseInt(args[7]) : 0
            };

            routeData.Stations.Add(station);
            Debug.Log($"[Station] {station.Name} at {station.Position.Meters}m");
        }

        /// <summary>
        /// 構造物定義を解析
        /// </summary>
        private void ParseStructure(string category, string[] args)
        {
            if (args.Length < 2)
                return;

            string key = $"{category}_{args[0]}";
            string modelPath = GetFullPath(args[1]);

            var structure = new StructureData
            {
                Key = key,
                ModelPath = modelPath
            };

            routeData.Structures[key] = structure;
            Debug.Log($"[Structure] {key} -> {modelPath}");
        }

        /// <summary>
        /// 勾配を解析
        /// </summary>
        private void ParsePitch(string[] args)
        {
            if (args.Length < 1)
                return;

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
        /// 曲線を解析
        /// </summary>
        private void ParseCurve(string[] args)
        {
            if (args.Length < 1)
                return;

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
        /// カントを解析
        /// </summary>
        private void ParseTurn(string[] args)
        {
            // Turn はカント（傾斜）の設定
            // 実装はCurveと組み合わせて使用
        }

        /// <summary>
        /// 地面オブジェクトを解析
        /// </summary>
        private void ParseTrackGround(string[] args)
        {
            if (args.Length < 1)
                return;

            string structureKey = $"ground_{args[0]}";

            var obj = new PlacedObject
            {
                Position = currentDistance,
                StructureKey = structureKey,
                RailIndex = 0
            };

            routeData.Objects.Add(obj);
        }

        /// <summary>
        /// 自由配置オブジェクトを解析
        /// </summary>
        private void ParseFreeObj(string[] args)
        {
            if (args.Length < 4)
                return;

            int railIndex = ParseInt(args[0]);
            string structureKey = args[1];
            float x = ParseFloat(args[2]);
            float y = ParseFloat(args[3]);
            float yaw = args.Length > 4 ? ParseFloat(args[4]) : 0;
            float pitch = args.Length > 5 ? ParseFloat(args[5]) : 0;
            float roll = args.Length > 6 ? ParseFloat(args[6]) : 0;

            var obj = new PlacedObject
            {
                Position = currentDistance,
                StructureKey = structureKey,
                RailIndex = railIndex,
                Offset = new Vector3(x, y, 0),
                RotationY = yaw
            };

            routeData.Objects.Add(obj);
        }

        /// <summary>
        /// 壁オブジェクトを解析
        /// </summary>
        private void ParseWall(string[] args)
        {
            if (args.Length < 2)
                return;

            int railIndex = ParseInt(args[0]);
            int direction = ParseInt(args[1]);
            string structureKey = args.Length > 2 ? args[2] : "";

            // 壁の配置処理
        }

        /// <summary>
        /// 背景を解析
        /// </summary>
        private void ParseBackground(string[] args)
        {
            if (args.Length < 1)
                return;

            routeData.Background = new BackgroundData
            {
                ImagePath = GetFullPath(args[0]),
                Mode = args.Length > 1 ? ParseInt(args[1]) : 0
            };

            Debug.Log($"[Background] {routeData.Background.ImagePath}");
        }

        // ヘルパーメソッド
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

        private int ParseInt(string value, int defaultValue = 0)
        {
            if (int.TryParse(value, out int result))
                return result;
            return defaultValue;
        }

        private float ParseTime(string timeString)
        {
            // HH.MMSSまたはHH:MM:SS形式の時刻を秒に変換
            if (string.IsNullOrEmpty(timeString))
                return -1;

            string[] parts = timeString.Split(new[] { '.', ':' });
            if (parts.Length >= 2)
            {
                int hours = ParseInt(parts[0]);
                int minutes = ParseInt(parts[1]);
                int seconds = parts.Length > 2 ? ParseInt(parts[2]) : 0;
                return hours * 3600 + minutes * 60 + seconds;
            }

            return -1;
        }

        private string GetFullPath(string relativePath)
        {
            if (string.IsNullOrEmpty(relativePath))
                return "";

            if (Path.IsPathRooted(relativePath))
                return relativePath;

            return Path.Combine(routeDirectory, relativePath);
        }
    }
}
