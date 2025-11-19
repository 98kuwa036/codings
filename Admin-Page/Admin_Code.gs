// [ Admin_Code.gs ]
// Webアプリのメインエントリーポイント (doGet, include)

/**
 * メインの受付関数
 */
function doGet(e) {
  // --- 1. 設定読み込み ---
  try {
    loadAdminConfig_(); // (Admin_Config.gs)
  } catch (configErr) {
    return HtmlService.createHtmlOutput(
      `<h1>サーバー設定エラー</h1><p>${configErr.message}</p>`
    ).setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }

  // --- 2. エラーページ生成用の補助関数 ---
  function showErrorPage(adminMessage, errorCode = 'UNKNOWN') { 
    Logger.log(`showErrorPage: [${errorCode}] ${adminMessage}`);
    writeLog_([], { // (Admin_Utils.gs)
      functionName: "doGet:showErrorPage",
      status: "Error",
      message: `[${errorCode}] ${adminMessage}`,
      editorName: "N/A" 
    });

    const template = HtmlService.createTemplateFromFile('ErrorPage'); 
    template.errorMessage = adminMessage; 
    template.errorCode = errorCode;     
    template.systemName = ADMIN_CONFIG.SYSTEM_NAME || "管理者ダッシュボード";
    
    let redirectUrl = ADMIN_CONFIG.LOGIN_PAGE_URL || "https://example.com/login"; 
    
    if (redirectUrl.includes('?')) {
      template.loginUrl = redirectUrl + '&redirect=admin';
    } else {
      template.loginUrl = redirectUrl + '?redirect=admin';
    }

    return template.evaluate()
        .setTitle('エラー')
        .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }

  // --- 3. 必須プロパティのチェック ---
  if (!ADMIN_CONFIG.TOKEN_SECRET_KEY || !ADMIN_CONFIG.SPREADSHEET_ID || !ADMIN_CONFIG.LOGIN_PAGE_URL || !ADMIN_CONFIG.SHEETS.USER) {
    return showErrorPage(
      "サーバー設定エラー: TOKEN_SECRET_KEY, SPREADSHEET_ID, LOGIN_PAGE_URL, または SHEETS_CONFIG_JSON が UserProperties に設定されていません。「Record Tool」側で SETUP_PROPERTIES() を実行してください。",
      'SERVER_CONFIG_ERROR' 
    );
  }

  // --- 4. メイン処理 (認証) ---
  const authResult = verifyTokenFromUrl(e.parameter); // (Admin_Auth.gs)
  
  switch (authResult.status) {
    
    case 'success': // 認証成功
      const successMsg = `認証成功 (success)。AdminPage.html を表示します。 (Role: ${authResult.userRole}, Name: ${authResult.userName})`;
      Logger.log(`doGet: ${successMsg}`);
      writeLog_([successMsg], {
        functionName: "doGet",
        status: "Success",
        message: `AdminPageを表示 (Role: ${authResult.userRole})`,
        editorName: authResult.userName 
      });
      
      const templateAdmin = HtmlService.createTemplateFromFile('AdminPage');
      
      templateAdmin.systemName = ADMIN_CONFIG.SYSTEM_NAME || "管理者ダッシュボード"; 
      templateAdmin.userRole = authResult.userRole; 
      templateAdmin.authInfoJson = JSON.stringify({
         uid: authResult.uid,
         name: authResult.userName
      });
      templateAdmin.allPermissionsJson = getRoleSettings(); // (Admin_Settings.gs)
      
      return templateAdmin.evaluate() 
        .setTitle('管理者ページ')
        .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);

    case 'require_2fa': // 2段階認証へ
      const logMsg2FA = `2段階認証 (require_2fa) が必要です。CodeEntryPage.html を表示します。 (Name: ${authResult.userName})`;
      Logger.log(`doGet: ${logMsg2FA}`);
      writeLog_([logMsg2FA], {
        functionName: "doGet",
        status: "Info",
        message: "2FAページを表示",
        editorName: authResult.userName
      });

      const mailResult = send2FACode(authResult.uid, authResult.userName); // (Admin_Auth.gs)
      
      if (mailResult.status === 'error') {
        return showErrorPage(mailResult.message, '2FA_MAIL_ERROR');
      }
      
      // ★ 修正: CodeEntryPage があればそれを使う
      try {
        const template2FA = HtmlService.createTemplateFromFile('CodeEntryPage');
        template2FA.p_original = authResult.p;
        template2FA.s_original = authResult.s;
        template2FA.uid_original = authResult.uid;
        template2FA.n_rec_original = authResult.n_rec || '';
        template2FA.n_adm_original = authResult.n_adm;
        template2FA.p_post_2fa = '';
        template2FA.s_post_2fa = '';
        template2FA.n_post_2fa = '';
        template2FA.userId = authResult.uid;
        template2FA.userName = authResult.userName;
        template2FA.adminBaseUrl = ScriptApp.getService().getUrl();

        return template2FA.evaluate()
          .setTitle('2段階認証')
          .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
          .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
      } catch (pageErr) {
        return showErrorPage("2段階認証ページの読み込みに失敗しました (CodeEntryPage.html が見つかりません)", "FILE_NOT_FOUND");
      }

    case 'error': // その他の認証エラー
    default:
      return showErrorPage(
        authResult.message + ' ログインからやり直してください。',
        authResult.errorCode || 'UNKNOWN' 
      );
  }
}

/**
 * HTMLから別ファイルをインクルードする用
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}
