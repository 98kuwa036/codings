// ========================================
// 設定定数
// ========================================
const CONFIG = {
  SOURCE_ID: '13IsEoCgT9v0-J5TAaCAb_vZyyDMjzv_yXaI5khqvFnY',
  DEST_ID: '1ZlkOr0n8Cc8ISwuyGUtZIoHoS2AutZ9uPmI9JcVxeaQ',
  MASTER_SHEET_NAME: 'マスター',
  CACHE_KEY: 'master_items_v2', // 荷姿単位対応のため v2 に変更
  CACHE_DURATION: 21600, // 6時間（秒）
  DATE_FORMAT: 'yyyy-MM-dd',
  CSV_MIME_TYPE: MimeType.CSV
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
      .setTitle('棚卸記録ツール')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0');
}

// ========================================
// マスターデータ取得
// ========================================

/**
 * マスターシートから物品リストを取得（キャッシュ対応）
 * @returns {Array<string>|Object} 物品リストまたはエラーオブジェクト
 */
function getMasterItems() {
  try {
    const cache = CacheService.getScriptCache();
    const cachedData = cache.get(CONFIG.CACHE_KEY);

    if (cachedData != null) {
      Logger.log('キャッシュからデータを取得しました。');
      return JSON.parse(cachedData);
    }

    const items = fetchItemsFromSheet();
    cache.put(CONFIG.CACHE_KEY, JSON.stringify(items), CONFIG.CACHE_DURATION);
    Logger.log(`取得したデータをキャッシュに保存しました。（キー: ${CONFIG.CACHE_KEY}）`);

    return items;
  } catch (e) {
    Logger.log(`getMasterItems エラー: ${e.toString()}`);
    return { error: e.toString() };
  }
}

/**
 * スプレッドシートから物品リストを取得（荷姿情報含む）
 * @returns {Array<Object>} 物品リスト [{name, minUnit, packUnit, packQuantity}, ...]
 */
function fetchItemsFromSheet() {
  Logger.log('スプレッドシートからデータを取得しています...');

  const ss = SpreadsheetApp.openById(CONFIG.SOURCE_ID);
  const sheet = ss.getSheetByName(CONFIG.MASTER_SHEET_NAME);

  if (!sheet) {
    throw new Error(`シート「${CONFIG.MASTER_SHEET_NAME}」が見つかりません。`);
  }

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return [];
  }

  // B列（物品名）、C列（最小単位）、D列（荷姿単位）、E列（荷姿入数）を取得
  const range = sheet.getRange(`B2:E${lastRow}`);
  const values = range.getValues();

  const items = values
    .filter(row => {
      const itemName = row[0];
      return typeof itemName === 'string' &&
             itemName.trim() !== '' &&
             !/---.*---/.test(itemName);
    })
    .map(row => ({
      name: row[0],
      minUnit: row[1] || '',        // C列: 最小単位
      packUnit: row[2] || '',       // D列: 荷姿単位
      packQuantity: row[3] || 0     // E列: 荷姿入数
    }));

  return items;
}

/**
 * キャッシュをクリア（手動実行用）
 */
function clearCache() {
  const cache = CacheService.getScriptCache();
  cache.remove(CONFIG.CACHE_KEY);
  Logger.log(`キャッシュ（キー: ${CONFIG.CACHE_KEY}）をクリアしました。`);
  return { success: true, message: 'キャッシュをクリアしました。' };
}

// ========================================
// 棚卸データ書き込み
// ========================================

/**
 * 棚卸データをスプレッドシートに書き込み、CSVエクスポート、クリアを実行
 * @param {Array<Object>} data - [{name, quantity, packUnits?, remainder?, packQuantity?}, ...]
 * @returns {Object} {success: boolean, message?: string, error?: string}
 */
function writeInventoryData(data) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG.DEST_ID);
    const sheet = ss.getSheetByName(CONFIG.MASTER_SHEET_NAME);

    if (!sheet) {
      throw new Error(`書き込み先のシート「${CONFIG.MASTER_SHEET_NAME}」が見つかりません。`);
    }

    const today = new Date();
    const timeZone = ss.getSpreadsheetTimeZone();
    const formattedDate = Utilities.formatDate(today, timeZone, CONFIG.DATE_FORMAT);

    // 1. スプレッドシートへの書き込み
    appendDataToSheet(sheet, data, formattedDate);

    // 2. CSV生成とエクスポート
    const csvFileName = exportToCSV(ss, sheet, today, timeZone, formattedDate);

    // 3. スプレッドシートクリア
    clearSheetData(sheet);

    return {
      success: true,
      message: `記録が完了し、CSVファイル(${csvFileName})として保存しました。\nスプレッドシートのデータはクリアされました。`
    };

  } catch (e) {
    Logger.log(`writeInventoryData エラー: ${e.toString()}`);
    return { success: false, error: e.toString() };
  }
}

/**
 * データをシートに追記
 * @param {Sheet} sheet - 対象シート
 * @param {Array<Object>} data - 書き込みデータ
 * @param {string} formattedDate - フォーマット済み日付
 */
function appendDataToSheet(sheet, data, formattedDate) {
  if (!data || data.length === 0) {
    Logger.log('書き込むデータがありません。');
    return;
  }

  const rows = data.map(item => {
    // 荷姿単位モードの場合は、最小単位に変換
    let totalQuantity = item.quantity;

    if (item.packUnits !== undefined && item.remainder !== undefined && item.packQuantity) {
      // 荷姿単位 × 荷姿入数 + 端数 = 最小単位での総数
      totalQuantity = (item.packUnits * item.packQuantity) + item.remainder;
    }

    return [
      formattedDate,
      item.name,
      totalQuantity
    ];
  });

  const startRow = sheet.getLastRow() + 1;
  sheet.getRange(startRow, 1, rows.length, 3).setValues(rows);
  Logger.log(`${rows.length}行のデータをスプレッドシートに追記しました。`);
}

/**
 * シートデータをCSVにエクスポート
 * @param {Spreadsheet} ss - スプレッドシート
 * @param {Sheet} sheet - 対象シート
 * @param {Date} today - 今日の日付
 * @param {string} timeZone - タイムゾーン
 * @param {string} formattedDate - フォーマット済み日付
 * @returns {string} CSVファイル名
 */
function exportToCSV(ss, sheet, today, timeZone, formattedDate) {
  const lastRow = sheet.getLastRow();

  if (lastRow === 0) {
    Logger.log('CSVとしてエクスポートするデータがシートにありません。');
    return null;
  }

  const range = sheet.getRange(`A1:C${lastRow}`);
  const values = range.getValues();

  // CSV生成（BOM付き UTF-8）
  const csvContent = generateCSVContent(values, timeZone);

  // ファイル保存
  const destinationFolder = getOrCreateYearFolder(ss, today.getFullYear());
  const fileName = `棚卸_${formattedDate}.csv`;

  destinationFolder.createFile(fileName, csvContent, CONFIG.CSV_MIME_TYPE);
  Logger.log(`CSVファイルを作成しました: ${fileName}（保存先: ${destinationFolder.getName()}）`);

  return fileName;
}

/**
 * CSV文字列を生成（BOM付き UTF-8）
 * @param {Array<Array>} values - シートの値
 * @param {string} timeZone - タイムゾーン
 * @returns {string} CSV文字列
 */
function generateCSVContent(values, timeZone) {
  const BOM = '\uFEFF'; // Excel文字化け対策

  const csvRows = values.map(row => {
    const processedRow = row.map((cell, index) => {
      // A列（日付列）の処理
      if (index === 0 && cell instanceof Date) {
        return Utilities.formatDate(cell, timeZone, CONFIG.DATE_FORMAT);
      }
      // クォートのエスケープ
      return `"${String(cell).replace(/"/g, '""')}"`;
    });
    return processedRow.join(',');
  });

  return BOM + csvRows.join('\n');
}

/**
 * 年度フォルダを取得または作成
 * @param {Spreadsheet} ss - スプレッドシート
 * @param {number} year - 年度
 * @returns {Folder} 年度フォルダ
 */
function getOrCreateYearFolder(ss, year) {
  const spreadsheetFile = DriveApp.getFileById(ss.getId());
  const parentFolder = spreadsheetFile.getParents().next();

  const yearFolders = parentFolder.getFoldersByName(year.toString());

  if (yearFolders.hasNext()) {
    return yearFolders.next();
  }

  return parentFolder.createFolder(year.toString());
}

/**
 * シートのデータをクリア
 * @param {Sheet} sheet - 対象シート
 */
function clearSheetData(sheet) {
  const lastRow = sheet.getLastRow();

  if (lastRow === 0) {
    Logger.log('クリアするデータがありません。');
    return;
  }

  const range = sheet.getRange(`A1:C${lastRow}`);
  range.clearContent();
  Logger.log(`シート（${sheet.getName()}）のA1:C${lastRow}のデータをクリアしました。`);
}
