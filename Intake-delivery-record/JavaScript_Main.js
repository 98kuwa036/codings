<script>
  console.log("✔ [Loaded] JavaScript_Main");
// ===============================================================
// --- ポーリング制御 (Main) ---
// ===============================================================

/**
 * ポーリング（サーバーへの更新確認）の開始・停止を制御します。
 */
function setupPollingController() {
    console.log("setupPollingController: Polling is disabled (Webhook mode).");
    // 旧ポーリング処理はすべて削除
    // checkForUpdates や setInterval はもう不要
}

// ===============================================================
// --- 初期化 (Main) ---
// ===============================================================

/**
 * (★ 修正: エラー処理を UI.js に移管)
 * アプリ起動時に非同期でデータを取得し、UIを初期化します。
 */
async function initialize() {
  // (★ 修正: 待機時間を 0.5秒 に短縮。不要なら削除してもOK)
  await new Promise(r => setTimeout(r, 500)); 
  try {
    console.log("Initialization started...");
    // (UI.js で定義)
    updateLoadingStatus('アプリを起動しています...'); 

    const { uid, n_adm, n_rec, originalUrl } = AUTH_DATA;
    state.originalUrl = originalUrl; 

    // ★ 修正: UI初期化ロジックを UI.js の関数に移動
    initializeFormDefaults(); // (UI.js で定義)

    // イベントリスナーの設定
    updateLoadingStatus('インターフェースを準備中...');
    setupEventListeners(); // (UI.js で定義)

    // サーバーから初期データを取得
    updateLoadingStatus('サーバーからデータを取得中...');
    
    // (Api.js で定義)
    const data = await api.getInitialData(uid, n_adm, n_rec); 

    if (!data) throw new Error("データの取得に失敗しました。");

    // (UI.js で定義)
    updateLoadingStatus('UIを構築しています...');
    
    // ★ 修正: onInitialDataSuccess -> onGetInitialDataSuccess (UI.jsで定義)
    onGetInitialDataSuccess(data); 

    // 完了。メインコンテンツを表示
    updateLoadingStatus('まもなく完了します...');
    showMainContent(); // (UI.js で定義)
    
    console.log("Initialization complete.");

  } catch (error) {
    // ★ 修正: エラー処理を UI.js の showFatalError 関数に移管
    showFatalError(error); // (UI.js で定義)
  }
}

/**
 * (★ 修正: UI.js の onGetInitialDataSuccess が担当するため、
 * この onInitialDataSuccess (空) は不要。削除。)
 */

/**
 * (★ 修正: 汎用エラーハンドラは UI.js の showApiError / showFatalError が
 * 担当するため、この onFailure (DOM操作) は不要。削除。)
 */

/**
 * (変更なし)
 * URLハッシュに基づき、初期ページを決定します。
 * (※ onGetInitialDataSuccess (UI.js) から呼び出される想定)
 */
function handleRouting() {
  const hash = window.location.hash; 
  if (hash === '#page2') { 
    showPage(2); // (UI.js で定義)
  } else { 
    navigateTo(1); // (UI.js で定義)
  }
}

/**
 * (★ 修正: UI初期化ロジックのため UI.js へ移動)
 * (getFormattedDate は UI.js 内の initializeFormDefaults が使用)
 */

</script>
