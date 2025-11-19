// ===============================================================
// [ Admin_Data.gs ]
// データ操作CRUD (ユーザー管理, 物品マスター)
// ===============================================================

/**
 * (A, B, C, D) 指定されたシートのデータを取得
 */
function getSheetData(sheetName) {
  ensureConfigLoaded_(); // ★ 追加

  try {
    const ss = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID);
    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) {
      Logger.log(`getSheetData: シート "${sheetName}" が見つかりません。`);
      return JSON.stringify([['エラー', `シート "${sheetName}" が見つかりません。`]]);
    }
    let range;
    let lastRow;
    const SHEETS = ADMIN_CONFIG.SHEETS;
    
    switch (sheetName) {
      case SHEETS.HISTORY: // '入出庫記録'
        range = sheet.getRange(1, 1, Math.min(sheet.getLastRow(), 500), 6);
        break;
      case SHEETS.LOG: // '実行ログ'
        range = sheet.getRange(1, 1, Math.min(sheet.getLastRow(), 500), 6);
        break;
      case SHEETS.USER: // 'ユーザー管理'
        lastRow = getLastRowByColumn(sheet, 1); // A列
        range = sheet.getRange(1, 1, lastRow, 7); // G列 まで
        break;
      case SHEETS.MASTER: // 'マスター'
        lastRow = getLastRowByColumn(sheet, 1); // A列
        range = sheet.getRange(1, 1, lastRow, 4); // D列 まで
        break;
      case SHEETS.UI_SETTINGS: // 'UI_Settings'
        lastRow = getLastRowByColumn(sheet, 1); // A列
        range = sheet.getRange(1, 1, lastRow, 2);
        break;
      default:
        lastRow = getLastRowByColumn(sheet, 1);
        range = sheet.getRange(1, 1, lastRow, 7);
        break;
    }
    const values = range.getValues();
    return JSON.stringify(values);
  } catch (e) {
    Logger.log(`getSheetData (Catch Error): ${e.message}`);
    return JSON.stringify([['エラー', e.message]]);
  }
}

/**
 * (C) ユーザー作成
 */
function createUserData(userData, authInfo) {
  ensureConfigLoaded_(); // ★ 追加

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  try {
    const sheet = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID).getSheetByName(ADMIN_CONFIG.SHEETS.USER);
    sheet.appendRow([
      userData.name, userData.id, userData.pass, '', '', userData.role, userData.status
    ]);
    
    notifyRecordApp_('dropdown_data'); // (Admin_Utils.gs)
    
    const successMsg = "ユーザーを新規登録しました。";
    writeLog_([successMsg], {
      functionName: "createUserData",
      status: "Success",
      message: `ユーザー [${userData.name}] を作成`,
      editorName: editorName
    });
    
    return successMsg;
  } catch (e) { 
    writeLog_([`createUserData Error: ${e.message}`], { /* ... */ });
    return "エラー: " + e.message; 
  }
}

/**
 * (C) ユーザー更新
 */
function updateUserData(rowIndex, userData, authInfo) {
  ensureConfigLoaded_(); // ★ 追加

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  try {
    const sheet = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID).getSheetByName(ADMIN_CONFIG.SHEETS.USER);
    const range = sheet.getRange(rowIndex, 1, 1, 7);
    const values = range.getValues()[0];
    const password = userData.pass ? userData.pass : values[2]; 

    range.setValues([[
      userData.name, userData.id, password, values[3], values[4], userData.role, userData.status
    ]]);
    
    notifyRecordApp_('dropdown_data');
    
    const successMsg = "ユーザー情報を更新しました。";
    writeLog_([successMsg], {
      functionName: "updateUserData",
      status: "Success",
      message: `ユーザー [${userData.name}] (Row: ${rowIndex}) を更新`,
      editorName: editorName
    });
    
    return successMsg;
  } catch (e) { 
    writeLog_([`updateUserData Error: ${e.message}`], { /* ... */ });
    return "エラー: " + e.message; 
  }
}

/**
 * (C) ユーザー削除
 */
function deleteUserData(rowIndex, userData, authInfo) {
  ensureConfigLoaded_(); // ★ 追加

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  const targetName = (userData && userData.name) ? userData.name : `Row ${rowIndex}`;
  try {
    const sheet = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID).getSheetByName(ADMIN_CONFIG.SHEETS.USER);
    sheet.deleteRow(rowIndex);
    
    notifyRecordApp_('dropdown_data');
    
    const successMsg = "ユーザーを削除しました。";
    writeLog_([successMsg], {
      functionName: "deleteUserData",
      status: "Success",
      message: `ユーザー [${targetName}] (Row: ${rowIndex}) を削除`,
      editorName: editorName
    });
    
    return successMsg;
  } catch (e) { 
    writeLog_([`deleteUserData Error: ${e.message}`], { /* ... */ });
    return "エラー: " + e.message; 
  }
}

/**
 * (D) マスター作成
 */
function createMasterData(masterData, authInfo) {
  ensureConfigLoaded_(); // ★ 追加

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  try {
    const sheet = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID).getSheetByName(ADMIN_CONFIG.SHEETS.MASTER);
    sheet.appendRow([
      masterData.code, masterData.name, masterData.category, masterData.status
    ]);
    
    notifyRecordApp_('dropdown_data');
    
    const successMsg = "物品マスターを新規登録しました。";
    writeLog_([successMsg], {
      functionName: "createMasterData",
      status: "Success",
      message: `マスター [${masterData.name}] を作成`,
      editorName: editorName
    });

    return successMsg;
  } catch (e) { 
    writeLog_([`createMasterData Error: ${e.message}`], { /* ... */ });
    return "エラー: " + e.message; 
  }
}

/**
 * (D) マスター更新
 */
function updateMasterData(rowIndex, masterData, authInfo) {
  ensureConfigLoaded_(); // ★ 追加

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  try {
    const sheet = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID).getSheetByName(ADMIN_CONFIG.SHEETS.MASTER);
    const range = sheet.getRange(rowIndex, 1, 1, 4);
    range.setValues([[
      masterData.code, masterData.name, masterData.category, masterData.status
    ]]);
    
    notifyRecordApp_('dropdown_data');
    
    const successMsg = "物品マスターを更新しました。";
    writeLog_([successMsg], {
      functionName: "updateMasterData",
      status: "Success",
      message: `マスター [${masterData.name}] (Row: ${rowIndex}) を更新`,
      editorName: editorName
    });
    
    return successMsg;
  } catch (e) { 
    writeLog_([`updateMasterData Error: ${e.message}`], { /* ... */ });
    return "エラー: " + e.message; 
  }
}

/**
 * (D) マスター削除
 */
function deleteMasterData(rowIndex, masterData, authInfo) {
  ensureConfigLoaded_(); // ★ 追加

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  const targetName = (masterData && masterData.name) ? masterData.name : `Row ${rowIndex}`;
  try {
    const sheet = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID).getSheetByName(ADMIN_CONFIG.SHEETS.MASTER);
    sheet.deleteRow(rowIndex);
    
    notifyRecordApp_('dropdown_data');
    
    const successMsg = "物品マスターを削除しました。";
    writeLog_([successMsg], {
      functionName: "deleteMasterData",
      status: "Success",
      message: `マスター [${targetName}] (Row: ${rowIndex}) を削除`,
      editorName: editorName
    });
    
    return successMsg;
  } catch (e) { 
    writeLog_([`deleteMasterData Error: ${e.message}`], { /* ... */ });
    return "エラー: " + e.message; 
  }
}
