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

    // A列（行番号）、B列（物品名）、C列（最小単位）、D列（荷姿単位）、E列（荷姿入数）、F列（発注点）を取得
    const range = sheet.getRange(`A2:F${lastRow}`);
    const values = range.getValues();

    const items = values
      .map((row, index) => ({
        rowIndex: index + 2, // 実際のシート行番号（1始まりで、ヘッダー分+1）
        itemNo: row[0] || '',
        name: row[1] || '',
        minUnit: row[2] || '',
        packUnit: row[3] || '',
        packQuantity: row[4] || 0,
        reorderPoint: row[5] || 0  // F列: 発注点
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
        // C列（最小単位）、D列（荷姿単位）、E列（荷姿入数）、F列（発注点）を更新
        const range = sheet.getRange(`C${item.rowIndex}:F${item.rowIndex}`);
        range.setValues([[
          item.minUnit || '',
          item.packUnit || '',
          item.packQuantity || 0,
          item.reorderPoint || 0
        ]]);
      }
    });

    // キャッシュをクリア（inventry-dataのキャッシュもクリア）
    const cache = CacheService.getScriptCache();
    cache.remove(CONFIG.CACHE_KEY);
    cache.remove('master_items_v2'); // inventry-dataのキャッシュキー（v2に更新）

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
 * @param {Object} item - 更新する物品データ {rowIndex, minUnit, packUnit, packQuantity, reorderPoint}
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

    // C列（最小単位）、D列（荷姿単位）、E列（荷姿入数）、F列（発注点）を更新
    const range = sheet.getRange(`C${item.rowIndex}:F${item.rowIndex}`);
    range.setValues([[
      item.minUnit || '',
      item.packUnit || '',
      item.packQuantity || 0,
      item.reorderPoint || 0
    ]]);

    // キャッシュをクリア
    const cache = CacheService.getScriptCache();
    cache.remove(CONFIG.CACHE_KEY);
    cache.remove('master_items_v2'); // inventry-dataのキャッシュキー（v2に更新）

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

// ========================================
// 発注点データコピー機能
// ========================================

/**
 * B列とH列が同一の値の場合、I列の値をF列にコピー
 * @returns {Object} {success: boolean, message?: string, copiedCount?: number, error?: string}
 */
function copyReorderPointFromHI() {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.SOURCE_ID);
    const sheet = ss.getSheetByName(CONFIG.MASTER_SHEET_NAME);

    if (!sheet) {
      throw new Error(`シート「${CONFIG.MASTER_SHEET_NAME}」が見つかりません。`);
    }

    const lastRow = sheet.getLastRow();

    if (lastRow < 2) {
      return {
        success: true,
        message: 'データが見つかりません。',
        copiedCount: 0
      };
    }

    // B、F、H、I列のデータを取得
    const dataRange = sheet.getRange(`A2:I${lastRow}`);
    const values = dataRange.getValues();

    let copiedCount = 0;
    const updates = [];

    // 2行目から順に処理
    for (let i = 0; i < values.length; i++) {
      const rowNum = i + 2; // 実際の行番号（1始まり、ヘッダー分+1）
      const itemNameB = values[i][1]; // B列（インデックス1）
      const currentReorderPoint = values[i][5]; // F列（インデックス5）
      const itemNameH = values[i][7]; // H列（インデックス7）
      const reorderPointI = values[i][8]; // I列（インデックス8）

      // B列とH列が同一の値かチェック（両方とも文字列として比較）
      if (itemNameB && itemNameH &&
          String(itemNameB).trim() === String(itemNameH).trim()) {

        // I列の値をF列にコピー（値がある場合）
        if (reorderPointI !== undefined && reorderPointI !== null && reorderPointI !== '') {
          updates.push({
            row: rowNum,
            value: reorderPointI
          });
          copiedCount++;

          Logger.log(`行${rowNum}: ${itemNameB} - 発注点 ${reorderPointI} をコピー`);
        }
      }
    }

    // 一括更新
    if (updates.length > 0) {
      updates.forEach(update => {
        sheet.getRange(`F${update.row}`).setValue(update.value);
      });

      // キャッシュをクリア
      const cache = CacheService.getScriptCache();
      cache.remove(CONFIG.CACHE_KEY);
      cache.remove('master_items_v2');
    }

    Logger.log(`発注点コピー完了: ${copiedCount}件`);

    return {
      success: true,
      message: `${copiedCount}件の発注点をコピーしました。`,
      copiedCount: copiedCount
    };

  } catch (e) {
    Logger.log(`copyReorderPointFromHI エラー: ${e.toString()}`);
    return { success: false, error: e.toString() };
  }
}
