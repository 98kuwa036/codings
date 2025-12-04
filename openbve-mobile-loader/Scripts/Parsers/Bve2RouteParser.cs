using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using OpenBveMobile.Core;

namespace OpenBveMobile.Parsers
{
    /// <summary>
    /// BVE2形式の路線ファイルパーサー
    /// BVE Trainsim 2.x の古い形式に対応
    /// </summary>
    public class Bve2RouteParser
    {
        private RouteData routeData;
        private string routeDirectory;
        private float currentDistance = 0f;
        private float distanceStep = 25f; // BVE2のデフォルト距離間隔

        /// <summary>
        /// BVE2路線ファイルを解析
        /// </summary>
        public RouteData Parse(string filePath)
        {
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"BVE2 route file not found: {filePath}");
            }

            routeData = new RouteData();
            routeDirectory = Path.GetDirectoryName(filePath);

            Debug.Log($"[Bve2RouteParser] Starting parse: {filePath}");

            try
            {
                Encoding shiftJis = Encoding.GetEncoding("shift_jis");
                string[] lines = File.ReadAllLines(filePath, shiftJis);
                ParseLines(lines);

                Debug.Log($"[Bve2RouteParser] Parse completed. Stations: {routeData.Stations.Count}");
                return routeData;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[Bve2RouteParser] Parse error: {ex.Message}\n{ex.StackTrace}");
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

                // コメント除去（BVE2は ; または // でコメント）
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
                    Debug.LogWarning($"[Bve2RouteParser] Line {i + 1} parse error: {ex.Message}\nLine: {line}");
                }
            }
        }

        /// <summary>
        /// 1行を解析
        /// </summary>
        private void ParseLine(string line, int lineNumber)
        {
            // BVE2は距離程が単独行の場合と、コマンドと同じ行の場合がある
            // 距離程のみの行
            if (float.TryParse(line, out float distance))
            {
                currentDistance = distance;
                return;
            }

            // コマンド解析
            string command = line.ToUpperInvariant();

            // 一般的なBVE2コマンド
            if (command.StartsWith("CURVE"))
            {
                ParseCurve(line);
            }
            else if (command.StartsWith("GRADIENT") || command.StartsWith("PITCH"))
            {
                ParseGradient(line);
            }
            else if (command.StartsWith("STATION"))
            {
                ParseStation(line);
            }
            else if (command.StartsWith("LIMIT"))
            {
                ParseLimit(line);
            }
            else if (command.StartsWith("RAIL"))
            {
                ParseRail(line);
            }
            else if (command.StartsWith("GROUND"))
            {
                ParseGround(line);
            }
            else if (command.StartsWith("REPEATER"))
            {
                // リピーターコマンド（構造物の繰り返し配置）
                ParseRepeater(line);
            }

            // 距離を自動的に進める（BVE2の仕様）
            // コマンド実行後に自動的に距離が進む場合がある
        }

        /// <summary>
        /// 曲線コマンド
        /// 形式: CURVE radius
        /// </summary>
        private void ParseCurve(string line)
        {
            string[] parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return;

            if (float.TryParse(parts[1], out float radius))
            {
                var geometry = new TrackGeometry
                {
                    StartPosition = currentDistance,
                    Radius = radius,
                    Gradient = 0
                };
                routeData.Geometries.Add(geometry);

                Debug.Log($"[Bve2RouteParser] Curve: R={radius}m at {currentDistance}m");
            }
        }

        /// <summary>
        /// 勾配コマンド
        /// 形式: GRADIENT value または PITCH value
        /// </summary>
        private void ParseGradient(string line)
        {
            string[] parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return;

            if (float.TryParse(parts[1], out float gradient))
            {
                var geometry = new TrackGeometry
                {
                    StartPosition = currentDistance,
                    Gradient = gradient,
                    Radius = 0
                };
                routeData.Geometries.Add(geometry);

                Debug.Log($"[Bve2RouteParser] Gradient: {gradient}‰ at {currentDistance}m");
            }
        }

        /// <summary>
        /// 駅コマンド
        /// 形式: STATION name
        /// </summary>
        private void ParseStation(string line)
        {
            // "STATION " 以降を駅名として取得
            int nameStart = line.IndexOf(' ');
            if (nameStart < 0) return;

            string stationName = line.Substring(nameStart + 1).Trim();

            var station = new StationData
            {
                Position = currentDistance,
                Name = stationName,
                ArrivalTime = -1,
                DepartureTime = -1,
                StopDuration = 15f,
                Doors = 1 // デフォルト右側
            };

            routeData.Stations.Add(station);
            Debug.Log($"[Bve2RouteParser] Station: {stationName} at {currentDistance}m");
        }

        /// <summary>
        /// 速度制限コマンド
        /// 形式: LIMIT speed
        /// </summary>
        private void ParseLimit(string line)
        {
            string[] parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return;

            if (float.TryParse(parts[1], out float limit))
            {
                Debug.Log($"[Bve2RouteParser] Speed limit: {limit}km/h at {currentDistance}m");
                // 速度制限データを保存（今後実装）
            }
        }

        /// <summary>
        /// レールコマンド
        /// 形式: RAIL index
        /// </summary>
        private void ParseRail(string line)
        {
            string[] parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return;

            if (int.TryParse(parts[1], out int railIndex))
            {
                // レール定義（副本線等）
                Debug.Log($"[Bve2RouteParser] Rail {railIndex} at {currentDistance}m");
            }
        }

        /// <summary>
        /// 地面コマンド
        /// 形式: GROUND index
        /// </summary>
        private void ParseGround(string line)
        {
            string[] parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return;

            if (int.TryParse(parts[1], out int groundIndex))
            {
                Debug.Log($"[Bve2RouteParser] Ground {groundIndex} at {currentDistance}m");
            }
        }

        /// <summary>
        /// リピーターコマンド
        /// 構造物を一定間隔で繰り返し配置
        /// </summary>
        private void ParseRepeater(string line)
        {
            // BVE2のRepeaterコマンド処理
            Debug.Log($"[Bve2RouteParser] Repeater at {currentDistance}m");
        }
    }
}
