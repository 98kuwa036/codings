using UnityEngine;
using System.Collections.Generic;

namespace OpenBveMobile.Core
{
    /// <summary>
    /// openBVEの基本データ型定義
    /// </summary>

    /// <summary>
    /// 距離程（メートル単位）
    /// </summary>
    public struct Distance
    {
        public float Meters;

        public Distance(float meters)
        {
            Meters = meters;
        }

        public static implicit operator float(Distance d) => d.Meters;
        public static implicit operator Distance(float f) => new Distance(f);
    }

    /// <summary>
    /// レール情報
    /// </summary>
    public class RailData
    {
        public int RailIndex;
        public Vector3 Position;
        public float Cant; // カント（傾斜）
    }

    /// <summary>
    /// 駅情報
    /// </summary>
    public class StationData
    {
        public string Name;
        public Distance Position;
        public float ArrivalTime;
        public float DepartureTime;
        public float StopDuration;
        public int PassAlarm; // 通過警告
        public int Doors; // ドア開閉（-1:左, 0:なし, 1:右）
        public bool ForcedRedSignal;
        public int System; // ATS/ATC種別
    }

    /// <summary>
    /// 構造物定義
    /// </summary>
    public class StructureData
    {
        public string Key; // Structure.Ground(0) の "0" 部分
        public string ModelPath;
        public GameObject LoadedModel;
    }

    /// <summary>
    /// 線形（曲線・勾配）データ
    /// </summary>
    public class TrackGeometry
    {
        public Distance StartPosition;
        public float Radius; // 曲線半径（0=直線）
        public float Gradient; // 勾配（パーミル）
    }

    /// <summary>
    /// 背景データ
    /// </summary>
    public class BackgroundData
    {
        public string ImagePath;
        public int Mode; // 0=繰り返し, 1=固定
        public Texture2D LoadedTexture;
    }

    /// <summary>
    /// オブジェクト配置情報
    /// </summary>
    public class PlacedObject
    {
        public Distance Position;
        public string StructureKey;
        public int RailIndex;
        public Vector3 Offset;
        public float RotationY;
        public float Tilt; // 傾き
        public GameObject Instance;
    }

    /// <summary>
    /// 信号機データ
    /// </summary>
    public class SignalData
    {
        public Distance Position;
        public int Aspects; // 現示数（2=2現示、3=3現示等）
        public List<string> ModelPaths;
    }

    /// <summary>
    /// 路線全体のデータ
    /// </summary>
    public class RouteData
    {
        public string RouteName;
        public string Comment;
        public string Image; // サムネイル
        public string TimeTableImage;

        // 路線設定
        public float Gauge = 1.435f; // 軌間（デフォルト1435mm）
        public float InitialElevation = 0f;

        // データコレクション
        public List<StationData> Stations = new List<StationData>();
        public List<TrackGeometry> Geometries = new List<TrackGeometry>();
        public Dictionary<string, StructureData> Structures = new Dictionary<string, StructureData>();
        public List<PlacedObject> Objects = new List<PlacedObject>();
        public List<SignalData> Signals = new List<SignalData>();
        public BackgroundData Background;

        // レール配置データ（レール番号 -> 位置リスト）
        public Dictionary<int, List<RailData>> Rails = new Dictionary<int, List<RailData>>();

        public RouteData()
        {
            // Rail 0（主レール）を初期化
            Rails[0] = new List<RailData>();
        }
    }

    /// <summary>
    /// CSVコマンドの種類
    /// </summary>
    public enum CommandType
    {
        Unknown,
        // Options
        Options_UnitOfLength,
        Options_UnitOfSpeed,
        // Route
        Route_Comment,
        Route_Image,
        Route_Gauge,
        Route_Elevation,
        // Station
        Station_Load,
        // Track
        Track_RailStart,
        Track_Rail,
        Track_RailEnd,
        Track_Ground,
        Track_Crack,
        Track_Adhesion,
        // Structure
        Structure_Ground,
        Structure_Rail,
        Structure_WallL,
        Structure_WallR,
        Structure_DikeL,
        Structure_DikeR,
        Structure_FormL,
        Structure_FormR,
        // Geometry
        Track_Pitch,
        Track_Curve,
        Track_Turn,
        // Objects
        Track_FreeObj,
        Track_Wall,
        Track_Dike,
        Track_Pole,
        // Background
        Track_Back,
        Track_Fog,
        // Signal
        Track_Signal,
        Track_Section,
        // Misc
        Track_Limit,
        Track_Stop,
        Track_Sta,
        Track_Form,
        Track_Beacon,
    }
}
