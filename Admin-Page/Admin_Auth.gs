// ===============================================================
// [ Admin_Auth.gs ]
// 認証処理 (トークン検証, 2FA, Nonce管理)
// ===============================================================

// --- 認証関連 ---
const CACHE_KEY_PREFIX_CODE = "2FA_CODE_";
const CACHE_KEY_PREFIX_FLAG = "2FA_FLAG_";
const CODE_EXPIRATION_SECONDS = 300;  // 認証コードの有効期限 (5分)
const FLAG_EXPIRATION_SECONDS = 3600; // 認証フラグの有効期限 (1時間)

/**
 * (ステップ4) 2FA認証コードを生成し、メールで送信する
 */
function send2FACode(uid, userName) {
  let deployerEmail = '';
  try {
    deployerEmail = Session.getEffectiveUser().getEmail();
    
    if (!deployerEmail) {
      throw new Error('スクリプト実行者のメールアドレスが取得できません。');
    }

    const code = Math.floor(100000 + Math.random() * 900000).toString();
    const cacheKey = CACHE_KEY_PREFIX_CODE + uid; 
    CacheService.getScriptCache().put(cacheKey, code, CODE_EXPIRATION_SECONDS);
    
    const subject = `【要対応】管理者ページ 2FAコード (対象: ${userName})`;
    const body = `デプロイ主（${deployerEmail}）様\n\n`
      + `管理者 [${userName} (ID: ${uid})] が管理者ページへのログインを試みています。\n\n`
      + "本人が操作していることを確認し、以下の認証コードを伝達してください。\n\n"
      + `認証コード: ${code}\n\n`
      + `このコードは ${CODE_EXPIRATION_SECONDS / 60} 分間有効です。\n`
      + "この操作に心当たりがない場合は、コードを伝達しないでください。";
      
    MailApp.sendEmail(deployerEmail, subject, body);
    
    const logMsg = `認証コード [${code}] を [${deployerEmail}] (UID: ${uid} のリクエスト) 宛に送信し、キャッシュ [${cacheKey}] に保存しました。`;
    Logger.log(`send2FACode: ${logMsg}`);
    writeLog_([logMsg], { functionName: "send2FACode", status: "Success", message: `2FAコードをデプロイ主 (${deployerEmail}) に送信`, editorName: userName });
    
    return { status: 'success' };
    
  } catch (e) {
    const errMsg = `2段階認証コードの送信に失敗しました。 (Error: ${e.message})`;
    Logger.log(`send2FACode: [${uid}] の処理中（送信先: ${deployerEmail}）に失敗しました。 Error: ${e.message}`);
    writeLog_([errMsg], { functionName: "send2FACode", status: "Error", message: e.message, editorName: userName });
    
    if (e.message.includes('無効なメール')) {
       return { 
         status: 'error', 
         message: `2段階認証コードの送信に失敗しました。宛先メールアドレス [${deployerEmail}] が無効です。`
       };
    }
    return { 
      status: 'error', 
      message: errMsg
    };
  }
}

/**
 * (ステップ3 & 7) URLパラメータのトークンを検証する
 */
function verifyTokenFromUrl(params) {
  const { p, s, uid, n_adm } = params;
  let userName = "N/A"; // ログ記録用の仮ユーザー名

  try {
    if (!p || !s || !uid || !n_adm) {
      return { status: 'error', message: '必要な認証パラメータ(p, s, uid, n_adm)が不足しています。', errorCode: 'INVALID_TOKEN' };
    }
    if (!verifySignature(p, s)) {
      return { status: 'error', message: 'トークンの署名が無効です。', errorCode: 'INVALID_TOKEN' };
    }

    const payload = JSON.parse(Utilities.newBlob(Utilities.base64DecodeWebSafe(p)).getDataAsString());
    if (payload.uid.toLowerCase() !== uid.toLowerCase()) throw new Error('Payload UID mismatch');
    const now = Math.floor(Date.now() / 1000);
    if (now > payload.exp) throw new Error('Token expired');

    const roleCheck = getUserRole(uid);
    if (roleCheck.status === 'error') {
      return { status: 'error', message: roleCheck.message, errorCode: 'SERVER_EXCEPTION' };
    }
    const userRole = roleCheck.role;
    userName = roleCheck.name; // ★ ログ記録用にユーザー名を取得

    const nonceResult = verifyNonce(n_adm, uid, userName); // ★ ユーザー名をログ関数に渡す
    if (nonceResult.status === 'replay_error') {
      return { status: 'error', message: nonceResult.message, errorCode: 'INVALID_NONCE' };
    }
    
    // (A) Nonce検証OK (初回アクセス)
    if (nonceResult.status === 'valid') {
      if (userRole === 'SuperAdmin') {
        Logger.log('verifyTokenFromUrl: 初回アクセス (Nonce消費)。SuperAdminのため 2FA を要求します。');
        return { status: 'require_2fa', ...params, userName: userName, userRole: userRole, uid: uid };
      } else {
        Logger.log(`verifyTokenFromUrl: 初回アクセス (Nonce消費)。役割 [${userRole}] のため2FA不要、即時許可します。`);
        return { status: 'success', userRole: userRole, userName: userName, uid: uid };
      }
    }
    
    // (B) 2FAフラグ検証OK
    if (nonceResult.status === 'valid_2fa') {
      Logger.log('verifyTokenFromUrl: 2FAフラグを検知・消費。認証を許可します。');
      return { status: 'success', userRole: userRole, userName: userName, uid: uid };
    }
    
    return { status: 'error', message: '不明な認証ステータスです。', errorCode: 'UNKNOWN' };

  } catch (err) {
    let code = (err.message === 'Token expired') ? 'TOKEN_EXPIRED' : 'INVALID_TOKEN';
    const errMsg = 'トークンペイロードが無効、または期限切れです: ' + err.message;
    writeLog_([errMsg], { functionName: "verifyTokenFromUrl", status: "Error", message: errMsg, editorName: userName });
    return { status: 'error', message: errMsg, errorCode: code };
  }
}


/**
 * (ステップ3 & 7) NonceB (n_adm) を検証する
 */
function verifyNonce(nonceB, userId, userName) { // ★ userName をログ用に受け取る
  const cache = CacheService.getScriptCache();
  const cachedNonce = cache.get(nonceB);
  const cacheKey_2FA = CACHE_KEY_PREFIX_FLAG + userId;

  if (cachedNonce === null) {
    cache.put(nonceB, userId, 600); 
    const logMsg = `Nonce [${nonceB}] をキャッシュに保存 (初回アクセス)。`;
    Logger.log(`verifyNonce: ${logMsg}`);
    writeLog_([logMsg], { functionName: "verifyNonce", status: "Info", message: "NonceB OK (初回)", editorName: userName });
    return { status: 'valid' };
  }
  
  const logMsgReplay = `Nonce [${nonceB}] は既に使用済みです (リプレイ疑い)。`;
  Logger.log(`verifyNonce: ${logMsgReplay}`);
  writeLog_([logMsgReplay], { functionName: "verifyNonce", status: "Warning", message: "NonceB 使用済み (リプレイ疑い)", editorName: userName });

  const flag_2FA = cache.get(cacheKey_2FA);
  if (flag_2FA !== null) {
    const logMsg2FA = `2FAフラグ [${cacheKey_2FA}] を検知。フラグを消費します。`;
    Logger.log(`verifyNonce: ${logMsg2FA}`);
    writeLog_([logMsg2FA], { functionName: "verifyNonce", status: "Info", message: "2FAフラグを検知・消費", editorName: userName });
    
    cache.remove(cacheKey_2FA); 
    return { status: 'valid_2fa' };
  } else {
    const errMsg = `2FAフラグ [${cacheKey_2FA}] が見つかりません。アクセスを拒否します。`;
    Logger.log(`verifyNonce: ${errMsg}`);
    writeLog_([errMsg], { functionName: "verifyNonce", status: "Error", message: "2FAフラグが見つからずアクセス拒否", editorName: userName });
    return { status: 'replay_error', message: 'Nonce (n_adm) が既に使用されています (リプレイ攻撃)。' };
  }
}

/**
 * (ステップ5) CodeEntryPage から呼び出される 2FAコード検証
 */
function verifyCode(uid, code, userName) { // ★ userName をログ用に受け取る
  try {
    const cache = CacheService.getScriptCache();
    const cacheKey_Code = CACHE_KEY_PREFIX_CODE + uid;
    const expectedCode = cache.get(cacheKey_Code);

    if (expectedCode === null) {
      const errMsg = `[${uid}] の認証コードがキャッシュに存在しないか、期限切れです。`;
      Logger.log(`verifyCode: ${errMsg}`);
      writeLog_([errMsg], { functionName: "verifyCode", status: "Error", message: "2FAコード期限切れ", editorName: userName });
      return { status: 'error', message: '認証コードの有効期限が切れました。ログインからやり直してください。' };
    }
    if (code === expectedCode) {
      cache.remove(cacheKey_Code);
      const cacheKey_Flag = CACHE_KEY_PREFIX_FLAG + uid;
      cache.put(cacheKey_Flag, 'ok', FLAG_EXPIRATION_SECONDS);
      
      const logMsg = `認証コード検証成功。コード [${cacheKey_Code}] を削除し、フラグ [${cacheKey_Flag}] を${FLAG_EXPIRATION_SECONDS}秒間保存しました。`;
      Logger.log(`verifyCode: ${logMsg}`);
      writeLog_([logMsg], { functionName: "verifyCode", status: "Success", message: "2FAコード検証成功", editorName: userName });
      
      return { status: 'success', message: '認証に成功しました。' };
    } else {
      const errMsg = `認証コード検証失敗。 [${uid}] (Input: ${code}, Expected: ${expectedCode})`;
      Logger.log(`verifyCode: ${errMsg}`);
      writeLog_([errMsg], { functionName: "verifyCode", status: "Error", message: "2FAコード検証失敗", editorName: userName });
      return { status: 'error', message: '認証コードが正しくありません。' };
    }
  } catch (e) {
    const errMsg = '認証中にエラーが発生しました: ' + e.message;
    Logger.log('verifyCode: エラー発生。' + e.message);
    writeLog_([errMsg], { functionName: "verifyCode", status: "Error", message: e.message, editorName: userName });
    return { status: 'error', message: errMsg };
  }
}

/**
 * 署名検証
 */
function verifySignature(payloadBase64, signatureBase64) {
  const TOKEN_SECRET_KEY = ADMIN_CONFIG.TOKEN_SECRET_KEY; // ★ 修正: CONFIG から読み込む
  if (!TOKEN_SECRET_KEY) return false;
  try {
    const signatureBytes = Utilities.base64DecodeWebSafe(signatureBase64);
    const expectedSignatureBytes = Utilities.computeHmacSha256Signature(payloadBase64, TOKEN_SECRET_KEY);
    if (signatureBytes.length !== expectedSignatureBytes.length) return false;
    for (let i = 0; i < signatureBytes.length; i++) {
      if (signatureBytes[i] !== expectedSignatureBytes[i]) return false;
    }
    return true;
  } catch (e) {
    Logger.log('Error during signature verification: ' + e.message);
    return false;
  }
}

/**
 * ユーザーIDから役割(F列)と名前(A列)を取得する
 */
function getUserRole(uid) {
  try {
    // ★ 修正: CONFIG から読み込む
    const SPREADSHEET_ID = ADMIN_CONFIG.SPREADSHEET_ID;
    const SHEETS = ADMIN_CONFIG.SHEETS;
    
    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEETS.USER); 
    if (!sheet) {
      return { status: 'error', message: `シート '${SHEETS.USER}' が見つかりません。` };
    }
    const targetRow = findRowById(sheet, uid, 2); // (Admin_Utils.gs) B列を検索
    if (targetRow > -1) {
      const name = sheet.getRange(targetRow, 1).getValue(); 
      const role = sheet.getRange(targetRow, 6).getValue(); 
      const trimmedRole = String(role).trim(); 
      Logger.log(`getUserRole: UID [${uid}] (Row ${targetRow}) found. Name: [${name}], Role(Raw): [${role}], Role(Trimmed): [${trimmedRole}]`);
      const finalRole = trimmedRole ? trimmedRole : 'User';
      return { status: 'success', role: finalRole, name: name };
    } else {
      Logger.log(`getUserRole: UID [${uid}] not found in sheet '${SHEETS.USER}'.`);
      return { status: 'error', message: `ユーザー [${uid}] が '${SHEETS.USER}' シートで見つかりません。` };
    }
  } catch(e) {
    Logger.log('getUserRole: Error ' + e.message);
    return { status: 'error', message: 'ユーザー役割の取得に失敗: ' + e.message };
  }
}
