// [ Utils.gs ]
// 汎用的な補助関数 (ログ書き込み、内部的なユーザー情報取得など)

function writeLog_(logMessagesArray, payload) {
  const logText = logMessagesArray.join('\n');
  if (payload.status === "Error") { console.error(logText); } else { console.log(logText); }
  try {
    // ★ 修正: CONFIG が null でも動作するようフォールバック
    // (★ 修正: 21:08 のグローバル変数（SS_ID_）を使用)
    const SPREADSHEET_ID = SS_ID_ || (CONFIG && CONFIG.SPREADSHEET_ID) || PropertiesService.getUserProperties().getProperty('SPREADSHEET_ID');
    const LOG_SHEET_NAME = LOG_SHEET_NAME_ || (CONFIG && CONFIG.SHEETS) ? CONFIG.SHEETS.LOG : '実行ログ';
    
    if (!SPREADSHEET_ID || !LOG_SHEET_NAME) { return; }
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const logSheet = ss.getSheetByName(LOG_SHEET_NAME);
    if (!logSheet) { return; }
    const timestamp = new Date();
    logSheet.insertRowBefore(2);
    
    // ★ 修正: 21:13 の4列フォーマット
    logSheet.getRange(2, 1, 1, 4).setValues([[
      timestamp, 
      payload.functionName || 'N/A', 
      payload.status || 'Info',
      payload.message || logMessagesArray[logMessagesArray.length - 1]
    ]]);

    const maxRows = 500;
    if (logSheet.getLastRow() > maxRows + 1) {
      logSheet.deleteRows(maxRows + 2, logSheet.getLastRow() - (maxRows + 1));
    }
  } catch (e) { console.error(`Failed to write log to sheet: ${e.message}`); }
}


/**
 * (内部) ユーザーIDから名前と役割を取得する
 * (Api_Client.gs -> getInitialData から呼び出される)
 */
function getUserInfo_(uid) {
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_(); // (Config.gs)
  }
  
  const sheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID).getSheetByName(CONFIG.SHEETS.USER);
  if (!sheet) {
    throw new Error(`シートが見つかりません: ${CONFIG.SHEETS.USER}`);
  }
  
  const targetRow = findRowById_(sheet, uid, 2); // B列(ID) を検索
  
  if (targetRow > -1) {
    const rowData = sheet.getRange(targetRow, 1, 1, 6).getValues()[0]; // A列(名前), F列(役割)
    const name = rowData[0];
    const roleRaw = rowData[5];
    const role = (roleRaw && String(roleRaw).trim() !== '') ? String(roleRaw).trim() : 'User';
    return { name: name, role: role, uid: uid };
  } else {
    throw new Error(`ユーザー [${uid}] がユーザー管理シートで見つかりません。`);
  }
}

/**
 * (内部) 管理者ページへの認証済みURLを生成する
 * (Api_Client.gs -> getInitialData から呼び出される)
 * ★ 修正: loginform/Code.gs の createSignedToken と同じ形式に統一
 */
function generateAdminPageUrl_(uid) {
  if (!CONFIG || !CONFIG.ADMIN_PAGE_URL) {
    loadConfig_(); // (Config.gs)
  }

  const ADMIN_PAGE_URL = CONFIG.ADMIN_PAGE_URL;

  if (!ADMIN_PAGE_URL || !TOKEN_SECRET_KEY) {
    Logger.log("generateAdminPageUrl: ADMIN_PAGE_URL または TOKEN_SECRET_KEY が未設定です。");
    return "#";
  }

  // ★ 修正: loginform/Code.gs の createSignedToken と同じ形式でトークン生成
  const now = Math.floor(Date.now() / 1000);
  const exp = now + 14400; // 4時間有効 (loginformと同じ)

  const payloadObj = { uid: uid, iat: now, exp: exp };

  // ★ payload のみを Base64 エンコード (header は含めない)
  const payloadBase64 = Utilities.base64EncodeWebSafe(JSON.stringify(payloadObj)).replace(/=+$/, '');

  // ★ 署名を生成 (末尾の = を削除)
  const signatureBytes = Utilities.computeHmacSha256Signature(payloadBase64, TOKEN_SECRET_KEY);
  const signatureBase64 = Utilities.base64EncodeWebSafe(signatureBytes).replace(/=+$/, '');

  // ★ Nonce を生成
  const nonceAdmin = Utilities.getUuid();

  // ★ URLを構築 (loginformと同じパラメータ形式)
  return `${ADMIN_PAGE_URL}?p=${encodeURIComponent(payloadBase64)}&s=${encodeURIComponent(signatureBase64)}&uid=${encodeURIComponent(uid)}&n_adm=${encodeURIComponent(nonceAdmin)}`;
}

/**
 * (内部) 補助関数: IDで行を検索
 */
function findRowById_(sheet, id, col) {
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
