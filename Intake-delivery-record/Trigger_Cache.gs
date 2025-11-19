// [ Trigger_Cache.gs ]
// キャッシュ管理 (Webhook とトリガー) 及び、キャッシュ読み込み関数

// ★ キャッシュのキーと有効期限をここで定義
const CACHE_KEY_PREFIX_UI_ = "cache_ui_settings";
const CACHE_KEY_PREFIX_DROPDOWN_ = "cache_dropdown_data";
const CACHE_EXPIRATION_ = 3600; // 1時間 (60 * 60)

/**
 * (内部) Webhook (doPost) から呼び出され、指定されたタイプのキャッシュを削除する
 */
function removeCacheByType_(updateType) {
  const cache = CacheService.getUserCache();
  let cacheKey = null;

  if (updateType === 'ui_settings') {
    cacheKey = CACHE_KEY_PREFIX_UI_;
    cache.remove(cacheKey);
  } else if (updateType === 'dropdown_data') {
    cacheKey = CACHE_KEY_PREFIX_DROPDOWN_;
    cache.remove(cacheKey);
  } else {
    throw new Error(`Unknown updateType: ${updateType}`);
  }
  return cacheKey;
}

/**
 * 【トリガー設定用】
 * スプレッドシートが編集されたときにキャッシュを自動削除（無効化）する
 */
function onMasterSheetEditTrigger(e) {
  const editedSheetName = e.source.getSheetName();
  
  // ★ 修正: CONFIG をロード
  if (!CONFIG || !CONFIG.SHEETS) {
    loadConfig_(); // (Config.gs)
  }

  const cache = CacheService.getUserCache();

  // 編集されたシートが「マスター」または「ユーザー管理」の場合
  if (editedSheetName === CONFIG.SHEETS.MASTER || editedSheetName === CONFIG.SHEETS.USER) {
    cache.remove(CACHE_KEY_PREFIX_DROPDOWN_);
    Logger.log(`Cache removed for ${CACHE_KEY_PREFIX_DROPDOWN_} due to sheet edit.`);
  }
  // 編集されたシートが「UI_Settings」の場合
  else if (editedSheetName === CONFIG.SHEETS.UI_SETTINGS) {
    cache.remove(CACHE_KEY_PREFIX_UI_);
    Logger.log(`Cache removed for ${CACHE_KEY_PREFIX_UI_} due to sheet edit.`);
  }
}


/**
 * (内部) UI設定をキャッシュまたはシートから取得
 * (Api_Client.gs -> getInitialData / checkForUiUpdates から呼び出される)
 */
function getUiSettingsData_() {
  const cache = CacheService.getUserCache();
  const cachedData = cache.get(CACHE_KEY_PREFIX_UI_);
  
  if (cachedData !== null) {
    return JSON.parse(cachedData);
  }

  // --- キャッシュがない場合、シートから読み込む ---
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_(); // (Config.gs)
  }
  
  const sheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID).getSheetByName(CONFIG.SHEETS.UI_SETTINGS);
  if (!sheet) throw new Error(`シートが見つかりません: ${CONFIG.SHEETS.UI_SETTINGS}`);

  const defaultSettings = { 
    ui_photo_upload_visible: true, ui_voucher_number_visible: true, ui_registrant_visible: true, 
    ui_date_visible: true, ui_toggle_mode_visible: true, ui_item_add_visible: true, 
    ui_item_list_visible: true 
  };
  
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) {
    cache.put(CACHE_KEY_PREFIX_UI_, JSON.stringify(defaultSettings), CACHE_EXPIRATION_);
    return defaultSettings;
  }
  
  const uiData = sheet.getRange(2, 1, lastRow - 1, 2).getValues();
  const loadedSettings = {};
  uiData.forEach(row => {
    const key = String(row[0]).trim();
    const valueString = String(row[1]).trim().toUpperCase();
    if (key && key in defaultSettings) { 
      loadedSettings[key] = (valueString !== 'FALSE'); 
    }
  });
  
  const settings = { ...defaultSettings, ...loadedSettings };
  cache.put(CACHE_KEY_PREFIX_UI_, JSON.stringify(settings), CACHE_EXPIRATION_);
  return settings;
}

/**
 * (内部) ドロップダウン（ユーザー/品名）をキャッシュまたはシートから取得
 * (Api_Client.gs -> getInitialData / checkForDropdownUpdates から呼び出される)
 */
function getDropdownData_() {
  const cache = CacheService.getUserCache();
  const cachedData = cache.get(CACHE_KEY_PREFIX_DROPDOWN_);

  if (cachedData !== null) {
    return JSON.parse(cachedData);
  }

  // --- キャッシュがない場合、シートから読み込む ---
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_(); // (Config.gs)
  }

  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const userSheet = ss.getSheetByName(CONFIG.SHEETS.USER);
  const masterSheet = ss.getSheetByName(CONFIG.SHEETS.MASTER);

  if (!userSheet || !masterSheet) throw new Error("ユーザーシートまたはマスターシートが見つかりません。");

  // 1. ユーザーリスト
  const userLastRow = userSheet.getLastRow();
  const dropdownNames = [];
  if (userLastRow > 1) {
    const userValues = userSheet.getRange(2, 1, userLastRow - 1, 1).getValues(); // A列(名前)のみ
    userValues.filter(r => r[0] && String(r[0]).trim() !== '').forEach(r => dropdownNames.push(r[0]));
  }
  
  // 2. 品名リスト
  const masterLastRow = masterSheet.getLastRow();
  const dropdownProducts = [];
  if (masterLastRow > 1) {
    const productValues = masterSheet.getRange(2, 2, masterLastRow - 1, 1).getValues(); // B列(品名)のみ
    productValues.filter(r => r[0] && String(r[0]).trim() !== '').forEach(r => dropdownProducts.push(r[0]));
  }

  const data = {
    users: dropdownNames,
    items: dropdownProducts
  };
  
  cache.put(CACHE_KEY_PREFIX_DROPDOWN_, JSON.stringify(data), CACHE_EXPIRATION_);
  return data;
}
