Attribute VB_Name = "OrderManagement"
'===============================================================================
' 発注管理モジュール
' Version: 2.0
' 作成日: 2025-11-27
'===============================================================================

Option Explicit

'===============================================================================
' 発注シート初期化
'===============================================================================

'-------------------------------------------------------------------------------
' 発注シートのセットアップ
'-------------------------------------------------------------------------------
Public Sub SetupOrderSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(ORDER_SHEET)

    ' ヘッダー設定
    With ws
        .Cells(1, 1).Value = "物品名"
        .Cells(1, 2).Value = "現在庫（最小単位）"
        .Cells(1, 3).Value = "発注点（最小単位）"
        .Cells(1, 4).Value = "不足数"
        .Cells(1, 5).Value = "推奨発注数（荷姿）"
        .Cells(1, 6).Value = "推奨発注数（最小単位）"
        .Cells(1, 7).Value = "発注後在庫"
        .Cells(1, 8).Value = "状態"

        ' ヘッダー書式
        .Range("A1:H1").Font.Bold = True
        .Range("A1:H1").Interior.Color = RGB(200, 200, 200)
        .Range("A1:H1").HorizontalAlignment = xlCenter

        ' 列幅調整
        .Columns("A:A").ColumnWidth = 20
        .Columns("B:B").ColumnWidth = 18
        .Columns("C:C").ColumnWidth = 18
        .Columns("D:D").ColumnWidth = 10
        .Columns("E:E").ColumnWidth = 18
        .Columns("F:F").ColumnWidth = 20
        .Columns("G:G").ColumnWidth = 14
        .Columns("H:H").ColumnWidth = 10
    End With
End Sub

'===============================================================================
' 発注判定・リスト生成
'===============================================================================

'-------------------------------------------------------------------------------
' 発注必要品目のリストを生成
'-------------------------------------------------------------------------------
Public Sub GenerateOrderList()
    On Error GoTo ErrorHandler

    Dim wsMaster As Worksheet
    Dim wsOrder As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim orderRow As Long
    Dim itemName As String
    Dim currentStock As Long
    Dim reorderPoint As Long
    Dim shortage As Long
    Dim orderQtyPackage As Long
    Dim orderQtyMin As Long
    Dim afterStock As Long
    Dim status As String

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    Set wsOrder = ThisWorkbook.Sheets(ORDER_SHEET)

    ' 発注シートをクリア
    ClearSheetData ORDER_SHEET

    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row
    orderRow = 2

    Application.ScreenUpdating = False

    ' 各物品をチェック
    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value
        currentStock = wsMaster.Cells(i, 7).Value
        reorderPoint = wsMaster.Cells(i, 6).Value

        ' 発注点以下の場合
        If currentStock <= reorderPoint Then
            ' 不足数計算
            shortage = reorderPoint - currentStock

            ' 推奨発注数計算
            orderQtyMin = CalculateOrderQuantity(itemName, currentStock, reorderPoint)
            orderQtyPackage = ConvertToPackages(orderQtyMin, itemName)

            ' 発注後在庫
            afterStock = currentStock + orderQtyMin

            ' 状態判定
            If currentStock < reorderPoint * 0.5 Then
                status = "🔴緊急"
            ElseIf currentStock < reorderPoint * 0.75 Then
                status = "🟠注意"
            Else
                status = "🟡要確認"
            End If

            ' 発注シートに追加
            With wsOrder
                .Cells(orderRow, 1).Value = itemName
                .Cells(orderRow, 2).Value = currentStock
                .Cells(orderRow, 3).Value = reorderPoint
                .Cells(orderRow, 4).Value = shortage
                .Cells(orderRow, 5).Value = orderQtyPackage
                .Cells(orderRow, 6).Value = orderQtyMin
                .Cells(orderRow, 7).Value = afterStock
                .Cells(orderRow, 8).Value = status

                ' 緊急の場合は行を赤くハイライト
                If status = "🔴緊急" Then
                    .Range("A" & orderRow & ":H" & orderRow).Interior.Color = RGB(255, 200, 200)
                ElseIf status = "🟠注意" Then
                    .Range("A" & orderRow & ":H" & orderRow).Interior.Color = RGB(255, 230, 200)
                End If
            End With

            orderRow = orderRow + 1
        End If
    Next i

    Application.ScreenUpdating = True

    If orderRow = 2 Then
        ShowSuccessMessage "発注が必要な品目はありません。"
    Else
        ShowSuccessMessage "発注必要品目を " & (orderRow - 2) & " 件抽出しました。"
    End If

    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    ShowErrorMessage "発注リスト生成エラー: " & Err.Description
End Sub

'===============================================================================
' 発注数計算
'===============================================================================

'-------------------------------------------------------------------------------
' 推奨発注数を計算（最小単位）
' ロジック: 発注点の2倍まで補充 → 荷姿単位で切り上げ
'-------------------------------------------------------------------------------
Private Function CalculateOrderQuantity(itemName As String, currentStock As Long, reorderPoint As Long) As Long
    Dim targetStock As Long
    Dim shortage As Long
    Dim packageSize As Long
    Dim packages As Long

    ' 目標在庫 = 発注点の2倍
    targetStock = reorderPoint * 2

    ' 不足数
    shortage = targetStock - currentStock

    If shortage <= 0 Then
        CalculateOrderQuantity = 0
        Exit Function
    End If

    ' 荷姿入数
    packageSize = GetPackageSize(itemName)

    ' 荷姿単位で切り上げ
    packages = Application.WorksheetFunction.RoundUp(shortage / packageSize, 0)

    ' 最小単位に戻す
    CalculateOrderQuantity = packages * packageSize
End Function

'-------------------------------------------------------------------------------
' 最小単位 → 荷姿数に変換
'-------------------------------------------------------------------------------
Private Function ConvertToPackages(qtyMin As Long, itemName As String) As Long
    Dim packageSize As Long

    packageSize = GetPackageSize(itemName)

    If packageSize = 0 Then packageSize = 1

    ConvertToPackages = qtyMin \ packageSize
End Function

'===============================================================================
' 発注状態更新
'===============================================================================

'-------------------------------------------------------------------------------
' マスターの状態を更新
'-------------------------------------------------------------------------------
Public Sub UpdateOrderStatus()
    On Error GoTo ErrorHandler

    Dim wsMaster As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim itemName As String
    Dim currentStock As Long
    Dim reorderPoint As Long
    Dim status As String

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    Application.ScreenUpdating = False

    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value
        currentStock = wsMaster.Cells(i, 7).Value
        reorderPoint = wsMaster.Cells(i, 6).Value

        ' 状態判定
        If currentStock < reorderPoint * 0.5 Then
            status = "🔴緊急"
            wsMaster.Cells(i, 8).Interior.Color = RGB(255, 200, 200)
        ElseIf currentStock < reorderPoint * 0.75 Then
            status = "🟠注意"
            wsMaster.Cells(i, 8).Interior.Color = RGB(255, 230, 200)
        ElseIf currentStock <= reorderPoint Then
            status = "🟡要確認"
            wsMaster.Cells(i, 8).Interior.Color = RGB(255, 255, 200)
        Else
            status = "🟢正常"
            wsMaster.Cells(i, 8).Interior.ColorIndex = xlNone
        End If

        wsMaster.Cells(i, 8).Value = status
    Next i

    Application.ScreenUpdating = True

    ShowSuccessMessage "発注状態を更新しました。"
    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    ShowErrorMessage "状態更新エラー: " & Err.Description
End Sub

'===============================================================================
' 発注完了記録
'===============================================================================

'-------------------------------------------------------------------------------
' 発注完了を記録（入庫として記録）
'-------------------------------------------------------------------------------
Public Sub RecordOrderComplete()
    On Error GoTo ErrorHandler

    Dim itemName As String
    Dim orderQty As Long
    Dim packages As Long

    ' 物品名を入力
    itemName = InputBox("発注完了した物品名を入力してください", "発注完了記録")
    If itemName = "" Then Exit Sub

    ' マスターに存在チェック
    If FindItemRow(itemName) = 0 Then
        ShowErrorMessage "マスターに未登録の物品です。"
        Exit Sub
    End If

    ' 発注数を入力（荷姿単位）
    packages = Val(InputBox("発注数を入力してください（" & GetPackageUnitName(itemName) & "）", "発注数", "1"))
    If packages <= 0 Then
        ShowErrorMessage "発注数が0以下です。"
        Exit Sub
    End If

    ' 最小単位に変換
    orderQty = packages * GetPackageSize(itemName)

    ' 確認
    If Not ShowConfirmMessage( _
        "物品: " & itemName & vbCrLf & _
        "発注数: " & packages & GetPackageUnitName(itemName) & " (" & orderQty & GetMinUnitName(itemName) & ")" & vbCrLf & vbCrLf & _
        "入庫として記録します。よろしいですか？") Then
        Exit Sub
    End If

    ' 入出庫履歴に入庫として記録
    Dim ws As Worksheet
    Dim lastRow As Long

    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    With ws
        .Cells(lastRow, 1).Value = Now
        .Cells(lastRow, 2).Value = "入庫"
        .Cells(lastRow, 3).Value = itemName
        .Cells(lastRow, 4).Value = orderQty
        .Cells(lastRow, 5).Value = GetMinUnitName(itemName)
        .Cells(lastRow, 6).Value = "発注完了"
        .Cells(lastRow, 7).Value = FormatAsPackage(orderQty, itemName)
    End With

    ShowSuccessMessage "発注完了を記録しました。" & vbCrLf & "現在庫の再計算を実行してください。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "発注完了記録エラー: " & Err.Description
End Sub
