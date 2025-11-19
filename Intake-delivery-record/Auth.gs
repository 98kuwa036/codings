// [ Auth.gs ]
// (★ 21:13 にご提示いただいた「お手本」の認証関数)

// --- 認証・検証ヘルパー (新版) ---
/**
 * Token 検証 + 必要なら Nonce 検証
 * @param {string} p base64URL payload
 * @param {string} s signature
 * @param {Object} options validateNonce: "rec" | "adm" | null
 */
function validateToken(p, s, options) {

  options = options || {};
  const nonceMode = options.validateNonce || null;

  if (!p || !s) return null;

  if (!TOKEN_SECRET_KEY) {
    throw new Error("TOKEN_SECRET_KEY が未設定です。");
  }

  try {
    const expected = computeHmacSha256_WebSafe(p, TOKEN_SECRET_KEY);
    if (expected !== s) {
      Logger.log("validateToken: Signature mismatch.");
      return null;
    }

    const payload = JSON.parse(
      Utilities.newBlob(Utilities.base64DecodeWebSafe(p)).getDataAsString()
    );

    //------------------------------------------------------------
    // 🔥 Nonce の種別ごとに検証（1回のみ消費）
    //------------------------------------------------------------
    if (nonceMode === "rec") {
      if (!validateNonce(payload.n_rec)) {
        Logger.log("validateToken: Invalid or consumed n_rec");
        return null;
      }
    }

    if (nonceMode === "adm") {
      if (!validateNonce(payload.n_adm)) {
        Logger.log("validateToken: Invalid or consumed n_adm");
        return null;
      }
    }

    return payload;

  } catch (err) {
    Logger.log("validateToken Error: " + err.message);
    return null;
  }
}


function validateNonce(nonce) {
 if (!nonce) { Logger.log("validateNonce: 'nonce' is missing."); return false; }
 try {
  const cache = CacheService.getScriptCache();
  const cacheKey = `nonce_${nonce}`;
  if (cache.get(cacheKey)) {
   Logger.log(`validateNonce: Replay attack detected. Nonce: ${nonce}`);
   return false; 
  }
  // ★ 修正: CONFIG を使用
    if (!CONFIG || !CONFIG.NONCE_CACHE_EXPIRATION) {
      loadConfig_(); // (Config.gs)
    }
  let nonceTtl = parseInt(CONFIG.NONCE_CACHE_EXPIRATION, 10);
  if (isNaN(nonceTtl) || nonceTtl <= 0) {
   nonceTtl = 600; 
  }
  cache.put(cacheKey, 'used', nonceTtl);
  return true; 
 } catch (err) { Logger.log(`validateNonce Error: ${err.message}`); return false; }
}

function computeHmacSha256_WebSafe(payload, secret) {
 const signatureBytes = Utilities.computeHmacSha256Signature(payload, secret);
 return Utilities.base64EncodeWebSafe(signatureBytes).replace(/=+$/, '');
}
