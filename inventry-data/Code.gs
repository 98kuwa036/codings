// スプレッドシートのIDを定数として定義
const SOURCE_ID = '13IsEoCgT9v0-J5TAaCAb_vZyyDMjzv_yXaI5khqvFnY'; // 読み取り元
const DEST_ID = '1ZlkOr0n8Cc8ISwuyGUtZIoHoS2AutZ9uPmI9JcVxeaQ';   // 書き込み先
const MASTER_SHEET_NAME = 'マスター';

// キャッシュキー
const CACHE_KEY = 'master_items_v1';

/**
 * Webアプリのメイン関数
 */
function doGet(e) {
  return HtmlService.createTemplateFromFile('index')
      .evaluate()
      .setTitle('棚卸記録ツール')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0');
}

/**
 * キャッシュをクリアするための手動実行関数
 */
function clearCache() {
  const cache = CacheService.getScriptCache();
  cache.remove(CACHE_KEY);
  console.log(`キャッシュ（キー: ${CACHE_KEY}）をクリアしました。`);
  Browser.msgBox('品目キャッシュをクリアしました。');
}

/**
 * 実際にスプレッドシートからデータを取得する内部関数
 */
function fetchItemsFromSheet() {
  console.log('スプレッドシートからデータを取得しています...');
  const ss = SpreadsheetApp.openById(SOURCE_ID);
  const sheet = ss.getSheetByName(MASTER_SHEET_NAME);
  if (!sheet) {
    throw new Error(`シート「${MASTER_SHEET_NAME}」が見つかりません。`);
  }
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return []; 
  }
  const range = sheet.getRange(`B2:B${lastRow}`);
  const values = range.getValues().flat();
  const items = values.filter(item => typeof item === 'string' && item.trim() !== '' && !/---.*---/.test(item));
  return items;
}

/**
 * マスターシートから物品リストを取得する（キャッシュ対応）
 */
function getMasterItems() {
  try {
    const cache = CacheService.getScriptCache();
    const cachedData = cache.get(CACHE_KEY);

    if (cachedData != null) {
      console.log('キャッシュからデータを取得しました。');
      return JSON.parse(cachedData);
    }

    const items = fetchItemsFromSheet();
    cache.put(CACHE_KEY, JSON.stringify(items), 21600); // 6時間キャッシュ
    console.log(`取得したデータをキャッシュに保存しました。（キー: ${CACHE_KEY}）`);

    return items;
  } catch (e) {
    console.error(e);
    return { "error": e.toString() };
  }
}


/**
 * ▼▼▼ 修正点 ▼▼▼
 * 棚卸データをスプレッドシートに書き込み、CSVとしてエクスポートし、
 * その後スプレッドシートのデータをクリアする一連の処理。
 *
 * @param {Array<Object>} data - Webアプリから送信されたデータ
 * @returns {Object} 成功または失敗を示すオブジェクト
 */
function writeInventoryData(data) {
  let ss;
  let sheet;
  
  try {
    // --- 1. スプレッドシートへの書き込み (追記) ---
    ss = SpreadsheetApp.openById(DEST_ID);
    sheet = ss.getSheetByName(MASTER_SHEET_NAME);
    if (!sheet) {
      throw new Error(`書き込み先のシート「${MASTER_SHEET_NAME}」が見つかりません。`);
    }
    
    const today = new Date(); // 共通の日付オブジェクトを使用
    const timeZone = ss.getSpreadsheetTimeZone();
    const formattedToday = Utilities.formatDate(today, timeZone, 'yyyy-MM-dd');
    
    const rows = data.map(item => [
      formattedToday, // A列: 日付 (yyyy-MM-dd文字列)
      item.name,      // B列: 物品名
      item.quantity   // C列: 実在庫数
    ]);
    
    if (rows.length > 0) {
      // データを最終行の下に追記
      sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, 3).setValues(rows);
      console.log(`${rows.length}行のデータをスプレッドシートに追記しました。`);
    } else {
      console.log('Webアプリから書き込むデータがありませんでした。');
    }

    // --- 2. CSVファイルに転記 (シートの全データを対象) ---
    const lastRow = sheet.getLastRow();
    if (lastRow === 0) {
      console.log('CSVとしてエクスポートするデータがシートにありません。');
      return { success: true, message: '棚卸データを記録しました（エクスポート対象なし）。' };
    }
    
    // A1からC列の最終行までの全データを取得
    const rangeToExport = sheet.getRange(`A1:C${lastRow}`);
    const values = rangeToExport.getValues();

    let csvContent = '';
    values.forEach((row, index) => {
      let newRow = [...row];
      // A列が万が一Dateオブジェクトだった場合に備えてフォーマット処理を残す
      if (newRow[0] instanceof Date) {
        newRow[0] = Utilities.formatDate(newRow[0], timeZone, 'yyyy-MM-dd');
      }
      // 各セルをダブルクォーテーションで囲む
      csvContent += newRow.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',') + '\n';
    });

    // --- 3. CSVファイル名を決定してルール通りに格納 ---
    const year = today.getFullYear().toString();
    const spreadsheetFile = DriveApp.getFileById(ss.getId());
    const parentFolder = spreadsheetFile.getParents().next();
    
    let destinationFolder;
    const yearFolders = parentFolder.getFoldersByName(year);
    
    if (yearFolders.hasNext()) {
      destinationFolder = yearFolders.next();
    } else {
      destinationFolder = parentFolder.createFolder(year);
    }
    
    const fileName = `棚卸_${formattedToday}.csv`;
    destinationFolder.createFile(fileName, csvContent, MimeType.CSV);
    console.log(`CSVファイルを作成しました: ${fileName}（保存先: ${destinationFolder.getName()}）`);

    // --- 4. スプレッドシートクリア ---
    // CSVに出力した範囲（A1:Cの最終行まで）のデータをクリアする
    rangeToExport.clearContent();
    console.log(`スプレッドシート（${MASTER_SHEET_NAME}）のA1:C${lastRow}のデータをクリアしました。`);
    
    return { 
      success: true, 
      message: `記録が完了し、CSVファイル(${fileName})として保存しました。\nスプレッドシートのデータはクリアされました。` 
    };

  } catch (e) {
    console.error(e);
    return { success: false, error: e.toString() };
  }
}
