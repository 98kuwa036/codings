Attribute VB_Name = "InventoryManagement"
'===============================================================================
' 在庫管理・注文管理システム VBAモジュール
' Version: 1.0
' 作成日: 2025-11-19
'===============================================================================

Option Explicit

' 定数定義
Private Const MASTER_SHEET As String = "マスター設定"
Private Const INVENTORY_SHEET As String = "棚卸データ"
Private Const TRANSACTION_SHEET As String = "入出庫履歴"
Private Const ORDER_SHEET As String = "発注管理"
Private Const DASHBOARD_SHEET As String = "ダッシュボード"

'===============================================================================
' 初期セットアップ
'===============================================================================

'-------------------------------------------------------------------------------
' シート初期化（システム全体のセットアップ）
'-------------------------------------------------------------------------------
Public Sub InitializeSystem()
    Application.ScreenUpdating = False

    ' 各シートを作成
    CreateSheetIfNotExists MASTER_SHEET
    CreateSheetIfNotExists INVENTORY_SHEET
    CreateSheetIfNotExists TRANSACTION_SHEET
    CreateSheetIfNotExists ORDER_SHEET
    CreateSheetIfNotExists DASHBOARD_SHEET

    ' マスター設定シートのヘッダー設定
    SetupMasterSheet

    ' 入出庫履歴シートのヘッダー設定
    SetupTransactionSheet

    ' 棚卸データシートのヘッダー設定
    SetupInventorySheet

    ' 発注管理シートのヘッダー設定
    SetupOrderSheet

    ' ダッシュボードシートのセットアップ
    SetupDashboardSheet

    Application.ScreenUpdating = True

    MsgBox "システムの初期化が完了しました。", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' シート存在チェック＆作成
'-------------------------------------------------------------------------------
Private Sub CreateSheetIfNotExists(sheetName As String)
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(sheetName)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
        ws.Name = sheetName
    End If
End Sub

'-------------------------------------------------------------------------------
' マスター設定シートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupMasterSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)

    ' ヘッダー設定
    With ws
        .Cells(1, 1).Value = "管理番号"
        .Cells(1, 2).Value = "物品名"
        .Cells(1, 3).Value = "発注点"
        .Cells(1, 4).Value = "最小単位"
        .Cells(1, 5).Value = "完品単位"
        .Cells(1, 6).Value = "完品個数"
        .Cells(1, 7).Value = "現在庫"
        .Cells(1, 8).Value = "発注要否"
        .Cells(1, 9).Value = "推奨発注数"

        ' ヘッダー書式設定
        .Range("A1:I1").Font.Bold = True
        .Range("A1:I1").Interior.Color = RGB(68, 114, 196)
        .Range("A1:I1").Font.Color = RGB(255, 255, 255)
        .Columns("A:I").AutoFit
    End With
End Sub

'-------------------------------------------------------------------------------
' 入出庫履歴シートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupTransactionSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    With ws
        .Cells(1, 1).Value = "タイムスタンプ"
        .Cells(1, 2).Value = "記録日"
        .Cells(1, 3).Value = "種別"
        .Cells(1, 4).Value = "記録者"
        .Cells(1, 5).Value = "品名"
        .Cells(1, 6).Value = "個数"

        .Range("A1:F1").Font.Bold = True
        .Range("A1:F1").Interior.Color = RGB(112, 173, 71)
        .Range("A1:F1").Font.Color = RGB(255, 255, 255)
        .Columns("A:F").AutoFit
    End With
End Sub

'-------------------------------------------------------------------------------
' 棚卸データシートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupInventorySheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(INVENTORY_SHEET)

    With ws
        .Cells(1, 1).Value = "棚卸日"
        .Cells(1, 2).Value = "品名"
        .Cells(1, 3).Value = "数量"

        .Range("A1:C1").Font.Bold = True
        .Range("A1:C1").Interior.Color = RGB(237, 125, 49)
        .Range("A1:C1").Font.Color = RGB(255, 255, 255)
        .Columns("A:C").AutoFit
    End With
End Sub

'-------------------------------------------------------------------------------
' 発注管理シートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupOrderSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(ORDER_SHEET)

    With ws
        .Cells(1, 1).Value = "発注日"
        .Cells(1, 2).Value = "管理番号"
        .Cells(1, 3).Value = "物品名"
        .Cells(1, 4).Value = "発注数量"
        .Cells(1, 5).Value = "完品数"
        .Cells(1, 6).Value = "ステータス"
        .Cells(1, 7).Value = "納品日"
        .Cells(1, 8).Value = "備考"

        .Range("A1:H1").Font.Bold = True
        .Range("A1:H1").Interior.Color = RGB(165, 165, 165)
        .Range("A1:H1").Font.Color = RGB(255, 255, 255)
        .Columns("A:H").AutoFit
    End With
End Sub

'-------------------------------------------------------------------------------
' ダッシュボードシートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupDashboardSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(DASHBOARD_SHEET)

    With ws
        .Cells(1, 1).Value = "在庫管理ダッシュボード"
        .Cells(1, 1).Font.Size = 16
        .Cells(1, 1).Font.Bold = True

        .Cells(3, 1).Value = "最終更新:"
        .Cells(3, 2).Value = Now

        .Cells(5, 1).Value = "総品目数:"
        .Cells(6, 1).Value = "発注必要品目:"
        .Cells(7, 1).Value = "在庫切れ品目:"
    End With
End Sub

'===============================================================================
' CSVインポート機能
'===============================================================================

'-------------------------------------------------------------------------------
' 入出庫CSVファイルのインポート
'-------------------------------------------------------------------------------
Public Sub ImportTransactionCSV()
    Dim filePath As String
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim line As String
    Dim fields() As String
    Dim fileNum As Integer
    Dim rowNum As Long

    ' ファイル選択ダイアログ
    filePath = Application.GetOpenFilename("CSVファイル (*.csv), *.csv", , "入出庫CSVファイルを選択")

    If filePath = "False" Then Exit Sub

    Set ws = ThisWorkbook.Sheets(TRANSACTION_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    fileNum = FreeFile
    Open filePath For Input As #fileNum

    ' ヘッダー行をスキップ
    If Not EOF(fileNum) Then Line Input #fileNum, line

    ' データ読み込み
    Do While Not EOF(fileNum)
        Line Input #fileNum, line
        fields = ParseCSVLine(line)

        If UBound(fields) >= 5 Then
            ws.Cells(lastRow, 1).Value = fields(0) ' タイムスタンプ
            ws.Cells(lastRow, 2).Value = fields(1) ' 記録日
            ws.Cells(lastRow, 3).Value = fields(2) ' 種別
            ws.Cells(lastRow, 4).Value = fields(3) ' 記録者
            ws.Cells(lastRow, 5).Value = fields(4) ' 品名
            ws.Cells(lastRow, 6).Value = Val(fields(5)) ' 個数
            lastRow = lastRow + 1
        End If
    Loop

    Close #fileNum

    ws.Columns("A:F").AutoFit

    MsgBox "入出庫データのインポートが完了しました。", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 棚卸CSVファイルのインポート
'-------------------------------------------------------------------------------
Public Sub ImportInventoryCSV()
    Dim filePath As String
    Dim ws As Worksheet
    Dim line As String
    Dim fields() As String
    Dim fileNum As Integer
    Dim rowNum As Long

    ' ファイル選択ダイアログ
    filePath = Application.GetOpenFilename("CSVファイル (*.csv), *.csv", , "棚卸CSVファイルを選択")

    If filePath = "False" Then Exit Sub

    Set ws = ThisWorkbook.Sheets(INVENTORY_SHEET)

    ' 既存データをクリア（ヘッダー以外）
    If ws.Cells(ws.Rows.Count, 1).End(xlUp).Row > 1 Then
        ws.Range("A2:C" & ws.Cells(ws.Rows.Count, 1).End(xlUp).Row).ClearContents
    End If

    fileNum = FreeFile
    Open filePath For Input As #fileNum

    rowNum = 2

    ' データ読み込み（ヘッダーなし形式）
    Do While Not EOF(fileNum)
        Line Input #fileNum, line
        fields = ParseCSVLine(line)

        If UBound(fields) >= 2 Then
            ws.Cells(rowNum, 1).Value = fields(0) ' 棚卸日
            ws.Cells(rowNum, 2).Value = fields(1) ' 品名
            ws.Cells(rowNum, 3).Value = Val(fields(2)) ' 数量
            rowNum = rowNum + 1
        End If
    Loop

    Close #fileNum

    ws.Columns("A:C").AutoFit

    MsgBox "棚卸データのインポートが完了しました。" & vbCrLf & _
           "インポート件数: " & (rowNum - 2) & "件", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' CSV行パーサー（ダブルクォート対応）
'-------------------------------------------------------------------------------
Private Function ParseCSVLine(line As String) As String()
    Dim result() As String
    Dim i As Long, j As Long
    Dim inQuotes As Boolean
    Dim fieldCount As Long
    Dim currentField As String

    fieldCount = 0
    ReDim result(0)
    inQuotes = False
    currentField = ""

    For i = 1 To Len(line)
        Dim c As String
        c = Mid(line, i, 1)

        If c = """" Then
            inQuotes = Not inQuotes
        ElseIf c = "," And Not inQuotes Then
            ReDim Preserve result(fieldCount)
            result(fieldCount) = currentField
            fieldCount = fieldCount + 1
            currentField = ""
        Else
            currentField = currentField & c
        End If
    Next i

    ' 最後のフィールド
    ReDim Preserve result(fieldCount)
    result(fieldCount) = currentField

    ParseCSVLine = result
End Function

'===============================================================================
' 在庫計算・発注判定
'===============================================================================

'-------------------------------------------------------------------------------
' 現在庫を計算してマスターシートを更新
'-------------------------------------------------------------------------------
Public Sub CalculateCurrentInventory()
    Dim wsMaster As Worksheet
    Dim wsInventory As Worksheet
    Dim wsTransaction As Worksheet
    Dim lastRowMaster As Long
    Dim lastRowInventory As Long
    Dim lastRowTrans As Long
    Dim i As Long, j As Long
    Dim itemName As String
    Dim currentStock As Double
    Dim inbound As Double
    Dim outbound As Double

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    Set wsInventory = ThisWorkbook.Sheets(INVENTORY_SHEET)
    Set wsTransaction = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    lastRowMaster = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row
    lastRowInventory = wsInventory.Cells(wsInventory.Rows.Count, 2).End(xlUp).Row
    lastRowTrans = wsTransaction.Cells(wsTransaction.Rows.Count, 5).End(xlUp).Row

    Application.ScreenUpdating = False

    For i = 2 To lastRowMaster
        itemName = wsMaster.Cells(i, 2).Value ' 物品名

        If itemName <> "" Then
            ' 棚卸データから初期在庫を取得
            currentStock = 0
            For j = 2 To lastRowInventory
                If wsInventory.Cells(j, 2).Value = itemName Then
                    currentStock = wsInventory.Cells(j, 3).Value
                    Exit For
                End If
            Next j

            ' 入出庫履歴から増減を計算
            inbound = 0
            outbound = 0
            For j = 2 To lastRowTrans
                If wsTransaction.Cells(j, 5).Value = itemName Then
                    If wsTransaction.Cells(j, 3).Value = "入庫" Then
                        inbound = inbound + wsTransaction.Cells(j, 6).Value
                    ElseIf wsTransaction.Cells(j, 3).Value = "出庫" Then
                        outbound = outbound + wsTransaction.Cells(j, 6).Value
                    End If
                End If
            Next j

            ' 現在庫を計算（棚卸後の入出庫を加減算）
            ' 注：実運用では棚卸日以降のデータのみ計算する必要あり
            wsMaster.Cells(i, 7).Value = currentStock + inbound - outbound
        End If
    Next i

    Application.ScreenUpdating = True

    MsgBox "現在庫の計算が完了しました。", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 発注判定と推奨発注数の計算
'-------------------------------------------------------------------------------
Public Sub CheckReorderPoints()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim currentStock As Double
    Dim reorderPoint As Double
    Dim minUnit As Double
    Dim completeUnit As String
    Dim completeQty As Double
    Dim shortage As Double
    Dim orderQty As Double

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    Application.ScreenUpdating = False

    For i = 2 To lastRow
        currentStock = Val(ws.Cells(i, 7).Value)  ' 現在庫
        reorderPoint = Val(ws.Cells(i, 3).Value)  ' 発注点
        minUnit = Val(ws.Cells(i, 4).Value)       ' 最小単位
        completeUnit = ws.Cells(i, 5).Value       ' 完品単位
        completeQty = Val(ws.Cells(i, 6).Value)   ' 完品個数

        If reorderPoint > 0 Then
            If currentStock <= reorderPoint Then
                ws.Cells(i, 8).Value = "要発注"
                ws.Cells(i, 8).Interior.Color = RGB(255, 199, 206)
                ws.Cells(i, 8).Font.Color = RGB(156, 0, 6)

                ' 推奨発注数を計算
                shortage = reorderPoint - currentStock + reorderPoint ' 発注点の2倍まで補充

                ' 完品単位で切り上げ
                If completeQty > 0 Then
                    orderQty = Application.WorksheetFunction.Ceiling(shortage / completeQty, 1) * completeQty
                Else
                    orderQty = shortage
                End If

                ' 最小単位で端数処理
                If minUnit > 0 Then
                    orderQty = Application.WorksheetFunction.Ceiling(orderQty / minUnit, 1) * minUnit
                End If

                ws.Cells(i, 9).Value = orderQty
            Else
                ws.Cells(i, 8).Value = "在庫あり"
                ws.Cells(i, 8).Interior.Color = RGB(198, 239, 206)
                ws.Cells(i, 8).Font.Color = RGB(0, 97, 0)
                ws.Cells(i, 9).Value = 0
            End If
        Else
            ws.Cells(i, 8).Value = "-"
            ws.Cells(i, 8).Interior.ColorIndex = xlNone
            ws.Cells(i, 8).Font.ColorIndex = xlAutomatic
            ws.Cells(i, 9).Value = "-"
        End If
    Next i

    ws.Columns("G:I").AutoFit

    Application.ScreenUpdating = True

    MsgBox "発注判定が完了しました。", vbInformation, "完了"
End Sub

'===============================================================================
' 発注管理機能
'===============================================================================

'-------------------------------------------------------------------------------
' 発注リストを生成
'-------------------------------------------------------------------------------
Public Sub GenerateOrderList()
    Dim wsMaster As Worksheet
    Dim wsOrder As Worksheet
    Dim lastRowMaster As Long
    Dim lastRowOrder As Long
    Dim i As Long
    Dim orderCount As Long

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    Set wsOrder = ThisWorkbook.Sheets(ORDER_SHEET)

    lastRowMaster = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row
    lastRowOrder = wsOrder.Cells(wsOrder.Rows.Count, 1).End(xlUp).Row + 1

    orderCount = 0

    For i = 2 To lastRowMaster
        If wsMaster.Cells(i, 8).Value = "要発注" Then
            wsOrder.Cells(lastRowOrder, 1).Value = Date ' 発注日
            wsOrder.Cells(lastRowOrder, 2).Value = wsMaster.Cells(i, 1).Value ' 管理番号
            wsOrder.Cells(lastRowOrder, 3).Value = wsMaster.Cells(i, 2).Value ' 物品名
            wsOrder.Cells(lastRowOrder, 4).Value = wsMaster.Cells(i, 9).Value ' 発注数量

            ' 完品数を計算
            Dim completeQty As Double
            completeQty = Val(wsMaster.Cells(i, 6).Value)
            If completeQty > 0 Then
                wsOrder.Cells(lastRowOrder, 5).Value = wsMaster.Cells(i, 9).Value / completeQty
            Else
                wsOrder.Cells(lastRowOrder, 5).Value = wsMaster.Cells(i, 9).Value
            End If

            wsOrder.Cells(lastRowOrder, 6).Value = "未発注"

            lastRowOrder = lastRowOrder + 1
            orderCount = orderCount + 1
        End If
    Next i

    wsOrder.Columns("A:H").AutoFit

    MsgBox orderCount & "件の発注候補を追加しました。", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 発注ステータスを更新
'-------------------------------------------------------------------------------
Public Sub UpdateOrderStatus()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(ORDER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For i = 2 To lastRow
        Select Case ws.Cells(i, 6).Value
            Case "未発注"
                ws.Cells(i, 6).Interior.Color = RGB(255, 199, 206)
            Case "発注済"
                ws.Cells(i, 6).Interior.Color = RGB(255, 235, 156)
            Case "納品済"
                ws.Cells(i, 6).Interior.Color = RGB(198, 239, 206)
            Case Else
                ws.Cells(i, 6).Interior.ColorIndex = xlNone
        End Select
    Next i
End Sub

'===============================================================================
' ダッシュボード更新
'===============================================================================

'-------------------------------------------------------------------------------
' ダッシュボードを更新
'-------------------------------------------------------------------------------
Public Sub UpdateDashboard()
    Dim wsDash As Worksheet
    Dim wsMaster As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim totalItems As Long
    Dim needOrder As Long
    Dim outOfStock As Long

    Set wsDash = ThisWorkbook.Sheets(DASHBOARD_SHEET)
    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)

    lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    totalItems = 0
    needOrder = 0
    outOfStock = 0

    For i = 2 To lastRow
        If wsMaster.Cells(i, 2).Value <> "" Then
            totalItems = totalItems + 1

            If wsMaster.Cells(i, 8).Value = "要発注" Then
                needOrder = needOrder + 1
            End If

            If Val(wsMaster.Cells(i, 7).Value) = 0 Then
                outOfStock = outOfStock + 1
            End If
        End If
    Next i

    wsDash.Cells(3, 2).Value = Now
    wsDash.Cells(5, 2).Value = totalItems
    wsDash.Cells(6, 2).Value = needOrder
    wsDash.Cells(7, 2).Value = outOfStock

    ' 警告表示
    If needOrder > 0 Then
        wsDash.Cells(6, 2).Interior.Color = RGB(255, 199, 206)
    Else
        wsDash.Cells(6, 2).Interior.Color = RGB(198, 239, 206)
    End If

    If outOfStock > 0 Then
        wsDash.Cells(7, 2).Interior.Color = RGB(255, 199, 206)
    Else
        wsDash.Cells(7, 2).Interior.Color = RGB(198, 239, 206)
    End If
End Sub

'===============================================================================
' 一括処理
'===============================================================================

'-------------------------------------------------------------------------------
' 全処理を実行（インポート後に実行）
'-------------------------------------------------------------------------------
Public Sub RunAllProcesses()
    CalculateCurrentInventory
    CheckReorderPoints
    UpdateDashboard
    UpdateOrderStatus

    MsgBox "全ての処理が完了しました。", vbInformation, "完了"
End Sub

'===============================================================================
' ユーティリティ
'===============================================================================

'-------------------------------------------------------------------------------
' マスターデータを棚卸データから自動生成
'-------------------------------------------------------------------------------
Public Sub GenerateMasterFromInventory()
    Dim wsMaster As Worksheet
    Dim wsInventory As Worksheet
    Dim lastRowInv As Long
    Dim lastRowMaster As Long
    Dim i As Long
    Dim itemName As String
    Dim found As Boolean
    Dim j As Long

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    Set wsInventory = ThisWorkbook.Sheets(INVENTORY_SHEET)

    lastRowInv = wsInventory.Cells(wsInventory.Rows.Count, 2).End(xlUp).Row

    For i = 2 To lastRowInv
        itemName = wsInventory.Cells(i, 2).Value

        If itemName <> "" Then
            ' 既存チェック
            found = False
            lastRowMaster = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

            For j = 2 To lastRowMaster
                If wsMaster.Cells(j, 2).Value = itemName Then
                    found = True
                    Exit For
                End If
            Next j

            ' 新規追加
            If Not found Then
                lastRowMaster = lastRowMaster + 1
                wsMaster.Cells(lastRowMaster, 1).Value = "AUTO-" & Format(lastRowMaster - 1, "000") ' 管理番号
                wsMaster.Cells(lastRowMaster, 2).Value = itemName ' 物品名
                wsMaster.Cells(lastRowMaster, 3).Value = 10 ' 発注点（デフォルト）
                wsMaster.Cells(lastRowMaster, 4).Value = 1 ' 最小単位
                wsMaster.Cells(lastRowMaster, 5).Value = "個" ' 完品単位
                wsMaster.Cells(lastRowMaster, 6).Value = 1 ' 完品個数
            End If
        End If
    Next i

    wsMaster.Columns("A:I").AutoFit

    MsgBox "マスターデータの生成が完了しました。" & vbCrLf & _
           "発注点・単位設定を確認してください。", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' レポート出力（発注必要品目リスト）
'-------------------------------------------------------------------------------
Public Sub ExportOrderReport()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim filePath As String
    Dim fileNum As Integer
    Dim orderCount As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    filePath = Application.GetSaveAsFilename( _
        InitialFileName:="発注リスト_" & Format(Date, "yyyy-mm-dd") & ".csv", _
        FileFilter:="CSVファイル (*.csv), *.csv", _
        Title:="発注リストを保存")

    If filePath = "False" Then Exit Sub

    fileNum = FreeFile
    Open filePath For Output As #fileNum

    ' ヘッダー
    Print #fileNum, "管理番号,物品名,現在庫,発注点,推奨発注数,完品単位,完品数"

    orderCount = 0
    For i = 2 To lastRow
        If ws.Cells(i, 8).Value = "要発注" Then
            Dim completeNum As Double
            If Val(ws.Cells(i, 6).Value) > 0 Then
                completeNum = Val(ws.Cells(i, 9).Value) / Val(ws.Cells(i, 6).Value)
            Else
                completeNum = Val(ws.Cells(i, 9).Value)
            End If

            Print #fileNum, ws.Cells(i, 1).Value & "," & _
                           ws.Cells(i, 2).Value & "," & _
                           ws.Cells(i, 7).Value & "," & _
                           ws.Cells(i, 3).Value & "," & _
                           ws.Cells(i, 9).Value & "," & _
                           ws.Cells(i, 5).Value & "," & _
                           completeNum
            orderCount = orderCount + 1
        End If
    Next i

    Close #fileNum

    MsgBox orderCount & "件の発注リストを出力しました。" & vbCrLf & _
           filePath, vbInformation, "完了"
End Sub
