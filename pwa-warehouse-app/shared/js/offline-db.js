/**
 * IndexedDB Manager for Offline Data Storage
 * 倉庫管理システム - オフラインデータベース管理
 */

class OfflineDB {
  constructor(dbName = 'WarehouseDB', version = 1) {
    this.dbName = dbName;
    this.version = version;
    this.db = null;
  }

  /**
   * データベース初期化
   */
  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => {
        console.error('IndexedDB open error:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        console.log('IndexedDB initialized successfully');
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // 入出庫記録ストア
        if (!db.objectStoreNames.contains('records')) {
          const recordStore = db.createObjectStore('records', {
            keyPath: 'id',
            autoIncrement: true
          });
          recordStore.createIndex('timestamp', 'timestamp', { unique: false });
          recordStore.createIndex('synced', 'synced', { unique: false });
          recordStore.createIndex('registrant', 'registrant', { unique: false });
          recordStore.createIndex('mode', 'mode', { unique: false });
        }

        // ユーザー情報ストア
        if (!db.objectStoreNames.contains('users')) {
          const userStore = db.createObjectStore('users', {
            keyPath: 'id'
          });
          userStore.createIndex('loginId', 'loginId', { unique: true });
        }

        // マスターデータストア（品目など）
        if (!db.objectStoreNames.contains('masterData')) {
          const masterStore = db.createObjectStore('masterData', {
            keyPath: 'key'
          });
        }

        // 同期キューストア
        if (!db.objectStoreNames.contains('syncQueue')) {
          const syncStore = db.createObjectStore('syncQueue', {
            keyPath: 'id',
            autoIncrement: true
          });
          syncStore.createIndex('timestamp', 'timestamp', { unique: false });
          syncStore.createIndex('type', 'type', { unique: false });
        }

        console.log('IndexedDB schema upgraded to version', this.version);
      };
    });
  }

  /**
   * レコード追加
   */
  async addRecord(record) {
    const transaction = this.db.transaction(['records'], 'readwrite');
    const store = transaction.objectStore('records');

    // タイムスタンプと同期状態を追加
    const recordWithMeta = {
      ...record,
      timestamp: Date.now(),
      synced: false,
      localId: this.generateLocalId()
    };

    return new Promise((resolve, reject) => {
      const request = store.add(recordWithMeta);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * レコード取得（全件）
   */
  async getAllRecords() {
    const transaction = this.db.transaction(['records'], 'readonly');
    const store = transaction.objectStore('records');

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * 未同期レコード取得
   */
  async getUnsyncedRecords() {
    const transaction = this.db.transaction(['records'], 'readonly');
    const store = transaction.objectStore('records');
    const index = store.index('synced');

    return new Promise((resolve, reject) => {
      const request = index.getAll(false);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * レコードを同期済みにマーク
   */
  async markAsSynced(id, serverId = null) {
    const transaction = this.db.transaction(['records'], 'readwrite');
    const store = transaction.objectStore('records');

    return new Promise((resolve, reject) => {
      const getRequest = store.get(id);

      getRequest.onsuccess = () => {
        const record = getRequest.result;
        if (record) {
          record.synced = true;
          record.syncedAt = Date.now();
          if (serverId) {
            record.serverId = serverId;
          }

          const updateRequest = store.put(record);
          updateRequest.onsuccess = () => resolve(updateRequest.result);
          updateRequest.onerror = () => reject(updateRequest.error);
        } else {
          reject(new Error('Record not found'));
        }
      };

      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  /**
   * レコード削除
   */
  async deleteRecord(id) {
    const transaction = this.db.transaction(['records'], 'readwrite');
    const store = transaction.objectStore('records');

    return new Promise((resolve, reject) => {
      const request = store.delete(id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * 同期キューに追加
   */
  async addToSyncQueue(operation) {
    const transaction = this.db.transaction(['syncQueue'], 'readwrite');
    const store = transaction.objectStore('syncQueue');

    const queueItem = {
      ...operation,
      timestamp: Date.now(),
      retries: 0
    };

    return new Promise((resolve, reject) => {
      const request = store.add(queueItem);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * 同期キュー取得
   */
  async getSyncQueue() {
    const transaction = this.db.transaction(['syncQueue'], 'readonly');
    const store = transaction.objectStore('syncQueue');

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * 同期キューからアイテム削除
   */
  async removeFromSyncQueue(id) {
    const transaction = this.db.transaction(['syncQueue'], 'readwrite');
    const store = transaction.objectStore('syncQueue');

    return new Promise((resolve, reject) => {
      const request = store.delete(id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * マスターデータ保存
   */
  async saveMasterData(key, data) {
    const transaction = this.db.transaction(['masterData'], 'readwrite');
    const store = transaction.objectStore('masterData');

    const masterItem = {
      key,
      data,
      updatedAt: Date.now()
    };

    return new Promise((resolve, reject) => {
      const request = store.put(masterItem);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * マスターデータ取得
   */
  async getMasterData(key) {
    const transaction = this.db.transaction(['masterData'], 'readonly');
    const store = transaction.objectStore('masterData');

    return new Promise((resolve, reject) => {
      const request = store.get(key);
      request.onsuccess = () => {
        const result = request.result;
        resolve(result ? result.data : null);
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * ユーザー情報保存
   */
  async saveUser(user) {
    const transaction = this.db.transaction(['users'], 'readwrite');
    const store = transaction.objectStore('users');

    return new Promise((resolve, reject) => {
      const request = store.put(user);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * ユーザー情報取得（ログインID）
   */
  async getUserByLoginId(loginId) {
    const transaction = this.db.transaction(['users'], 'readonly');
    const store = transaction.objectStore('users');
    const index = store.index('loginId');

    return new Promise((resolve, reject) => {
      const request = index.get(loginId);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * ローカルID生成
   */
  generateLocalId() {
    return `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * データベースクリア（デバッグ用）
   */
  async clearAll() {
    const storeNames = ['records', 'users', 'masterData', 'syncQueue'];
    const promises = storeNames.map(storeName => {
      return new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.clear();
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    });

    return Promise.all(promises);
  }

  /**
   * データベースクローズ
   */
  close() {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

// グローバルインスタンス
const offlineDB = new OfflineDB();
