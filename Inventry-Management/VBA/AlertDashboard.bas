Attribute VB_Name = "AlertDashboard"
'===============================================================================
' アラートダッシュボードモジュール
' Version: 2.0
' 作成日: 2025-11-27
'===============================================================================

Option Explicit

'===============================================================================
' アラートシート初期化
'===============================================================================

'-------------------------------------------------------------------------------
' アラートシートのセットアップ
'-------------------------------------------------------------------------------
Public Sub SetupAlertSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(ALERT_SHEET)

    ws.Cells.Clear

    ' タイトル
    With ws.Range("A1:G1")
        .Merge
        .Value = "【在庫アラートダッシュボード】"
        .Font.Size = 18
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
        .Interior.Color = RGB(255, 200, 100)
    End With

    ' 発注必要セクション
    ws.Range("A3").Value = "■ 発注必要品目"
    ws.Range("A3").Font.Size = 14
    ws.Range("A3").Font.Bold = True

    With ws
        .Cells(4, 1).Value = "物品名"
        .Cells(4, 2).Value = "現在庫"
        .Cells(4, 3).Value = "発注点"
        .Cells(4, 4).Value = "不足"
        .Cells(4, 5).Value = "推奨発注"
        .Cells(4, 6).Value = "状態"

        .Range("A4:F4").Font.Bold = True
        .Range("A4:F4").Interior.Color = RGB(220, 220, 220)
    End With

    ' 使用急増セクション（20行下に配置）
    ws.Range("A23").Value = "■ 使用量急増品目"
    ws.Range("A23").Font.Size = 14
    ws.Range("A23").Font.Bold = True

    With ws
        .Cells(24, 1).Value = "物品名"
        .Cells(24, 2).Value = "今月使用量"
        .Cells(24, 3).Value = "前月使用量"
        .Cells(24, 4).Value = "増加率"
        .Cells(24, 5).Value = "3ヶ月平均"
        .Cells(24, 6).Value = "状態"

        .Range("A24:F24").Font.Bold = True
        .Range("A24:F24").Interior.Color = RGB(220, 220, 220)
    End With

    ' 列幅調整
    ws.Columns("A:A").ColumnWidth = 20
    ws.Columns("B:B").ColumnWidth = 25
    ws.Columns("C:C").ColumnWidth = 25
    ws.Columns("D:D").ColumnWidth = 15
    ws.Columns("E:E").ColumnWidth = 25
    ws.Columns("F:F").ColumnWidth = 10
End Sub

'===============================================================================
' アラート更新
'===============================================================================

'-------------------------------------------------------------------------------
' アラートダッシュボードを更新
'-------------------------------------------------------------------------------
Public Sub UpdateAlertDashboard()
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(ALERT_SHEET)

    Application.ScreenUpdating = False

    ' シートをクリアして再セットアップ
    SetupAlertSheet

    ' 発注アラートを表示
    DisplayOrderAlerts ws

    ' 使用急増アラートを表示
    DisplayUsageSurgeAlerts ws

    Application.ScreenUpdating = True

    ShowSuccessMessage "アラートダッシュボードを更新しました。"
    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    ShowErrorMessage "ダッシュボード更新エラー: " & Err.Description
End Sub

'===============================================================================
' 発注アラート表示
'===============================================================================

'-------------------------------------------------------------------------------
' 発注必要品目をアラート表示
'-------------------------------------------------------------------------------
Private Sub DisplayOrderAlerts(ws As Worksheet)
    Dim wsMaster As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim alertRow As Long
    Dim itemName As String
    Dim currentStock As Long
    Dim reorderPoint As Long
    Dim shortage As Long
    Dim orderQty As Long
    Dim status As String
    Dim alertCount As Integer

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    alertRow = 5
    alertCount = 0

    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value
        currentStock = wsMaster.Cells(i, 7).Value
        reorderPoint = wsMaster.Cells(i, 6).Value

        ' 発注点以下の場合のみ表示
        If currentStock <= reorderPoint Then
            shortage = reorderPoint - currentStock
            orderQty = CalculateOrderQuantity(itemName, currentStock, reorderPoint)

            ' 状態判定
            If currentStock < reorderPoint * 0.5 Then
                status = "[緊急]"
            ElseIf currentStock < reorderPoint * 0.75 Then
                status = "[注意]"
            Else
                status = "[要確認]"
            End If

            ' データ表示
            With ws
                .Cells(alertRow, 1).Value = itemName
                .Cells(alertRow, 2).Value = FormatAsPackage(currentStock, itemName)
                .Cells(alertRow, 3).Value = FormatAsPackage(reorderPoint, itemName)
                .Cells(alertRow, 4).Value = "-" & shortage & GetMinUnitName(itemName)
                .Cells(alertRow, 5).Value = ConvertToPackages(orderQty, itemName) & GetPackageUnitName(itemName) & _
                                             " (" & orderQty & GetMinUnitName(itemName) & ")"
                .Cells(alertRow, 6).Value = status

                ' ハイライト
                If status = "[緊急]" Then
                    .Range("A" & alertRow & ":F" & alertRow).Interior.Color = RGB(255, 200, 200)
                    .Cells(alertRow, 6).Font.Color = RGB(200, 0, 0)
                    .Cells(alertRow, 6).Font.Bold = True
                ElseIf status = "[注意]" Then
                    .Range("A" & alertRow & ":F" & alertRow).Interior.Color = RGB(255, 230, 200)
                    .Cells(alertRow, 6).Font.Color = RGB(255, 100, 0)
                    .Cells(alertRow, 6).Font.Bold = True
                Else
                    .Range("A" & alertRow & ":F" & alertRow).Interior.Color = RGB(255, 255, 220)
                    .Cells(alertRow, 6).Font.Color = RGB(200, 150, 0)
                    .Cells(alertRow, 6).Font.Bold = True
                End If
            End With

            alertRow = alertRow + 1
            alertCount = alertCount + 1
        End If
    Next i

    ' アラート件数を表示
    ws.Range("A3").Value = "■ 発注必要品目 (" & alertCount & "件)"

    If alertCount = 0 Then
        ws.Cells(5, 1).Value = "発注が必要な品目はありません"
        ws.Range("A5:F5").Merge
        ws.Range("A5").HorizontalAlignment = xlCenter
        ws.Range("A5").Interior.Color = RGB(200, 255, 200)
    End If
End Sub

'===============================================================================
' 使用急増アラート表示
'===============================================================================

'-------------------------------------------------------------------------------
' 使用量急増品目をアラート表示
'-------------------------------------------------------------------------------
Private Sub DisplayUsageSurgeAlerts(ws As Worksheet)
    Dim wsMaster As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim alertRow As Long
    Dim itemName As String
    Dim currentMonth As String
    Dim prevMonth As String
    Dim currentUsage As Long
    Dim prevUsage As Long
    Dim avgUsage As Long
    Dim changeRate As Double
    Dim alertCount As Integer

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    currentMonth = Format(Date, "yyyy-mm")
    prevMonth = Format(DateAdd("m", -1, Date), "yyyy-mm")

    alertRow = 25
    alertCount = 0

    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value
        currentUsage = GetMonthlyUsage(itemName, currentMonth)
        prevUsage = GetMonthlyUsage(itemName, prevMonth)
        avgUsage = Calculate3MonthAverage(itemName)

        ' 前月比率計算
        If prevUsage > 0 Then
            changeRate = ((currentUsage - prevUsage) / prevUsage) * 100
        ElseIf currentUsage > 0 Then
            changeRate = 100
        Else
            changeRate = 0
        End If

        ' 急増判定（前月比150%以上 または 3ヶ月平均の2倍以上）
        If (changeRate >= 150 And prevUsage > 0) Or (currentUsage >= avgUsage * 2 And avgUsage > 0) Then
            With ws
                .Cells(alertRow, 1).Value = itemName
                .Cells(alertRow, 2).Value = FormatAsPackage(currentUsage, itemName)
                .Cells(alertRow, 3).Value = FormatAsPackage(prevUsage, itemName)
                .Cells(alertRow, 4).Value = "+" & Format(changeRate, "0") & "%"
                .Cells(alertRow, 5).Value = FormatAsPackage(avgUsage, itemName)
                .Cells(alertRow, 6).Value = "[急増]"

                ' ハイライト
                .Range("A" & alertRow & ":F" & alertRow).Interior.Color = RGB(255, 255, 200)
                .Cells(alertRow, 6).Font.Color = RGB(200, 150, 0)
                .Cells(alertRow, 6).Font.Bold = True
            End With

            alertRow = alertRow + 1
            alertCount = alertCount + 1
        End If
    Next i

    ' アラート件数を表示
    ws.Range("A23").Value = "■ 使用量急増品目 (" & alertCount & "件)"

    If alertCount = 0 Then
        ws.Cells(25, 1).Value = "使用量が急増している品目はありません"
        ws.Range("A25:F25").Merge
        ws.Range("A25").HorizontalAlignment = xlCenter
        ws.Range("A25").Interior.Color = RGB(200, 255, 200)
    End If
End Sub

'===============================================================================
' ワンクリック更新ボタン
'===============================================================================

'-------------------------------------------------------------------------------
' ダッシュボードをワンクリックで全更新
'-------------------------------------------------------------------------------
Public Sub RefreshAll()
    On Error GoTo ErrorHandler

    Application.ScreenUpdating = False

    ' 現在庫計算
    Call CalculateAllCurrentStock

    ' 発注状態更新
    Call UpdateOrderStatus

    ' トレンド分析
    Call AnalyzeMonthlyUsage

    ' 在庫一覧更新
    Call UpdateStockView

    ' アラートダッシュボード更新
    Call UpdateAlertDashboard

    Application.ScreenUpdating = True

    ShowSuccessMessage "全データを更新しました。"
    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    ShowErrorMessage "更新エラー: " & Err.Description
End Sub

'===============================================================================
' 補助関数（他モジュールからコピー）
'===============================================================================

Private Function CalculateOrderQuantity(itemName As String, currentStock As Long, reorderPoint As Long) As Long
    Dim targetStock As Long
    Dim shortage As Long
    Dim packageSize As Long
    Dim packages As Long

    targetStock = reorderPoint * 2
    shortage = targetStock - currentStock

    If shortage <= 0 Then
        CalculateOrderQuantity = 0
        Exit Function
    End If

    packageSize = GetPackageSize(itemName)
    packages = Application.WorksheetFunction.RoundUp(shortage / packageSize, 0)
    CalculateOrderQuantity = packages * packageSize
End Function

Private Function ConvertToPackages(qtyMin As Long, itemName As String) As Long
    Dim packageSize As Long
    packageSize = GetPackageSize(itemName)
    If packageSize = 0 Then packageSize = 1
    ConvertToPackages = qtyMin \ packageSize
End Function

Private Function Calculate3MonthAverage(itemName As String) As Long
    Dim month1 As String, month2 As String, month3 As String
    Dim total As Long

    month1 = Format(DateAdd("m", -1, Date), "yyyy-mm")
    month2 = Format(DateAdd("m", -2, Date), "yyyy-mm")
    month3 = Format(DateAdd("m", -3, Date), "yyyy-mm")

    total = GetMonthlyUsage(itemName, month1) + _
            GetMonthlyUsage(itemName, month2) + _
            GetMonthlyUsage(itemName, month3)

    Calculate3MonthAverage = total \ 3
End Function
