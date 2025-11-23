// ===============================================================
// [ Admin_Config.gs ]
// 設定管理 (グローバル変数, SETUP_PROPERTIES_ADMIN, loadAdminConfig_)
// ===============================================================

// グローバル変数
let ADMIN_CONFIG = {};
let SS_ID_ = null; // ログ書き込み用
let LOG_SHEET_NAME_ = '実行ログ';

/**
 * ★★★ 管理者ページ用の設定を実行する関数 ★★★
 * この関数を一度だけ手動実行してください。
 */
function SETUP_PROPERTIES_ADMIN() {// ★ SET_ADMIN_PROPERTIES からリネーム
  
  // ▼▼▼ この中の「...」部分を正しい値に書き換えてください ▼▼▼
  
  const SECRET_KEY = 'yIm43SkRO#Oeq_Gg2smY8EVAx3FJ=TkQA?QiCdhWWn-#PU]nHyD-0jpcYn1KYwA[';
  const LOGIN_URL  = 'https://script.google.com/macros/s/AKfycbzdcXP_S-H7NwU3NDmtSs0exvStl6HL136Yn9CepSGzdYT0NbTwL1DwOM6H0z_5VVFd/exec'; // ★ ログインページのURL
  const SS_ID = "1h3MNEOKWeOIzHvGcrPIF1rR9nBoP668xZO-C8pq_3As"; 
  const RECORD_APP_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwDPdFavwioHJpAgvUK_xUDVdC1O3t-QJ7eKPZwSOwnGxvbA5ayaOH5t6jVRDRTOZwjlQ/exec";  // ★ 記録ツールのURL
  const WEBHOOK_SECRET = "2qjuVWevemyd2UBjYYYdgh4rrdVJhbu2D";

  // ★ 修正: 記録ツールと設定を合わせる
  const ADMIN_PAGE_URL = ScriptApp.getService().getUrl(); // ★ この管理者ページのURL
  const NONCE_CACHE_EXPIRATION = 600; // 10分
  const SYSTEM_NAME = "管理者ダッシュボード"; // ★ AdminPage.html が参照

  const SHEETS_CONFIG = {
    MASTER: 'マスター',
    USER: 'ユーザー管理',
    HISTORY: '入出庫記録',
    PROCESSING_QUEUE: '一時作業',
    LOG: '実行ログ',
    UI_SETTINGS: 'UI_Settings'
  };
  
  // ▲▲▲ ここまで ▲▲▲

  try {
    const props = PropertiesService.getUserProperties();
    
    // ★ Record Tool と Admin Tool が共有するプロパティを設定
    props.setProperties({
      'TOKEN_SECRET_KEY': SECRET_KEY,
      'LOGIN_PAGE_URL': LOGIN_URL, 
      'ADMIN_PAGE_URL': ADMIN_PAGE_URL, 
      'SPREADSHEET_ID': SS_ID,
      'RECORD_APP_WEBHOOK_URL': RECORD_APP_WEBHOOK_URL,
      'WEBHOOK_SECRET': WEBHOOK_SECRET,
      'SHEETS_CONFIG_JSON': JSON.stringify(SHEETS_CONFIG),
      'SYSTEM_NAME': SYSTEM_NAME, 
      'NONCE_CACHE_EXPIRATION': NONCE_CACHE_EXPIRATION, 
      'VISION_API_KEY': props.getProperty('VISION_API_KEY') || '' // Record Tool側の設定を維持
    });
    
    console.log('--- 管理者ツールの UserProperties 設定完了 ---');
    console.log('LOGIN_PAGE_URL: ' + LOGIN_URL);
    console.log('SPREADSHEET_ID: ' + SS_ID);

  } catch (e) {
    console.error('管理者ツールのプロパティ設定に失敗しました: ' + e.message);
  }
}

/**
 * (内部) すべての設定を Properties から読み込み、
 * グローバル変数 ADMIN_CONFIG に格納する。
 * (doGet や他の関数から呼び出される)
 */
function loadAdminConfig_() {
  const props = PropertiesService.getUserProperties();
  const configJson = props.getProperty('SHEETS_CONFIG_JSON');
  
  if (!configJson) {
    throw new Error("設定が読み込めません（CONFIG）。Record Tool または Admin Tool の Config.gs で SETUP 関数を実行してください。");
  }
  
  const SHEETS_CONFIG = JSON.parse(configJson);
  
  // すべての設定をグローバル変数 ADMIN_CONFIG に格納
  ADMIN_CONFIG = {
    SYSTEM_NAME: props.getProperty('SYSTEM_NAME') || '管理者ダッシュボード',
    SPREADSHEET_ID: props.getProperty('SPREADSHEET_ID'),
    TOKEN_SECRET_KEY: props.getProperty('TOKEN_SECRET_KEY'),
    LOGIN_PAGE_URL: props.getProperty('LOGIN_PAGE_URL'),
    ADMIN_PAGE_URL: props.getProperty('ADMIN_PAGE_URL'),
    WEBHOOK_SECRET: props.getProperty('WEBHOOK_SECRET'),
    RECORD_APP_WEBHOOK_URL: props.getProperty('RECORD_APP_WEBHOOK_URL'),
    SHEETS: SHEETS_CONFIG,
    ROLE_SETTINGS: props.getProperty('roleSettings') // 権限設定
  };
  
  // ★ ログ書き込み用に、グローバル変数もセット
  LOG_SHEET_NAME_ = SHEETS_CONFIG.LOG;
  SS_ID_ = ADMIN_CONFIG.SPREADSHEET_ID;
  
  return ADMIN_CONFIG;
}
