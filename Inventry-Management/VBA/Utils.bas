'===============================================================================
' 共通ユーティリティ関数モジュール
' Version: 2.0
' 作成日: 2025-11-27
'
' モジュール名: Utils
'===============================================================================

Option Explicit

' 定数定義
Public Const MASTER_SHEET As String = "マスター設定"
Public Const INVENTORY_SHEET As String = "棚卸データ"
Public Const TRANSACTION_SHEET As String = "入出庫履歴"
Public Const ORDER_SHEET As String = "発注管理"
Public Const ALERT_SHEET As String = "アラート"
Public Const TREND_SHEET As String = "使用量トレンド"
Public Const STOCK_VIEW_SHEET As String = "在庫一覧"
Public Const HOME_SHEET As String = "ホーム"

'===============================================================================
' 単位変換関数
'===============================================================================

'-------------------------------------------------------------------------------
' 荷姿+端数 → 最小単位に変換
'-------------------------------------------------------------------------------
Public Function ConvertToMinUnit(packages As Long, remainder As Long, itemName As String) As Long
    On Error GoTo ErrorHandler

    Dim packageSize As Long
    packageSize = GetPackageSize(itemName)

    ConvertToMinUnit = (packages * packageSize) + remainder
    Exit Function

ErrorHandler:
    MsgBox "単位変換エラー: " & itemName & vbCrLf & Err.Description, vbCritical
    ConvertToMinUnit = 0
End Function

'-------------------------------------------------------------------------------
' 最小単位 → 荷姿表示に変換（表示用）
'-------------------------------------------------------------------------------
Public Function FormatAsPackage(qty As Long, itemName As String) As String
    On Error GoTo ErrorHandler

    Dim packageUnit As String
    Dim minUnit As String
    Dim packageSize As Long
    Dim packages As Long
    Dim remainder As Long

    packageUnit = GetPackageUnitName(itemName)
    minUnit = GetMinUnitName(itemName)
    packageSize = GetPackageSize(itemName)

    If packageSize = 0 Then
        FormatAsPackage = qty & minUnit
        Exit Function
    End If

    packages = qty \ packageSize
    remainder = qty Mod packageSize

    If remainder = 0 Then
        FormatAsPackage = packages & packageUnit & " (" & qty & minUnit & ")"
    Else
        FormatAsPackage = packages & packageUnit & "+" & remainder & minUnit & " (" & qty & minUnit & ")"
    End If
    Exit Function

ErrorHandler:
    FormatAsPackage = qty & "個"
End Function

'===============================================================================
' マスターデータ取得関数
'===============================================================================

'-------------------------------------------------------------------------------
' 物品の最小単位名を取得
'-------------------------------------------------------------------------------
Public Function GetMinUnitName(itemName As String) As String
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    For i = 2 To lastRow
        If ws.Cells(i, 2).Value = itemName Then
            GetMinUnitName = ws.Cells(i, 3).Value
            Exit Function
        End If
    Next i

    GetMinUnitName = "個"
    Exit Function

ErrorHandler:
    GetMinUnitName = "個"
End Function

'-------------------------------------------------------------------------------
' 物品の荷姿単位名を取得
'-------------------------------------------------------------------------------
Public Function GetPackageUnitName(itemName As String) As String
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    For i = 2 To lastRow
        If ws.Cells(i, 2).Value = itemName Then
            GetPackageUnitName = ws.Cells(i, 4).Value
            Exit Function
        End If
    Next i

    GetPackageUnitName = "セット"
    Exit Function

ErrorHandler:
    GetPackageUnitName = "セット"
End Function

'-------------------------------------------------------------------------------
' 物品の荷姿入数を取得
'-------------------------------------------------------------------------------
Public Function GetPackageSize(itemName As String) As Long
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    For i = 2 To lastRow
        If ws.Cells(i, 2).Value = itemName Then
            GetPackageSize = ws.Cells(i, 5).Value
            Exit Function
        End If
    Next i

    GetPackageSize = 1
    Exit Function

ErrorHandler:
    GetPackageSize = 1
End Function

'-------------------------------------------------------------------------------
' 物品の発注点を取得（最小単位）
'-------------------------------------------------------------------------------
Public Function GetReorderPoint(itemName As String) As Long
    On Error GoTo ErrorHandler

    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long

    Set ws = ThisWorkbook.Sheets(MASTER_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    For i = 2 To lastRow
        If ws.Cells(i, 2).Value = itemName Then
            GetReorderPoint = ws.Cells(i, 6).Value
            Exit Function
        End If
    Next i

    GetReorderPoint = 0
    Exit Function

ErrorHandler:
    GetReorderPoint = 0
End Function

'===============================================================================
' フォルダ・ファイル操作
'===============================================================================

'-------------------------------------------------------------------------------
' フォルダが存在しなければ作成
'-------------------------------------------------------------------------------
Public Sub CreateFolderIfNotExists(folderPath As String)
    Dim fso As Object
    Set fso = CreateObject("Scripting.FileSystemObject")

    If Not fso.FolderExists(folderPath) Then
        fso.CreateFolder folderPath
    End If
End Sub

'-------------------------------------------------------------------------------
' ファイル名に使える形式の日付文字列を生成
'-------------------------------------------------------------------------------
Public Function GetDateString() As String
    GetDateString = Format(Date, "yyyy-mm-dd")
End Function

'-------------------------------------------------------------------------------
' ファイル名に使える形式の年月文字列を生成
'-------------------------------------------------------------------------------
Public Function GetYearMonthString() As String
    GetYearMonthString = Format(Date, "yyyy-mm")
End Function

'===============================================================================
' シート操作
'===============================================================================

'-------------------------------------------------------------------------------
' シートが存在するかチェック
'-------------------------------------------------------------------------------
Public Function SheetExists(sheetName As String) As Boolean
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(sheetName)
    SheetExists = Not ws Is Nothing
    On Error GoTo 0
End Function

'-------------------------------------------------------------------------------
' シートをクリア（ヘッダー行は残す）
'-------------------------------------------------------------------------------
Public Sub ClearSheetData(sheetName As String)
    Dim ws As Worksheet
    Dim lastRow As Long

    If Not SheetExists(sheetName) Then Exit Sub

    Set ws = ThisWorkbook.Sheets(sheetName)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow > 1 Then
        ws.Range("A2:Z" & lastRow).ClearContents
    End If
End Sub

'===============================================================================
' データ検証
'===============================================================================

'-------------------------------------------------------------------------------
' 数値チェック
'-------------------------------------------------------------------------------
Public Function IsNumericValue(value As Variant) As Boolean
    IsNumericValue = IsNumeric(value) And value <> ""
End Function

'-------------------------------------------------------------------------------
' 日付チェック
'-------------------------------------------------------------------------------
Public Function IsDateValue(value As Variant) As Boolean
    IsDateValue = IsDate(value)
End Function

'===============================================================================
' メッセージ表示
'===============================================================================

'-------------------------------------------------------------------------------
' 成功メッセージ
'-------------------------------------------------------------------------------
Public Sub ShowSuccessMessage(message As String)
    MsgBox message, vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' エラーメッセージ
'-------------------------------------------------------------------------------
Public Sub ShowErrorMessage(message As String)
    MsgBox message, vbCritical, "エラー"
End Sub

'-------------------------------------------------------------------------------
' 確認メッセージ
'-------------------------------------------------------------------------------
Public Function ShowConfirmMessage(message As String) As Boolean
    ShowConfirmMessage = (MsgBox(message, vbYesNo + vbQuestion, "確認") = vbYes)
End Function
