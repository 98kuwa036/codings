<script>
"use strict"; // V8ランタイム推奨
let handleVerifyClick; // グローバルスコープで宣言

document.addEventListener("DOMContentLoaded", () => {

  // --- 1. 変数の読み込み ---
  if (typeof AUTH_DATA === 'undefined') {
      console.error("AUTH_DATA is not defined. Check CodeEntryPage.html script block.");
      // ユーザーにエラーを表示
      showMessage('ページの初期化に失敗しました。', 'error');
      return;
  }
  
  // (A) 2FAコード検証用
  const USER_ID = AUTH_DATA.userId;
  
  // (B) 認証成功後のリダイレクト用パラメータ
  const REDIRECT_URL_BASE = AUTH_DATA.adminBaseUrl;
  const p_orig = AUTH_DATA.p_original;
  const s_orig = AUTH_DATA.s_original;
  const uid_orig = AUTH_DATA.uid_original;
  const n_rec_orig = AUTH_DATA.n_rec_original;
  const n_adm_orig = AUTH_DATA.n_adm_original;

  // UI要素
  const verifyButton = document.getElementById('verify-button');
  const buttonText = document.getElementById('button-text');
  const buttonSpinner = document.getElementById('button-spinner');
  const adminLinkButton = document.getElementById('admin-link-button');
  const codeInput = document.getElementById('code-input');
  const messageArea = document.getElementById('message-area');

  // --- 2. イベントリスナーと関数の定義 ---

  // 6桁入力で認証ボタンを有効化
  codeInput.addEventListener('input', () => {
    // 認証処理中でない場合のみ
    if (buttonText.textContent !== '認証中...') {
      if (codeInput.value.length === 6) {
        verifyButton.disabled = false;
      } else {
        verifyButton.disabled = true;
      }
    }
  });

  // Enterキー対応
  codeInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && verifyButton && !verifyButton.disabled) {
      e.preventDefault();
      handleVerifyClick();
    }
  });

  // (HTMLの onclick から呼び出される)
  handleVerifyClick = function() {
    const submittedCode = codeInput.value;
    if (submittedCode.length !== 6) {
      showMessage('6桁のコードを入力してください。', 'error');
      return;
    }
    setButtonLoading(true);
    google.script.run
      .withSuccessHandler(handleVerificationSuccess)
      .withFailureHandler(handleVerificationFailure)
      .verifyCode(USER_ID, submittedCode);
  }

  /**
   * ★★★ 修正箇所 (ここから) ★★★
   * サーバーからのレスポンス (result) の形式に合わせて修正
   */
  function handleVerificationSuccess(result) {
    // サーバーが { status: 'success' } を返したか確認
    if (result && result.status === 'success') { 
      
      // 1. URLを構築
      let redirectUrl = REDIRECT_URL_BASE;
      redirectUrl += `?p=${encodeURIComponent(p_orig)}`;
      redirectUrl += `&s=${encodeURIComponent(s_orig)}`;
      redirectUrl += `&uid=${encodeURIComponent(uid_orig)}`;
      // n_rec が存在する場合のみ追加
      if (n_rec_orig) {
        redirectUrl += `&n_rec=${encodeURIComponent(n_rec_orig)}`;
      }
      redirectUrl += `&n_adm=${encodeURIComponent(n_adm_orig)}`;
      
      // 2. 黄緑ボタン(aタグ)にURLを設定し、有効化
      adminLinkButton.href = redirectUrl;
      adminLinkButton.classList.remove('button-disabled');
      // 成功（有効）のクラス（緑色）を追加
      adminLinkButton.classList.add('bg-green-600', 'hover:bg-green-700');

      // 3. 認証ボタンをグレーアウトし、ローディングを解除
      setButtonLoading(false); 
      verifyButton.disabled = true; 
      codeInput.disabled = true; 
      
      // 4. 成功メッセージを表示 (サーバーからのメッセージを優先)
      showMessage(result.message || '認証に成功しました。ボタンで次に進んでください。', 'success');

    } else {
      // サーバーが { status: 'error' } を返した場合、または予期せぬレスポンスの場合
      const errorMessage = (result && result.message) ? result.message : "認証に失敗しました。";
      handleVerificationFailure({ message: errorMessage });
    }
  }
  /**
   * ★★★ 修正箇所 (ここまで) ★★★
   */

  function handleVerificationFailure(error) {
    showMessage(error.message || '不明なエラーが発生しました。', 'error');
    setButtonLoading(false); // ボタンを元に戻す
    codeInput.value = ''; // 入力をクリア
    codeInput.focus();
  }

  function setButtonLoading(isLoading) {
    if (isLoading) {
      verifyButton.disabled = true;
      buttonText.textContent = '認証中...';
      buttonSpinner.classList.remove('hidden');
      messageArea.textContent = '';
    } else {
      // 失敗時（isLoading=false）は、再度入力を促す
      verifyButton.disabled = (codeInput.value.length !== 6);
      buttonText.textContent = '認証する >';
      buttonSpinner.classList.add('hidden');
    }
  }

  function showMessage(text, type) {
    messageArea.textContent = text;
    if (type === 'error') {
      messageArea.className = 'text-center text-sm text-red-600 min-h-[1.25rem] mb-6';
    } else if (type === 'success') {
      messageArea.className = 'text-center text-sm text-green-600 min-h-[1.25rem] mb-6';
    } else {
      messageArea.className = 'text-center text-sm text-gray-500 min-h-[1.25rem] mb-6';
    }
  }

}); // DOMContentLoaded の終わり
</script>
