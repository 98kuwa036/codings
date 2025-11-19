// ===============================================================
// [ ExternalApi.gs ]
// 外部API連携 (Vision OCR, Drive アップロード)
// ===============================================================

/**
 * Vision API を呼び出してテキストを抽出する
 * @param {string} imageBase64 - Base64エンコードされた画像データ
 * @return {string} 検出されたテキスト
 */
function runOCR(imageBase64) {
  // 設定を読み込み
  if (!CONFIG || !CONFIG.VISION_API_KEY) {
    loadConfig_();
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
            type: 'TEXT_DETECTION'
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
      Logger.log("OCR Success: Text detected.");
      return detectedText;
    } else if (result.responses && result.responses[0].error) {
      Logger.log(`OCR API Error: ${result.responses[0].error.message}`);
      throw new Error(`Vision APIエラー: ${result.responses[0].error.message}`);
    } else {
      Logger.log("OCR Success: No text detected.");
      return "（テキストは検出されませんでした）";
    }
  } catch (error) {
    Logger.log(`runOCR Error: ${error.message}`);
    throw new Error(`OCRの実行に失敗しました: ${error.message}`);
  }
}

/**
 * Google Drive へのアップロード用URLを取得する
 * @param {string} fileName - ファイル名
 * @param {string} mimeType - MIMEタイプ
 * @return {Object} {uploadUrl, fileId}
 */
function getResumableUploadUrl(fileName, mimeType) {
  // 設定を読み込み
  if (!CONFIG || !CONFIG.TEMP_DRIVE_FOLDER_ID) {
    loadConfig_();
  }

  const TEMP_FOLDER_ID = CONFIG.TEMP_DRIVE_FOLDER_ID;

  if (!TEMP_FOLDER_ID || TEMP_FOLDER_ID.includes("...")) {
    throw new Error("サーバー設定エラー: TEMP_DRIVE_FOLDER_ID が未設定です。");
  }

  try {
    const accessToken = ScriptApp.getOAuthToken();

    const metadata = {
      name: fileName,
      parents: [TEMP_FOLDER_ID]
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
      throw new Error(`Drive API Error: ${responseCode} - ${response.getContentText()}`);
    }

    const uploadUrl = response.getHeaders()['Location'];

    const fileIdMatch = uploadUrl.match(/id=([^&]+)/);
    if (!fileIdMatch || !fileIdMatch[1]) {
      throw new Error("アップロードURLからFileIDの抽出に失敗しました。");
    }
    const fileId = fileIdMatch[1];

    Logger.log(`Resumable Upload URL generated for: ${fileName}`);
    return { uploadUrl: uploadUrl, fileId: fileId };

  } catch (error) {
    Logger.log(`getResumableUploadUrl Error: ${error.message}`);
    throw new Error(`アップロードURLの取得に失敗: ${error.message}`);
  }
}
