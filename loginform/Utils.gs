// ===============================================================
// [ Utils.gs ]
// ユーティリティ関数
// ===============================================================

/**
 * IDが紐付いていない担当者名リストを取得する
 * @return {Array<string>} 担当者名の配列
 */
function getUnlinkedNames() {
  try {
    const allData = getAllUsersData_();
    if (!allData || allData.length === 0) return [];

    const names = [];
    for (const row of allData) {
      const name = row[COLS.NAME - 1]; // A列
      const id = row[COLS.ID - 1];     // B列

      if (name && !id) {
        names.push(name);
      }
    }
    return names;

  } catch (e) {
    console.error("getUnlinkedNames Error:", e.message);
    throw new Error("担当者リストの取得に失敗しました。");
  }
}

/**
 * IDで行番号を検索する
 * @param {Sheet} sheet - スプレッドシートのシート
 * @param {string} id - 検索するID
 * @return {number} 行番号 (見つからない場合は -1)
 */
function findRowById_(sheet, id) {
  if (!sheet || sheet.getLastRow() < 2) return -1;
  const data = sheet.getRange(2, COLS.ID, sheet.getLastRow() - 1, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    if (String(data[i][0]) === String(id)) return i + 2;
  }
  return -1;
}

/**
 * 担当者名で行番号を検索する
 * @param {Sheet} sheet - スプレッドシートのシート
 * @param {string} name - 検索する担当者名
 * @return {number} 行番号 (見つからない場合は -1)
 */
function findRowByName_(sheet, name) {
  if (!sheet || sheet.getLastRow() < 2) return -1;
  const data = sheet.getRange(2, COLS.NAME, sheet.getLastRow() - 1, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    if (data[i][0] == name) return i + 2;
  }
  return -1;
}

/**
 * ユーザー管理シートを取得する
 * @return {Sheet} シートオブジェクト
 */
function getUserSheet_() {
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_();
  }

  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const sheetName = CONFIG.SHEETS.USER || 'ユーザー管理';
  const sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    throw new Error(`シート「${sheetName}」が見つかりません。`);
  }

  return sheet;
}

/**
 * HTMLテンプレートにファイルをインクルードする
 * @param {string} filename - インクルードするファイル名
 * @return {string} ファイルの内容
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}
