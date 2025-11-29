Attribute VB_Name = "MasterManagement"
'===============================================================================
' マスター管理モジュール
' Version: 2.0
' 作成日: 2025-11-27
'===============================================================================

Option Explicit

'===============================================================================
' マスターシート初期化
'===============================================================================

'-------------------------------------------------------------------------------
' マスターシートのセットアップ
'-------------------------------------------------------------------------------
Public Sub SetupMasterSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)

    ' ヘッダー設定
    With ws
        .Cells(1, 1).Value = "管理番号"
        .Cells(1, 2).Value = "物品名"
        .Cells(1, 3).Value = "最小単位名"
        .Cells(1, 4).Value = "荷姿単位名"
        .Cells(1, 5).Value = "荷姿入数"
        .Cells(1, 6).Value = "発注点（最小単位）"
        .Cells(1, 7).Value = "現在庫（最小単位）"
        .Cells(1, 8).Value = "状態"

        ' ヘッダー書式
        .Range("A1:H1").Font.Bold = True
        .Range("A1:H1").Interior.Color = RGB(200, 200, 200)
        .Range("A1:H1").HorizontalAlignment = xlCenter

        ' 列幅調整
        .Columns("A:A").ColumnWidth = 12
        .Columns("B:B").ColumnWidth = 20
        .Columns("C:C").ColumnWidth = 12
        .Columns("D:D").ColumnWidth = 12
        .Columns("E:E").ColumnWidth = 10
        .Columns("F:F").ColumnWidth = 16
        .Columns("G:G").ColumnWidth = 16
        .Columns("H:H").ColumnWidth = 10
    End With
End Sub

'===============================================================================
' マスターデータ操作
'===============================================================================

'-------------------------------------------------------------------------------
' 新規物品をマスターに追加
'-------------------------------------------------------------------------------
Public Sub AddNewItem()
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim lastRow As Long
    Dim itemID As String
    Dim itemName As String
    Dim minUnit As String
    Dim packageUnit As String
    Dim packageSize As Long
    Dim reorderPoint As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)

    ' 入力フォーム（簡易版）
    itemName = InputBox("物品名を入力してください", "新規物品登録")
    If itemName = "" Then Exit Sub

    ' 既存チェック
    If ItemExists(itemName) Then
        ShowErrorMessage "既に登録されている物品名です。"
        Exit Sub
    End If

    minUnit = InputBox("最小単位名を入力してください（例：本、個、枚）", "最小単位", "個")
    If minUnit = "" Then minUnit = "個"

    packageUnit = InputBox("荷姿単位名を入力してください（例：ダース、ケース、箱）", "荷姿単位", "セット")
    If packageUnit = "" Then packageUnit = "セット"

    packageSize = Val(InputBox("荷姿入数を入力してください（1" & packageUnit & "あたりの" & minUnit & "数）", "荷姿入数", "1"))
    If packageSize <= 0 Then packageSize = 1

    reorderPoint = Val(InputBox("発注点を入力してください（最小単位）", "発注点", "10"))
    If reorderPoint < 0 Then reorderPoint = 0

    ' 管理番号を自動生成
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow = 1 Then
        itemID = "A001"
    Else
        itemID = "A" & Format(lastRow, "000")
    End If

    ' データ追加
    With ws
        .Cells(lastRow + 1, 1).Value = itemID
        .Cells(lastRow + 1, 2).Value = itemName
        .Cells(lastRow + 1, 3).Value = minUnit
        .Cells(lastRow + 1, 4).Value = packageUnit
        .Cells(lastRow + 1, 5).Value = packageSize
        .Cells(lastRow + 1, 6).Value = reorderPoint
        .Cells(lastRow + 1, 7).Value = 0 ' 現在庫初期値
        .Cells(lastRow + 1, 8).Value = "未使用"
    End With

    ShowSuccessMessage "物品「" & itemName & "」を登録しました。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "物品登録エラー: " & Err.Description
End Sub

'-------------------------------------------------------------------------------
' 物品が既に存在するかチェック
'-------------------------------------------------------------------------------
Private Function ItemExists(itemName As String) As Boolean
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    For i = 2 To lastRow
        If ws.Cells(i, 2).Value = itemName Then
            ItemExists = True
            Exit Function
        End If
    Next i

    ItemExists = False
End Function

'-------------------------------------------------------------------------------
' 物品情報を更新
'-------------------------------------------------------------------------------
Public Sub UpdateItemInfo()
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim itemName As String
    Dim rowNum As Long
    Dim response As String
    Dim newValue As Variant

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)

    ' 物品名を入力
    itemName = InputBox("更新する物品名を入力してください", "物品情報更新")
    If itemName = "" Then Exit Sub

    ' 物品を検索
    rowNum = FindItemRow(itemName)
    If rowNum = 0 Then
        ShowErrorMessage "物品が見つかりませんでした。"
        Exit Sub
    End If

    ' 更新項目を選択
    response = InputBox( _
        "更新する項目を選択してください" & vbCrLf & vbCrLf & _
        "1: 最小単位名" & vbCrLf & _
        "2: 荷姿単位名" & vbCrLf & _
        "3: 荷姿入数" & vbCrLf & _
        "4: 発注点", _
        "更新項目選択", "1")

    Select Case response
        Case "1"
            newValue = InputBox("新しい最小単位名を入力してください", "最小単位名", ws.Cells(rowNum, 3).Value)
            If newValue <> "" Then ws.Cells(rowNum, 3).Value = newValue

        Case "2"
            newValue = InputBox("新しい荷姿単位名を入力してください", "荷姿単位名", ws.Cells(rowNum, 4).Value)
            If newValue <> "" Then ws.Cells(rowNum, 4).Value = newValue

        Case "3"
            newValue = InputBox("新しい荷姿入数を入力してください", "荷姿入数", ws.Cells(rowNum, 5).Value)
            If IsNumericValue(newValue) Then ws.Cells(rowNum, 5).Value = CLng(newValue)

        Case "4"
            newValue = InputBox("新しい発注点を入力してください（最小単位）", "発注点", ws.Cells(rowNum, 6).Value)
            If IsNumericValue(newValue) Then ws.Cells(rowNum, 6).Value = CLng(newValue)

        Case Else
            Exit Sub
    End Select

    ShowSuccessMessage "物品情報を更新しました。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "更新エラー: " & Err.Description
End Sub

'-------------------------------------------------------------------------------
' 物品の行番号を検索
'-------------------------------------------------------------------------------
Public Function FindItemRow(itemName As String) As Long
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    For i = 2 To lastRow
        If ws.Cells(i, 2).Value = itemName Then
            FindItemRow = i
            Exit Function
        End If
    Next i

    FindItemRow = 0
End Function

'-------------------------------------------------------------------------------
' 物品を削除
'-------------------------------------------------------------------------------
Public Sub DeleteItem()
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim itemName As String
    Dim rowNum As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)

    ' 物品名を入力
    itemName = InputBox("削除する物品名を入力してください", "物品削除")
    If itemName = "" Then Exit Sub

    ' 物品を検索
    rowNum = FindItemRow(itemName)
    If rowNum = 0 Then
        ShowErrorMessage "物品が見つかりませんでした。"
        Exit Sub
    End If

    ' 確認
    If Not ShowConfirmMessage("物品「" & itemName & "」を削除します。よろしいですか？") Then
        Exit Sub
    End If

    ' 行削除
    ws.Rows(rowNum).Delete

    ShowSuccessMessage "物品を削除しました。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "削除エラー: " & Err.Description
End Sub

'===============================================================================
' マスター自動生成
'===============================================================================

'-------------------------------------------------------------------------------
' 棚卸データから物品マスターを自動生成
'-------------------------------------------------------------------------------
Public Sub GenerateMasterFromInventory()
    On Error GoTo ErrorHandler

    Dim wsInv As Worksheet
    Dim wsMaster As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim itemName As String
    Dim itemID As String
    Dim masterRow As Long

    Set wsInv = ThisWorkbook.Sheets(INVENTORY_SHEET)
    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)

    lastRow = wsInv.Cells(wsInv.Rows.Count, 2).End(xlUp).Row

    If lastRow < 2 Then
        ShowErrorMessage "棚卸データがありません。"
        Exit Sub
    End If

    If Not ShowConfirmMessage("棚卸データから物品マスターを生成します。" & vbCrLf & "（発注点等は後で設定してください）") Then
        Exit Sub
    End If

    masterRow = wsMaster.Cells(wsMaster.Rows.Count, 1).End(xlUp).Row + 1

    For i = 2 To lastRow
        itemName = wsInv.Cells(i, 2).Value

        ' 既に存在する物品はスキップ
        If Not ItemExists(itemName) Then
            itemID = "A" & Format(masterRow - 1, "000")

            With wsMaster
                .Cells(masterRow, 1).Value = itemID
                .Cells(masterRow, 2).Value = itemName
                .Cells(masterRow, 3).Value = "個" ' デフォルト
                .Cells(masterRow, 4).Value = "セット" ' デフォルト
                .Cells(masterRow, 5).Value = 1 ' デフォルト
                .Cells(masterRow, 6).Value = 10 ' デフォルト
                .Cells(masterRow, 7).Value = 0
                .Cells(masterRow, 8).Value = "未設定"
            End With

            masterRow = masterRow + 1
        End If
    Next i

    ShowSuccessMessage "マスターを生成しました。" & vbCrLf & "発注点等の設定を忘れずに行ってください。"
    Exit Sub

ErrorHandler:
    ShowErrorMessage "マスター生成エラー: " & Err.Description
End Sub
