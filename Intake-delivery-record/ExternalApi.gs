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

  // Base64データを抽出（data:image/jpeg;base64, のプレフィックスを除去）
  let base64Content;
  if (imageBase64.includes(',')) {
    base64Content = imageBase64.split(',')[1];
  } else {
    base64Content = imageBase64;
  }

  Logger.log(`OCR開始: Base64データサイズ = ${base64Content.length} 文字`);

  const payload = {
    requests: [
      {
        image: {
          content: base64Content
        },
        features: [
          {
            type: 'TEXT_DETECTION',
            maxResults: 10
          }
        ],
        imageContext: {
          languageHints: ["ja", "en"] // 日本語と英語をヒントにする
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
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    Logger.log(`Vision API Response Code: ${responseCode}`);

    if (responseCode !== 200) {
      Logger.log(`Vision API Error Response: ${responseText}`);
      throw new Error(`Vision APIがエラーを返しました (HTTP ${responseCode}): ${responseText.substring(0, 200)}`);
    }

    const result = JSON.parse(responseText);

    // レスポンス全体をログ出力（デバッグ用）
    Logger.log(`Vision API Response: ${JSON.stringify(result).substring(0, 500)}`);

    if (result.responses && result.responses[0]) {
      const firstResponse = result.responses[0];

      // エラーチェック
      if (firstResponse.error) {
        Logger.log(`OCR API Error: ${JSON.stringify(firstResponse.error)}`);
        throw new Error(`Vision APIエラー: ${firstResponse.error.message} (コード: ${firstResponse.error.code})`);
      }

      // テキスト検出結果
      if (firstResponse.fullTextAnnotation && firstResponse.fullTextAnnotation.text) {
        const detectedText = firstResponse.fullTextAnnotation.text;
        Logger.log(`OCR Success: ${detectedText.length}文字のテキストを検出`);
        Logger.log(`検出テキスト(最初の100文字): ${detectedText.substring(0, 100)}`);
        return detectedText;
      } else if (firstResponse.textAnnotations && firstResponse.textAnnotations.length > 0) {
        // fullTextAnnotation が無い場合は textAnnotations を使用
        const detectedText = firstResponse.textAnnotations[0].description;
        Logger.log(`OCR Success (textAnnotations): ${detectedText.length}文字のテキストを検出`);
        return detectedText;
      } else {
        Logger.log("OCR Success: テキストが検出されませんでした");
        Logger.log(`Response詳細: ${JSON.stringify(firstResponse)}`);
        return "（テキストは検出されませんでした。画像が不鮮明か、テキストが含まれていない可能性があります）";
      }
    } else {
      Logger.log(`予期しないレスポンス形式: ${responseText}`);
      throw new Error("Vision APIから予期しないレスポンス形式が返されました");
    }
  } catch (error) {
    Logger.log(`runOCR Error: ${error.message}`);
    Logger.log(`Error Stack: ${error.stack}`);
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
