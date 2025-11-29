Attribute VB_Name = "TransactionLog"
'===============================================================================
' 入出庫記録モジュール
' Version: 2.0
' 作成日: 2025-11-27
'===============================================================================

Option Explicit

'===============================================================================
' 入出庫シート初期化
'===============================================================================

'-------------------------------------------------------------------------------
' 入出庫シートのセットアップ
'-------------------------------------------------------------------------------
Public Sub SetupTransactionSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    ' ヘッダー設定
    With ws
        .Cells(1, 1).Value = "日時"
        .Cells(1, 2).Value = "種別"
        .Cells(1, 3).Value = "物品名"
        .Cells(1, 4).Value = "数量（最小単位）"
        .Cells(1, 5).Value = "単位"
        .Cells(1, 6).Value = "記録者"
        .Cells(1, 7).Value = "荷姿換算"

        ' ヘッダー書式
        .Range("A1:G1").Font.Bold = True
        .Range("A1:G1").Interior.Color = RGB(200, 200, 200)
        .Range("A1:G1").HorizontalAlignment = xlCenter

        ' 列幅調整
        .Columns("A:A").ColumnWidth = 18
        .Columns("B:B").ColumnWidth = 8
        .Columns("C:C").ColumnWidth = 20
        .Columns("D:D").ColumnWidth = 16
        .Columns("E:E").ColumnWidth = 10
        .Columns("F:F").ColumnWidth = 12
        .Columns("G:G").ColumnWidth = 20
    End With
End Sub

'===============================================================================
' 入出庫記録（荷姿入力版）
'===============================================================================

'-------------------------------------------------------------------------------
' 入庫記録（荷姿+端数入力、最小単位で保存）
'-------------------------------------------------------------------------------
Public Sub RecordInbound()
    Call RecordTransaction("入庫")
End Sub

'-------------------------------------------------------------------------------
' 出庫記録（荷姿+端数入力、最小単位で保存）
'-------------------------------------------------------------------------------
Public Sub RecordOutbound()
    Call RecordTransaction("出庫")
End Sub

'-------------------------------------------------------------------------------
' 入出庫記録の共通処理
'-------------------------------------------------------------------------------
Private Sub RecordTransaction(transType As String)
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim itemName As String
    Dim packages As Long
    Dim remainder As Long
    Dim totalQty As Long
    Dim minUnit As String
    Dim packageUnit As String
    Dim recorder As String
    Dim lastRow As Long

    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    ' 物品名を入力
    itemName = InputBox("物品名を入力してください", transType & "記録")
    If itemName = "" Then Exit Sub

    ' マスターに存在チェック
    If FindItemRow(itemName) = 0 Then
        ShowErrorMessage "マスターに未登録の物品です。先にマスター登録してください。"
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

    If totalQty = 0 Then
        ShowErrorMessage "数量が0です。記録をキャンセルします。"
        Exit Sub
    End If

    ' 記録者
    recorder = InputBox("記録者名を入力してください", "記録者", Environ("USERNAME"))
    If recorder = "" Then recorder = "未記入"

    ' 確認
    Dim confirmMsg As String
    confirmMsg = "種別: " & transType & vbCrLf & _
                 "物品名: " & itemName & vbCrLf & _
                 "荷姿: " & packages & packageUnit & vbCrLf & _
                 "端数: " & remainder & minUnit & vbCrLf & _
                 "合計: " & totalQty & minUnit & vbCrLf & _
                 "記録者: " & recorder & vbCrLf & vbCrLf & _
                 "この内容で記録しますか？"

    If Not ShowConfirmMessage(confirmMsg) Then Exit Sub

    ' データ追加
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    With ws
        .Cells(lastRow, 1).Value = Now
        .Cells(lastRow, 2).Value = transType
        .Cells(lastRow, 3).Value = itemName
        .Cells(lastRow, 4).Value = totalQty ' 最小単位で保存
        .Cells(lastRow, 5).Value = minUnit
        .Cells(lastRow, 6).Value = recorder
        .Cells(lastRow, 7).Value = FormatAsPackage(totalQty, itemName) ' 荷姿表示
    End With

    ShowSuccessMessage transType & "を記録しました。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage transType & "記録エラー: " & Err.Description
End Sub

'===============================================================================
' 入出庫記録（最小単位直接入力版）
'===============================================================================

'-------------------------------------------------------------------------------
' 最小単位で直接入力（端数のみの場合に便利）
'-------------------------------------------------------------------------------
Public Sub RecordTransactionDirect()
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim itemName As String
    Dim transType As String
    Dim qty As Long
    Dim minUnit As String
    Dim recorder As String
    Dim lastRow As Long

    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    ' 種別選択
    transType = InputBox("種別を入力してください" & vbCrLf & "1: 入庫" & vbCrLf & "2: 出庫", "種別選択", "1")
    If transType = "1" Then
        transType = "入庫"
    ElseIf transType = "2" Then
        transType = "出庫"
    Else
        Exit Sub
    End If

    ' 物品名を入力
    itemName = InputBox("物品名を入力してください", transType & "記録")
    If itemName = "" Then Exit Sub

    ' マスターに存在チェック
    If FindItemRow(itemName) = 0 Then
        ShowErrorMessage "マスターに未登録の物品です。"
        Exit Sub
    End If

    ' 単位情報取得
    minUnit = GetMinUnitName(itemName)

    ' 数量入力（最小単位）
    qty = Val(InputBox("数量を入力してください（" & minUnit & "）", "数量入力", "1"))
    If qty <= 0 Then
        ShowErrorMessage "数量が0以下です。記録をキャンセルします。"
        Exit Sub
    End If

    ' 記録者
    recorder = InputBox("記録者名を入力してください", "記録者", Environ("USERNAME"))
    If recorder = "" Then recorder = "未記入"

    ' 確認
    Dim confirmMsg As String
    confirmMsg = "種別: " & transType & vbCrLf & _
                 "物品名: " & itemName & vbCrLf & _
                 "数量: " & qty & minUnit & vbCrLf & _
                 "参考: " & FormatAsPackage(qty, itemName) & vbCrLf & _
                 "記録者: " & recorder & vbCrLf & vbCrLf & _
                 "この内容で記録しますか？"

    If Not ShowConfirmMessage(confirmMsg) Then Exit Sub

    ' データ追加
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    With ws
        .Cells(lastRow, 1).Value = Now
        .Cells(lastRow, 2).Value = transType
        .Cells(lastRow, 3).Value = itemName
        .Cells(lastRow, 4).Value = qty ' 最小単位
        .Cells(lastRow, 5).Value = minUnit
        .Cells(lastRow, 6).Value = recorder
        .Cells(lastRow, 7).Value = FormatAsPackage(qty, itemName) ' 荷姿表示
    End With

    ShowSuccessMessage transType & "を記録しました。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "記録エラー: " & Err.Description
End Sub

'===============================================================================
' 履歴表示
'===============================================================================

'-------------------------------------------------------------------------------
' 特定物品の入出庫履歴を表示
'-------------------------------------------------------------------------------
Public Sub ShowItemHistory()
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim itemName As String
    Dim lastRow As Long
    Dim i As Long
    Dim historyMsg As String
    Dim count As Integer

    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    ' 物品名を入力
    itemName = InputBox("履歴を表示する物品名を入力してください", "履歴表示")
    If itemName = "" Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 3).End(xlUp).Row
    count = 0
    historyMsg = "【" & itemName & " の入出庫履歴】" & vbCrLf & vbCrLf

    ' 最新10件を表示
    For i = lastRow To 2 Step -1
        If ws.Cells(i, 3).Value = itemName Then
            historyMsg = historyMsg & _
                         Format(ws.Cells(i, 1).Value, "yyyy/mm/dd hh:nn") & " | " & _
                         ws.Cells(i, 2).Value & " | " & _
                         ws.Cells(i, 7).Value & " | " & _
                         ws.Cells(i, 6).Value & vbCrLf

            count = count + 1
            If count >= 10 Then Exit For
        End If
    Next i

    If count = 0 Then
        historyMsg = historyMsg & "履歴がありません。"
    End If

    MsgBox historyMsg, vbInformation, "入出庫履歴"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "履歴表示エラー: " & Err.Description
End Sub

'===============================================================================
' 月次集計
'===============================================================================

'-------------------------------------------------------------------------------
' 指定月の物品別使用量を集計
'-------------------------------------------------------------------------------
Public Function GetMonthlyUsage(itemName As String, targetMonth As String) As Long
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim transDate As Date
    Dim total As Long

    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 3).End(xlUp).Row

    total = 0

    For i = 2 To lastRow
        If ws.Cells(i, 3).Value = itemName And ws.Cells(i, 2).Value = "出庫" Then
            transDate = ws.Cells(i, 1).Value
            If Format(transDate, "yyyy-mm") = targetMonth Then
                total = total + ws.Cells(i, 4).Value
            End If
        End If
    Next i

    GetMonthlyUsage = total
    Exit Function

ErrorHandler:
    GetMonthlyUsage = 0
End Function
