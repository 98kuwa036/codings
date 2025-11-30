// ========================================
// 設定定数
// ========================================
const CONFIG = {
  SOURCE_ID: '13IsEoCgT9v0-J5TAaCAb_vZyyDMjzv_yXaI5khqvFnY',
  MASTER_SHEET_NAME: 'マスター',
  CACHE_KEY: 'item_master_editor_v1',
  CACHE_DURATION: 300 // 5分（秒）
};

// ========================================
// Webアプリケーション
// ========================================

/**
 * WebアプリのGETリクエストハンドラ
 */
function doGet(e) {
  return HtmlService.createTemplateFromFile('index')
      .evaluate()
      .setTitle('物品マスター編集ツール')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0');
}

// ========================================
// マスターデータ取得
// ========================================

/**
 * 物品マスターデータを取得
 * @returns {Array<Object>|Object} 物品リストまたはエラーオブジェクト
 */
function getItemMasterData() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.SOURCE_ID);
    const sheet = ss.getSheetByName(CONFIG.MASTER_SHEET_NAME);

    if (!sheet) {
      throw new Error(`シート「${CONFIG.MASTER_SHEET_NAME}」が見つかりません。`);
    }

    const lastRow = sheet.getLastRow();
    if (lastRow < 2) {
      return [];
    }

    // A列（行番号）、B列（物品名）、C列（最小単位）、D列（荷姿単位）、E列（荷姿入数）を取得
    const range = sheet.getRange(`A2:E${lastRow}`);
    const values = range.getValues();

    const items = values
      .map((row, index) => ({
        rowIndex: index + 2, // 実際のシート行番号（1始まりで、ヘッダー分+1）
        itemNo: row[0] || '',
        name: row[1] || '',
        minUnit: row[2] || '',
        packUnit: row[3] || '',
        packQuantity: row[4] || 0
      }))
      .filter(item => {
        // 物品名が空でなく、区切り線（---...---）でないものをフィルタ
        return item.name.trim() !== '' && !/---.*---/.test(item.name);
      });

    return items;
  } catch (e) {
    Logger.log(`getItemMasterData エラー: ${e.toString()}`);
    return { error: e.toString() };
  }
}

// ========================================
// マスターデータ更新
// ========================================

/**
 * 物品マスターデータを更新
 * @param {Array<Object>} items - 更新する物品データ [{rowIndex, minUnit, packUnit, packQuantity}, ...]
 * @returns {Object} {success: boolean, message?: string, error?: string}
 */
function updateItemMasterData(items) {
  try {
    if (!items || items.length === 0) {
      throw new Error('更新するデータがありません。');
    }

    const ss = SpreadsheetApp.openById(CONFIG.SOURCE_ID);
    const sheet = ss.getSheetByName(CONFIG.MASTER_SHEET_NAME);

    if (!sheet) {
      throw new Error(`シート「${CONFIG.MASTER_SHEET_NAME}」が見つかりません。`);
    }

    // 各アイテムを更新
    items.forEach(item => {
      if (item.rowIndex) {
        // C列（最小単位）、D列（荷姿単位）、E列（荷姿入数）を更新
        const range = sheet.getRange(`C${item.rowIndex}:E${item.rowIndex}`);
        range.setValues([[
          item.minUnit || '',
          item.packUnit || '',
          item.packQuantity || 0
        ]]);
      }
    });

    // キャッシュをクリア（inventry-dataのキャッシュもクリア）
    const cache = CacheService.getScriptCache();
    cache.remove(CONFIG.CACHE_KEY);
    cache.remove('master_items_v1'); // inventry-dataのキャッシュキー

    Logger.log(`${items.length}件のデータを更新しました。`);

    return {
      success: true,
      message: `${items.length}件のデータを更新しました。`
    };

  } catch (e) {
    Logger.log(`updateItemMasterData エラー: ${e.toString()}`);
    return { success: false, error: e.toString() };
  }
}

/**
 * 単一アイテムの更新
 * @param {Object} item - 更新する物品データ {rowIndex, minUnit, packUnit, packQuantity}
 * @returns {Object} {success: boolean, message?: string, error?: string}
 */
function updateSingleItem(item) {
  try {
    if (!item || !item.rowIndex) {
      throw new Error('更新するデータが不正です。');
    }

    const ss = SpreadsheetApp.openById(CONFIG.SOURCE_ID);
    const sheet = ss.getSheetByName(CONFIG.MASTER_SHEET_NAME);

    if (!sheet) {
      throw new Error(`シート「${CONFIG.MASTER_SHEET_NAME}」が見つかりません。`);
    }

    // C列（最小単位）、D列（荷姿単位）、E列（荷姿入数）を更新
    const range = sheet.getRange(`C${item.rowIndex}:E${item.rowIndex}`);
    range.setValues([[
      item.minUnit || '',
      item.packUnit || '',
      item.packQuantity || 0
    ]]);

    // キャッシュをクリア
    const cache = CacheService.getScriptCache();
    cache.remove(CONFIG.CACHE_KEY);
    cache.remove('master_items_v1');

    Logger.log(`行${item.rowIndex}のデータを更新しました。`);

    return {
      success: true,
      message: 'データを更新しました。'
    };

  } catch (e) {
    Logger.log(`updateSingleItem エラー: ${e.toString()}`);
    return { success: false, error: e.toString() };
  }
}
