// ===============================================================
// [ Admin_Setting.gs ]
// UI設定・権限設定管理
// ===============================================================

// ★ 必ず設定ロード（どの関数でも最初に実行される安全策）
function ensureConfigLoaded_() {
  if (!ADMIN_CONFIG.SHEETS) {
    loadAdminConfig_(); 
  }
}

/**
 * (E) UI設定取得
 */
function getUiSettings() {

  ensureConfigLoaded_();

  const sheetName = ADMIN_CONFIG.SHEETS.UI_SETTINGS;
  const jsonString = getSheetData(sheetName);
  const data = JSON.parse(jsonString);
  const settings = {};

  if (data.length > 0 && data[0][0] === 'エラー') {
    Logger.log('getUiSettings: getSheetDataからエラー: ' + data[0][1]);
    return JSON.stringify({});
  }
  if (data.length <= 1) {
    Logger.log('getUiSettings: UI_Settings にデータがありません。');
    return JSON.stringify({});
  }

  for (let i = 1; i < data.length; i++) {
    const key = data[i][0];
    const value = data[i][1];
    if (key) settings[key] = value;
  }

  return JSON.stringify(settings);
}

/**
 * (E) UI設定の保存
 */
function updateUiSettings(settings, authInfo) {

  ensureConfigLoaded_();

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  try {

    const sheet = SpreadsheetApp
      .openById(ADMIN_CONFIG.SPREADSHEET_ID)
      .getSheetByName(ADMIN_CONFIG.SHEETS.UI_SETTINGS);

    if (!sheet) return 'エラー: "UI_Settings" シートが見つかりません。';

    const lastRow = getLastRowByColumn(sheet, 1);
    const data = sheet.getRange(1, 1, lastRow, 2).getValues();

    const newData = [data[0]];

    for (let i = 1; i < data.length; i++) {
      const key = data[i][0];
      if (key && settings.hasOwnProperty(key)) {
        newData.push([key, settings[key]]);
      } else if (key) {
        newData.push([key, data[i][1]]);
      }
    }

    sheet.getRange(1, 1, newData.length, newData[0].length).setValues(newData);

    notifyRecordApp_('ui_settings');

    const successMsg = "設定を保存しました。（反映まで最大10秒）";
    writeLog_([successMsg], {
      functionName: "updateUiSettings",
      status: "Success",
      message: "UI設定を更新",
      editorName: editorName
    });

    return successMsg;

  } catch (e) {
    writeLog_([`updateUiSettings Error: ${e.message}`], {
      functionName: "updateUiSettings",
      status: "Error",
      message: e.message,
      editorName: editorName
    });
    return "エラー: " + e.message;
  }
}

/**
 * (F) 権限設定を ScriptProperties から読み込む
 */
function getRoleSettings() {

  ensureConfigLoaded_();

  try {
    const properties = PropertiesService.getUserProperties();
    const jsonString = properties.getProperty('roleSettings');

    if (jsonString) {
      Logger.log("getRoleSettings: ScriptProperties から読み込み");
      return jsonString;
    } else {

      const defaultSettings = {
        "Admin": {
          "pageA": true, "pageB": true, "pageC": true, "pageD": true,
          "pageE": true, "pageF": false, "pageG": true
        },
        "User": {
          "pageA": true, "pageB": false, "pageC": false, "pageD": false,
          "pageE": false, "pageF": false, "pageG": false
        }
      };

      const defaultJson = JSON.stringify(defaultSettings);
      properties.setProperty('roleSettings', defaultJson);
      Logger.log("getRoleSettings: デフォルト作成");
      return defaultJson;
    }

  } catch (e) {
    Logger.log("getRoleSettings Error: " + e.message);
    return JSON.stringify({});
  }
}

/**
 * (F) 権限設定を ScriptProperties に保存する
 */
function saveRoleSettings(role, menuId, isVisible, authInfo) {

  ensureConfigLoaded_();

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';

  try {
    const properties = PropertiesService.getUserProperties();
    const jsonString = properties.getProperty('roleSettings');

    let settings = {};
    if (jsonString) settings = JSON.parse(jsonString);

    if (role === 'SuperAdmin') {
      return "SuperAdmin の権限は変更できません。";
    }

    if (!settings[role]) settings[role] = {};
    settings[role][menuId] = isVisible;

    properties.setProperty('roleSettings', JSON.stringify(settings));

    const msg = `設定保存: ${role} - ${menuId} = ${isVisible}`;
    writeLog_([msg], {
      functionName: "saveRoleSettings",
      status: "Success",
      message: msg,
      editorName: editorName
    });

    return msg;

  } catch (e) {
    const errMsg = "エラー: 設定の保存に失敗しました。";
    writeLog_([errMsg], {
      functionName: "saveRoleSettings",
      status: "Error",
      message: e.message,
      editorName: editorName
    });
    return errMsg;
  }
}
