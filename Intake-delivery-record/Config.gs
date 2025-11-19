// [ Config.gs ]
// このファイルは、すべての設定値を一元管理し、
// PropertiesService に保存するためのものです。

/**
 * ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
 * ★ 【重要】 この関数を一度だけ手動実行してください ★
 * ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
 *
 * 必要な設定値をすべて ScriptProperties に保存します。
 */
function SETUP_PROPERTIES() {
  
  // ▼▼▼▼▼▼▼▼▼▼▼▼【ここから設定】▼▼▼▼▼▼▼▼▼▼▼▼
  // ★ 修正: SYSTEM_NAME を追加
  // 1. スプレッドシートID (ブラウザのURLからコピー)
  const SYSTEM_NAME = "入出庫記録ツール"; // ★ アプリの正式名称
  const SPREADSHEET_ID = "1h3MNEOKWeOIzHvGcrPIF1rR9nBoP668xZO-C8pq_3As";

  // 2. 認証トークン (管理者ページと必ず同じ値にする)
  const TOKEN_SECRET_KEY = "yIm43SkRO#Oeq_Gg2smY8EVAx3FJ=TkQA?QiCdhWWn-#PU]nHyD-0jpcYn1KYwA[";

  // 3. 連携する「ログインページ」のデプロイURL (WebアプリURL)
  const LOGIN_APP_URL = "https://script.google.com/macros/s/AKfycbzdcXP_S-H7NwU3NDmtSs0exvStl6HL136Yn9CepSGzdYT0NbTwL1DwOM6H0z_5VVFd/exec";

  // 3. 連携する「管理者ページ」のデプロイURL (WebアプリURL)
  const ADMIN_PAGE_URL = "https://script.google.com/macros/s/AKfycbxizLvAXXaazROVyJ7Q4b6draSX6cuGCxnn6RQ7itvJU1an15on7-bP0SI0ymPtuNA/exec"; // ★要確認

  // 4. Webhookシークレット (管理者ページと必ず同じ値にする)
  const WEBHOOK_SECRET = "2qjuVWevemyd2UBjYYYdgh4rrdVJhbu2D";

  // 5. Cloud Vision APIキー (GCPから取得)
  const VISION_API_KEY = "AIzaSyAowbAd4wglz45lrZcHyBRFe1phpG2gibI"; // ★要確認

  // (5) ★ 修正: 2段階アップロード用のフォルダID
  const TEMP_DRIVE_FOLDER_ID = "1PEoJ7-yjuJMdZuRY_0Eu90DRZoWc_ENm"; // ★ 仮アップロード先のフォルダID
  const FINAL_DRIVE_FOLDER_ID = "17T_D7sHLv6V_XyBh9pzJkjGYLum5F0_L"; // ★ 最終保存先のフォルダID
  
  // (6) Nonceの有効期限 (秒)
  const NONCE_CACHE_EXPIRATION = 600; // 10分

  // (7) シート名定義
  const SHEETS_CONFIG = {
    MASTER: 'マスター',
    USER: 'ユーザー管理',
    HISTORY: '入出庫記録',
    PROCESSING_QUEUE: '一時作業',
    LOG: '実行ログ',
    UI_SETTINGS: 'UI_Settings'
  };
  
  // ▲▲▲▲▲▲▲▲▲▲▲▲【設定はここまで】▲▲▲▲▲▲▲▲▲▲▲▲

  try {
    const props = PropertiesService.getScriptProperties();
    
    props.setProperties({
      'SYSTEM_NAME': SYSTEM_NAME,
      'SPREADSHEET_ID': SPREADSHEET_ID,
      'TOKEN_SECRET_KEY': TOKEN_SECRET_KEY,
      'LOGIN_APP_URL': LOGIN_APP_URL, // ★ 修正: お手本(doGet)が要求するキー名
      'ADMIN_PAGE_URL': ADMIN_PAGE_URL,
      'WEBHOOK_SECRET': WEBHOOK_SECRET,
      'VISION_API_KEY': VISION_API_KEY,
      'TEMP_DRIVE_FOLDER_ID': TEMP_DRIVE_FOLDER_ID,
      'FINAL_DRIVE_FOLDER_ID': FINAL_DRIVE_FOLDER_ID,
      'NONCE_CACHE_EXPIRATION': NONCE_CACHE_EXPIRATION,
      'SHEETS_CONFIG_JSON': JSON.stringify(SHEETS_CONFIG)
    });
    
    Logger.log("✅ 正常に設定が保存されました。");
    Logger.log(`LOGIN_APP_URL: ${LOGIN_APP_URL}`);
    Logger.log(`SYSTEM_NAME: ${SYSTEM_NAME}`); // ★ 修正

  } catch (e) {
    Logger.log(`❌ 設定の保存に失敗しました: ${e.message}`);
    throw e;
  }
}

/**
 * (内部) すべての設定を Properties から読み込む
 */
function loadConfig_() {
  const props = PropertiesService.getScriptProperties();
  const configJson = props.getProperty('SHEETS_CONFIG_JSON');
  
  if (!configJson) {
    throw new Error("サーバー設定が不完全です（CONFIG）。管理者に連絡し、Config.gs の SETUP_PROPERTIES() 関数を実行するよう依頼してください。");
  }
  
  const SHEETS_CONFIG = JSON.parse(configJson);
  
  CONFIG = {
    SYSTEM_NAME: props.getProperty('SYSTEM_NAME'),
    SPREADSHEET_ID: props.getProperty('SPREADSHEET_ID'),
    LOGIN_APP_URL: props.getProperty('LOGIN_APP_URL'), // ★ 修正
    ADMIN_PAGE_URL: props.getProperty('ADMIN_PAGE_URL'),
    WEBHOOK_SECRET: props.getProperty('WEBHOOK_SECRET'),
    VISION_API_KEY: props.getProperty('VISION_API_KEY'),
    TEMP_DRIVE_FOLDER_ID: props.getProperty('TEMP_DRIVE_FOLDER_ID'),
    FINAL_DRIVE_FOLDER_ID: props.getProperty('FINAL_DRIVE_FOLDER_ID'),
    NONCE_CACHE_EXPIRATION: props.getProperty('NONCE_CACHE_EXPIRATION'),
    SHEETS: SHEETS_CONFIG,
    RECORD_APP_URL: ScriptApp.getService().getUrl() 
  };
  
  TOKEN_SECRET_KEY = props.getProperty('TOKEN_SECRET_KEY');
  LOG_SHEET_NAME_ = SHEETS_CONFIG.LOG;
  SS_ID_ = CONFIG.SPREADSHEET_ID;
}

// ★ CONFIG とログ用のグローバル変数（loadConfig_ で設定される）
let CONFIG = {};
let TOKEN_SECRET_KEY = ""; // ★ 21:13 の doGet が参照
let LOG_SHEET_NAME_ = '実行ログ';
let SS_ID_ = null;
