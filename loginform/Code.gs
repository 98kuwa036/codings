// ===============================================================
// [ Code.gs ]
// メインエントリーポイント (doGet / doPost)
// ===============================================================

/**
 * GETリクエストを処理する（ログインページを表示）
 * @param {Object} e - リクエストパラメータ
 * @return {HtmlOutput} HTMLページ
 */
function doGet(e) {
  try {
    // 設定を読み込み
    loadConfig_();

    // 設定チェック
    if (!CONFIG.SPREADSHEET_ID || !CONFIG.RECORD_APP_URL || !CONFIG.ADMIN_APP_URL) {
      return HtmlService.createHtmlOutput(
        '<h1>設定エラー</h1>' +
        '<p>スクリプトの初期設定が必要です。</p>' +
        '<p>エディタから <code>SETUP_PROPERTIES</code> 関数を実行してください。</p>'
      );
    }

    // リダイレクトフラグをホワイトリスト化
    const rawFlag = (e.parameter && e.parameter.redirect) ? e.parameter.redirect.toLowerCase() : '';
    const redirectFlag = (rawFlag === 'admin') ? 'admin' : 'record';
    console.log('doGet: rawFlag =', rawFlag, ' → redirectFlag =', redirectFlag);

    // HTMLテンプレートを生成
    const template = HtmlService.createTemplateFromFile('index');
    template.redirectFlag = redirectFlag;
    template.scriptUrl = ScriptApp.getService().getUrl();
    template.systemName = CONFIG.SYSTEM_NAME;

    return template.evaluate()
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
      .setTitle('ログイン | ' + CONFIG.SYSTEM_NAME);

  } catch (err) {
    console.error('doGet Error:', err.message);
    return HtmlService.createHtmlOutput(
      '<h1>エラー</h1><p>' + err.message + '</p>'
    );
  }
}

/**
 * POSTリクエストを処理する（ユーザー情報編集）
 * @param {Object} e - リクエストパラメータ
 * @return {TextOutput} JSON形式のレスポンス
 */
function doPost(e) {
  let response;

  try {
    // 設定を読み込み
    loadConfig_();

    const sheet = getUserSheet_();
    const action = e.parameter.action;
    const targetId = e.parameter.id;
    const password = e.parameter.password;
    const targetName = e.parameter.name;

    // 入力値検証
    if (!action || !targetId) {
      throw new Error('必須パラメータが不足しています。');
    }

    const idRow = findRowById_(sheet, targetId);

    // --- 登録処理 ---
    if (action === '登録') {
      if (idRow > -1) {
        throw new Error(`ID「${targetId}」は既に使用されています。`);
      }
      if (!targetName) {
        throw new Error('担当者名が選択されていません。');
      }
      if (!password) {
        throw new Error('パスワードを入力してください。');
      }

      const newSalt = Utilities.getUuid();
      const newHash = hashPassword_(password, newSalt);
      const nameRow = findRowByName_(sheet, targetName);

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
    }
    // --- 削除処理 ---
    else if (action === '削除') {
      if (idRow > -1) {
        sheet.deleteRow(idRow);
        response = {
          status: 'success',
          message: `ID「${targetId}」を削除しました。`
        };
      } else {
        throw new Error(`削除対象のID「${targetId}」が見つかりませんでした。`);
      }
    }
    // --- パスワード変更処理 ---
    else if (action === 'パスワード変更') {
      if (!password) {
        throw new Error('新しいパスワードを入力してください。');
      }
      if (idRow > -1) {
        const newSalt = Utilities.getUuid();
        const newHash = hashPassword_(password, newSalt);
        sheet.getRange(idRow, COLS.HASH).setValue(newHash);
        sheet.getRange(idRow, COLS.SALT).setValue(newSalt);
        response = {
          status: 'success',
          message: `ID「${targetId}」のパスワードを更新しました。`
        };
      } else {
        throw new Error(`パスワード変更対象のID「${targetId}」が見つかりませんでした。`);
      }
    }
    // --- 無効な操作 ---
    else {
      throw new Error('無効な操作です。');
    }

    // キャッシュをクリア
    clearUserCache_();

  } catch (err) {
    console.error('doPost Error:', err.message);
    response = {
      status: 'error',
      message: err.message
    };
  }

  return ContentService
    .createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}
