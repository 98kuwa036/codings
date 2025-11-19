// ===============================================================
// [ Cache.gs ]
// キャッシュ管理関連の関数
// ===============================================================

const CACHE_KEY_USER_DATA = 'userData';

/**
 * キャッシュサービス（スクリプトキャッシュ）を取得する
 * @return {Cache} キャッシュオブジェクト
 */
function getCache_() {
  return CacheService.getScriptCache();
}

/**
 * ユーザー情報のキャッシュを削除する
 * (doPost でユーザー情報を変更した後に呼び出す)
 */
function clearUserCache_() {
  const cache = getCache_();
  cache.remove(CACHE_KEY_USER_DATA);
  console.log('ユーザーキャッシュをクリアしました。');
}

/**
 * キャッシュまたはスプレッドシートから全ユーザーデータを取得する
 * @return {Array<Array<Object>>} スプレッドシートの全データ (ヘッダー除く)
 */
function getAllUsersData_() {
  // 設定を読み込み
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_();
  }

  const cache = getCache_();
  const cached = cache.get(CACHE_KEY_USER_DATA);

  // キャッシュがあればそれを返す
  if (cached != null) {
    console.log('キャッシュからユーザーデータを取得しました。');
    return JSON.parse(cached);
  }

  // スプレッドシートから取得
  console.log('スプレッドシートからユーザーデータを読み込んでいます...');

  const sheet = getUserSheet_();
  if (sheet.getLastRow() < 2) {
    return []; // データがない場合は空配列
  }

  // 1行目（ヘッダー）を除き、A列からE列まで取得
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 5).getValues();

  // キャッシュに保存
  const cacheExpiration = CONFIG.CACHE_EXPIRATION || 3600;
  cache.put(CACHE_KEY_USER_DATA, JSON.stringify(data), cacheExpiration);

  return data;
}
