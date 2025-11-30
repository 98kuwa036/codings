/**
 * OCR Helper using Tesseract.js
 * Tesseract.jsを使用したオフラインOCR機能
 */

class OCRHelper {
  constructor() {
    this.worker = null;
    this.isInitialized = false;
    this.isProcessing = false;
  }

  /**
   * Tesseract.js初期化
   */
  async initialize() {
    if (this.isInitialized) {
      return;
    }

    try {
      console.log('[OCR] Initializing Tesseract.js...');

      // Tesseract.jsがロードされているか確認
      if (typeof Tesseract === 'undefined') {
        throw new Error('Tesseract.js is not loaded. Please include the script.');
      }

      // ワーカー作成
      this.worker = await Tesseract.createWorker('jpn', 1, {
        logger: (m) => {
          console.log('[OCR]', m);
        }
      });

      this.isInitialized = true;
      console.log('[OCR] Initialization complete');
    } catch (error) {
      console.error('[OCR] Initialization failed:', error);
      throw error;
    }
  }

  /**
   * 画像からテキストを抽出
   * @param {File|Blob|string} image - 画像ファイル、Blob、またはData URL
   * @param {Object} options - オプション設定
   * @returns {Promise<Object>} - 抽出結果
   */
  async extractText(image, options = {}) {
    if (this.isProcessing) {
      throw new Error('OCR processing is already in progress');
    }

    this.isProcessing = true;

    try {
      // 初期化されていない場合は初期化
      if (!this.isInitialized) {
        await this.initialize();
      }

      console.log('[OCR] Starting text extraction...');

      // 画像を認識
      const result = await this.worker.recognize(image, {
        ...options
      });

      console.log('[OCR] Text extraction complete');
      console.log('[OCR] Confidence:', result.data.confidence);

      return {
        text: result.data.text.trim(),
        confidence: result.data.confidence,
        lines: result.data.lines.map(line => ({
          text: line.text,
          confidence: line.confidence,
          bbox: line.bbox
        })),
        words: result.data.words.map(word => ({
          text: word.text,
          confidence: word.confidence,
          bbox: word.bbox
        }))
      };
    } catch (error) {
      console.error('[OCR] Text extraction failed:', error);
      throw error;
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * ファイルからテキスト抽出（ヘルパーメソッド）
   */
  async extractFromFile(file, progressCallback = null) {
    if (!file || !file.type.startsWith('image/')) {
      throw new Error('Invalid file type. Please provide an image file.');
    }

    // ファイルサイズチェック（10MB以上は警告）
    const sizeMB = file.size / 1024 / 1024;
    if (sizeMB > 10) {
      console.warn(`[OCR] Large file size: ${sizeMB.toFixed(2)}MB`);

      if (progressCallback) {
        progressCallback({
          type: 'warning',
          message: `警告: 画像サイズが${sizeMB.toFixed(1)}MBと大きいです。処理に時間がかかる場合があります。`
        });
      }
    }

    // 進行状況コールバック設定
    if (progressCallback) {
      progressCallback({
        type: 'progress',
        message: '読み取り中...',
        progress: 0
      });
    }

    try {
      const result = await this.extractText(file);

      if (progressCallback) {
        progressCallback({
          type: 'complete',
          message: 'テキスト抽出完了',
          progress: 100
        });
      }

      return result;
    } catch (error) {
      if (progressCallback) {
        progressCallback({
          type: 'error',
          message: 'OCRエラーが発生しました',
          error
        });
      }
      throw error;
    }
  }

  /**
   * テキスト抽出結果のクリーニング（品名用）
   */
  cleanExtractedText(text) {
    if (!text) {
      return '';
    }

    // 改行を統一
    let cleaned = text.replace(/\r\n/g, '\n');

    // 連続する空白を1つに
    cleaned = cleaned.replace(/[ \t]+/g, ' ');

    // 前後の空白削除
    cleaned = cleaned.trim();

    return cleaned;
  }

  /**
   * ワーカー終了
   */
  async terminate() {
    if (this.worker) {
      await this.worker.terminate();
      this.worker = null;
      this.isInitialized = false;
      console.log('[OCR] Worker terminated');
    }
  }

  /**
   * 処理状態取得
   */
  getStatus() {
    return {
      isInitialized: this.isInitialized,
      isProcessing: this.isProcessing
    };
  }
}

// グローバルインスタンス
const ocrHelper = new OCRHelper();

/**
 * オンライン/オフラインOCRマネージャー
 * オンライン時はGoogle Vision API、オフライン時はTesseract.jsを使用
 */
class OCRManager {
  constructor() {
    this.preferOnline = true; // オンライン優先
  }

  /**
   * OCR実行（オンライン/オフライン自動切り替え）
   */
  async performOCR(file, options = {}) {
    const isOnline = navigator.onLine;

    if (isOnline && this.preferOnline && options.visionApiAvailable) {
      // オンライン時でGoogle Vision APIが利用可能な場合
      try {
        return await this.performOnlineOCR(file, options);
      } catch (error) {
        console.warn('[OCR] Online OCR failed, falling back to offline OCR:', error);
        // オンラインOCRが失敗した場合はオフラインOCRにフォールバック
        return await this.performOfflineOCR(file, options.progressCallback);
      }
    } else {
      // オフライン時またはVision API未設定の場合
      return await this.performOfflineOCR(file, options.progressCallback);
    }
  }

  /**
   * オンラインOCR（Google Vision API）
   */
  async performOnlineOCR(file, options) {
    if (typeof google !== 'undefined' && google.script && google.script.run) {
      // GAS環境での実行
      return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = (e) => {
          const base64Image = e.target.result.split(',')[1];

          google.script.run
            .withSuccessHandler((result) => {
              resolve({
                text: result.text || '',
                confidence: result.confidence || 0,
                source: 'google-vision'
              });
            })
            .withFailureHandler((error) => {
              reject(new Error(error.message || 'Vision API call failed'));
            })
            .performOCR(base64Image);
        };

        reader.onerror = () => reject(new Error('File read failed'));
        reader.readAsDataURL(file);
      });
    } else {
      throw new Error('Google Apps Script environment not available');
    }
  }

  /**
   * オフラインOCR（Tesseract.js）
   */
  async performOfflineOCR(file, progressCallback) {
    const result = await ocrHelper.extractFromFile(file, progressCallback);

    return {
      text: ocrHelper.cleanExtractedText(result.text),
      confidence: result.confidence,
      source: 'tesseract',
      lines: result.lines,
      words: result.words
    };
  }

  /**
   * オンライン優先設定
   */
  setPreferOnline(prefer) {
    this.preferOnline = prefer;
  }
}

// グローバルインスタンス
const ocrManager = new OCRManager();
