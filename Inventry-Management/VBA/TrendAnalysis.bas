Attribute VB_Name = "TrendAnalysis"
'===============================================================================
' 使用量トレンド分析モジュール
' Version: 2.0
' 作成日: 2025-11-27
'===============================================================================

Option Explicit

'===============================================================================
' トレンドシート初期化
'===============================================================================

'-------------------------------------------------------------------------------
' 使用量トレンドシートのセットアップ
'-------------------------------------------------------------------------------
Public Sub SetupTrendSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(TREND_SHEET)

    ' ヘッダー設定
    With ws
        .Cells(1, 1).Value = "年月"
        .Cells(1, 2).Value = "物品名"
        .Cells(1, 3).Value = "使用量（最小単位）"
        .Cells(1, 4).Value = "単位"
        .Cells(1, 5).Value = "前月比"
        .Cells(1, 6).Value = "前月比率"
        .Cells(1, 7).Value = "3ヶ月平均"
        .Cells(1, 8).Value = "状態"

        ' ヘッダー書式
        .Range("A1:H1").Font.Bold = True
        .Range("A1:H1").Interior.Color = RGB(200, 200, 200)
        .Range("A1:H1").HorizontalAlignment = xlCenter

        ' 列幅調整
        .Columns("A:A").ColumnWidth = 10
        .Columns("B:B").ColumnWidth = 20
        .Columns("C:C").ColumnWidth = 18
        .Columns("D:D").ColumnWidth = 8
        .Columns("E:E").ColumnWidth = 10
        .Columns("F:F").ColumnWidth = 12
        .Columns("G:G").ColumnWidth = 14
        .Columns("H:H").ColumnWidth = 10
    End With
End Sub

'===============================================================================
' 使用量集計
'===============================================================================

'-------------------------------------------------------------------------------
' 全物品の月次使用量を集計
'-------------------------------------------------------------------------------
Public Sub AnalyzeMonthlyUsage()
    On Error GoTo ErrorHandler

    Dim wsMaster As Worksheet
    Dim wsTrend As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim trendRow As Long
    Dim itemName As String
    Dim currentMonth As String
    Dim prevMonth As String
    Dim currentUsage As Long
    Dim prevUsage As Long
    Dim avgUsage As Long
    Dim changeRate As Double
    Dim status As String

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    Set wsTrend = ThisWorkbook.Sheets(TREND_SHEET)

    ' データクリア
    ClearSheetData TREND_SHEET

    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row
    trendRow = 2

    ' 当月と前月
    currentMonth = Format(Date, "yyyy-mm")
    prevMonth = Format(DateAdd("m", -1, Date), "yyyy-mm")

    Application.ScreenUpdating = False

    ' 各物品を分析
    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value

        ' 当月使用量
        currentUsage = GetMonthlyUsage(itemName, currentMonth)

        ' 前月使用量
        prevUsage = GetMonthlyUsage(itemName, prevMonth)

        ' 3ヶ月平均
        avgUsage = Calculate3MonthAverage(itemName)

        ' 前月比率計算
        If prevUsage > 0 Then
            changeRate = ((currentUsage - prevUsage) / prevUsage) * 100
        ElseIf currentUsage > 0 Then
            changeRate = 100
        Else
            changeRate = 0
        End If

        ' 急増検知
        status = DetectUsageSurge(currentUsage, prevUsage, avgUsage, changeRate)

        ' データ記録
        With wsTrend
            .Cells(trendRow, 1).Value = currentMonth
            .Cells(trendRow, 2).Value = itemName
            .Cells(trendRow, 3).Value = currentUsage
            .Cells(trendRow, 4).Value = GetMinUnitName(itemName)
            .Cells(trendRow, 5).Value = currentUsage - prevUsage
            .Cells(trendRow, 6).Value = Format(changeRate, "0") & "%"
            .Cells(trendRow, 7).Value = avgUsage
            .Cells(trendRow, 8).Value = status

            ' 急増の場合はハイライト
            If status = "🟡急増" Then
                .Range("A" & trendRow & ":H" & trendRow).Interior.Color = RGB(255, 255, 200)
            End If
        End With

        trendRow = trendRow + 1
    Next i

    Application.ScreenUpdating = True

    ShowSuccessMessage "使用量トレンド分析を完了しました。"
    Exit Sub

ErrorHandler:
    Application.ScreenUpdating = True
    ShowErrorMessage "トレンド分析エラー: " & Err.Description
End Sub

'===============================================================================
' 使用量計算
'===============================================================================

'-------------------------------------------------------------------------------
' 3ヶ月平均使用量を計算
'-------------------------------------------------------------------------------
Private Function Calculate3MonthAverage(itemName As String) As Long
    Dim month1 As String
    Dim month2 As String
    Dim month3 As String
    Dim total As Long

    month1 = Format(DateAdd("m", -1, Date), "yyyy-mm")
    month2 = Format(DateAdd("m", -2, Date), "yyyy-mm")
    month3 = Format(DateAdd("m", -3, Date), "yyyy-mm")

    total = GetMonthlyUsage(itemName, month1) + _
            GetMonthlyUsage(itemName, month2) + _
            GetMonthlyUsage(itemName, month3)

    Calculate3MonthAverage = total \ 3
End Function

'===============================================================================
' 急増検知アルゴリズム
'===============================================================================

'-------------------------------------------------------------------------------
' 使用量急増を検知
' 条件: 前月比150%以上 または 3ヶ月平均の2倍以上
'-------------------------------------------------------------------------------
Private Function DetectUsageSurge(currentUsage As Long, prevUsage As Long, avgUsage As Long, changeRate As Double) As String
    ' 条件1: 前月比150%以上
    If changeRate >= 150 And prevUsage > 0 Then
        DetectUsageSurge = "🟡急増"
        Exit Function
    End If

    ' 条件2: 3ヶ月平均の2倍以上
    If currentUsage >= avgUsage * 2 And avgUsage > 0 Then
        DetectUsageSurge = "🟡急増"
        Exit Function
    End If

    ' 通常
    DetectUsageSurge = "正常"
End Function

'===============================================================================
' グラフ生成
'===============================================================================

'-------------------------------------------------------------------------------
' 特定物品の使用量推移グラフを自動生成
'-------------------------------------------------------------------------------
Public Sub CreateUsageTrendChart()
    On Error GoTo ErrorHandler

    Dim itemName As String
    Dim ws As Worksheet
    Dim chartObj As ChartObject
    Dim lastRow As Long
    Dim dataRange As Range
    Dim monthData() As String
    Dim usageData() As Long
    Dim i As Long
    Dim count As Integer

    ' 物品名を入力
    itemName = InputBox("グラフを作成する物品名を入力してください", "グラフ作成")
    If itemName = "" Then Exit Sub

    ' マスターに存在チェック
    If FindItemRow(itemName) = 0 Then
        ShowErrorMessage "マスターに未登録の物品です。"
        Exit Sub
    End If

    Set ws = ThisWorkbook.Sheets(TREND_SHEET)

    ' 過去6ヶ月のデータを取得
    ReDim monthData(1 To 6)
    ReDim usageData(1 To 6)

    For i = 0 To 5
        monthData(i + 1) = Format(DateAdd("m", -(5 - i), Date), "yyyy-mm")
        usageData(i + 1) = GetMonthlyUsage(itemName, monthData(i + 1))
    Next i

    ' 既存のグラフを削除
    For Each chartObj In ws.ChartObjects
        If chartObj.Name = "UsageTrendChart_" & itemName Then
            chartObj.Delete
        End If
    Next chartObj

    ' 新しいグラフを作成
    Set chartObj = ws.ChartObjects.Add(Left:=500, Top:=50, Width:=400, Height:=300)
    chartObj.Name = "UsageTrendChart_" & itemName

    With chartObj.Chart
        .ChartType = xlLine
        .HasTitle = True
        .ChartTitle.Text = itemName & " 使用量推移"

        ' データ系列追加
        .SeriesCollection.NewSeries
        With .SeriesCollection(1)
            .Name = "使用量"
            .Values = usageData
            .XValues = monthData
        End With

        ' 軸ラベル
        .Axes(xlCategory).HasTitle = True
        .Axes(xlCategory).AxisTitle.Text = "年月"
        .Axes(xlValue).HasTitle = True
        .Axes(xlValue).AxisTitle.Text = "使用量 (" & GetMinUnitName(itemName) & ")"

        ' 発注点の水平線を追加
        Dim reorderPoint As Long
        reorderPoint = GetReorderPoint(itemName)

        If reorderPoint > 0 Then
            .SeriesCollection.NewSeries
            With .SeriesCollection(2)
                .Name = "発注点"
                .ChartType = xlLine
                Dim refLine(1 To 6) As Long
                For i = 1 To 6
                    refLine(i) = reorderPoint
                Next i
                .Values = refLine
                .Border.Color = RGB(255, 0, 0)
                .Border.LineStyle = xlDash
            End With
        End If
    End With

    ShowSuccessMessage "グラフを作成しました。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "グラフ作成エラー: " & Err.Description
End Sub

'===============================================================================
' 発注点見直し提案
'===============================================================================

'-------------------------------------------------------------------------------
' 使用量トレンドに基づいて発注点の見直しを提案
'-------------------------------------------------------------------------------
Public Sub SuggestReorderPointAdjustment()
    On Error GoTo ErrorHandler

    Dim wsMaster As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim itemName As String
    Dim currentReorderPoint As Long
    Dim avgUsage As Long
    Dim suggestedReorderPoint As Long
    Dim msg As String

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    msg = "【発注点見直し提案】" & vbCrLf & vbCrLf

    For i = 2 To lastRow
        itemName = wsMaster.Cells(i, 2).Value
        currentReorderPoint = wsMaster.Cells(i, 6).Value
        avgUsage = Calculate3MonthAverage(itemName)

        ' 3ヶ月平均の1.5倍を推奨発注点とする
        suggestedReorderPoint = avgUsage * 1.5

        ' 現在の発注点と大きく異なる場合のみ提案
        If Abs(suggestedReorderPoint - currentReorderPoint) > currentReorderPoint * 0.3 Then
            msg = msg & itemName & ":" & vbCrLf
            msg = msg & "  現在: " & currentReorderPoint & GetMinUnitName(itemName) & vbCrLf
            msg = msg & "  推奨: " & suggestedReorderPoint & GetMinUnitName(itemName) & vbCrLf
            msg = msg & "  (3ヶ月平均: " & avgUsage & GetMinUnitName(itemName) & ")" & vbCrLf & vbCrLf
        End If
    Next i

    If Len(msg) < 50 Then
        msg = msg & "見直しが必要な品目はありません。"
    End If

    MsgBox msg, vbInformation, "発注点見直し提案"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "発注点見直しエラー: " & Err.Description
End Sub
