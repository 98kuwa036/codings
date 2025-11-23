// ===============================================================
// [ Auth.gs ]
// 認証関連の関数
// ===============================================================

/**
 * ログイン認証を行い、署名付きトークンを含むリダイレクトURLを生成する
 * @param {string} id - ユーザーID
 * @param {string} password - パスワード
 * @param {string} redirectFlag - リダイレクト先フラグ ('record' or 'admin')
 * @return {object} { success: boolean, redirectUrl?: string, message?: string }
 */
function checkLogin(id, password, redirectFlag) {
  console.log('--- checkLogin 開始 ---');
  console.log('ID:', id, 'Flag:', redirectFlag);

  try {
    // 設定を読み込み
    if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
      loadConfig_();
    }

    // --- 入力値検証 ---
    if (!id || !password) {
      return { success: false, message: 'IDとパスワードを入力してください。' };
    }

    // --- 認証処理 ---
    const allUsersData = getAllUsersData_();
    if (allUsersData.length === 0) {
      console.log('Login failed: No user data found.');
      return { success: false, message: 'IDまたはパスワードが正しくありません。' };
    }

    // ユーザー検索
    let targetUser = null;
    for (const row of allUsersData) {
      const userId = row[COLS.ID - 1]; // B列
      if (String(userId) === String(id)) {
        targetUser = {
          id: userId,
          hash: row[COLS.HASH - 1], // C列
          salt: row[COLS.SALT - 1]  // E列
        };
        break;
      }
    }

    // ユーザーが見つからない
    if (targetUser === null) {
      console.log(`Login failed: ID not found for ${id}`);
      return { success: false, message: 'IDまたはパスワードが正しくありません。' };
    }

    // パスワード照合
    if (hashPassword_(password, targetUser.salt) !== targetUser.hash) {
      console.log(`Login failed: Password mismatch for ${id}`);
      return { success: false, message: 'IDまたはパスワードが正しくありません。' };
    }
    console.log('パスワード認証成功。');

    // --- トークン生成 ---
    const tokenParts = createSignedToken_(id);
    console.log('トークン生成完了。');

    // --- リダイレクトURL生成 ---
    const normalizedFlag = (typeof redirectFlag === 'string' && redirectFlag.toLowerCase() === 'admin') ? 'admin' : 'record';
    const baseUrl = (normalizedFlag === 'admin') ? CONFIG.ADMIN_APP_URL : CONFIG.RECORD_APP_URL;
    console.log('選択された baseUrl:', baseUrl);

    const redirectUrl = baseUrl
      + '?p=' + encodeURIComponent(tokenParts.payload)
      + '&s=' + encodeURIComponent(tokenParts.signature)
      + '&uid=' + encodeURIComponent(tokenParts.userId)
      + '&n_rec=' + encodeURIComponent(tokenParts.n_rec)
      + '&n_adm=' + encodeURIComponent(tokenParts.n_adm);

    console.log('生成された redirectUrl:', redirectUrl);
    console.log('--- checkLogin 正常終了 ---');
    return { success: true, redirectUrl: redirectUrl };

  } catch (err) {
    console.error('checkLogin でエラー:', err.stack || err.message);
    return { success: false, message: '認証中にエラーが発生しました: ' + (err.message || err.toString()) };
  }
}

/**
 * 署名付きトークンと両方のNonceを生成する
 * @param {string} userId - ユーザーID
 * @return {object} トークン情報 {payload, signature, userId, n_rec, n_adm, exp}
 */
function createSignedToken_(userId) {
  if (!TOKEN_SECRET_KEY) {
    throw new Error('TOKEN_SECRET_KEYが設定されていません。SETUP_PROPERTIESを実行してください。');
  }

  const now = Math.floor(Date.now() / 1000);
  const exp = now + (CONFIG.TOKEN_EXPIRATION || 14400);

  const payloadObj = { uid: userId, iat: now, exp: exp };
  const payloadBase64 = Utilities.base64EncodeWebSafe(JSON.stringify(payloadObj)).replace(/=+$/, '');

  console.log(`[createSignedToken_] Payload Base64: "${payloadBase64}"`);

  const signatureBytes = Utilities.computeHmacSha256Signature(payloadBase64, TOKEN_SECRET_KEY);
  const signatureBase64 = Utilities.base64EncodeWebSafe(signatureBytes).replace(/=+$/, '');

  const nonceRecord = Utilities.getUuid();
  const nonceAdmin = Utilities.getUuid();

  return {
    payload: payloadBase64,
    signature: signatureBase64,
    userId: userId,
    n_rec: nonceRecord,
    n_adm: nonceAdmin,
    exp: exp
  };
}

/**
 * パスワードをハッシュ化する
 * @param {string} password - 平文パスワード
 * @param {string} salt - ソルト
 * @return {string} ハッシュ値 (16進数文字列)
 */
function hashPassword_(password, salt) {
  const digest = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    password + salt,
    Utilities.Charset.UTF_8
  );
  return digest.map(byte => ('0' + (byte & 0xFF).toString(16)).slice(-2)).join('');
}

// ===============================================================
// 列定義 (スプレッドシートの構造)
// ===============================================================
const COLS = {
  NAME: 1, // A列: 担当者名
  ID: 2,   // B列: ユーザーID
  HASH: 3, // C列: パスワードハッシュ
  // D列は未使用
  SALT: 5  // E列: ソルト
};
