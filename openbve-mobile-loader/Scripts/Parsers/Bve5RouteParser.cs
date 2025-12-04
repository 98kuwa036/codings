using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Xml;
using OpenBveMobile.Core;

namespace OpenBveMobile.Parsers
{
    /// <summary>
    /// BVE5形式の路線ファイルパーサー
    /// BVE Trainsim 5.x の XML 形式に対応
    /// </summary>
    public class Bve5RouteParser
    {
        private RouteData routeData;
        private string routeDirectory;

        /// <summary>
        /// BVE5路線ファイルを解析（XML形式）
        /// </summary>
        public RouteData Parse(string filePath)
        {
            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"BVE5 route file not found: {filePath}");
            }

            routeData = new RouteData();
            routeDirectory = Path.GetDirectoryName(filePath);

            Debug.Log($"[Bve5RouteParser] Starting parse: {filePath}");

            try
            {
                XmlDocument xmlDoc = new XmlDocument();
                xmlDoc.Load(filePath);

                // ルート要素を取得
                XmlElement root = xmlDoc.DocumentElement;

                if (root == null || root.Name != "Route")
                {
                    throw new Exception("Invalid BVE5 route file: missing <Route> root element");
                }

                // 路線情報を解析
                ParseRouteInfo(root);

                // 構造物定義を解析
                ParseStructures(root);

                // 線形データを解析
                ParseTracks(root);

                // 駅を解析
                ParseStations(root);

                Debug.Log($"[Bve5RouteParser] Parse completed. Stations: {routeData.Stations.Count}");
                return routeData;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[Bve5RouteParser] Parse error: {ex.Message}\n{ex.StackTrace}");
                throw;
            }
        }

        /// <summary>
        /// 路線情報を解析
        /// </summary>
        private void ParseRouteInfo(XmlElement root)
        {
            XmlNode infoNode = root.SelectSingleNode("Info");
            if (infoNode != null)
            {
                routeData.RouteName = GetNodeValue(infoNode, "Name", "Unnamed Route");
                routeData.Comment = GetNodeValue(infoNode, "Comment", "");
                routeData.Image = GetNodeValue(infoNode, "Image", "");

                string gaugeStr = GetNodeValue(infoNode, "Gauge", "1.435");
                if (float.TryParse(gaugeStr, out float gauge))
                {
                    routeData.Gauge = gauge;
                }

                Debug.Log($"[Bve5RouteParser] Route: {routeData.RouteName}, Gauge: {routeData.Gauge}m");
            }
        }

        /// <summary>
        /// 構造物定義を解析
        /// </summary>
        private void ParseStructures(XmlElement root)
        {
            XmlNode structuresNode = root.SelectSingleNode("Structures");
            if (structuresNode == null) return;

            foreach (XmlNode structureNode in structuresNode.ChildNodes)
            {
                if (structureNode.NodeType != XmlNodeType.Element)
                    continue;

                string category = structureNode.Name; // Ground, Rail, etc.
                string key = GetAttributeValue(structureNode, "Key", "0");
                string modelPath = GetAttributeValue(structureNode, "FilePath", "");

                if (!string.IsNullOrEmpty(modelPath))
                {
                    string fullKey = $"{category.ToLower()}_{key}";
                    modelPath = Path.Combine(routeDirectory, modelPath);

                    var structure = new StructureData
                    {
                        Key = fullKey,
                        ModelPath = modelPath
                    };

                    routeData.Structures[fullKey] = structure;
                    Debug.Log($"[Bve5RouteParser] Structure: {fullKey} -> {modelPath}");
                }
            }
        }

        /// <summary>
        /// 線形データを解析
        /// </summary>
        private void ParseTracks(XmlElement root)
        {
            XmlNode tracksNode = root.SelectSingleNode("Tracks");
            if (tracksNode == null) return;

            foreach (XmlNode trackNode in tracksNode.ChildNodes)
            {
                if (trackNode.NodeType != XmlNodeType.Element)
                    continue;

                string distanceStr = GetAttributeValue(trackNode, "Distance", "0");
                if (!float.TryParse(distanceStr, out float distance))
                    continue;

                string type = trackNode.Name;

                switch (type)
                {
                    case "Curve":
                        ParseCurve(trackNode, distance);
                        break;

                    case "Gradient":
                    case "Pitch":
                        ParseGradient(trackNode, distance);
                        break;

                    case "Ground":
                        ParseGroundPlacement(trackNode, distance);
                        break;

                    case "FreeObj":
                        ParseFreeObject(trackNode, distance);
                        break;
                }
            }
        }

        /// <summary>
        /// 曲線を解析
        /// </summary>
        private void ParseCurve(XmlNode node, float distance)
        {
            string radiusStr = GetAttributeValue(node, "Radius", "0");
            string cantStr = GetAttributeValue(node, "Cant", "0");

            if (float.TryParse(radiusStr, out float radius))
            {
                var geometry = new TrackGeometry
                {
                    StartPosition = distance,
                    Radius = radius,
                    Gradient = 0
                };
                routeData.Geometries.Add(geometry);
            }
        }

        /// <summary>
        /// 勾配を解析
        /// </summary>
        private void ParseGradient(XmlNode node, float distance)
        {
            string gradientStr = GetAttributeValue(node, "Value", "0");

            if (float.TryParse(gradientStr, out float gradient))
            {
                var geometry = new TrackGeometry
                {
                    StartPosition = distance,
                    Gradient = gradient,
                    Radius = 0
                };
                routeData.Geometries.Add(geometry);
            }
        }

        /// <summary>
        /// 地面オブジェクト配置を解析
        /// </summary>
        private void ParseGroundPlacement(XmlNode node, float distance)
        {
            string keyStr = GetAttributeValue(node, "Key", "0");
            string structureKey = $"ground_{keyStr}";

            var obj = new PlacedObject
            {
                Position = distance,
                StructureKey = structureKey,
                RailIndex = 0
            };

            routeData.Objects.Add(obj);
        }

        /// <summary>
        /// 自由配置オブジェクトを解析
        /// </summary>
        private void ParseFreeObject(XmlNode node, float distance)
        {
            string railStr = GetAttributeValue(node, "Rail", "0");
            string key = GetAttributeValue(node, "Key", "");
            string xStr = GetAttributeValue(node, "X", "0");
            string yStr = GetAttributeValue(node, "Y", "0");
            string yawStr = GetAttributeValue(node, "Yaw", "0");

            if (int.TryParse(railStr, out int railIndex) &&
                float.TryParse(xStr, out float x) &&
                float.TryParse(yStr, out float y) &&
                float.TryParse(yawStr, out float yaw))
            {
                var obj = new PlacedObject
                {
                    Position = distance,
                    StructureKey = key,
                    RailIndex = railIndex,
                    Offset = new Vector3(x, y, 0),
                    RotationY = yaw
                };

                routeData.Objects.Add(obj);
            }
        }

        /// <summary>
        /// 駅を解析
        /// </summary>
        private void ParseStations(XmlElement root)
        {
            XmlNode stationsNode = root.SelectSingleNode("Stations");
            if (stationsNode == null) return;

            foreach (XmlNode stationNode in stationsNode.ChildNodes)
            {
                if (stationNode.NodeType != XmlNodeType.Element)
                    continue;

                string distanceStr = GetAttributeValue(stationNode, "Distance", "0");
                if (!float.TryParse(distanceStr, out float distance))
                    continue;

                string name = GetAttributeValue(stationNode, "Name", "Unnamed Station");
                string arrivalStr = GetAttributeValue(stationNode, "ArrivalTime", "");
                string departureStr = GetAttributeValue(stationNode, "DepartureTime", "");
                string doorsStr = GetAttributeValue(stationNode, "Doors", "1");

                var station = new StationData
                {
                    Position = distance,
                    Name = name,
                    ArrivalTime = ParseBve5Time(arrivalStr),
                    DepartureTime = ParseBve5Time(departureStr),
                    StopDuration = 15f,
                    Doors = int.TryParse(doorsStr, out int doors) ? doors : 1
                };

                routeData.Stations.Add(station);
                Debug.Log($"[Bve5RouteParser] Station: {name} at {distance}m");
            }
        }

        // ヘルパーメソッド

        private string GetNodeValue(XmlNode parent, string nodeName, string defaultValue = "")
        {
            XmlNode node = parent.SelectSingleNode(nodeName);
            return node?.InnerText ?? defaultValue;
        }

        private string GetAttributeValue(XmlNode node, string attributeName, string defaultValue = "")
        {
            XmlAttribute attr = node.Attributes?[attributeName];
            return attr?.Value ?? defaultValue;
        }

        private float ParseBve5Time(string timeString)
        {
            if (string.IsNullOrEmpty(timeString))
                return -1;

            // HH:MM:SS形式
            string[] parts = timeString.Split(':');
            if (parts.Length >= 2)
            {
                int hours = int.Parse(parts[0]);
                int minutes = int.Parse(parts[1]);
                int seconds = parts.Length > 2 ? int.Parse(parts[2]) : 0;
                return hours * 3600 + minutes * 60 + seconds;
            }

            return -1;
        }
    }
}
