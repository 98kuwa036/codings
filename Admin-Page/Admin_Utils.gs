// [ Admin_Utils.gs ]
// 共通関数 (ログ, Webhook, ヘルパー)
// (★ 22:07 の Code.gs から移管)

// ★ 修正: Config.gs との重複宣言をすべて削除
// let ADMIN_CONFIG.SPREADSHEET_ID_ = null;
// let LOG_SHEET_NAME_ = '実行ログ';
// ★ 修正ここまで

/**
 * [新設] 入出庫記録ツールに更新を通知する Webhook を送信する
 */
function notifyRecordApp_(updateType) {
  // ★ 修正: グローバル変数 WEBHOOK_SECRET を使用
  if (!RECORD_APP_WEBHOOK_URL || !RECORD_APP_WEBHOOK_URL.includes('/exec') || !WEBHOOK_SECRET) {
     Logger.log('Webhook URL または SECRET が設定されていません。送信をスキップしました。');
     return; 
  }
  
  try {
    const payload = {
      secret: WEBHOOK_SECRET,
      updateType: updateType
    };
    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    const response = UrlFetchApp.fetch(RECORD_APP_WEBHOOK_URL, options);
    Logger.log(`Webhook sent to Record App. Type: ${updateType}. Response: ${response.getResponseCode()}`);
  } catch (e) {
    Logger.log(`Webhook send error: ${e.message}`);
  }
}

/**
 * ログを「実行ログ」シートに書き込む (AdminPage 6列版)
 */
function writeLog_(logMessagesArray, payload) {
  const logText = logMessagesArray.join('\n');
  if (payload.status === "Error") { console.error(logText); } else { console.log(logText); }
  
  try {
    // ★ 修正: グローバル変数 ADMIN_CONFIG.SPREADSHEET_ID_ と LOG_SHEET_NAME_ を使用
    if (!ADMIN_CONFIG.SPREADSHEET_ID_ || !LOG_SHEET_NAME_) {
      // ログ書き込みの瞬間に CONFIG がない場合 (doGet前など)
      const props = PropertiesService.getUserProperties();
      ADMIN_CONFIG.SPREADSHEET_ID_ = props.getProperty('SPREADSHEET_ID');
      const sheetsConfigJson = props.getProperty('SHEETS_CONFIG_JSON');
      if (sheetsConfigJson) {
        LOG_SHEET_NAME_ = JSON.parse(sheetsConfigJson).LOG;
      }
      if (!ADMIN_CONFIG.SPREADSHEET_ID_ || !LOG_SHEET_NAME_) {
         console.error('Failed to write log: SPREADSHEET_ID or LOG_SHEET_NAME is not set.');
         return;
      }
    }

    const ss = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID_);
    const logSheet = ss.getSheetByName(LOG_SHEET_NAME_);
    if (!logSheet) { 
      console.error(`Failed to write log: Sheet "${LOG_SHEET_NAME_}" not found.`);
      return; 
    }
    
    const timestamp = new Date();
    logSheet.insertRowBefore(2);
    
    // --- ★ ログフォーマット (6列) ★ ---
    logSheet.getRange(2, 1, 1, 6).setValues([[
      timestamp,                                      // A: タイムスタンプ
      "admin",                                        // B: ログ種別
      payload.editorName || 'N/A',                    // C: 編集者名
      payload.functionName || 'N/A',                  // D: 関数名
      payload.status || 'Info',                       // E: ステータス
      payload.message || logMessagesArray[logMessagesArray.length - 1] // F: メッセージ
    ]]);
    
    const maxRows = 500;
    if (logSheet.getLastRow() > maxRows + 1) {
      logSheet.deleteRows(maxRows + 2, logSheet.getLastRow() - (maxRows + 1));
    }
  } catch (e) { 
    console.error(`Failed to write log to sheet: ${e.message}`); 
  }
}

/**
 * 補助関数: 指定された列(col)を検索して行番号を返す
 */
function findRowById(sheet, id, col) {
  if (!sheet || sheet.getLastRow() < 2) return -1;
  const searchId = String(id).trim().toLowerCase(); 
  const data = sheet.getRange(2, col, sheet.getLastRow() - 1, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    if (String(data[i][0]).trim().toLowerCase() === searchId) {
      return i + 2; 
    }
  }
  return -1;
}

/**
 * 補助関数: 指定された列(colNum)を基準に最終行を取得する
 */
function getLastRowByColumn(sheet, colNum) {
  try {
    const actualLastRow = sheet.getLastRow();
    if (actualLastRow === 0) return 1; 

    const columnData = sheet.getRange(1, colNum, actualLastRow, 1).getValues();
    let lastRowInCol = 1; 
    
    for (let i = actualLastRow - 1; i >= 0; i--) {
      if (columnData[i][0] !== "") {
        lastRowInCol = i + 1; 
        break; 
      }
    }
    return lastRowInCol;

  } catch (e) {
    Logger.log(`getLastRowByColumn Error (Col: ${colNum}): ${e.message}`);
    return 1; 
  }
}

/**
 * デバッグ用
 */
function LOG_ALL_PROPERTIES() {
  try {
    const props = PropertiesService.getUserProperties().getProperties();
    console.log("--- UserProperties に保存されている全キャッシュ ---");
    console.log(props);
    return props;
  } catch (e) {
    console.error("LOG_ALL_PROPERTIES Error: " + e.message);
    return { error: e.message };
  }
}
