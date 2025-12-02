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
 * B列の各値をH列全体から検索し、一致した行のI列の値をF列にコピー
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

    // H列とI列のマップを作成（検索用）
    const hColumnMap = new Map(); // key: H列の値, value: I列の値

    for (let i = 0; i < values.length; i++) {
      const itemNameH = values[i][7]; // H列（インデックス7）
      const reorderPointI = values[i][8]; // I列（インデックス8）

      // H列に値があり、I列にも値がある場合のみマップに追加
      if (itemNameH && String(itemNameH).trim() !== '' &&
          reorderPointI !== undefined && reorderPointI !== null && reorderPointI !== '') {
        const key = String(itemNameH).trim();
        // 同じ物品名が複数ある場合は最初の値を使用
        if (!hColumnMap.has(key)) {
          hColumnMap.set(key, reorderPointI);
          Logger.log(`H列マップ追加: ${key} → ${reorderPointI}`);
        }
      }
    }

    let copiedCount = 0;
    const updates = [];

    // B列の各行を処理
    for (let i = 0; i < values.length; i++) {
      const rowNum = i + 2; // 実際の行番号（1始まり、ヘッダー分+1）
      const itemNameB = values[i][1]; // B列（インデックス1）

      // B列に値がある場合のみ処理
      if (itemNameB && String(itemNameB).trim() !== '') {
        const searchKey = String(itemNameB).trim();

        // H列マップから一致する値を検索
        if (hColumnMap.has(searchKey)) {
          const reorderPoint = hColumnMap.get(searchKey);

          updates.push({
            row: rowNum,
            value: reorderPoint,
            itemName: itemNameB
          });
          copiedCount++;

          Logger.log(`行${rowNum}: ${itemNameB} - 発注点 ${reorderPoint} をコピー（H列から検索）`);
        } else {
          Logger.log(`行${rowNum}: ${itemNameB} - H列に一致するデータなし`);
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

      Logger.log(`発注点コピー完了: ${copiedCount}件`);
    } else {
      Logger.log('コピーするデータがありませんでした。');
    }

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
