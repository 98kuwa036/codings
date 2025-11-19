// ===============================================================
// --- ★ 定数：URLS 定義をファイルの最上部に配置 ★ ---
// ===============================================================
const URLS = {
  RECORD_APP: 'https://script.google.com/macros/s/AKfycbwDPdFavwioHJpAgvUK_xUDVdC1O3t-QJ7eKPZwSOwnGxvbA5ayaOH5t6jVRDRTOZwjlQ/exec', 
  
  // 記録ページ (デフォルト)
  ADMIN_APP: 'https://script.google.com/macros/s/AKfycbxizLvAXXaazROVyJ7Q4b6draSX6cuGCxnn6RQ7itvJU1an15on7-bP0SI0ymPtuNA/exec' // 管理者ページ
};

// ===============================================================
// --- 秘密鍵と各種ID設定用関数 (初回に手動実行) ---
// ===============================================================
function SET_SECRETS() {
  const props = PropertiesService.getScriptProperties();
  props.setProperties({
    'TOKEN_SECRET_KEY': 'yIm43SkRO#Oeq_Gg2smY8EVAx3FJ=TkQA?QiCdhWWn-#PU]nHyD-0jpcYn1KYwA[',
    'SPREADSHEET_ID': '1h3MNEOKWeOIzHvGcrPIF1rR9nBoP668xZO-C8pq_3As',
    'RECORD_APP_URL': URLS.RECORD_APP,
    'ADMIN_APP_URL': URLS.ADMIN_APP
  });
  console.log('ログインツールの秘密プロパティを設定しました。');
}

const SCRIPT_PROPS = PropertiesService.getScriptProperties();

const SPREADSHEET_ID = SCRIPT_PROPS.getProperty('SPREADSHEET_ID');

// ★ TOKEN_SECRET_KEY をここで定数化する
const TOKEN_SECRET_KEY = SCRIPT_PROPS.getProperty('TOKEN_SECRET_KEY');

const CONFIG = {
  RECORD_APP_URL: SCRIPT_PROPS.getProperty(
    'RECORD_APP_URL') || URLS.RECORD_APP,
  ADMIN_APP_URL: SCRIPT_PROPS.getProperty(
    'ADMIN_APP_URL') || URLS.ADMIN_APP
};

const USER_INFO = 'ユーザー管理';
// ★ 列の定義をまとめて管理 (保守性向上のため)
const COLS = {
  NAME: 1, // A列
  ID: 2,   // B列
  HASH: 3, // C列
  // (D列は未使用)
  SALT: 5  // E列
};

// ===============================================================
// --- ★ キャッシュ関連の関数 (新規追加) ★ ---
// ===============================================================

/**
 * キャッシュサービス（スクリプトキャッシュ）を取得します。
 */
function getCache() {
  return CacheService.getScriptCache();
}

/**
 * ユーザー情報のキャッシュを削除します。
 * (doPost でユーザー情報を変更した後に必ず呼び出します)
 */
function clearUserCache() {
  const cache = getCache();
  cache.remove('userData');
  console.log('ユーザーキャッシュをクリアしました。');
}

/**
 * キャッシュまたはスプレッドシートから全ユーザーデータを取得します。
 * @return {Array<Array<Object>>} スプレッドシートの全データ (ヘッダー除く)
 */
function getAllUsersData() {
  const cache = getCache();
  const CACHE_KEY = 'userData';
  const cached = cache.get(CACHE_KEY);

  if (cached != null) {
    console.log('キャッシュからユーザーデータを取得しました。');
    return JSON.parse(cached);
  }

  console.log('スプレッドシートからユーザーデータを読み込んでいます...');
  if (!SPREADSHEET_ID) throw new Error('スプレッドシートIDが設定されていません。');
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(USER_INFO);
  if (!sheet || sheet.getLastRow() < 2) {
    return []; // データがない場合は空配列を返す
  }

  // 1行目（ヘッダー）を除き、A列からE列まですべて取得
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 5).getValues(); 

  // キャッシュに保存 (例: 1時間 = 3600秒)
  cache.put(CACHE_KEY, JSON.stringify(data), 3600); 

  return data;
}

// --- メイン処理 ---
function doGet(e) {
  if (!SPREADSHEET_ID || !CONFIG.RECORD_APP_URL || !CONFIG.ADMIN_APP_URL) {
    return HtmlService.createHtmlOutput(
      'スクリプトの初期設定が必要です。エディタから SET_SECRETS 関数を実行してください。');
  }

  // リダイレクトフラグをホワイトリスト化
  const rawFlag = (e.parameter && e.parameter.redirect) ? e.parameter.redirect.toLowerCase() : '';
  const redirectFlag = (rawFlag === 'admin') ? 'admin' : 'record';
  console.log('doGet：受け取った rawFlag =', rawFlag, ' → 使用する redirectFlag =', redirectFlag);

  const template = HtmlService.createTemplateFromFile('index'); // HTMLファイル名

  template.redirectFlag = redirectFlag;
  template.scriptUrl = ScriptApp.getService().getUrl();

  return template.evaluate().addMetaTag('viewport',
    'width=device-width, initial-scale=1.0').setTitle('ログイン');
}

// --- フォーム処理 (利用者情報編集用) (★ 修正あり) ---
function doPost(e) {
  let response;
  try {
    if (!SPREADSHEET_ID) throw new Error('スプレッドシートIDが設定されていません。');
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = ss.getSheetByName(USER_INFO);
    if (!sheet) throw new Error(`シート「${USER_INFO}」が見つかりません。`);
    const action = e.parameter.action;
    const targetId = e.parameter.id;
    const password = e.parameter.password;
    const targetName = e.parameter.name;
    const idRow = findRowById(sheet, targetId); // doPost内では従来通りDBアクセスでOK

    if (action === '登録') {
      if (idRow > -1) throw new Error(`ID「${targetId}」は既に使用されています。`);
      if (!targetName) throw new Error('担当者名が選択されていません。');
      const newSalt = Utilities.getUuid();
      const newHash = hashPassword(password, newSalt);
      const nameRow = findRowByName(sheet, targetName);
      if (nameRow > -1) {
        sheet.getRange(nameRow, COLS.ID).setValue(targetId);
        sheet.getRange(nameRow, COLS.HASH).setValue(newHash);
        sheet.getRange(nameRow, COLS.SALT).setValue(newSalt);
        response = {
          status: 'success',
          message: `「${targetName}」に新しいID「${targetId}」を紐付けました。`
        };
      } else {
        throw new Error(`選択された担当者「${targetName}」が見つかりませんでした。`);
      }
    } else if (action === '削除') {
      if (idRow > -1) {
        sheet.deleteRow(idRow);
        response = {
          status: 'success',
          message: `ID「${targetId}」を削除しました。`
        };
      } else {
        throw new Error(`削除対象のID「${targetId}」が見つかりませんでした。`);
      }
    } else if (action === 'パスワード変更') {
      if (idRow > -1) {
        const newSalt = Utilities.getUuid();
        const newHash = hashPassword(password, newSalt);
        sheet.getRange(idRow, COLS.HASH).setValue(newHash);
        sheet.getRange(idRow, COLS.SALT).setValue(newSalt);
        response = {
          status: 'success',
          message: `ID「${targetId}」のパスワードを更新しました。`
        };
      } else {
        throw new Error(`パスワード変更対象のID「${targetId}」が見つかりませんでした。`);
      }
    } else {
      throw new Error('無効な操作です。');
    }

    // ★★★★★ 重要 ★★★★★
    // データが変更されたので、必ずキャッシュをクリアする
    clearUserCache(); 
    // ★★★★★★★★★★★★★

  } catch (err) {
    response = {
      status: 'error',
      message: err.message
    };
  }
  return ContentService.createTextOutput(JSON.stringify(response)).setMimeType(
    ContentService.MimeType.JSON);
}


// --- 補助関数 ---

/**
 * キャッシュ（またはシート）から、IDが紐付いていない担当者名リストを取得します。
 * (★ 修正)
 */
function getUnlinkedNames() {
  try {
    const allData = getAllUsersData(); // ★ キャッシュ対応の関数を呼ぶ
    if (!allData || allData.length === 0) return [];

    const names = [];
    for (const row of allData) {
      // row[COLS.NAME - 1] は A列(名前)
      // row[COLS.ID - 1] は B列(ID)
      const name = row[COLS.NAME - 1]; 
      const id = row[COLS.ID - 1];   

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

function findRowById(sheet, id) {
  if (!sheet || sheet.getLastRow() < 2) return -1;
  const data = sheet.getRange(2, COLS.ID, sheet.getLastRow() - 1, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    if (String(data[i][0]) === String(id)) return i + 2; 
  }
  return -1;
}

function findRowByName(sheet, name) {
  if (!sheet || sheet.getLastRow() < 2) return -1;
  const data = sheet.getRange(2, COLS.NAME, sheet.getLastRow() - 1, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    if (data[i][0] == name) return i + 2; 
  }
  return -1;
}

function hashPassword(password, salt) {
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,
    password + salt, Utilities.Charset.UTF_8);
  return digest.map(byte => ('0' + (byte & 0xFF).toString(16)).slice(-2)).join('');
}

// --- ★ 修正: トークン生成関数 (署名付きトークン方式) ★ ---
/**
 * 署名付きトークンと両方のNonceを生成する (保存はしない)
 * @param {string} userId - ユーザーID
 * @return {object} トークン情報 {payload, signature, userId, n_rec, n_adm, exp}
 */
function createSignedToken(userId) {
  // const TOKEN_SECRET_KEY = ... (← 上記の行を削除)

  // グローバル定数を直接参照する
  if (!TOKEN_SECRET_KEY) { 
     console.error('createSignedToken Error: TOKEN_SECRET_KEY is not set in ScriptProperties.');
     throw new Error('TOKEN_SECRET_KEYが設定されていません。SET_SECRETSを実行してください。'); 
  }

  const now = Math.floor(Date.now() / 1000);
  const exp = now + 14400; // 4時間有効

  const payloadObj = { uid: userId, iat: now, exp: exp };
  const payloadBase64 = Utilities.base64EncodeWebSafe(JSON.stringify(payloadObj)).replace(/=+$/, ''); 

  console.log(`[createSignedToken] Payload Base64 for Signing: "${payloadBase64}"`);

  const signatureBytes = Utilities.computeHmacSha256Signature(payloadBase64, TOKEN_SECRET_KEY);
  let signatureBase64 = Utilities.base64EncodeWebSafe(signatureBytes);
  signatureBase64 = signatureBase64.replace(/=+$/, ''); // ★ '=' を削除

  const nonceRecord = Utilities.getUuid();
  const nonceAdmin = Utilities.getUuid();

  const tokenParts = {
    payload: payloadBase64,
    signature: signatureBase64,
    userId: userId,
    n_rec: nonceRecord, 
    n_adm: nonceAdmin,  
    exp: exp 
  };

  console.log(`[createSignedToken] Generated Token Parts: ${JSON.stringify(tokenParts)}`);
  return tokenParts;
}

// --- ★ 修正: ログインチェックとリダイレクトURL生成 (署名付きトークン方式) (★ 修正あり) ★ ---
/**
 * ログイン認証を行い、署名付きトークンを含むリダイレクトURLを生成する
 * @param {string} id - ユーザーID
 * @param {string} password - パスワード
 * @param {string} redirectFlag - リダイレクト先フラグ ('record' or 'admin')
 * @return {object} { success: boolean, redirectUrl?: string, message?: string }
 */
function checkLogin(id, password, redirectFlag) {
  console.log('--- checkLogin (Cache Enabled) 開始 ---');
  console.log('ID:', id, 'Flag:', redirectFlag);

  try {
    // --- 認証処理 ---
    if (!SPREADSHEET_ID || !CONFIG.RECORD_APP_URL || !CONFIG.ADMIN_APP_URL) { 
      throw new Error('スクリプトプロパティ(Spreadsheet ID / URLs)が設定されていません。');
    }

    // ★★★★★ 修正点 ★★★★★
    // スプレッドシートの代わりに、キャッシュ対応の関数から全データを取得
    const allUsersData = getAllUsersData();
    if (allUsersData.length === 0) {
      // ユーザーデータが空でも、SET_SECRETS直後などはあり得るのでエラーにはしない
      console.log('Login failed: No user data found in cache/sheet.');
      return { success: false, message: 'IDまたはパスワードが正しくありません。' };
    }

    let targetUser = null;
    
    // 取得した全データ（配列）をループしてIDを検索
    for (const row of allUsersData) {
      const userId = row[COLS.ID - 1]; // B列

      // ★ 比較前に文字列に変換して厳密比較 (IDが数値の場合も考慮)
      if (String(userId) === String(id)) {
        targetUser = {
          id: userId,
          hash: row[COLS.HASH - 1], // C列
          salt: row[COLS.SALT - 1]  // E列
        };
        break; // 該当者が見つかったらループ終了
      }
    }

    // 該当者がいなかった場合
    if (targetUser === null) {
      console.log(`Login failed: ID not found for ${id}`);
      return { success: false, message: 'IDまたはパスワードが正しくありません。' };
    }
    
    // パスワードの照合
    if (hashPassword(password, targetUser.salt) !== targetUser.hash) { 
      console.log(`Login failed: Password mismatch for ${id}`);
      return { success: false, message: 'IDまたはパスワードが正しくありません。' };
    }
    console.log('パスワード認証成功。');
    // ★★★★★ 修正ここまで ★★★★★


    // ★ トークン生成 ★
    const tokenParts = createSignedToken(id); 
    console.log('トークン生成完了 (Nonce含む)。');

    // ★ リダイレクト先のベースURLを決定 ★
    const normalizedFlag = (typeof redirectFlag === 'string' && redirectFlag.toLowerCase() === 'admin') ? 'admin' : 'record';
    const baseUrl = (normalizedFlag === 'admin') ? CONFIG.ADMIN_APP_URL : CONFIG.RECORD_APP_URL;
    console.log('選択された baseUrl:', baseUrl);

    // ★ URLを構築 (p, s, uid, n_rec, n_adm をすべて含める) ★
    const redirectUrl = baseUrl
      + '?p=' + encodeURIComponent(tokenParts.payload)
      + '&s=' + encodeURIComponent(tokenParts.signature)
      + '&uid=' + encodeURIComponent(tokenParts.userId)
      + '&n_rec=' + encodeURIComponent(tokenParts.n_rec) // 記録用Nonce
      + '&n_adm=' + encodeURIComponent(tokenParts.n_adm); // 管理者用Nonce

    console.log('生成された redirectUrl:', redirectUrl);
    console.log('--- checkLogin 正常終了 ---');
    return { success: true, redirectUrl: redirectUrl }; // HTML側にURLを返す

  } catch (err) {
    console.error('checkLogin でエラー:', err.stack || err.message);
    return { success: false, message: '認証中にエラーが発生しました: ' + (err.message || err.toString()) };
  }
}
