// ===============================================================
// [ Admin_Approval.gs ]
// 仮登録の承認ワークフロー
// ===============================================================

/**
 * (G) 「一時作業」シートから "Pending" 状態のデータを読み込む
 */
function getPendingItems() {
  ensureConfigLoaded_(); // ★ 追加

  try {
    const ss = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID);
    const sheet = ss.getSheetByName(ADMIN_CONFIG.SHEETS.PROCESSING_QUEUE);
    
    if (!sheet) {
      return JSON.stringify([['エラー', `シート "${ADMIN_CONFIG.SHEETS.PROCESSING_QUEUE}" が見つかりません。`]]);
    }
    
    const lastRow = sheet.getLastRow();
    if (lastRow < 2) {
      return JSON.stringify([['承認待ちのデータはありません。']]);
    }
    
    const data = sheet.getRange(1, 1, lastRow, 6).getValues(); // A列からF列まで取得
    
    const headers = [data[0][0], data[0][1], data[0][2], data[0][3], data[0][4], "操作"]; // F列を「操作」に変更
    const pendingItems = [headers];
    
    for (let i = 1; i < data.length; i++) {
      if (data[i][5] === 'Pending') {
        pendingItems.push([data[i][0], data[i][1], data[i][2], data[i][3], data[i][4], i + 1]); // F列の代わりに「行番号」を渡す
      }
    }

    if (pendingItems.length <= 1) {
      return JSON.stringify([['承認待ちのデータはありません。']]);
    }

    return JSON.stringify(pendingItems);
    
  } catch (e) {
    Logger.log(`getPendingItems (Catch Error): ${e.message}`);
    return JSON.stringify([['エラー', e.message]]);
  }
}

/**
 * (G) 承認待ちアイテムを「承認」する
 * (★ 自動採番ロジック組み込み ★)
 */
function approveItem(rowNum, itemData, authInfo) { 
  ensureConfigLoaded_(); // ★ 追加

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    throw new Error("他の処理が実行中のため、承認（ロック取得）に失敗しました。");
  }
  
  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';

  try {
    const ss = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID);
    const masterSheet = ss.getSheetByName(ADMIN_CONFIG.SHEETS.MASTER);
    const queueSheet = ss.getSheetByName(ADMIN_CONFIG.SHEETS.PROCESSING_QUEUE);

    if (!masterSheet || !queueSheet) {
      throw new Error("必要なシート（マスターまたは一時作業）が見つかりません。");
    }

    // 1. カテゴリ名から新しい管理番号を生成
    const newManagementId = generateNewManagementId(itemData.category);

    // 2. マスターシート に追加
    masterSheet.appendRow([
      newManagementId,
      itemData.name || '',
      itemData.category || '',
      'Active'
    ]);

    // 3. 一時作業 シートのステータスを "Approved" に変更 (F列 / index 5)
    queueSheet.getRange(rowNum, 6).setValue("Approved");

    // 4. 記録ツールに「マスター更新あり」と通知
    notifyRecordApp_('dropdown_data');

    const successMsg = `「${itemData.name}」を管理番号 ${newManagementId} でマスターに登録しました。`;
    writeLog_([successMsg], {
      functionName: "approveItem",
      status: "Success",
      message: `(Row: ${rowNum}, Name: ${itemData.name}, NewID: ${newManagementId})`,
      editorName: editorName
    });
    
    return { success: true, message: successMsg };

  } catch (e) {
    writeLog_([`approveItem Error: ${e.message}`], { /* ... */ });
    throw new Error(`承認エラー: ${e.message}`);
  } finally {
    lock.releaseLock();
  }
}

/**
 * (G) 承認待ちアイテムを「拒否」（削除）する
 */
function rejectItem(rowNum, itemData, authInfo) { 
  ensureConfigLoaded_(); // ★ 追加

  const editorName = (authInfo && authInfo.name) ? authInfo.name : 'N/A';
  const itemName = (itemData && itemData.name) ? itemData.name : `Row ${rowNum}`;

  try {
    const ss = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID);
    const queueSheet = ss.getSheetByName(ADMIN_CONFIG.SHEETS.PROCESSING_QUEUE);

    if (!queueSheet) {
      throw new Error("シート「一時作業」が見つかりません。");
    }

    queueSheet.getRange(rowNum, 6).setValue("Rejected");
    
    const successMsg = `行番号 ${rowNum} の仮登録を拒否（削除）しました。`;
    writeLog_([successMsg], {
      functionName: "rejectItem",
      status: "Success",
      message: `(Row: ${rowNum}, Name: ${itemName})`,
      editorName: editorName
    });
    
    return { success: true, message: successMsg };

  } catch (e) {
    writeLog_([`rejectItem Error: ${e.message}`], { /* ... */ });
    throw new Error(`拒否エラー: ${e.message}`);
  }
}


/**
 * 【★★★ Record Tool からコピー ★★★】
 * カテゴリ名から次の管理番号を生成します。
 */
function generateNewManagementId(categoryName) {
  ensureConfigLoaded_(); // ★ 追加（念のため）

  const categoryPrefixMap = {
    "劇薬薬品": "A",
    "普通薬品": "B",
    "治療用資材": "C",
    "繁殖用資材": "D",
    "点滴用資材": "E",
    "飼料添加物": "F",
    "消耗品": "G",
    "その他": "H"
  };

  const prefix = categoryPrefixMap[categoryName];
  if (!prefix) {
    throw new Error(`カテゴリ「${categoryName}」に対応する管理番号頭文字(A～G)が定義されていません。`);
  }

  const ss = SpreadsheetApp.openById(ADMIN_CONFIG.SPREADSHEET_ID);
  const masterSheetName = ADMIN_CONFIG.SHEETS.MASTER;
  const idColumnIndex = 1; // A列
  
  const sheet = ss.getSheetByName(masterSheetName);
  if (!sheet) {
    throw new Error(`エラー: マスターシート「${masterSheetName}」が見つかりません。`);
  }
  
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    return prefix + "001";
  }
  
  const idRange = sheet.getRange(2, idColumnIndex, lastRow - 1, 1);
  const idValues = idRange.getValues().flat();

  let maxNum = 0;
  idValues.forEach(id => {
    if (id && typeof id === 'string' && id.startsWith(prefix)) {
      const numPartStr = id.substring(prefix.length);
      const numPart = parseInt(numPartStr, 10);
      if (!isNaN(numPart) && numPart > maxNum) {
        maxNum = numPart;
      }
    }
  });

  const newNum = maxNum + 1;
  const newId = prefix + String(newNum).padStart(3, '0'); 

  Logger.log(`generateNewManagementId: カテゴリ「${categoryName}」(Prefix: ${prefix}) の最大値 ${maxNum} -> 新規ID ${newId}`);
  return newId;
}
