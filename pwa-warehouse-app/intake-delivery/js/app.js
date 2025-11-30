// ===============================================================
// PWA倉庫管理システム - 入出庫記録アプリ
// ===============================================================

// GAS API エンドポイント
const GAS_INTAKE_API_URL = 'https://script.google.com/macros/s/AKfycbxnm6ga-jK6MZ6IYI83RwVcEoSssZCIueiuf0LIfKmlFOtR-pbS0hCg2Q52TLHvDDtJ9A/exec';

// ===============================================================
// 多言語対応
// ===============================================================
const TRANSLATIONS = {
    ja: {
        loading: 'アプリを起動しています...',
        title_outbound: '出庫登録ツール',
        title_inbound: '入庫登録ツール',
        label_registrant: '担当者名',
        label_date: '日付',
        btn_next: '次へ進む',
        btn_mode_outbound: '入庫',
        btn_mode_inbound: '出庫',
        label_item_name: '品名',
        label_quantity: '個数',
        btn_add_item: '品目を追加',
        heading_added_items: '追加済みリスト',
        btn_confirm: '内容を確認する',
        btn_back: '戻る',
        heading_confirmation: '確認画面',
        label_confirm_registrant: '登録者名',
        label_confirm_date: '日付',
        label_confirm_mode_outbound: '出庫品目',
        label_confirm_mode_inbound: '入庫品目',
        btn_register: 'この内容で登録する',
        btn_edit: '修正する',
        success_title: '登録完了',
        success_message: 'データの登録が正常に完了しました。',
        btn_new_entry: '新しい記録を追加する',
        msg_no_items_added: '品目が追加されていません。',
        msg_registering: '登録処理中...',
        offline_notice: 'オフラインモード - データは後で同期されます',
        online_notice: 'オンラインに復帰しました',
        sync_pending: '同期待ち',
        synced: '同期済み'
    },
    en: {
        loading: 'Starting application...',
        title_outbound: 'Inventory Release Tool',
        title_inbound: 'Inventory Receipt Tool',
        label_registrant: 'Person in Charge',
        label_date: 'Date',
        btn_next: 'Next',
        btn_mode_outbound: 'Inbound',
        btn_mode_inbound: 'Outbound',
        label_item_name: 'Item Name',
        label_quantity: 'Quantity',
        btn_add_item: 'Add Item',
        heading_added_items: 'Added List',
        btn_confirm: 'Confirm',
        btn_back: 'Back',
        heading_confirmation: 'Confirmation',
        label_confirm_registrant: 'Registered By',
        label_confirm_date: 'Date',
        label_confirm_mode_outbound: 'Outbound Items',
        label_confirm_mode_inbound: 'Inbound Items',
        btn_register: 'Register',
        btn_edit: 'Edit',
        success_title: 'Registration Complete',
        success_message: 'Data has been registered successfully.',
        btn_new_entry: 'Add New Record',
        msg_no_items_added: 'No items added.',
        msg_registering: 'Registering...',
        offline_notice: 'Offline Mode - Data will sync later',
        online_notice: 'Back Online',
        sync_pending: 'Pending Sync',
        synced: 'Synced'
    },
    id: {
        loading: 'Memulai aplikasi...',
        title_outbound: 'Alat Pencatatan Pengeluaran',
        title_inbound: 'Alat Pencatatan Penerimaan',
        label_registrant: 'Penanggung Jawab',
        label_date: 'Tanggal',
        btn_next: 'Lanjut',
        btn_mode_outbound: 'Masuk',
        btn_mode_inbound: 'Keluar',
        label_item_name: 'Nama Item',
        label_quantity: 'Jumlah',
        btn_add_item: 'Tambah Item',
        heading_added_items: 'Daftar Ditambahkan',
        btn_confirm: 'Konfirmasi',
        btn_back: 'Kembali',
        heading_confirmation: 'Konfirmasi',
        label_confirm_registrant: 'Didaftarkan Oleh',
        label_confirm_date: 'Tanggal',
        label_confirm_mode_outbound: 'Item Keluar',
        label_confirm_mode_inbound: 'Item Masuk',
        btn_register: 'Daftarkan',
        btn_edit: 'Edit',
        success_title: 'Pendaftaran Selesai',
        success_message: 'Data telah berhasil didaftarkan.',
        btn_new_entry: 'Tambah Catatan Baru',
        msg_no_items_added: 'Tidak ada item yang ditambahkan.',
        msg_registering: 'Mendaftarkan...',
        offline_notice: 'Mode Offline - Data akan disinkronkan nanti',
        online_notice: 'Kembali Online',
        sync_pending: 'Menunggu Sinkronisasi',
        synced: 'Tersinkronisasi'
    }
};

// 現在の言語
let currentLang = 'ja';

// 言語切り替え関数
function switchLanguage(lang) {
    currentLang = lang;
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-lang') === lang) {
            btn.classList.add('active');
        }
    });
    updateUILanguage();
}

// UI言語を更新
function updateUILanguage() {
    const t = TRANSLATIONS[currentLang];
    document.getElementById('loading-status-text').textContent = t.loading;
    document.getElementById('main-title').textContent = state.mode === 'inbound' ? t.title_inbound : t.title_outbound;
    document.getElementById('toggle-mode-button').textContent = state.mode === 'outbound' ? t.btn_mode_outbound : t.btn_mode_inbound;
}

// ===============================================================
// グローバル状態
// ===============================================================
const state = {
    mode: 'outbound', // outbound または inbound
    items: [],
    userName: null
};

// ===============================================================
// DOM要素のキャッシュ
// ===============================================================
const dom = {
    statusMessage: document.getElementById('status-message'),
    loadingStatusText: document.getElementById('loading-status-text'),
    mainContent: document.getElementById('main-content'),
    mainTitle: document.getElementById('main-title'),

    // Page 1
    page1: document.getElementById('page1'),
    registrantName: document.getElementById('registrant-name'),
    dateInput: document.getElementById('date-input'),
    nextBtn: document.getElementById('next-btn'),
    toggleModeBtn: document.getElementById('toggle-mode-button'),

    // Page 2
    page2: document.getElementById('page2'),
    itemName: document.getElementById('item-name'),
    quantity: document.getElementById('quantity'),
    addItemBtn: document.getElementById('add-item-button'),
    addedItemsList: document.getElementById('added-items-list'),
    confirmBtn: document.getElementById('confirm-button'),
    backToPage1Btn: document.getElementById('back-to-page1-btn'),

    // Page 3
    page3: document.getElementById('page3'),
    confirmRegistrant: document.getElementById('confirm-registrant'),
    confirmDate: document.getElementById('confirm-date'),
    confirmItemsList: document.getElementById('confirm-items-list'),
    registerBtn: document.getElementById('register-btn'),
    backToPage2Btn: document.getElementById('back-to-page2-btn'),

    // Success
    successScreen: document.getElementById('success-screen'),
    newEntryBtn: document.getElementById('new-entry-btn')
};

// ===============================================================
// ページナビゲーション
// ===============================================================
function showPage(pageNum) {
    dom.page1.style.display = 'none';
    dom.page2.style.display = 'none';
    dom.page3.style.display = 'none';
    dom.successScreen.style.display = 'none';

    if (pageNum === 1) dom.page1.style.display = 'block';
    if (pageNum === 2) dom.page2.style.display = 'block';
    if (pageNum === 3) dom.page3.style.display = 'block';
    if (pageNum === 'success') dom.successScreen.style.display = 'block';
}

// ===============================================================
// 品目管理
// ===============================================================
function addItem() {
    const t = TRANSLATIONS[currentLang];
    const itemName = dom.itemName.value.trim();
    const quantity = parseInt(dom.quantity.value);

    if (!itemName || !quantity || quantity <= 0) {
        alert('品名と個数を正しく入力してください');
        return;
    }

    state.items.push({ name: itemName, quantity });

    // リストを更新
    updateItemsList();

    // フォームをクリア
    dom.itemName.value = '';
    dom.quantity.value = '';
}

function updateItemsList() {
    const t = TRANSLATIONS[currentLang];

    if (state.items.length === 0) {
        dom.addedItemsList.innerHTML = `<p class="text-sm text-gray-500">${t.msg_no_items_added}</p>`;
        dom.confirmBtn.disabled = true;
    } else {
        dom.addedItemsList.innerHTML = state.items.map((item, index) => `
            <div class="flex justify-between items-center py-2 border-b border-gray-200">
                <span class="text-gray-800">${item.name} × ${item.quantity}</span>
                <button onclick="removeItem(${index})" class="text-red-500 text-sm">削除</button>
            </div>
        `).join('');
        dom.confirmBtn.disabled = false;
    }
}

function removeItem(index) {
    state.items.splice(index, 1);
    updateItemsList();
}

// ===============================================================
// 確認画面
// ===============================================================
function showConfirmationPage() {
    const t = TRANSLATIONS[currentLang];

    dom.confirmRegistrant.textContent = dom.registrantName.value || state.userName || '不明';
    dom.confirmDate.textContent = dom.dateInput.value;

    dom.confirmItemsList.innerHTML = state.items.map(item => `
        <div class="py-2 border-b border-gray-200">
            <span class="text-gray-800">${item.name} × ${item.quantity}</span>
        </div>
    `).join('');

    showPage(3);
}

// ===============================================================
// データ登録
// ===============================================================
async function registerRecord() {
    const t = TRANSLATIONS[currentLang];
    dom.registerBtn.disabled = true;
    dom.registerBtn.textContent = t.msg_registering;

    const record = {
        registrant: dom.registrantName.value || state.userName || '不明',
        date: dom.dateInput.value,
        mode: state.mode,
        items: state.items,
        timestamp: Date.now(),
        synced: false
    };

    try {
        // IndexedDBに保存
        const localId = await offlineDB.addRecord(record);
        console.log('Record saved to IndexedDB:', localId);

        // オンラインなら同期を試みる
        if (navigator.onLine) {
            try {
                await syncManager.syncRecord(localId);
                console.log('Record synced to server');
            } catch (error) {
                console.log('Sync failed, will retry later:', error);
            }
        }

        // 成功画面へ
        showPage('success');

    } catch (error) {
        console.error('Registration error:', error);
        alert('登録エラー: ' + error.message);
    } finally {
        dom.registerBtn.disabled = false;
        dom.registerBtn.textContent = t.btn_register;
    }
}

// ===============================================================
// 新規記録
// ===============================================================
function resetForNewEntry() {
    state.items = [];
    dom.registrantName.value = '';
    dom.dateInput.value = new Date().toISOString().split('T')[0];
    dom.itemName.value = '';
    dom.quantity.value = '';
    updateItemsList();
    showPage(1);
}

// ===============================================================
// モード切り替え
// ===============================================================
function toggleMode() {
    const t = TRANSLATIONS[currentLang];
    state.mode = state.mode === 'outbound' ? 'inbound' : 'outbound';
    dom.mainTitle.textContent = state.mode === 'inbound' ? t.title_inbound : t.title_outbound;
    dom.toggleModeBtn.textContent = state.mode === 'outbound' ? t.btn_mode_outbound : t.btn_mode_inbound;
}

// ===============================================================
// イベントリスナー
// ===============================================================
function initializeEventListeners() {
    dom.nextBtn.addEventListener('click', () => showPage(2));
    dom.toggleModeBtn.addEventListener('click', toggleMode);
    dom.addItemBtn.addEventListener('click', addItem);
    dom.confirmBtn.addEventListener('click', showConfirmationPage);
    dom.backToPage1Btn.addEventListener('click', () => showPage(1));
    dom.registerBtn.addEventListener('click', registerRecord);
    dom.backToPage2Btn.addEventListener('click', () => showPage(2));
    dom.newEntryBtn.addEventListener('click', resetForNewEntry);
}

// ===============================================================
// 初期化
// ===============================================================
async function initialize() {
    const t = TRANSLATIONS[currentLang];

    try {
        console.log('Initializing app...');

        // IndexedDB初期化
        dom.loadingStatusText.textContent = 'データベースを初期化中...';
        await offlineDB.init();
        console.log('IndexedDB initialized');

        // URLパラメータからユーザー名を取得
        const urlParams = new URLSearchParams(window.location.search);
        state.userName = urlParams.get('user') || 'ゲスト';
        dom.registrantName.value = state.userName;

        // 日付のデフォルト値を設定
        dom.dateInput.value = new Date().toISOString().split('T')[0];

        // イベントリスナー設定
        dom.loadingStatusText.textContent = 'インターフェースを準備中...';
        initializeEventListeners();

        // 品目リストを初期化
        updateItemsList();

        // UI言語更新
        updateUILanguage();

        // メインコンテンツを表示
        dom.loadingStatusText.textContent = 'まもなく完了します...';
        showMainContent();

        console.log('Initialization complete');

    } catch (error) {
        console.error('Initialization error:', error);
        dom.loadingStatusText.textContent = 'エラー: ' + error.message;
    }
}

// メインコンテンツを表示
function showMainContent() {
    dom.statusMessage.classList.remove('animate-pulse');
    dom.statusMessage.style.opacity = '0';

    setTimeout(() => {
        dom.statusMessage.style.display = 'none';
        dom.mainContent.style.display = 'block';
        dom.mainContent.style.opacity = '1';
    }, 300);
}

// ===============================================================
// ネットワーク状態監視
// ===============================================================
function setupNetworkMonitoring() {
    const t = TRANSLATIONS[currentLang];

    networkStatus.addListener(async (isOnline) => {
        const statusEl = document.getElementById('network-status');
        const statusText = document.getElementById('network-status-text');

        if (isOnline) {
            statusText.textContent = t.online_notice;
            statusEl.classList.remove('offline');
            statusEl.classList.add('online', 'show');

            // 自動同期
            console.log('Online - starting sync');
            try {
                const result = await syncManager.syncAll();
                console.log('Sync result:', result);
            } catch (error) {
                console.error('Sync error:', error);
            }

            setTimeout(() => {
                statusEl.classList.remove('show');
            }, 3000);
        } else {
            statusText.textContent = t.offline_notice;
            statusEl.classList.remove('online');
            statusEl.classList.add('offline', 'show');
        }
    });
}

// ===============================================================
// アプリ起動
// ===============================================================
document.addEventListener('DOMContentLoaded', async function() {
    try {
        await initialize();
        setupNetworkMonitoring();
    } catch (error) {
        console.error('App startup error:', error);
        alert('アプリケーションの起動に失敗しました: ' + error.message);
    }
});
