/**
 * Googleフォームの回答をトリガーに実行されるメイン関数です。
 * フォームで指定された年月のデータを抽出し、品名を商品コードに変換してCSVとして保存します。
 *
 * 【差分エクスポート機能】
 * - 前回エクスポート日時以降のデータのみを抽出（重複防止）
 * - 月が変わった場合は月初からの全データを取得
 *
 * @param {Object} e - フォーム送信イベントオブジェクト
 */
function onFormSubmit(e) {
  // --- 設定値 ---
  const DATA_SPREADSHEET_ID = "13IsEoCgT9v0-J5TAaCAb_vZyyDMjzv_yXaI5khqvFnY";
  const DATA_SHEET_NAME = "入出庫記録";
  const MASTER_SHEET_NAME = "マスター";
  // --------------------

  if (!e || !e.response) {
    Logger.log("重大エラー: イベントオブジェクト (e) が不正です。");
    return;
  }

  try {
    // --- 1. フォームの回答を受け取る（年・月のみ） ---
    const itemResponses = e.response.getItemResponses();
    if (itemResponses.length < 2) {
      Logger.log("致命的エラー: フォームから年・月の2つの回答が取得できませんでした。");
      return;
    }

    const targetYear = parseInt(itemResponses[0].getResponse(), 10);  // 1問目から「年」を取得
    const targetMonth = parseInt(itemResponses[1].getResponse(), 10); // 2問目から「月」を取得

    if (isNaN(targetYear) || isNaN(targetMonth) || targetMonth < 1 || targetMonth > 12) {
      Logger.log(`集計対象の年月が不正です。年: ${targetYear}, 月: ${targetMonth}`);
      return;
    }

    // --- 2. データの準備（スプレッドシートを開く） ---
    const ss = SpreadsheetApp.openById(DATA_SPREADSHEET_ID);
    const dataSheet = ss.getSheetByName(DATA_SHEET_NAME);
    const masterSheet = ss.getSheetByName(MASTER_SHEET_NAME);

    if (!dataSheet) {
      Logger.log(`エラー: データシートが見つかりません: ${DATA_SHEET_NAME}`);
      return;
    }
    if (!masterSheet) {
      Logger.log(`エラー: マスターシートが見つかりません: ${MASTER_SHEET_NAME}`);
    }

    // --- 3. 前回エクスポート情報の取得 ---
    const scriptProps = PropertiesService.getScriptProperties();
    const lastExportKey = `lastExport_${targetYear}_${targetMonth}`;
    const lastExportDateStr = scriptProps.getProperty(lastExportKey);

    let startDate = null;
    if (lastExportDateStr) {
      startDate = new Date(lastExportDateStr);
      Logger.log(`前回エクスポート日時: ${Utilities.formatDate(startDate, ss.getSpreadsheetTimeZone(), "yyyy/MM/dd HH:mm:ss")}`);
    } else {
      Logger.log("初回エクスポート（月初からのデータを取得）");
    }

    // --- 4. マスターデータの取得と変換マップ作成 ---
    const codeMap = {};
    if (masterSheet) {
        const masterData = masterSheet.getDataRange().getValues();
        for (let i = 1; i < masterData.length; i++) {
            const productCode = masterData[i][1]; // B列: 商品コード
            const productName = String(masterData[i][2]).trim(); // C列: 品名
            if (productName) {
                codeMap[productName] = productCode;
            }
        }
    }

    // --- 5. データ抽出と品名の置換（差分対応） ---
    const allData = dataSheet.getDataRange().getValues();
    if (allData.length <= 1) {
      Logger.log("データがありません。");
      return;
    }

    const headerRow = allData.shift();
    const exportHeader = headerRow.slice(0, 6);

    const filteredData = [];
    const TIMEZONE = ss.getSpreadsheetTimeZone();
    const currentExportDate = new Date(); // 今回のエクスポート日時

    for (const row of allData) {
      const timestamp = row[0]; // A列: タイムスタンプ
      const recordDate = row[1]; // B列: 記録日

      if (recordDate instanceof Date) {
        const rowYear = parseInt(Utilities.formatDate(recordDate, TIMEZONE, "yyyy"), 10);
        const rowMonth = parseInt(Utilities.formatDate(recordDate, TIMEZONE, "M"), 10);

        // 対象年月のデータのみ
        if (rowYear === targetYear && rowMonth === targetMonth) {

          // 差分チェック：前回エクスポート日時より後のデータのみ
          if (startDate && timestamp instanceof Date) {
            if (timestamp <= startDate) {
              continue; // 前回エクスポート済みのデータはスキップ
            }
          }

          const exportRow = row.slice(0, 6);
          const productNameInRecord = String(exportRow[4]).trim(); // E列: 品名

          // 品名を商品コードに置換
          if (productNameInRecord && codeMap[productNameInRecord]) {
              exportRow[4] = codeMap[productNameInRecord];
          }

          filteredData.push(exportRow);
        }
      }
    }

    if (filteredData.length === 0) {
      Logger.log(`該当するデータが見つかりませんでした。（対象年月: ${targetYear}年${targetMonth}月、差分エクスポート対応）`);
      Logger.log("※ 既にすべてのデータがエクスポート済みの可能性があります。");
      return;
    }

    // --- 6. CSVコンテンツの作成 ---
    let csvContent = exportHeader.map(col => `"${String(col).replace(/"/g, '""')}"`).join(',') + '\n';

    csvContent += filteredData.map(row => {
      return row.map((col, colIndex) => {
        let cellValue = col;
        if (col instanceof Date) {
          cellValue = (colIndex === 1)
            ? Utilities.formatDate(col, TIMEZONE, "yyyy-MM-dd")
            : Utilities.formatDate(col, TIMEZONE, "yyyy/MM/dd HH:mm:ss");
        } else if (typeof col === 'string') {
          cellValue = col.replace(/(\r\n|\n|\r)/gm, " ");
        }
        return `"${String(cellValue).replace(/"/g, '""')}"`;
      }).join(',');
    }).join('\n');

    // --- 7. ファイルの作成と保存 ---
    const formId = e.source.getId();
    const formFile = DriveApp.getFileById(formId);
    const parentFolder = formFile.getParents().next();

    // 保存先フォルダを「年」で作成
    const targetFolderName = String(targetYear);
    const folders = parentFolder.getFoldersByName(targetFolderName);
    const exportFolder = folders.hasNext() ? folders.next() : parentFolder.createFolder(targetFolderName);

    // ファイル名を生成
    const month = ('0' + targetMonth).slice(-2);
    const now = new Date();
    const day = Utilities.formatDate(now, 'Asia/Tokyo', 'dd');
    const time = Utilities.formatDate(now, 'Asia/Tokyo', 'HHmm');
    const fileName = `入出庫_${targetYear}-${month}-${day}_${time}.csv`;

    const csvBlob = Utilities.newBlob(csvContent, 'text/csv', fileName);
    const file = exportFolder.createFile(csvBlob);

    Logger.log(`✅ CSVファイルが作成されました: ${file.getName()} (${file.getUrl()})`);
    Logger.log(`📊 エクスポート件数: ${filteredData.length}件`);

    // --- 8. 今回のエクスポート日時を保存 ---
    scriptProps.setProperty(lastExportKey, currentExportDate.toISOString());
    Logger.log(`✅ エクスポート日時を保存しました: ${Utilities.formatDate(currentExportDate, TIMEZONE, "yyyy/MM/dd HH:mm:ss")}`);

  } catch (error) {
    Logger.log("処理中にエラーが発生しました: " + error.toString());
  }
}

/**
 * 【管理用】前回エクスポート情報をリセットする関数
 * 月初や年度初めなど、最初からエクスポートし直したい場合に使用
 *
 * @param {number} year - リセット対象の年
 * @param {number} month - リセット対象の月
 */
function resetExportHistory(year, month) {
  const scriptProps = PropertiesService.getScriptProperties();
  const lastExportKey = `lastExport_${year}_${month}`;
  scriptProps.deleteProperty(lastExportKey);
  Logger.log(`✅ エクスポート履歴をリセットしました: ${year}年${month}月`);
}

/**
 * 【管理用】すべての月のエクスポート履歴を表示
 */
function viewAllExportHistory() {
  const scriptProps = PropertiesService.getScriptProperties();
  const allProps = scriptProps.getProperties();

  Logger.log("=== エクスポート履歴一覧 ===");
  let count = 0;
  for (const key in allProps) {
    if (key.startsWith('lastExport_')) {
      const dateStr = allProps[key];
      const date = new Date(dateStr);
      Logger.log(`${key}: ${Utilities.formatDate(date, 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss')}`);
      count++;
    }
  }
  if (count === 0) {
    Logger.log("エクスポート履歴がありません。");
  }
  Logger.log(`合計: ${count}件`);
}

/**
 * 【管理用】指定年のすべての月のエクスポート履歴をリセット
 *
 * @param {number} year - リセット対象の年
 */
function resetYearExportHistory(year) {
  const scriptProps = PropertiesService.getScriptProperties();
  for (let month = 1; month <= 12; month++) {
    const lastExportKey = `lastExport_${year}_${month}`;
    scriptProps.deleteProperty(lastExportKey);
  }
  Logger.log(`✅ ${year}年のすべてのエクスポート履歴をリセットしました`);
}

//==============================================================================
// HTML管理画面用の関数
//==============================================================================

/**
 * Web アプリとして公開した際の GET リクエスト処理
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('入出庫記録 CSVエクスポート管理')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * 【HTML画面用】CSVエクスポートを実行
 *
 * @param {number} year - 対象年
 * @param {number} month - 対象月
 * @return {Object} 実行結果
 */
function exportCSV(year, month) {
  // --- 設定値 ---
  const DATA_SPREADSHEET_ID = "13IsEoCgT9v0-J5TAaCAb_vZyyDMjzv_yXaI5khqvFnY";
  const DATA_SHEET_NAME = "入出庫記録";
  const MASTER_SHEET_NAME = "マスター";
  const EXPORT_FOLDER_ID = null; // nullの場合はスクリプトと同じフォルダ
  // --------------------

  try {
    const targetYear = parseInt(year, 10);
    const targetMonth = parseInt(month, 10);

    if (isNaN(targetYear) || isNaN(targetMonth) || targetMonth < 1 || targetMonth > 12) {
      throw new Error(`集計対象の年月が不正です。年: ${targetYear}, 月: ${targetMonth}`);
    }

    // データの準備
    const ss = SpreadsheetApp.openById(DATA_SPREADSHEET_ID);
    const dataSheet = ss.getSheetByName(DATA_SHEET_NAME);
    const masterSheet = ss.getSheetByName(MASTER_SHEET_NAME);

    if (!dataSheet) {
      throw new Error(`データシートが見つかりません: ${DATA_SHEET_NAME}`);
    }

    // 前回エクスポート情報の取得
    const scriptProps = PropertiesService.getScriptProperties();
    const lastExportKey = `lastExport_${targetYear}_${targetMonth}`;
    const lastExportDateStr = scriptProps.getProperty(lastExportKey);

    let startDate = null;
    if (lastExportDateStr) {
      startDate = new Date(lastExportDateStr);
      Logger.log(`前回エクスポート日時: ${Utilities.formatDate(startDate, ss.getSpreadsheetTimeZone(), "yyyy/MM/dd HH:mm:ss")}`);
    } else {
      Logger.log("初回エクスポート（月初からのデータを取得）");
    }

    // マスターデータの取得
    const codeMap = {};
    if (masterSheet) {
      const masterData = masterSheet.getDataRange().getValues();
      for (let i = 1; i < masterData.length; i++) {
        const productCode = masterData[i][1];
        const productName = String(masterData[i][2]).trim();
        if (productName) {
          codeMap[productName] = productCode;
        }
      }
    }

    // データ抽出
    const allData = dataSheet.getDataRange().getValues();
    if (allData.length <= 1) {
      throw new Error("データがありません。");
    }

    const headerRow = allData.shift();
    const exportHeader = headerRow.slice(0, 6);
    const filteredData = [];
    const TIMEZONE = ss.getSpreadsheetTimeZone();
    const currentExportDate = new Date();

    for (const row of allData) {
      const timestamp = row[0];
      const recordDate = row[1];

      if (recordDate instanceof Date) {
        const rowYear = parseInt(Utilities.formatDate(recordDate, TIMEZONE, "yyyy"), 10);
        const rowMonth = parseInt(Utilities.formatDate(recordDate, TIMEZONE, "M"), 10);

        if (rowYear === targetYear && rowMonth === targetMonth) {
          if (startDate && timestamp instanceof Date) {
            if (timestamp <= startDate) {
              continue;
            }
          }

          const exportRow = row.slice(0, 6);
          const productNameInRecord = String(exportRow[4]).trim();

          if (productNameInRecord && codeMap[productNameInRecord]) {
            exportRow[4] = codeMap[productNameInRecord];
          }

          filteredData.push(exportRow);
        }
      }
    }

    if (filteredData.length === 0) {
      return {
        success: false,
        message: `該当するデータが見つかりませんでした。既にすべてのデータがエクスポート済みの可能性があります。`,
        count: 0
      };
    }

    // CSVコンテンツの作成
    let csvContent = exportHeader.map(col => `"${String(col).replace(/"/g, '""')}"`).join(',') + '\n';

    csvContent += filteredData.map(row => {
      return row.map((col, colIndex) => {
        let cellValue = col;
        if (col instanceof Date) {
          cellValue = (colIndex === 1)
            ? Utilities.formatDate(col, TIMEZONE, "yyyy-MM-dd")
            : Utilities.formatDate(col, TIMEZONE, "yyyy/MM/dd HH:mm:ss");
        } else if (typeof col === 'string') {
          cellValue = col.replace(/(\r\n|\n|\r)/gm, " ");
        }
        return `"${String(cellValue).replace(/"/g, '""')}"`;
      }).join(',');
    }).join('\n');

    // ファイルの作成と保存
    let exportFolder;
    if (EXPORT_FOLDER_ID) {
      exportFolder = DriveApp.getFolderById(EXPORT_FOLDER_ID);
    } else {
      // スクリプトファイルと同じフォルダに保存
      const scriptFile = DriveApp.getFileById(ScriptApp.getScriptId());
      exportFolder = scriptFile.getParents().next();
    }

    // 年フォルダを作成
    const targetFolderName = String(targetYear);
    const folders = exportFolder.getFoldersByName(targetFolderName);
    const yearFolder = folders.hasNext() ? folders.next() : exportFolder.createFolder(targetFolderName);

    // ファイル名を生成
    const month_str = ('0' + targetMonth).slice(-2);
    const now = new Date();
    const day = Utilities.formatDate(now, 'Asia/Tokyo', 'dd');
    const time = Utilities.formatDate(now, 'Asia/Tokyo', 'HHmm');
    const fileName = `入出庫_${targetYear}-${month_str}-${day}_${time}.csv`;

    const csvBlob = Utilities.newBlob(csvContent, 'text/csv', fileName);
    const file = yearFolder.createFile(csvBlob);

    Logger.log(`✅ CSVファイルが作成されました: ${file.getName()}`);
    Logger.log(`📊 エクスポート件数: ${filteredData.length}件`);

    // エクスポート日時を保存
    scriptProps.setProperty(lastExportKey, currentExportDate.toISOString());

    return {
      success: true,
      fileName: fileName,
      fileUrl: file.getUrl(),
      count: filteredData.length
    };

  } catch (error) {
    Logger.log("エラー: " + error.toString());
    throw error;
  }
}

/**
 * 【HTML画面用】すべてのエクスポート履歴を取得
 *
 * @return {Array} 履歴の配列
 */
function getAllExportHistory() {
  const scriptProps = PropertiesService.getScriptProperties();
  const allProps = scriptProps.getProperties();

  const history = [];
  for (const key in allProps) {
    if (key.startsWith('lastExport_')) {
      const parts = key.replace('lastExport_', '').split('_');
      const year = parts[0];
      const month = parts[1];
      const dateStr = allProps[key];
      const date = new Date(dateStr);

      history.push({
        yearMonth: `${year}年${month}月`,
        dateTime: Utilities.formatDate(date, 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss')
      });
    }
  }

  // 年月でソート
  history.sort((a, b) => {
    const aMatch = a.yearMonth.match(/(\d+)年(\d+)月/);
    const bMatch = b.yearMonth.match(/(\d+)年(\d+)月/);
    const aVal = parseInt(aMatch[1]) * 100 + parseInt(aMatch[2]);
    const bVal = parseInt(bMatch[1]) * 100 + parseInt(bMatch[2]);
    return bVal - aVal; // 降順
  });

  return history;
}
