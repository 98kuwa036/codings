<script>
  console.log("✔ [Loaded] JavaScript_Api");
// ===============================================================
// --- APIラッパー (Promiseベース) ---
// ===============================================================

/**
 * google.script.run を Promise でラップする
 * @param {string} funcName 呼び出すGAS側の関数名
 * @param {...any} args 関数に渡す引数
 * @returns {Promise<any>} 実行結果
 */
function runAsync(funcName, ...args) {
    return new Promise((resolve, reject) => {
        google.script.run
            .withSuccessHandler(resolve)
            .withFailureHandler(reject)
            [funcName](...args);
    });
}

/**
 * API呼び出しをオブジェクトにまとめる
 */
const api = {
    /**
     * [Main.js が使用] 初期データを取得する
     */
    getInitialData: (uid, n_adm, n_rec) => {
        return runAsync('getInitialData', uid, n_adm, n_rec);
    },

    // ▼▼▼ 修正: 以下のポーリング用関数は不要なため削除 ▼▼▼
    // /**
    //  * [checkForUpdates が使用] UI設定の更新を確認
    //  */
    // checkForUiUpdates: () => {
    //     return runAsync('checkForUiUpdates');
    // },
    //
    // /**
    //  * [checkForUpdates が使用] ドロップダウンの更新を確認
    //  */
    // checkForDropdownUpdates: () => {
    //     return runAsync('checkForDropdownUpdates');
    // },
    // ▲▲▲ 修正ここまで ▲▲▲

    /**
     * [UI.js (handleSubmitRegistration) が使用] アップロードURLを取得
     */
    getResumableUploadUrl: (fileName, mimeType) => {
        return runAsync('getResumableUploadUrl', fileName, mimeType);
    },

    /**
     * [UI.js (handleSubmitRegistration) が使用] 登録データを送信
     */
    acceptRegistrationData: (formData, fileId) => {
        return runAsync('acceptRegistrationData', formData, fileId);
    },

    /**
     * [UI.js (handleSubmitTemporaryRegistration) が使用] 仮物品を登録
     */
    saveTemporaryItem: (itemData) => {
        return runAsync('saveTemporaryItem', itemData);
    }
};

// ===============================================================
// --- サーバー通信 (ポーリング) ---
// ===============================================================

// ▼▼▼ 修正: 以下のポーリング関連関数はすべて不要なため削除 ▼▼▼
// async function checkForUpdates() { ... }
// function onSettingsUpdated(response) { ... }
// function onDropdownUpdated(response) { ... }
// ▲▲▲ 修正ここまで ▲▲▲


// ===============================================================
// --- データ送信 ---
// ===============================================================

// (データ送信関連の関数 (submitRegistration など) は
//  すべて UI.js に移管済みのため、ここには何もないのが正しい状態です)

</script>
