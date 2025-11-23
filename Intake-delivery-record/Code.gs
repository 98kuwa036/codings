// ===============================================================
// --- メインエントリーポイント (ルーター機能付き) ---
// ===============================================================
function doGet(e) {
  
  // 1. 設定読み込み
  try {
    if (typeof loadConfig_ === 'function') loadConfig_();
  } catch (configErr) {
    return HtmlService.createHtmlOutput(`<h1>Config Error</h1><p>${configErr.message}</p>`)
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }

  // 2. パラメータ取得
  const params = e.parameter;
  
  // パラメータがない、または必須情報(p, s)がない場合はログインページへ
  if (!params || !params.p || !params.s) {
    return routeToLoginPage(e);
  }

  const { p, s, n_rec, n_adm } = params;

  // =================================================================
  // ★ ルーティング分岐
  // =================================================================
  
  // パターンA: n_rec (記録用トークン) がある場合
  // → 「記録ツール」を表示する
  if (n_rec) {
    return routeToRecordTool(e, p, s, n_rec, n_adm);
  } 
  
  // パターンB: n_rec はないが、n_adm (管理者用トークン) がある場合
  // → 「管理者メニュー（ログイン画面）」に戻る
  else if (n_adm) {
    // 認証済みフラグ(true)を渡してログインページを表示
    return routeToLoginPage(e, true);
  }

  // それ以外は通常のログインページへ
  return routeToLoginPage(e);
}

// ===============================================================
// A. 記録ツール (PageVersion) 表示用関数
// ===============================================================
function routeToRecordTool(e, p, s, n_rec, n_adm) {
  const appUrl = ScriptApp.getService().getUrl();
  const log = ["--- 記録ツール表示処理 ---"];
  let logPayload = { functionName: "routeToRecordTool", userId: "unknown" };

  try {
    // --- 1. トークン検証 ---
    const payload = validateToken(p, s); 
    if (!payload) return renderAuthError("認証に失敗しました (Invalid Token)。", 401, appUrl);
    
    const { uid, exp } = payload;
    logPayload.userId = uid;

    if (exp * 1000 < Date.now()) return renderAuthError("セッション有効期限切れです。", 401, appUrl);
    
    // Nonce検証
    if (!validateNonce(n_rec)) return renderAuthError("このURLは無効か、既に使用されています。", 403, appUrl);

    log.push(`✅ 認証成功 User: ${uid}`);

    // --- 2. 管理者メニューへ戻るためのURLを作成 ---
    // ★★★ 修正箇所: encodeURIComponent でパラメータを保護する ★★★
    // これにより、Base64文字 (+, /, =) がURL内で壊れるのを防ぎます
    const adminReturnUrl = `${appUrl}?p=${encodeURIComponent(p)}&s=${encodeURIComponent(s)}&n_adm=${encodeURIComponent(n_adm)}`;

    // --- 3. HTML生成 ---
    const template = HtmlService.createTemplateFromFile('PageVersion');
    template.systemName = (typeof CONFIG !== 'undefined' && CONFIG.SYSTEM_NAME) ? CONFIG.SYSTEM_NAME : '入出庫記録ツール';
    
    template.errorCode = "";
    template.errorMessage = "";
    template.loginUrl = "";
    
    // HTML側に渡す変数
    template.adminUrl = adminReturnUrl; 

    // アプリ用データ
    template.initialAuthData = {
      uid: uid,
      n_adm: n_adm,
      n_rec: n_rec,
      originalUrl: appUrl + '?' + e.queryString
    };

    const htmlOutput = template.evaluate()
      .setTitle(template.systemName)
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);

    logPayload.status = "Success";
    if (typeof writeLog_ === 'function') writeLog_(log, logPayload);

    return htmlOutput;

  } catch (err) {
    return renderFatalError("システムエラーが発生しました。", err, 500, appUrl);
  }
}

// ===============================================================
// B. ログインページ / 管理者メニュー (Index) 表示用関数
// ===============================================================
function routeToLoginPage(e, isAuthenticated = false) {
  try {
    // Index.html (ログイン兼メニュー画面) を読み込み
    const template = HtmlService.createTemplateFromFile('Index');
    
    // 必要な変数をセット
    template.redirectFlag = isAuthenticated ? 'admin' : ''; 
    template.scriptUrl = ScriptApp.getService().getUrl();
    template.systemName = (typeof CONFIG !== 'undefined' && CONFIG.SYSTEM_NAME) ? CONFIG.SYSTEM_NAME : '入出庫管理';

    return template.evaluate()
      .setTitle('ログイン | ' + template.systemName)
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);

  } catch (err) {
    return HtmlService.createHtmlOutput(`<h1>Login Page Error</h1><p>${err.message}</p>`);
  }
}

// ===============================================================
// Webhook (管理者ページからの更新通知) を受信する
// ===============================================================
function doPost(e) {
  // 設定読み込み
  if (typeof CONFIG === 'undefined' || !CONFIG || !CONFIG.WEBHOOK_SECRET) {
    try { 
      if (typeof loadConfig_ === 'function') loadConfig_(); 
    } catch (err) { /* ログ書き込み失敗の可能性 */ }
  }

  if (!CONFIG || !CONFIG.WEBHOOK_SECRET) {
    Logger.log('doPost Error: WEBHOOK_SECRET が未設定です。');
    return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: 'Webhook secret not configured' })).setMimeType(ContentService.MimeType.JSON);
  }
  try {
    const payload = JSON.parse(e.postData.contents);
    if (payload.secret !== CONFIG.WEBHOOK_SECRET) {
      throw new Error('Invalid Webhook secret.');
    }
    
    // Triggers.gs の関数呼び出し (存在チェック)
    let cacheKey = "unknown";
    if (typeof removeCacheByType_ === 'function') {
        cacheKey = removeCacheByType_(payload.updateType);
    }
    
    Logger.log(`Webhook Success: Cache removed for '${cacheKey}'`);
    return ContentService.createTextOutput(JSON.stringify({ status: 'success', cache_removed: cacheKey })).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    Logger.log(`doPost (Webhook) Error: ${error.message}`);
    return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: error.message })).setMimeType(ContentService.MimeType.JSON);
  }
}

// ===============================================================
// HTMLテンプレートにスクリプトをインクルードする
// ===============================================================
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

// ===============================================================
// エラー画面描画用ヘルパー関数 (ErrorPage.html)
// ===============================================================
function renderAuthError(msg, code, url) {
  return createErrorOutput(msg, code, url, "認証エラー");
}

function renderFatalError(msg, err, code, url) {
  const detailedMsg = msg + (err ? " (" + err.message + ")" : "");
  console.error(detailedMsg);
  return createErrorOutput(detailedMsg, code, url, "システムエラー");
}

function createErrorOutput(msg, code, url, title) {
  const template = HtmlService.createTemplateFromFile('ErrorPage');

  // URLの調整 (再ログイン用) - ログインページのURLを使用
  let loginUrl = "";
  if (typeof CONFIG !== 'undefined' && CONFIG.LOGIN_APP_URL) {
    loginUrl = CONFIG.LOGIN_APP_URL;
  } else {
    // CONFIGが読み込まれていない場合は読み込む
    try {
      if (typeof loadConfig_ === 'function') loadConfig_();
      loginUrl = CONFIG.LOGIN_APP_URL || url || "";
    } catch (e) {
      loginUrl = url || "";
    }
  }

  if (loginUrl && !loginUrl.includes('redirect=')) {
    loginUrl += loginUrl.includes('?') ? '&redirect=record' : '?redirect=record';
  }

  template.errorMessage = msg;
  template.errorCode = code || 500;
  template.loginUrl = loginUrl;
  template.systemName = (typeof CONFIG !== 'undefined') ? CONFIG.SYSTEM_NAME : 'システム';

  // JSON版 (安全策)
  template.errorMessageJson = JSON.stringify(msg);
  template.errorCodeJson = JSON.stringify(code);
  template.loginUrlJson = JSON.stringify(loginUrl);
  template.systemNameJson = JSON.stringify(template.systemName);

  return template.evaluate()
    .setTitle(title)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
