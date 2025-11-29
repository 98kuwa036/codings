Attribute VB_Name = "InventoryOperations"
'===============================================================================
' 棚卸操作モジュール
' Version: 2.0
' 作成日: 2025-11-27
'===============================================================================

Option Explicit

'===============================================================================
' 棚卸シート初期化
'===============================================================================

'-------------------------------------------------------------------------------
' 棚卸シートのセットアップ
'-------------------------------------------------------------------------------
Public Sub SetupInventorySheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(INVENTORY_SHEET)

    ' ヘッダー設定
    With ws
        .Cells(1, 1).Value = "日付"
        .Cells(1, 2).Value = "物品名"
        .Cells(1, 3).Value = "数量（最小単位）"
        .Cells(1, 4).Value = "単位"
        .Cells(1, 5).Value = "荷姿換算"

        ' ヘッダー書式
        .Range("A1:E1").Font.Bold = True
        .Range("A1:E1").Interior.Color = RGB(200, 200, 200)
        .Range("A1:E1").HorizontalAlignment = xlCenter

        ' 列幅調整
        .Columns("A:A").ColumnWidth = 12
        .Columns("B:B").ColumnWidth = 20
        .Columns("C:C").ColumnWidth = 16
        .Columns("D:D").ColumnWidth = 10
        .Columns("E:E").ColumnWidth = 20
    End With
End Sub

'===============================================================================
' 棚卸入力
'===============================================================================

'-------------------------------------------------------------------------------
' 棚卸データを入力（荷姿+端数入力、最小単位で保存）
'-------------------------------------------------------------------------------
Public Sub InputInventory()
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim itemName As String
    Dim packages As Long
    Dim remainder As Long
    Dim totalQty As Long
    Dim minUnit As String
    Dim packageUnit As String
    Dim lastRow As Long

    Set ws = ThisWorkbook.Sheets(INVENTORY_SHEET)

    ' 物品名を入力
    itemName = InputBox("物品名を入力してください", "棚卸入力")
    If itemName = "" Then Exit Sub

    ' マスターに存在チェック
    If FindItemRow(itemName) = 0 Then
        If ShowConfirmMessage("マスターに未登録の物品です。登録しますか？") Then
            Call AddNewItem
        End If
        Exit Sub
    End If

    ' 単位情報取得
    minUnit = GetMinUnitName(itemName)
    packageUnit = GetPackageUnitName(itemName)

    ' 荷姿入力
    packages = Val(InputBox("荷姿数を入力してください（" & packageUnit & "）", "荷姿入力", "0"))
    If packages < 0 Then packages = 0

    ' 端数入力
    remainder = Val(InputBox("端数を入力してください（" & minUnit & "）", "端数入力", "0"))
    If remainder < 0 Then remainder = 0

    ' 最小単位に変換
    totalQty = ConvertToMinUnit(packages, remainder, itemName)

    ' 確認
    Dim confirmMsg As String
    confirmMsg = "物品名: " & itemName & vbCrLf & _
                 "荷姿: " & packages & packageUnit & vbCrLf & _
                 "端数: " & remainder & minUnit & vbCrLf & _
                 "合計: " & totalQty & minUnit & vbCrLf & vbCrLf & _
                 "この内容で登録しますか？"

    If Not ShowConfirmMessage(confirmMsg) Then Exit Sub

    ' データ追加
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    With ws
        .Cells(lastRow, 1).Value = Date
        .Cells(lastRow, 2).Value = itemName
        .Cells(lastRow, 3).Value = totalQty ' 最小単位で保存
        .Cells(lastRow, 4).Value = minUnit
        .Cells(lastRow, 5).Value = FormatAsPackage(totalQty, itemName) ' 荷姿表示
    End With

    ShowSuccessMessage "棚卸データを登録しました。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "棚卸入力エラー: " & Err.Description
End Sub

'===============================================================================
' 現在庫計算
'===============================================================================

'-------------------------------------------------------------------------------
' 全物品の現在庫を計算してマスターを更新
'-------------------------------------------------------------------------------
Public Sub CalculateAllCurrentStock()
    On Error GoTo ErrorHandler

    Dim wsMaster As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim itemName As String
    Dim currentStock As Long

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    If lastRow < 2 Then
        ShowErrorMessage "マスターデータがありません。"
        Exit Sub
    End If

    Application.ScreenUpdating = False

    ' 各物品の現在庫を計算
    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value
        currentStock = CalculateCurrentStock(itemName)
        wsMaster.Cells(i, 7).Value = currentStock
    Next i

    Application.ScreenUpdating = True

    ShowSuccessMessage "現在庫の計算が完了しました。"
    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    ShowErrorMessage "現在庫計算エラー: " & Err.Description
End Sub

'-------------------------------------------------------------------------------
' 特定物品の現在庫を計算
' 計算式: 棚卸数量 + 入庫合計 - 出庫合計
'-------------------------------------------------------------------------------
Public Function CalculateCurrentStock(itemName As String) As Long
    On Error GoTo ErrorHandler

    Dim inventoryQty As Long
    Dim inQty As Long
    Dim outQty As Long

    ' 最新の棚卸数量を取得
    inventoryQty = GetLatestInventoryQty(itemName)

    ' 入庫合計を取得
    inQty = GetTransactionTotal(itemName, "入庫")

    ' 出庫合計を取得
    outQty = GetTransactionTotal(itemName, "出庫")

    ' 現在庫計算
    CalculateCurrentStock = inventoryQty + inQty - outQty

    If CalculateCurrentStock < 0 Then CalculateCurrentStock = 0

    Exit Function

ErrorHandler:
    CalculateCurrentStock = 0
End Function

'-------------------------------------------------------------------------------
' 最新の棚卸数量を取得
'-------------------------------------------------------------------------------
Private Function GetLatestInventoryQty(itemName As String) As Long
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(INVENTORY_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    ' 最新の棚卸データを検索（下から上へ）
    For i = lastRow To 2 Step -1
        If ws.Cells(i, 2).Value = itemName Then
            GetLatestInventoryQty = ws.Cells(i, 3).Value
            Exit Function
        End If
    Next i

    GetLatestInventoryQty = 0
End Function

'-------------------------------------------------------------------------------
' 入出庫合計を取得
'-------------------------------------------------------------------------------
Private Function GetTransactionTotal(itemName As String, transType As String) As Long
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim total As Long

    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    total = 0

    For i = 2 To lastRow
        If ws.Cells(i, 3).Value = itemName And ws.Cells(i, 2).Value = transType Then
            total = total + ws.Cells(i, 4).Value
        End If
    Next i

    GetTransactionTotal = total
End Function

'===============================================================================
' 在庫一覧表示
'===============================================================================

'-------------------------------------------------------------------------------
' 在庫一覧シートのセットアップ
'-------------------------------------------------------------------------------
Public Sub SetupStockViewSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(STOCK_VIEW_SHEET)

    ' ヘッダー設定
    With ws
        .Cells(1, 1).Value = "物品名"
        .Cells(1, 2).Value = "現在庫（最小単位）"
        .Cells(1, 3).Value = "現在庫（荷姿換算）"
        .Cells(1, 4).Value = "発注点（最小単位）"
        .Cells(1, 5).Value = "発注点（荷姿換算）"
        .Cells(1, 6).Value = "余裕"
        .Cells(1, 7).Value = "状態"

        ' ヘッダー書式
        .Range("A1:G1").Font.Bold = True
        .Range("A1:G1").Interior.Color = RGB(200, 200, 200)
        .Range("A1:G1").HorizontalAlignment = xlCenter

        ' 列幅調整
        .Columns("A:A").ColumnWidth = 20
        .Columns("B:B").ColumnWidth = 18
        .Columns("C:C").ColumnWidth = 25
        .Columns("D:D").ColumnWidth = 18
        .Columns("E:E").ColumnWidth = 25
        .Columns("F:F").ColumnWidth = 12
        .Columns("G:G").ColumnWidth = 10
    End With
End Sub

'-------------------------------------------------------------------------------
' 在庫一覧を更新
'-------------------------------------------------------------------------------
Public Sub UpdateStockView()
    On Error GoTo ErrorHandler

    Dim wsMaster As Worksheet
    Dim wsView As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim itemName As String
    Dim currentStock As Long
    Dim reorderPoint As Long
    Dim diff As Long
    Dim status As String

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    Set wsView = ThisWorkbook.Sheets(STOCK_VIEW_SHEET)

    ' データクリア
    ClearSheetData STOCK_VIEW_SHEET

    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    Application.ScreenUpdating = False

    ' データ転記
    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value
        currentStock = wsMaster.Cells(i, 7).Value
        reorderPoint = wsMaster.Cells(i, 6).Value
        diff = currentStock - reorderPoint

        ' 状態判定
        If currentStock < reorderPoint * 0.5 Then
            status = "🔴緊急"
        ElseIf currentStock < reorderPoint * 0.75 Then
            status = "🟠注意"
        ElseIf currentStock < reorderPoint Then
            status = "🟡要確認"
        Else
            status = "🟢正常"
        End If

        With wsView
            .Cells(i, 1).Value = itemName
            .Cells(i, 2).Value = currentStock & GetMinUnitName(itemName)
            .Cells(i, 3).Value = FormatAsPackage(currentStock, itemName)
            .Cells(i, 4).Value = reorderPoint & GetMinUnitName(itemName)
            .Cells(i, 5).Value = FormatAsPackage(reorderPoint, itemName)
            .Cells(i, 6).Value = IIf(diff >= 0, "+", "") & diff & GetMinUnitName(itemName)
            .Cells(i, 7).Value = status
        End With
    Next i

    Application.ScreenUpdating = True

    ShowSuccessMessage "在庫一覧を更新しました。"
    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    ShowErrorMessage "在庫一覧更新エラー: " & Err.Description
End Sub
