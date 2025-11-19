/**
 * ★★★ Cloud Vision APIキー設定用 (手動実行) ★★★
 * この関数を一度だけ手動実行してください。
 */
/*
function SET_VISION_API_KEY() {

  // ▼▼▼ この「...」部分を、先ほどGCPでコピーしたAPIキーに書き換えてください ▼▼▼

  const VISION_API_KEY = "AIzaSyAowbAd4wglz45lrZcHyBRFe1phpG2gibI";

  // ▲▲▲ ここまで ▲▲▲

  if (VISION_API_KEY.includes('...')) {
    throw new Error('VISION_API_KEY が書き換えられていません。');
  }

  try {
    PropertiesService.getUserProperties().setProperty('VISION_API_KEY', VISION_API_KEY);
    console.log('--- Cloud Vision API キーの設定完了 ---');
    console.log('VISION_API_KEY: 安全に保存されました。');
  } catch (e) {
    console.error('APIキーの保存に失敗しました: ' + e.message);
  }
}
// [ Ocr-Settings.gs ]
// 外部API (OCR) とファイルアップロードURLの生成

/**
 * (Api.js - runOCR)
 * Vision API を呼び出してテキストを抽出する
 */
function runOCR(imageBase64) {
  // ★ 修正: CONFIG をロード
  if (!CONFIG || !CONFIG.VISION_API_KEY) {
    loadConfig_(); // (Config.gs)
  }
  const VISION_API_KEY = CONFIG.VISION_API_KEY;

  if (!VISION_API_KEY || VISION_API_KEY.includes("...")) {
    throw new Error("サーバーエラー: Vision APIキーが設定されていません。");
  }
  
  const apiUrl = `https://vision.googleapis.com/v1/images:annotate?key=${VISION_API_KEY}`;
  
  const payload = {
    requests: [
      {
        image: {
          content: imageBase64.split(',')[1] // Base64データ本体のみ
        },
        features: [
          {
            type: 'TEXT_DETECTION' // テキスト検出
          }
        ],
        imageContext: {
            languageHints: ["ja"] // 日本語をヒントにする
        }
      }
    ]
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(apiUrl, options);
    const result = JSON.parse(response.getContentText());

    if (result.responses && result.responses[0] && result.responses[0].fullTextAnnotation) {
      const detectedText = result.responses[0].fullTextAnnotation.text;
      Logger.log(`OCR Success: Text detected.`);
      return detectedText;
    } else if (result.responses && result.responses[0].error) {
      Logger.log(`OCR API Error: ${result.responses[0].error.message}`);
      throw new Error(`Vision APIエラー: ${result.responses[0].error.message}`);
    } else {
      Logger.log(`OCR Success: No text detected.`);
      return "（テキストは検出されませんでした）";
    }
  } catch (error) {
    Logger.log(`runOCR Fetch Error: ${error.message}`);
    throw new Error(`OCRの実行に失敗しました: ${error.message}`);
  }
}

/**
 * (Api.js - getResumableUploadUrl)
 * ★★★ 修正: 「Tempフォルダ」に保存するよう変更 ★★★
 */
function getResumableUploadUrl(fileName, mimeType) {
  // ★ 修正: CONFIG をロード
  if (!CONFIG || !CONFIG.TEMP_DRIVE_FOLDER_ID) {
    loadConfig_(); // (Config.gs)
  }
  const TEMP_FOLDER_ID = CONFIG.TEMP_DRIVE_FOLDER_ID; // ★ 修正

  if (!TEMP_FOLDER_ID || TEMP_FOLDER_ID.includes("...")) {
    throw new Error("サーバー設定エラー: TEMP_DRIVE_FOLDER_ID が未設定です。");
  }

  try {
    const accessToken = ScriptApp.getOAuthToken();

    const metadata = {
      name: fileName,
      parents: [TEMP_FOLDER_ID] // ★ 修正: 保存先を Temp フォルダに変更
    };

    const url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable';
    
    const response = UrlFetchApp.fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Upload-Content-Type': mimeType
      },
      payload: JSON.stringify(metadata),
      muteHttpExceptions: true
    });
    
    const responseCode = response.getResponseCode();
    if (responseCode !== 200) {
      throw new Error(`Drive API (get URL) Error: ${responseCode} - ${response.getContentText()}`);
    }

    const uploadUrl = response.getHeaders()['Location'];
    
    const fileIdMatch = uploadUrl.match(/id=([^&]+)/);
    if (!fileIdMatch || !fileIdMatch[1]) {
      throw new Error("アップロードURLからFileIDの抽出に失敗しました。");
    }
    const fileId = fileIdMatch[1];
    
    Logger.log(`Resumable Upload URL (and FileID) generated for: ${fileName}`);
    return { uploadUrl: uploadUrl, fileId: fileId };

  } catch (error) {
    Logger.log(`getResumableUploadUrl Error: ${error.message}`);
    throw new Error(`アップロードURLの取得に失敗: ${error.message}`);
  }
}
