================================================================================
VBAモジュール インポート手順
================================================================================

以下の手順で各.basファイルの内容を標準モジュールにコピーしてください。

【手順】
1. Excelを開き、Alt+F11でVBAエディタを開く

2. 以下の順序で9つのモジュールを作成：
   - プロジェクトを右クリック → 挿入 → 標準モジュール
   
3. 各モジュールの名前を設定（プロパティウィンドウで変更）：
   - Module1 → Utils
   - Module2 → CSVHandler
   - Module3 → MasterManagement
   - Module4 → InventoryOperations
   - Module5 → TransactionLog
   - Module6 → OrderManagement
   - Module7 → TrendAnalysis
   - Module8 → AlertDashboard
   - Module9 → Main

4. 各.basファイルをメモ帳またはVSCodeで開く

5. ファイル内容を**すべて選択してコピー**

6. VBAエディタの対応するモジュールウィンドウに**ペースト**

7. すべてのモジュールで繰り返す

8. Main.basの InitializeSystem を実行してシートを作成

【推奨インポート順序】
1. Utils.bas           （共通関数 - 最初に必要）
2. CSVHandler.bas      （CSV処理）
3. MasterManagement.bas
4. InventoryOperations.bas
5. TransactionLog.bas
6. OrderManagement.bas
7. TrendAnalysis.bas
8. AlertDashboard.bas
9. Main.bas            （メイン処理 - 最後）

【注意】
- Attribute VB_Name = "モジュール名" の行は削除済みです
- ファイル先頭のコメントにモジュール名が記載されています
- UTF-8エンコーディングのまま使用できます

================================================================================
