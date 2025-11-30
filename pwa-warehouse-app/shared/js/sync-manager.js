/**
 * Sync Manager - Data Synchronization with Last-Write-Wins Strategy
 * データ同期マネージャー（最終書き込み優先戦略）
 */

class SyncManager {
  constructor(apiConfig = {}) {
    this.apiConfig = {
      baseUrl: apiConfig.baseUrl || '',
      endpoints: apiConfig.endpoints || {},
      timeout: apiConfig.timeout || 30000
    };
    this.syncInProgress = false;
    this.syncCallbacks = [];
  }

  /**
   * 全データ同期
   */
  async syncAll() {
    if (this.syncInProgress) {
      console.log('Sync already in progress');
      return { success: false, message: '同期処理中です' };
    }

    if (!navigator.onLine) {
      console.log('Cannot sync: offline');
      return { success: false, message: 'オフラインです' };
    }

    this.syncInProgress = true;
    this.notifyCallbacks('start');

    try {
      const unsyncedRecords = await offlineDB.getUnsyncedRecords();

      if (unsyncedRecords.length === 0) {
        console.log('No records to sync');
        this.syncInProgress = false;
        this.notifyCallbacks('complete', { synced: 0 });
        return { success: true, synced: 0, message: '同期するデータがありません' };
      }

      console.log(`Syncing ${unsyncedRecords.length} records...`);

      const results = await Promise.allSettled(
        unsyncedRecords.map(record => this.syncRecord(record))
      );

      const successful = results.filter(r => r.status === 'fulfilled').length;
      const failed = results.filter(r => r.status === 'rejected').length;

      console.log(`Sync complete: ${successful} succeeded, ${failed} failed`);

      this.syncInProgress = false;
      this.notifyCallbacks('complete', { synced: successful, failed });

      return {
        success: true,
        synced: successful,
        failed,
        message: `${successful}件同期完了`
      };
    } catch (error) {
      console.error('Sync error:', error);
      this.syncInProgress = false;
      this.notifyCallbacks('error', error);

      return {
        success: false,
        message: '同期エラー: ' + error.message
      };
    }
  }

  /**
   * 単一レコード同期
   */
  async syncRecord(record) {
    try {
      // サーバーにデータ送信
      const response = await this.sendToServer(record);

      if (response.success) {
        // 同期成功 - レコードを同期済みにマーク
        await offlineDB.markAsSynced(record.id, response.serverId);
        console.log(`Record ${record.id} synced successfully`);
        return { success: true, localId: record.id, serverId: response.serverId };
      } else {
        throw new Error(response.error || 'Server returned error');
      }
    } catch (error) {
      console.error(`Failed to sync record ${record.id}:`, error);

      // リトライカウント増加
      if (record.retries === undefined) {
        record.retries = 0;
      }
      record.retries++;

      // 最大リトライ回数を超えた場合はエラーマーク
      if (record.retries >= 3) {
        console.error(`Record ${record.id} failed after 3 retries`);
        // エラーログに記録するなどの処理
      }

      throw error;
    }
  }

  /**
   * サーバーにデータ送信（GAS対応）
   */
  async sendToServer(record) {
    // GAS環境での送信
    if (typeof google !== 'undefined' && google.script && google.script.run) {
      return new Promise((resolve, reject) => {
        google.script.run
          .withSuccessHandler((result) => {
            resolve({ success: true, ...result });
          })
          .withFailureHandler((error) => {
            reject(new Error(error.message || 'GAS call failed'));
          })
          .registerRecord(record);
      });
    }

    // スタンドアロンAPIでの送信
    const endpoint = this.apiConfig.endpoints.register || '/api/register';
    const url = this.apiConfig.baseUrl + endpoint;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(record),
        signal: AbortSignal.timeout(this.apiConfig.timeout)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('リクエストがタイムアウトしました');
      }
      throw error;
    }
  }

  /**
   * Last-Write-Wins 競合解決
   * サーバーから既存データを取得し、タイムスタンプ比較
   */
  async resolveConflict(localRecord, serverRecord) {
    if (!serverRecord) {
      // サーバーにデータがない場合はローカルを採用
      return localRecord;
    }

    const localTimestamp = localRecord.timestamp || 0;
    const serverTimestamp = serverRecord.timestamp || 0;

    // 最終書き込み時刻が新しい方を採用
    if (localTimestamp > serverTimestamp) {
      console.log(`Conflict resolved: local record is newer (${localTimestamp} > ${serverTimestamp})`);
      return localRecord;
    } else {
      console.log(`Conflict resolved: server record is newer (${serverTimestamp} >= ${localTimestamp})`);
      return serverRecord;
    }
  }

  /**
   * マスターデータ同期（品目リストなど）
   */
  async syncMasterData(dataType) {
    if (!navigator.onLine) {
      console.log('Cannot sync master data: offline');
      // オフライン時はキャッシュから取得
      return await offlineDB.getMasterData(dataType);
    }

    try {
      const data = await this.fetchMasterData(dataType);

      if (data) {
        // IndexedDBに保存
        await offlineDB.saveMasterData(dataType, data);
        console.log(`Master data '${dataType}' synced`);
        return data;
      }

      return null;
    } catch (error) {
      console.error(`Failed to sync master data '${dataType}':`, error);

      // エラー時はキャッシュから取得
      return await offlineDB.getMasterData(dataType);
    }
  }

  /**
   * マスターデータ取得
   */
  async fetchMasterData(dataType) {
    // GAS環境での取得
    if (typeof google !== 'undefined' && google.script && google.script.run) {
      return new Promise((resolve, reject) => {
        google.script.run
          .withSuccessHandler(resolve)
          .withFailureHandler(reject)
          .getMasterData(dataType);
      });
    }

    // スタンドアロンAPIでの取得
    const endpoint = this.apiConfig.endpoints.masterData || '/api/master-data';
    const url = `${this.apiConfig.baseUrl}${endpoint}?type=${dataType}`;

    const response = await fetch(url, {
      signal: AbortSignal.timeout(this.apiConfig.timeout)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  }

  /**
   * 同期コールバック登録
   */
  onSync(callback) {
    this.syncCallbacks.push(callback);
  }

  /**
   * コールバック通知
   */
  notifyCallbacks(event, data = null) {
    this.syncCallbacks.forEach(callback => {
      try {
        callback(event, data);
      } catch (error) {
        console.error('Sync callback error:', error);
      }
    });
  }

  /**
   * 同期状態取得
   */
  isSyncing() {
    return this.syncInProgress;
  }

  /**
   * API設定更新
   */
  updateApiConfig(config) {
    this.apiConfig = {
      ...this.apiConfig,
      ...config
    };
  }
}

// グローバルインスタンス
const syncManager = new SyncManager({
  baseUrl: 'https://script.google.com/macros/s/AKfycbxnm6ga-jK6MZ6IYI83RwVcEoSssZCIueiuf0LIfKmlFOtR-pbS0hCg2Q52TLHvDDtJ9A/exec',
  endpoints: {
    register: '',
    masterData: ''
  },
  timeout: 30000
});
