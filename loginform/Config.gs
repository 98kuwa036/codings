// ===============================================================
// [ Config.gs ]
// 設定値の一元管理
// ===============================================================

/**
 * ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
 * ★ 【重要】 この関数を一度だけ手動実行してください ★
 * ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
 *
 * 必要な設定値をすべて ScriptProperties に保存します。
 */
function SETUP_PROPERTIES() {

  // ▼▼▼▼▼▼▼▼▼▼▼▼【ここから設定】▼▼▼▼▼▼▼▼▼▼▼▼

  // 1. システム名
  const SYSTEM_NAME = "入出庫登録ツール";

  // 2. スプレッドシートID (ブラウザのURLからコピー)
  const SPREADSHEET_ID = "1h3MNEOKWeOIzHvGcrPIF1rR9nBoP668xZO-C8pq_3As";

  // 3. 認証トークン秘密鍵 (他のプロジェクトと必ず同じ値にする)
  const TOKEN_SECRET_KEY = "yIm43SkRO#Oeq_Gg2smY8EVAx3FJ=TkQA?QiCdhWWn-#PU]nHyD-0jpcYn1KYwA[";

  // 4. 連携先URL
  const URLS = {
    // 記録ページ (データ入力フォーム)
    RECORD_APP: 'https://script.google.com/macros/s/AKfycbwDPdFavwioHJpAgvUK_xUDVdC1O3t-QJ7eKPZwSOwnGxvbA5ayaOH5t6jVRDRTOZwjlQ/exec',
    // 管理者ページ
    ADMIN_APP: 'https://script.google.com/macros/s/AKfycbxizLvAXXaazROVyJ7Q4b6draSX6cuGCxnn6RQ7itvJU1an15on7-bP0SI0ymPtuNA/exec'
  };

  // 5. シート名定義
  const SHEETS_CONFIG = {
    USER: 'ユーザー管理'
  };

  // 6. トークン有効期限 (秒)
  const TOKEN_EXPIRATION = 14400; // 4時間

  // 7. キャッシュ有効期限 (秒)
  const CACHE_EXPIRATION = 3600; // 1時間

  // ▲▲▲▲▲▲▲▲▲▲▲▲【設定はここまで】▲▲▲▲▲▲▲▲▲▲▲▲

  try {
    const props = PropertiesService.getScriptProperties();

    props.setProperties({
      'SYSTEM_NAME': SYSTEM_NAME,
      'SPREADSHEET_ID': SPREADSHEET_ID,
      'TOKEN_SECRET_KEY': TOKEN_SECRET_KEY,
      'RECORD_APP_URL': URLS.RECORD_APP,
      'ADMIN_APP_URL': URLS.ADMIN_APP,
      'TOKEN_EXPIRATION': String(TOKEN_EXPIRATION),
      'CACHE_EXPIRATION': String(CACHE_EXPIRATION),
      'SHEETS_CONFIG_JSON': JSON.stringify(SHEETS_CONFIG)
    });

    Logger.log("✅ 正常に設定が保存されました。");
    Logger.log(`SYSTEM_NAME: ${SYSTEM_NAME}`);
    Logger.log(`SPREADSHEET_ID: ${SPREADSHEET_ID}`);
    Logger.log(`RECORD_APP_URL: ${URLS.RECORD_APP}`);
    Logger.log(`ADMIN_APP_URL: ${URLS.ADMIN_APP}`);

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
    throw new Error("サーバー設定が不完全です。管理者に連絡し、Config.gs の SETUP_PROPERTIES() 関数を実行するよう依頼してください。");
  }

  const SHEETS_CONFIG = JSON.parse(configJson);

  CONFIG = {
    SYSTEM_NAME: props.getProperty('SYSTEM_NAME') || '入出庫登録ツール',
    SPREADSHEET_ID: props.getProperty('SPREADSHEET_ID'),
    RECORD_APP_URL: props.getProperty('RECORD_APP_URL'),
    ADMIN_APP_URL: props.getProperty('ADMIN_APP_URL'),
    TOKEN_EXPIRATION: parseInt(props.getProperty('TOKEN_EXPIRATION') || '14400', 10),
    CACHE_EXPIRATION: parseInt(props.getProperty('CACHE_EXPIRATION') || '3600', 10),
    SHEETS: SHEETS_CONFIG,
    LOGIN_APP_URL: ScriptApp.getService().getUrl()
  };

  TOKEN_SECRET_KEY = props.getProperty('TOKEN_SECRET_KEY');

  if (!CONFIG.SPREADSHEET_ID || !TOKEN_SECRET_KEY) {
    throw new Error("必須の設定値が不足しています。SETUP_PROPERTIES() を実行してください。");
  }
}

// ===============================================================
// グローバル変数（loadConfig_ で設定される）
// ===============================================================
let CONFIG = {};
let TOKEN_SECRET_KEY = "";
