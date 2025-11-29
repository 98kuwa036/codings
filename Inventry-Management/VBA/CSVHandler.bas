Attribute VB_Name = "CSVHandler"
'===============================================================================
' CSV入出力モジュール
' Version: 2.0
' 作成日: 2025-11-27
'===============================================================================

Option Explicit

'===============================================================================
' CSVインポート機能
'===============================================================================

'-------------------------------------------------------------------------------
' 棚卸CSVをインポート（最小単位で保存）
'-------------------------------------------------------------------------------
Public Sub ImportInventoryCSV()
    On Error GoTo ErrorHandler

    Dim filePath As Variant
    Dim ws As Worksheet
    Dim fileNum As Integer
    Dim lineText As String
    Dim rowNum As Long
    Dim fields() As String

    ' ファイル選択ダイアログ
    filePath = Application.GetOpenFilename("CSVファイル (*.csv),*.csv", , "棚卸CSVを選択")
    If filePath = False Then Exit Sub

    ' シート取得
    Set ws = ThisWorkbook.Sheets(INVENTORY_SHEET)

    ' 確認メッセージ
    If Not ShowConfirmMessage("既存の棚卸データは削除されます。よろしいですか？") Then
        Exit Sub
    End If

    ' データクリア
    ClearSheetData INVENTORY_SHEET

    ' CSVファイルを読み込み
    fileNum = FreeFile
    Open filePath For Input As fileNum

    rowNum = 2

    Do While Not EOF(fileNum)
        Line Input #fileNum, lineText

        ' ヘッダー行をスキップ
        If InStr(lineText, "日付") > 0 Then GoTo NextLine
        If Trim(lineText) = "" Then GoTo NextLine

        ' カンマで分割
        fields = Split(lineText, ",")

        If UBound(fields) >= 2 Then
            ws.Cells(rowNum, 1).Value = fields(0) ' 日付
            ws.Cells(rowNum, 2).Value = fields(1) ' 物品名
            ws.Cells(rowNum, 3).Value = CLng(fields(2)) ' 数量（最小単位）
            ws.Cells(rowNum, 4).Value = GetMinUnitName(fields(1)) ' 単位
            rowNum = rowNum + 1
        End If

NextLine:
    Loop

    Close fileNum

    ShowSuccessMessage "棚卸データを " & (rowNum - 2) & " 件インポートしました。"
    Exit Sub

ErrorHandler:
    If fileNum > 0 Then Close fileNum
    ShowErrorMessage "CSVインポートエラー: " & Err.Description
End Sub

'-------------------------------------------------------------------------------
' 入出庫CSVをインポート（最小単位で保存）
'-------------------------------------------------------------------------------
Public Sub ImportTransactionCSV()
    On Error GoTo ErrorHandler

    Dim filePath As Variant
    Dim ws As Worksheet
    Dim fileNum As Integer
    Dim lineText As String
    Dim rowNum As Long
    Dim fields() As String
    Dim lastRow As Long

    ' ファイル選択ダイアログ
    filePath = Application.GetOpenFilename("CSVファイル (*.csv),*.csv", , "入出庫CSVを選択")
    If filePath = False Then Exit Sub

    ' シート取得
    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    ' 確認メッセージ
    If Not ShowConfirmMessage("入出庫履歴に追加します。よろしいですか？") Then
        Exit Sub
    End If

    ' 最終行を取得
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    rowNum = lastRow + 1

    ' CSVファイルを読み込み
    fileNum = FreeFile
    Open filePath For Input As fileNum

    Do While Not EOF(fileNum)
        Line Input #fileNum, lineText

        ' ヘッダー行をスキップ
        If InStr(lineText, "日時") > 0 Then GoTo NextLine2
        If Trim(lineText) = "" Then GoTo NextLine2

        ' カンマで分割
        fields = Split(lineText, ",")

        If UBound(fields) >= 4 Then
            ws.Cells(rowNum, 1).Value = fields(0) ' 日時
            ws.Cells(rowNum, 2).Value = fields(1) ' 種別
            ws.Cells(rowNum, 3).Value = fields(2) ' 物品名
            ws.Cells(rowNum, 4).Value = CLng(fields(3)) ' 数量（最小単位）
            ws.Cells(rowNum, 5).Value = GetMinUnitName(fields(2)) ' 単位
            If UBound(fields) >= 5 Then
                ws.Cells(rowNum, 6).Value = fields(5) ' 記録者
            End If
            rowNum = rowNum + 1
        End If

NextLine2:
    Loop

    Close fileNum

    ShowSuccessMessage "入出庫データを " & (rowNum - lastRow - 1) & " 件追加しました。"
    Exit Sub

ErrorHandler:
    If fileNum > 0 Then Close fileNum
    ShowErrorMessage "CSVインポートエラー: " & Err.Description
End Sub

'===============================================================================
' CSVエクスポート機能
'===============================================================================

'-------------------------------------------------------------------------------
' 発注リストをCSV出力（荷姿単位版）
'-------------------------------------------------------------------------------
Public Sub ExportOrderListPackage()
    On Error GoTo ErrorHandler

    Dim filePath As Variant
    Dim ws As Worksheet
    Dim fileNum As Integer
    Dim lastRow As Long
    Dim i As Long
    Dim itemName As String
    Dim orderQty As Long
    Dim packageUnit As String

    ' 保存先選択
    filePath = Application.GetSaveAsFilename( _
        InitialFileName:="発注リスト_荷姿_" & GetDateString() & ".csv", _
        FileFilter:="CSVファイル (*.csv),*.csv")

    If filePath = False Then Exit Sub

    ' シート取得
    Set ws = ThisWorkbook.Sheets(ORDER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        ShowErrorMessage "発注が必要な品目がありません。"
        Exit Sub
    End If

    ' CSVファイルに書き込み
    fileNum = FreeFile
    Open filePath For Output As fileNum

    ' ヘッダー
    Print #fileNum, "物品名,発注数,単位"

    ' データ行
    For i = 2 To lastRow
        itemName = ws.Cells(i, 1).Value
        orderQty = ws.Cells(i, 5).Value ' 推奨発注数（荷姿）
        packageUnit = GetPackageUnitName(itemName)

        Print #fileNum, itemName & "," & orderQty & "," & packageUnit
    Next i

    Close fileNum

    ShowSuccessMessage "発注リスト（荷姿単位）を出力しました。" & vbCrLf & filePath
    Exit Sub

ErrorHandler:
    If fileNum > 0 Then Close fileNum
    ShowErrorMessage "CSV出力エラー: " & Err.Description
End Sub

'-------------------------------------------------------------------------------
' 発注リストをCSV出力（最小単位版・データ管理用）
'-------------------------------------------------------------------------------
Public Sub ExportOrderListDetail()
    On Error GoTo ErrorHandler

    Dim filePath As Variant
    Dim ws As Worksheet
    Dim fileNum As Integer
    Dim lastRow As Long
    Dim i As Long
    Dim itemName As String
    Dim currentStock As Long
    Dim reorderPoint As Long
    Dim orderQtyPackage As Long
    Dim orderQtyMin As Long
    Dim packageUnit As String
    Dim minUnit As String

    ' 保存先選択
    filePath = Application.GetSaveAsFilename( _
        InitialFileName:="発注リスト_詳細_" & GetDateString() & ".csv", _
        FileFilter:="CSVファイル (*.csv),*.csv")

    If filePath = False Then Exit Sub

    ' シート取得
    Set ws = ThisWorkbook.Sheets(ORDER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        ShowErrorMessage "発注が必要な品目がありません。"
        Exit Sub
    End If

    ' CSVファイルに書き込み
    fileNum = FreeFile
    Open filePath For Output As fileNum

    ' ヘッダー
    Print #fileNum, "物品名,現在庫,単位,発注点,推奨発注数（荷姿）,推奨発注数（最小単位）,発注後在庫"

    ' データ行
    For i = 2 To lastRow
        itemName = ws.Cells(i, 1).Value
        currentStock = ws.Cells(i, 2).Value
        reorderPoint = ws.Cells(i, 3).Value
        orderQtyPackage = ws.Cells(i, 5).Value
        orderQtyMin = ws.Cells(i, 6).Value
        packageUnit = GetPackageUnitName(itemName)
        minUnit = GetMinUnitName(itemName)

        Print #fileNum, itemName & "," & _
                        currentStock & "," & _
                        minUnit & "," & _
                        reorderPoint & "," & _
                        orderQtyPackage & packageUnit & "," & _
                        orderQtyMin & "," & _
                        (currentStock + orderQtyMin)
    Next i

    Close fileNum

    ShowSuccessMessage "発注リスト（詳細）を出力しました。" & vbCrLf & filePath
    Exit Sub

ErrorHandler:
    If fileNum > 0 Then Close fileNum
    ShowErrorMessage "CSV出力エラー: " & Err.Description
End Sub

'-------------------------------------------------------------------------------
' 使用量トレンドをCSV出力（最小単位）
'-------------------------------------------------------------------------------
Public Sub ExportUsageTrend()
    On Error GoTo ErrorHandler

    Dim filePath As Variant
    Dim ws As Worksheet
    Dim fileNum As Integer
    Dim lastRow As Long
    Dim i As Long

    ' 保存先選択
    filePath = Application.GetSaveAsFilename( _
        InitialFileName:="使用量トレンド_" & GetDateString() & ".csv", _
        FileFilter:="CSVファイル (*.csv),*.csv")

    If filePath = False Then Exit Sub

    ' シート取得
    Set ws = ThisWorkbook.Sheets(TREND_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        ShowErrorMessage "データがありません。"
        Exit Sub
    End If

    ' CSVファイルに書き込み
    fileNum = FreeFile
    Open filePath For Output As fileNum

    ' ヘッダー
    Print #fileNum, "年月,物品名,使用量,単位,前月比"

    ' データ行
    For i = 2 To lastRow
        Print #fileNum, ws.Cells(i, 1).Value & "," & _
                        ws.Cells(i, 2).Value & "," & _
                        ws.Cells(i, 3).Value & "," & _
                        ws.Cells(i, 4).Value & "," & _
                        ws.Cells(i, 5).Value
    Next i

    Close fileNum

    ShowSuccessMessage "使用量トレンドを出力しました。" & vbCrLf & filePath
    Exit Sub

ErrorHandler:
    If fileNum > 0 Then Close fileNum
    ShowErrorMessage "CSV出力エラー: " & Err.Description
End Sub
