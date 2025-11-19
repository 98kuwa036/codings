// [ Services.gs ]
// 外部API (Google Cloud Vision など) との連携

/**
 * (Api.js - runOCR)
 * Vision API を呼び出してテキストを抽出する
 */
function runOCR(imageBase64) {
  // ★ 修正: グローバル定数の代わりに Properties を使用
  const VISION_API_KEY = PropertiesService.getScriptProperties().getProperty('VISION_API_KEY');
  if (!VISION_API_KEY) {
    throw new Error("サーバーエラー: Vision APIキー(VISION_API_KEY)が設定されていません。");
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
