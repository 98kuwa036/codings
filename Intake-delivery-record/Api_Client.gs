function getInitialData(uid, n_adm, n_rec) {
  // ★ 修正: CONFIG をロード (doGetでロード済みだが念のため)
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_(); // (Config.gs)
  }

  try {
    // 1. Nonce (リプレイ攻撃防止) を検証 (Auth.gs)
    // (★ 21:13 のお手本 `doGet` は n_rec しか検証していない)
    // (※ 21:13 の `doGet` が既に `validateNonce(n_rec)` を実行済みのため、
    //   `getInitialData` での二重検証は不要)
    // if (!validateNonce(n_rec)) { 
    //   throw new Error("無効なリクエストです (Invalid Nonce)。");
    // }
    
    // 2. ユーザー情報とロールを取得 (Utils.gs)
    const currentUserInfo = getUserInfo_(uid);

    // 3. UI設定を取得 (Triggers.gs)
    const settings = getUiSettingsData_();

    // 4. ドロップダウンデータを取得 (Triggers.gs)
    const dropdownData = getDropdownData_();
    
    // 5. 管理者ページへのリンクを生成 (Utils.gs)
    const adminLink = (currentUserInfo.role === 'SuperAdmin' || currentUserInfo.role === 'Admin')
      ? generateAdminPageUrl_(uid) 
      : null;

    // 6. データをクライアントに返す
    return {
      users: dropdownData.users,
      items: dropdownData.items,
      adminLink: adminLink,
      currentUserInfo: currentUserInfo,
      settings: settings
    };

  } catch (error) {
    Logger.log(`getInitialData Error: ${error.message}`);
    throw new Error(`初期データの取得に失敗しました: ${error.message}`);
  }
}

/**
 * (Api.js - acceptRegistrationData)
 * ★★★ 修正: ファイル移動＆リネーム処理を追加 ★★★
 */
function acceptRegistrationData(formData, fileId) {
  // ★ 修正: CONFIG をロード
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_(); // (Config.gs)
  }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    throw new Error("サーバーが混み合っています。少し待ってから再度お試しください。");
  }

  try {
    const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
    const historySheet = ss.getSheetByName(CONFIG.SHEETS.HISTORY);
    if (!historySheet) throw new Error(`シートが見つかりません: ${CONFIG.SHEETS.HISTORY}`);

    const timestamp = new Date();
    const rowsToAdd = [];
    const { registrant, date, mode, items } = formData;
    let finalFileUrl = "";

    // (入庫モードでファイルありの場合)
    if (fileId) {
      // ★ 1. ファイルをリネームして移動
      const FINAL_FOLDER_ID = CONFIG.FINAL_DRIVE_FOLDER_ID;
      if (!FINAL_FOLDER_ID || FINAL_FOLDER_ID.includes("...")) {
        throw new Error("最終保存先フォルダID(FINAL_DRIVE_FOLDER_ID)が未設定です。");
      }
      
      const file = DriveApp.getFileById(fileId);
      // ★ 修正: createFileName_ をこのファイル内に定義
      const newName = createFileName_(timestamp, registrant, formData.voucherNumber, file.getName()); 
      
      file.setName(newName);
      file.moveTo(DriveApp.getFolderById(FINAL_FOLDER_ID));
      
      finalFileUrl = file.getUrl();
      
      // ★ 2. ログシートに書き込む行を準備 (G列まで)
      rowsToAdd.push([
        timestamp,
        mode, // "inbound"
        date,
        registrant,
        "（伝票）", // 品名
        formData.voucherNumber || newName, // 個数欄に伝票番号
        finalFileUrl // G列 (★ URLを保存)
      ]);
    }
    
    // (品目リスト)
    items.forEach(item => {
      rowsToAdd.push([
        timestamp,
        mode,
        date,
        registrant,
        item.name,
        item.quantity,
        "" // G列 (URLなし)
      ]);
    });

    if (rowsToAdd.length > 0) {
      // ★ 修正: G列 (7列) まで書き込む
      const numColumns = 7; 
      historySheet.insertRowsAfter(1, rowsToAdd.length);
      historySheet.getRange(2, 1, rowsToAdd.length, numColumns).setValues(rowsToAdd);
    }
    
    Logger.log(`Registration Accepted: ${rowsToAdd.length} rows added by ${registrant}`);
    return { success: true, message: `登録が完了しました。(処理 ${rowsToAdd.length} 件)` };

  } catch (error) {
    Logger.log(`acceptRegistrationData Error: ${error.message}`);
    throw new Error(`データ書き込みエラー: ${error.message}`);
  } finally {
    lock.releaseLock();
  }
}

/**
 * (★ 移管) 伝票ファイル名を生成する (Utils.gs から移管)
 */
function createFileName_(timestamp, registrant, voucherNumber, originalFileName) {
  try {
    const yyyy = timestamp.getFullYear();
    const mm = (timestamp.getMonth() + 1).toString().padStart(2, '0');
    const dd = timestamp.getDate().toString().padStart(2, '0');
    const hh = timestamp.getHours().toString().padStart(2, '0');
    const min = timestamp.getMinutes().toString().padStart(2, '0');
    
    const safeRegistrant = registrant.replace(/[^a-zA-Z0-9\u3000-\u9FFF\u3040-\u309F\u30A0-\u30FF]/g, '_');
    const safeVoucher = voucherNumber.replace(/[^a-zA-Z0-9]/g, '-');
    
    // ★ 修正: 元のファイルの拡張子を保持する
    const extensionMatch = originalFileName.match(/\.([^.]+)$/);
    const extension = (extensionMatch && extensionMatch[1]) ? `.${extensionMatch[1]}` : '.jpg'; // デフォルト.jpg
    
    return `${yyyy}-${mm}-${dd}_${hh}${min}_${safeRegistrant}_${safeVoucher || '伝票'}${extension}`;
  } catch(e) {
    return `file_${timestamp.getTime()}.jpg`;
  }
}

/**
 * (Api.js - saveTemporaryItem)
 * 仮登録物品を「一時作業」シートに書き込む
 */
function saveTemporaryItem(itemData) {
  // ★ 修正: CONFIG をロード
  if (!CONFIG || !CONFIG.SPREADSHEET_ID) {
    loadConfig_(); // (Config.gs)
  }
  
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    throw new Error("サーバーが混み合っています。");
  }
  try {
    const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
    const queueSheet = ss.getSheetByName(CONFIG.SHEETS.PROCESSING_QUEUE);
    if (!queueSheet) throw new Error(`シートが見つかりません: ${CONFIG.SHEETS.PROCESSING_QUEUE}`);

    queueSheet.appendRow([
      new Date(),       // A: タイムスタンプ
      itemData.code,    // B: コード (JANなど)
      itemData.name,    // C: 品名
      itemData.category,// D: カテゴリ
      itemData.registrant, // E: 登録者
      'Pending'         // F: ステータス
    ]);
    
    Logger.log(`Temporary Item Saved: ${itemData.name} by ${itemData.registrant}`);
    return { success: true, message: "物品の仮登録を申請しました。管理者の承認をお待ちください。" };

  } catch (error) {
    Logger.log(`saveTemporaryItem Error: ${error.message}`);
    throw new Error(`仮登録エラー: ${error.message}`);
  } finally {
    lock.releaseLock();
  }
}
