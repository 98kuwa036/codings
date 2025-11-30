/**
 * Network Status Manager
 * ネットワーク状態監視とUI更新
 */

class NetworkStatus {
  constructor() {
    this.isOnline = navigator.onLine;
    this.listeners = [];
    this.statusIndicator = null;
    this.syncInProgress = false;

    this.init();
  }

  /**
   * 初期化
   */
  init() {
    // オンライン/オフラインイベントリスナー
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());

    // 定期的な接続確認（オプション）
    setInterval(() => this.checkConnection(), 30000); // 30秒ごと
  }

  /**
   * オンライン状態になった時の処理
   */
  async handleOnline() {
    console.log('Network: Online');
    this.isOnline = true;
    this.updateUI();
    this.notifyListeners(true);

    // 自動同期を試行
    await this.triggerSync();
  }

  /**
   * オフライン状態になった時の処理
   */
  handleOffline() {
    console.log('Network: Offline');
    this.isOnline = false;
    this.updateUI();
    this.notifyListeners(false);
  }

  /**
   * 接続確認（fetch テスト）
   */
  async checkConnection() {
    try {
      // 軽量なリクエストで接続確認
      const response = await fetch('/favicon.ico', {
        method: 'HEAD',
        cache: 'no-cache'
      });

      const wasOnline = this.isOnline;
      this.isOnline = response.ok;

      // 状態が変わった場合のみ処理
      if (wasOnline !== this.isOnline) {
        if (this.isOnline) {
          await this.handleOnline();
        } else {
          this.handleOffline();
        }
      }
    } catch (error) {
      if (this.isOnline) {
        this.handleOffline();
      }
    }
  }

  /**
   * UI更新
   */
  updateUI() {
    if (!this.statusIndicator) {
      this.createStatusIndicator();
    }

    const indicator = this.statusIndicator;
    const statusText = indicator.querySelector('.status-text');
    const statusDot = indicator.querySelector('.status-dot');

    if (this.isOnline) {
      indicator.classList.remove('offline');
      indicator.classList.add('online');
      statusText.textContent = 'オンライン';
      statusDot.style.backgroundColor = '#22c55e';

      // オンライン時は3秒後に非表示
      setTimeout(() => {
        if (this.isOnline && !this.syncInProgress) {
          indicator.classList.add('hidden');
        }
      }, 3000);
    } else {
      indicator.classList.remove('online', 'hidden');
      indicator.classList.add('offline');
      statusText.textContent = 'オフライン';
      statusDot.style.backgroundColor = '#ef4444';
    }
  }

  /**
   * ステータスインジケーター作成
   */
  createStatusIndicator() {
    if (document.getElementById('network-status-indicator')) {
      this.statusIndicator = document.getElementById('network-status-indicator');
      return;
    }

    const indicator = document.createElement('div');
    indicator.id = 'network-status-indicator';
    indicator.className = 'network-status-indicator hidden';
    indicator.innerHTML = `
      <div class="status-content">
        <span class="status-dot"></span>
        <span class="status-text">オンライン</span>
        <span class="sync-info"></span>
      </div>
    `;

    // スタイル追加
    const style = document.createElement('style');
    style.textContent = `
      .network-status-indicator {
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        padding: 8px 16px;
        border-radius: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        transition: opacity 0.3s, transform 0.3s;
        font-size: 14px;
        display: flex;
        align-items: center;
      }

      .network-status-indicator.hidden {
        opacity: 0;
        transform: translateX(-50%) translateY(-20px);
        pointer-events: none;
      }

      .network-status-indicator.offline {
        background: #fee2e2;
        border: 1px solid #ef4444;
      }

      .network-status-indicator.online {
        background: #d1fae5;
        border: 1px solid #22c55e;
      }

      .status-content {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
      }

      .status-text {
        font-weight: 600;
        color: #1f2937;
      }

      .sync-info {
        font-size: 12px;
        color: #6b7280;
        margin-left: 8px;
      }
    `;

    document.head.appendChild(style);
    document.body.appendChild(indicator);
    this.statusIndicator = indicator;
  }

  /**
   * 同期トリガー
   */
  async triggerSync() {
    if (!this.isOnline || this.syncInProgress) {
      return;
    }

    this.syncInProgress = true;
    this.updateSyncInfo('同期中...');

    try {
      // syncManager が定義されている場合に同期実行
      if (typeof syncManager !== 'undefined') {
        const result = await syncManager.syncAll();

        if (result.success) {
          this.updateSyncInfo(`${result.synced}件同期完了`);
          setTimeout(() => this.updateSyncInfo(''), 3000);
        } else {
          this.updateSyncInfo('同期エラー');
          setTimeout(() => this.updateSyncInfo(''), 3000);
        }
      }
    } catch (error) {
      console.error('Sync error:', error);
      this.updateSyncInfo('同期エラー');
      setTimeout(() => this.updateSyncInfo(''), 3000);
    } finally {
      this.syncInProgress = false;
    }
  }

  /**
   * 同期情報更新
   */
  updateSyncInfo(text) {
    if (this.statusIndicator) {
      const syncInfo = this.statusIndicator.querySelector('.sync-info');
      if (syncInfo) {
        syncInfo.textContent = text;

        if (text) {
          this.statusIndicator.classList.remove('hidden');
        }
      }
    }
  }

  /**
   * リスナー登録
   */
  addListener(callback) {
    this.listeners.push(callback);
  }

  /**
   * リスナー削除
   */
  removeListener(callback) {
    this.listeners = this.listeners.filter(cb => cb !== callback);
  }

  /**
   * リスナーに通知
   */
  notifyListeners(isOnline) {
    this.listeners.forEach(callback => {
      try {
        callback(isOnline);
      } catch (error) {
        console.error('Listener error:', error);
      }
    });
  }

  /**
   * 現在のオンライン状態取得
   */
  getStatus() {
    return this.isOnline;
  }

  /**
   * 手動同期実行
   */
  async manualSync() {
    if (!this.isOnline) {
      alert('オフライン状態では同期できません。オンラインになってから再試行してください。');
      return;
    }

    await this.triggerSync();
  }
}

// グローバルインスタンス
const networkStatus = new NetworkStatus();
