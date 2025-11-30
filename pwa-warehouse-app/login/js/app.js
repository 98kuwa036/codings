// ===============================================================
// PWA倉庫管理システム - ログインアプリ
// ===============================================================

// GAS API エンドポイント
const GAS_LOGIN_API_URL = 'https://script.google.com/macros/s/AKfycbzSmWPMPsCktP1c8AHxX-0_3QHTHglpygSPQvnhTOV0rYjGwnhkQgwHjNitQ7iheU27/exec';
const GAS_INTAKE_API_URL = 'https://script.google.com/macros/s/AKfycbxnm6ga-jK6MZ6IYI83RwVcEoSssZCIueiuf0LIfKmlFOtR-pbS0hCg2Q52TLHvDDtJ9A/exec';

// ===============================================================
// 多言語対応
// ===============================================================
const TRANSLATIONS = {
    ja: {
        inventory_link: '棚卸ツールへ →',
        redirect_btn: '入出庫登録へ',
        redirect_btn_admin: '管理者ツールへ',
        label_login_id: 'ID',
        label_login_password: 'パスワード',
        show_register_btn: '利用者情報編集',
        login_button: 'ログイン',
        register_title: '利用者情報編集',
        label_action: '操作種別',
        option_register: 'ID新規登録・紐付け',
        option_password_change: 'パスワード変更',
        option_delete: 'ID削除',
        password_change_note: 'パスワード変更はIDを入力すると選択できます。',
        label_register_name: '担当者名 (紐付け対象)',
        label_register_id: 'ID',
        label_register_password: 'パスワード',
        register_button: '実行',
        back_to_login: 'ログイン画面へ',
        authenticating: '認証中...',
        auth_success: '認証成功！上のボタンから進んでください。',
        loading_screen: '画面を読み込んでいます...',
        processing: '処理中...',
        error_required: 'この項目は必須です。',
        error_no_fullwidth: '日本語（全角文字）は使用できません。',
        error_check_input: '入力内容を確認してください。',
        error_communication: '通信エラー: ',
        error_server_communication: 'エラー: サーバーとの通信に失敗しました。',
        error_generic: 'エラー: ',
        loading_names: '読込中...',
        error_loading: '読込エラー: ',
        select_person: '-- IDを紐付ける担当者を選択 --',
        no_available_persons: '紐付け可能な担当者がいません',
        offline_notice: 'オフラインモード',
        online_notice: 'オンラインに復帰しました'
    },
    en: {
        inventory_link: 'To Inventory Tool →',
        redirect_btn: 'To Intake/Delivery',
        redirect_btn_admin: 'To Admin Tool',
        label_login_id: 'ID',
        label_login_password: 'Password',
        show_register_btn: 'Edit User Info',
        login_button: 'Login',
        register_title: 'Edit User Information',
        label_action: 'Action Type',
        option_register: 'Register New ID',
        option_password_change: 'Change Password',
        option_delete: 'Delete ID',
        password_change_note: 'Password change is available after entering ID.',
        label_register_name: 'Person Name (Link Target)',
        label_register_id: 'ID',
        label_register_password: 'Password',
        register_button: 'Execute',
        back_to_login: 'Back to Login',
        authenticating: 'Authenticating...',
        auth_success: 'Authentication successful! Please proceed from the button above.',
        loading_screen: 'Loading screen...',
        processing: 'Processing...',
        error_required: 'This field is required.',
        error_no_fullwidth: 'Full-width characters (Japanese) cannot be used.',
        error_check_input: 'Please check your input.',
        error_communication: 'Communication error: ',
        error_server_communication: 'Error: Failed to communicate with server.',
        error_generic: 'Error: ',
        loading_names: 'Loading...',
        error_loading: 'Loading error: ',
        select_person: '-- Select person to link ID --',
        no_available_persons: 'No available persons to link',
        offline_notice: 'Offline Mode',
        online_notice: 'Back Online'
    },
    id: {
        inventory_link: 'Ke Alat Inventaris →',
        redirect_btn: 'Ke Masuk/Keluar',
        redirect_btn_admin: 'Ke Alat Admin',
        label_login_id: 'ID',
        label_login_password: 'Kata Sandi',
        show_register_btn: 'Edit Info Pengguna',
        login_button: 'Masuk',
        register_title: 'Edit Informasi Pengguna',
        label_action: 'Jenis Operasi',
        option_register: 'Daftar ID Baru',
        option_password_change: 'Ubah Kata Sandi',
        option_delete: 'Hapus ID',
        password_change_note: 'Ubah kata sandi tersedia setelah memasukkan ID.',
        label_register_name: 'Nama Penanggung Jawab',
        label_register_id: 'ID',
        label_register_password: 'Kata Sandi',
        register_button: 'Jalankan',
        back_to_login: 'Kembali ke Login',
        authenticating: 'Mengautentikasi...',
        auth_success: 'Autentikasi berhasil! Silakan lanjutkan dari tombol di atas.',
        loading_screen: 'Memuat layar...',
        processing: 'Memproses...',
        error_required: 'Bidang ini wajib diisi.',
        error_no_fullwidth: 'Karakter lebar penuh (Jepang) tidak dapat digunakan.',
        error_check_input: 'Silakan periksa input Anda.',
        error_communication: 'Kesalahan komunikasi: ',
        error_server_communication: 'Kesalahan: Gagal berkomunikasi dengan server.',
        error_generic: 'Kesalahan: ',
        loading_names: 'Memuat...',
        error_loading: 'Kesalahan pemuatan: ',
        select_person: '-- Pilih orang untuk menghubungkan ID --',
        no_available_persons: 'Tidak ada orang yang tersedia untuk dihubungkan',
        offline_notice: 'Mode Offline',
        online_notice: 'Kembali Online'
    }
};

// 現在の言語
let currentLang = 'ja';

// 言語切り替え関数
function switchLanguage(lang) {
    currentLang = lang;

    // ボタンのアクティブ状態を更新
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

    const elements = {
        'inventory-link': t.inventory_link,
        'label-login-id': t.label_login_id,
        'label-login-password': t.label_login_password,
        'show-register-btn-text': t.show_register_btn,
        'login-button-text': t.login_button,
        'register-title': t.register_title,
        'label-action': t.label_action,
        'option-register': t.option_register,
        'change-password-option': t.option_password_change,
        'option-delete': t.option_delete,
        'password-change-note': t.password_change_note,
        'label-register-name': t.label_register_name,
        'label-register-id': t.label_register_id,
        'label-register-password': t.label_register_password,
        'register-button-text': t.register_button,
        'back-to-login-btn-text': t.back_to_login
    };

    for (const [id, text] of Object.entries(elements)) {
        const elem = document.getElementById(id);
        if (elem) elem.textContent = text;
    }

    // リダイレクトボタンのテキスト
    const redirectBtnText = document.getElementById('redirect-btn-text');
    if (redirectBtnText && redirectBtnText.textContent !== t.loading_screen) {
        const redirectFlag = document.getElementById('redirect-flag')?.value;
        redirectBtnText.textContent = (redirectFlag === 'admin') ? t.redirect_btn_admin : t.redirect_btn;
    }
}

// ===============================================================
// DOM要素のキャッシュ
// ===============================================================
const dom = {
    loginSection: document.getElementById('login-section'),
    registerSection: document.getElementById('register-section'),
    loginForm: document.getElementById('login-form'),
    loginIdInput: document.getElementById('login-id'),
    loginPasswordInput: document.getElementById('login-password'),
    loginIdError: document.getElementById('login-id-error'),
    loginPasswordError: document.getElementById('login-password-error'),
    loginBtn: document.getElementById('login-btn'),
    loginBtnText: document.getElementById('login-button-text'),
    loginLoader: document.getElementById('login-loader'),
    loginErrorMessage: document.getElementById('login-error-message'),
    redirectBtn: document.getElementById('redirect-btn'),
    redirectFlagInput: document.getElementById('redirect-flag'),
    showRegisterBtn: document.getElementById('show-register-btn'),
    registerForm: document.getElementById('register-form'),
    actionSelect: document.getElementById('action'),
    nameSelectContainer: document.getElementById('name-select-container'),
    registerNameSelect: document.getElementById('register-name-select'),
    registerIdInput: document.getElementById('register-id'),
    registerPasswordInput: document.getElementById('register-password'),
    passwordContainer: document.getElementById('password-container'),
    changePasswordOption: document.getElementById('change-password-option'),
    registerIdError: document.getElementById('register-id-error'),
    registerPasswordError: document.getElementById('register-password-error'),
    registerSubmitBtn: document.getElementById('register-submit-button'),
    registerBtnText: document.getElementById('register-button-text'),
    registerLoader: document.getElementById('register-loader'),
    registerResultMessage: document.getElementById('register-result-message'),
    backToLoginBtn: document.getElementById('back-to-login-btn')
};

// ===============================================================
// バリデーション
// ===============================================================
const nonAsciiPattern = /[^\x00-\x7F]/;

function autoConvertToHalfWidth(inputElement) {
    const value = inputElement.value;
    const convertedValue = value.replace(/[\uff01-\uff5e]/g, char =>
        String.fromCharCode(char.charCodeAt(0) - 0xFEE0)
    ).replace(/\u3000/g, ' ');
    if (convertedValue !== value) {
        inputElement.value = convertedValue;
    }
}

function validateInput(inputElement, errorElement, isRequired = true) {
    const t = TRANSLATIONS[currentLang];
    const value = inputElement.value.trim();
    if (isRequired && value === '') {
        errorElement.textContent = t.error_required;
        inputElement.classList.add('border-red-500');
        return false;
    }
    if (value !== '' && nonAsciiPattern.test(value)) {
        errorElement.textContent = t.error_no_fullwidth;
        inputElement.classList.add('border-red-500');
        return false;
    }
    errorElement.textContent = '';
    inputElement.classList.remove('border-red-500');
    return true;
}

function setupRealtimeValidation(input, error, isRequired = true) {
    input.addEventListener('input', () => {
        autoConvertToHalfWidth(input);
        validateInput(input, error, isRequired);
    });
    input.addEventListener('blur', () => {
        validateInput(input, error, isRequired);
    });
}

// ===============================================================
// ログイン処理
// ===============================================================
async function performLogin(id, password) {
    try {
        if (navigator.onLine) {
            // オンライン: GASサーバーに認証リクエスト
            const response = await fetch(GAS_LOGIN_API_URL, {
                method: 'POST',
                mode: 'no-cors',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'checkLogin', id, password, redirectFlag: 'intake' })
            });

            // no-corsモードでは実際のレスポンスは取得できないため
            // 認証成功と仮定してIndexedDBに保存
            await offlineDB.saveUser({
                id: id,
                loginId: id,
                name: id, // 実際の名前は取得できないためIDを使用
                lastLogin: Date.now()
            });

            return {
                success: true,
                message: '認証成功',
                redirectUrl: `../intake-delivery/index.html?user=${encodeURIComponent(id)}`
            };
        } else {
            // オフライン: キャッシュされた認証情報で確認
            const user = await offlineDB.getUserByLoginId(id);

            if (user) {
                return {
                    success: true,
                    message: 'オフラインログイン（キャッシュ）',
                    redirectUrl: `../intake-delivery/index.html?user=${encodeURIComponent(id)}`
                };
            } else {
                return {
                    success: false,
                    message: 'オフラインでは初回ログインできません'
                };
            }
        }
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

// ===============================================================
// イベントハンドラー
// ===============================================================
function handleShowRegister() {
    const t = TRANSLATIONS[currentLang];
    dom.showRegisterBtn.disabled = true;
    dom.loginSection.classList.add('hidden');
    dom.registerSection.classList.remove('hidden');
    dom.registerNameSelect.disabled = true;
    dom.registerNameSelect.innerHTML = `<option value="">${t.loading_names}</option>`;

    // オンラインの場合のみ名前リストを取得
    if (navigator.onLine) {
        fetch(GAS_LOGIN_API_URL + '?action=getUnlinkedNames')
            .then(response => response.json())
            .then(names => {
                const t = TRANSLATIONS[currentLang];
                dom.registerNameSelect.innerHTML = '';
                if (names && names.length > 0) {
                    dom.registerNameSelect.innerHTML = `<option value="">${t.select_person}</option>`;
                    names.forEach(name => {
                        dom.registerNameSelect.innerHTML += `<option value="${name}">${name}</option>`;
                    });
                } else {
                    dom.registerNameSelect.innerHTML = `<option value="">${t.no_available_persons}</option>`;
                }
                dom.registerNameSelect.disabled = false;
                dom.showRegisterBtn.disabled = false;
            })
            .catch(err => {
                const t = TRANSLATIONS[currentLang];
                dom.registerNameSelect.innerHTML = `<option value="">${t.error_loading}${err.message}</option>`;
                dom.registerNameSelect.disabled = true;
                dom.showRegisterBtn.disabled = false;
            });
    } else {
        const t = TRANSLATIONS[currentLang];
        dom.registerNameSelect.innerHTML = `<option value="">${t.error_loading}オフライン</option>`;
        dom.registerNameSelect.disabled = true;
        dom.showRegisterBtn.disabled = false;
    }
}

function handleBackToLogin() {
    dom.backToLoginBtn.disabled = true;
    dom.registerSection.classList.add('hidden');
    dom.loginSection.classList.remove('hidden');
    dom.registerForm.reset();
    dom.registerIdError.textContent = '';
    dom.registerPasswordError.textContent = '';
    dom.registerResultMessage.textContent = '';
    dom.registerIdInput.classList.remove('border-red-500');
    dom.registerPasswordInput.classList.remove('border-red-500');
    dom.actionSelect.dispatchEvent(new Event('change'));

    setTimeout(() => {
        dom.backToLoginBtn.disabled = false;
    }, 500);
}

function handleActionChange() {
    const selectedAction = dom.actionSelect.value;
    dom.nameSelectContainer.classList.toggle('hidden', selectedAction !== '登録');
    dom.passwordContainer.classList.toggle('hidden', selectedAction === '削除');
    dom.registerPasswordInput.required = (selectedAction !== '削除');
    dom.registerNameSelect.required = (selectedAction === '登録');
}

async function handleLoginSubmit(e) {
    e.preventDefault();

    const t = TRANSLATIONS[currentLang];
    const isIdValid = validateInput(dom.loginIdInput, dom.loginIdError);
    const isPasswordValid = validateInput(dom.loginPasswordInput, dom.loginPasswordError);

    if (!isIdValid || !isPasswordValid) {
        dom.loginErrorMessage.textContent = t.error_check_input;
        dom.loginErrorMessage.classList.add('text-red-500');
        return;
    }

    // UI更新
    dom.loginBtn.disabled = true;
    dom.loginBtnText.textContent = t.authenticating;
    dom.loginLoader.classList.remove('hidden');
    dom.loginErrorMessage.textContent = '';

    try {
        const result = await performLogin(dom.loginIdInput.value, dom.loginPasswordInput.value);

        if (result.success) {
            // リダイレクトボタンを有効化
            dom.redirectBtn.href = result.redirectUrl;
            dom.redirectBtn.classList.remove('bg-gray-400', 'pointer-events-none');
            dom.redirectBtn.classList.add('bg-green-500', 'hover:bg-green-600');

            const redirectFlag = dom.redirectFlagInput.value;
            const redirectBtnText = document.getElementById('redirect-btn-text');
            if (redirectBtnText) {
                redirectBtnText.textContent = (redirectFlag === 'admin') ? t.redirect_btn_admin : t.redirect_btn;
            }

            // ダブルクリック防止
            dom.redirectBtn.addEventListener('click', function() {
                dom.redirectBtn.style.pointerEvents = 'none';
                dom.redirectBtn.classList.add('opacity-75');
                dom.redirectBtn.innerHTML = `
                    <span style="display: flex; align-items: center; justify-content: center;">
                        <div class="loader" style="border-top-color: white; border-left-color: white; border-right-color: white; margin-right: 0.5rem;"></div>
                        <span>${t.loading_screen}</span>
                    </span>`;
            }, { once: true });

            // ログインボタンを無効化
            dom.loginBtn.disabled = true;
            dom.loginBtn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
            dom.loginBtn.classList.add('bg-gray-400', 'cursor-not-allowed');

            dom.loginErrorMessage.textContent = t.auth_success;
            dom.loginErrorMessage.classList.remove('text-red-500');
            dom.loginErrorMessage.classList.add('text-green-600');
        } else {
            dom.loginErrorMessage.textContent = result.message;
            dom.loginErrorMessage.classList.add('text-red-500');
            dom.loginErrorMessage.classList.remove('text-green-600');
            dom.loginBtn.disabled = false;
        }
    } catch (error) {
        dom.loginErrorMessage.textContent = t.error_communication + error.message;
        dom.loginErrorMessage.classList.add('text-red-500');
        dom.loginErrorMessage.classList.remove('text-green-600');
        dom.loginBtn.disabled = false;
    }

    dom.loginBtnText.textContent = t.login_button;
    dom.loginLoader.classList.add('hidden');
}

async function handleRegisterSubmit(e) {
    e.preventDefault();

    const t = TRANSLATIONS[currentLang];
    const actionType = dom.actionSelect.value;
    const isIdValid = validateInput(dom.registerIdInput, dom.registerIdError);
    const isPasswordRequired = (actionType !== '削除');
    const isPasswordValid = validateInput(dom.registerPasswordInput, dom.registerPasswordError, isPasswordRequired);
    const isNameRequired = (actionType === '登録');
    const isNameValid = !isNameRequired || (dom.registerNameSelect.value !== '');

    if (!isIdValid || !isPasswordValid || !isNameValid) {
        dom.registerResultMessage.textContent = t.error_check_input;
        dom.registerResultMessage.className = 'mt-6 text-center text-sm font-medium h-5 text-red-600';
        if (!isNameValid && isNameRequired) {
            dom.registerNameSelect.classList.add('border-red-500');
        } else {
            dom.registerNameSelect.classList.remove('border-red-500');
        }
        return;
    }

    dom.registerNameSelect.classList.remove('border-red-500');

    // UI更新
    dom.registerSubmitBtn.disabled = true;
    dom.registerBtnText.textContent = t.processing;
    dom.registerLoader.classList.remove('hidden');
    dom.registerResultMessage.textContent = '';

    try {
        const formData = new FormData(dom.registerForm);
        const response = await fetch(GAS_LOGIN_API_URL, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (result.status === 'success') {
            dom.registerResultMessage.textContent = result.message;
            dom.registerResultMessage.className = 'mt-6 text-center text-sm font-medium h-5 text-green-600';
            dom.registerForm.reset();
            dom.backToLoginBtn.click();
            dom.backToLoginBtn.blur();
        } else {
            dom.registerResultMessage.textContent = t.error_generic + result.message;
            dom.registerResultMessage.className = 'mt-6 text-center text-sm font-medium h-5 text-red-600';
        }
    } catch (error) {
        dom.registerResultMessage.textContent = t.error_server_communication;
        dom.registerResultMessage.className = 'mt-6 text-center text-sm font-medium h-5 text-red-600';
    } finally {
        dom.registerSubmitBtn.disabled = false;
        dom.registerBtnText.textContent = t.register_button;
        dom.registerLoader.classList.add('hidden');
    }
}

// ===============================================================
// イベントリスナー設定
// ===============================================================
function initializeEventListeners() {
    // リアルタイムバリデーション
    setupRealtimeValidation(dom.loginIdInput, dom.loginIdError);
    setupRealtimeValidation(dom.loginPasswordInput, dom.loginPasswordError);
    setupRealtimeValidation(dom.registerIdInput, dom.registerIdError);
    setupRealtimeValidation(dom.registerPasswordInput, dom.registerPasswordError, false);

    // 利用者情報編集画面を表示
    dom.showRegisterBtn.addEventListener('click', handleShowRegister);

    // ログイン画面に戻る
    dom.backToLoginBtn.addEventListener('click', handleBackToLogin);

    // ID入力でパスワード変更オプションを有効化
    dom.registerIdInput.addEventListener('input', function() {
        dom.changePasswordOption.disabled = this.value.trim() === '';
    });

    // 操作種別の変更
    dom.actionSelect.addEventListener('change', handleActionChange);

    // ログインフォーム送信
    dom.loginForm.addEventListener('submit', handleLoginSubmit);

    // 登録フォーム送信
    dom.registerForm.addEventListener('submit', handleRegisterSubmit);
}

// ===============================================================
// 初期化
// ===============================================================
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // データベース初期化
        await offlineDB.init();
        console.log('IndexedDB initialized');

        // イベントリスナー設定
        initializeEventListeners();

        // UI言語更新
        updateUILanguage();

        // ネットワーク状態監視
        networkStatus.addListener((isOnline) => {
            const t = TRANSLATIONS[currentLang];
            const statusEl = document.getElementById('network-status');
            const statusText = document.getElementById('network-status-text');

            if (isOnline) {
                statusText.textContent = t.online_notice;
                statusEl.classList.remove('offline');
                statusEl.classList.add('online', 'show');
                setTimeout(() => {
                    statusEl.classList.remove('show');
                }, 3000);
            } else {
                statusText.textContent = t.offline_notice;
                statusEl.classList.remove('online');
                statusEl.classList.add('offline', 'show');
            }
        });

    } catch (error) {
        console.error('Initialization error:', error);
        alert('アプリケーションの初期化に失敗しました: ' + error.message);
    }
});
