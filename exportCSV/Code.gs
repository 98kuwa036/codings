/**
 * Googleフォームの回答をトリガーに実行されるメイン関数です。
 * フォームで指定された年月のデータを抽出し、品名を商品コードに変換してCSVとして保存します。
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

    // --- 3. マスターデータの取得と変換マップ作成 ---
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

    // --- 4. データ抽出と品名の置換 ---
    const allData = dataSheet.getDataRange().getValues();
    if (allData.length <= 1) {
      Logger.log("データがありません。");
      return;
    }

    const headerRow = allData.shift();
    const exportHeader = headerRow.slice(0, 6); 

    const filteredData = [];
    const TIMEZONE = ss.getSpreadsheetTimeZone();
    
    for (const row of allData) {
      const recordDate = row[1]; // B列: 記録日
      
      if (recordDate instanceof Date) {
        const rowYear = parseInt(Utilities.formatDate(recordDate, TIMEZONE, "yyyy"), 10);
        const rowMonth = parseInt(Utilities.formatDate(recordDate, TIMEZONE, "M"), 10);

        if (rowYear === targetYear && rowMonth === targetMonth) {
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
      Logger.log(`該当するデータが見つかりませんでした。（対象年月: ${targetYear}年${targetMonth}月）`);
      return;
    }

    // --- 5. CSVコンテンツの作成 ---
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

    // --- 6. ファイルの作成と保存 ---
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
    const day = Utilities.formatDate(now, 'Asia/Tokyo', 'dd')
    const fileName = `入出庫_${targetYear}-${month}-${day}.csv`;

    const csvBlob = Utilities.newBlob(csvContent, 'text/csv', fileName);
    const file = exportFolder.createFile(csvBlob);
    
    Logger.log(`✅ CSVファイルが作成されました: ${file.getName()} (${file.getUrl()})`);

  } catch (error) {
    Logger.log("処理中にエラーが発生しました: " + error.toString());
  }
}
