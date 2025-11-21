Attribute VB_Name = "InventoryManagement"
'===============================================================================
' 在庫管理・注文管理システム VBAモジュール
' Version: 1.0
' 作成日: 2025-11-19
'===============================================================================

Option Explicit

' 定数定義
Private Const HELP_SHEET As String = "使い方ガイド"
Private Const MASTER_SHEET As String = "マスター設定"
Private Const INVENTORY_SHEET As String = "棚卸データ"
Private Const TRANSACTION_SHEET As String = "入出庫履歴"
Private Const ORDER_SHEET As String = "発注管理"
Private Const DASHBOARD_SHEET As String = "ダッシュボード"
Private Const DISCREPANCY_SHEET As String = "差異分析"
Private Const PREV_INVENTORY_SHEET As String = "前回棚卸"
Private Const USAGE_ANALYSIS_SHEET As String = "使用量分析"

'===============================================================================
' 初期セットアップ
'===============================================================================

'-------------------------------------------------------------------------------
' シート初期化（システム全体のセットアップ）
'-------------------------------------------------------------------------------
Public Sub InitializeSystem()
    Application.ScreenUpdating = False

    ' 各シートを作成
    CreateSheetIfNotExists HELP_SHEET
    CreateSheetIfNotExists MASTER_SHEET
    CreateSheetIfNotExists INVENTORY_SHEET
    CreateSheetIfNotExists PREV_INVENTORY_SHEET
    CreateSheetIfNotExists TRANSACTION_SHEET
    CreateSheetIfNotExists ORDER_SHEET
    CreateSheetIfNotExists DISCREPANCY_SHEET
    CreateSheetIfNotExists USAGE_ANALYSIS_SHEET
    CreateSheetIfNotExists DASHBOARD_SHEET

    ' 使い方ガイドシートのセットアップ
    SetupHelpSheet

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

    ' 差異分析シートのセットアップ
    SetupDiscrepancySheet

    ' 前回棚卸シートのセットアップ
    SetupPrevInventorySheet

    ' 使用量分析シートのセットアップ
    SetupUsageAnalysisSheet

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
' 使い方ガイドシートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupHelpSheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(HELP_SHEET)

    ' シートをクリア
    ws.Cells.Clear

    ' タイトル行
    With ws.Range("A1:F1")
        .Merge
        .Value = "在庫管理・注文管理システム 使い方ガイド"
        .Font.Size = 18
        .Font.Bold = True
        .Interior.Color = RGB(68, 114, 196)
        .Font.Color = RGB(255, 255, 255)
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .RowHeight = 40
    End With

    ' システム概要
    ws.Range("A3").Value = "【システム概要】"
    ws.Range("A3").Font.Size = 14
    ws.Range("A3").Font.Bold = True
    ws.Range("A3").Interior.Color = RGB(217, 225, 242)

    ws.Range("A4").Value = "このシステムは、物品の在庫管理・棚卸・発注管理を効率的に行うためのExcel VBAツールです。"
    ws.Range("A5").Value = "Webアプリケーションと連携して、リアルタイムでの在庫追跡と履歴管理が可能です。"
    ws.Range("A6").Value = ""

    ' 主な機能
    ws.Range("A7").Value = "【主な機能】"
    ws.Range("A7").Font.Size = 14
    ws.Range("A7").Font.Bold = True
    ws.Range("A7").Interior.Color = RGB(217, 225, 242)

    ws.Range("A8").Value = "✓ 物品マスター管理（管理番号、品名、発注点、単位設定）"
    ws.Range("A9").Value = "✓ 入出庫履歴の自動記録と追跡"
    ws.Range("A10").Value = "✓ 定期棚卸データの管理と差異分析"
    ws.Range("A11").Value = "✓ 発注管理と発注点に基づく自動アラート"
    ws.Range("A12").Value = "✓ ダッシュボードでの在庫状況可視化"
    ws.Range("A13").Value = "✓ 使用量分析とトレンド把握"
    ws.Range("A14").Value = ""

    ' 各シートの詳細説明
    ws.Range("A15").Value = "【各シートの詳細説明】"
    ws.Range("A15").Font.Size = 14
    ws.Range("A15").Font.Bold = True
    ws.Range("A15").Interior.Color = RGB(217, 225, 242)

    Dim row As Integer
    row = 16

    ' 1. マスター設定シート
    ws.Cells(row, 1).Value = "1. マスター設定シート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "管理対象物品の基本情報を登録・管理するマスターデータベースです。"
    row = row + 1

    ws.Cells(row, 1).Value = "【主な項目】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "・管理番号：物品を一意に識別するコード（例：A001, B002）"
    row = row + 1
    ws.Cells(row, 2).Value = "・物品名：物品の正式名称（例：ボールペン 黒、コピー用紙 A4）"
    row = row + 1
    ws.Cells(row, 2).Value = "・発注点：この在庫数を下回ったら発注が必要（例：10個）"
    row = row + 1
    ws.Cells(row, 2).Value = "・最小単位：最小の取り扱い単位（例：本、枚、箱）"
    row = row + 1
    ws.Cells(row, 2).Value = "・完品単位：発注時の単位（例：ダース、ケース、箱）"
    row = row + 1
    ws.Cells(row, 2).Value = "・完品個数：完品単位1つに含まれる最小単位の数（例：1ダース=12本）"
    row = row + 1
    ws.Cells(row, 2).Value = "・現在庫：リアルタイムで更新される現在の在庫数"
    row = row + 1
    ws.Cells(row, 2).Value = "・発注要否：発注点を下回った場合「要発注」と自動表示"
    row = row + 1
    ws.Cells(row, 2).Value = "・推奨発注数：適正在庫まで回復するための推奨発注量"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 新規物品を追加する場合は、最終行の次の行に必要情報を入力"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 管理番号は重複しないように設定（A001, A002...のように連番推奨）"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 発注点は、過去の使用実績や調達リードタイムを考慮して設定"
    row = row + 1
    ws.Cells(row, 2).Value = "4) 完品単位と完品個数を正確に設定することで、発注量計算が正確になります"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 2. 棚卸データシート
    ws.Cells(row, 1).Value = "2. 棚卸データシート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "定期的な実地棚卸の結果を記録し、理論在庫との差異を把握します。"
    row = row + 1

    ws.Cells(row, 1).Value = "【主な項目】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "・棚卸日：実地棚卸を実施した日付"
    row = row + 1
    ws.Cells(row, 2).Value = "・物品名：プルダウンから選択（マスター設定の物品リストから選択）"
    row = row + 1
    ws.Cells(row, 2).Value = "・管理番号：物品名を選択すると自動的に表示されます"
    row = row + 1
    ws.Cells(row, 2).Value = "・実地棚卸数：実際に数えた在庫数を入力"
    row = row + 1
    ws.Cells(row, 2).Value = "・理論在庫：システム上の在庫数（マスターから自動取得）"
    row = row + 1
    ws.Cells(row, 2).Value = "・差異：実地棚卸数 - 理論在庫（自動計算、プラスは実在庫過剰、マイナスは不足）"
    row = row + 1
    ws.Cells(row, 2).Value = "・備考：差異の原因や特記事項を記入"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 月初や四半期ごとなど、定期的に実地棚卸を実施"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 棚卸日を入力し、物品名をプルダウンから選択（管理番号と理論在庫は自動表示）"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 実地棚卸数を入力すると、差異が自動計算されます"
    row = row + 1
    ws.Cells(row, 2).Value = "4) 大きな差異がある場合は、原因を調査して備考欄に記録"
    row = row + 1
    ws.Cells(row, 2).Value = "5) 棚卸後は「前回棚卸」シートに履歴が保存されます"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 3. 入出庫履歴シート
    ws.Cells(row, 1).Value = "3. 入出庫履歴シート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "すべての入庫・出庫の履歴を記録し、在庫の動きを追跡します。"
    row = row + 1

    ws.Cells(row, 1).Value = "【主な項目】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "・タイムスタンプ：記録が作成された日時"
    row = row + 1
    ws.Cells(row, 2).Value = "・記録日：実際の入出庫日（タイムスタンプと同じか遡及入力の場合は過去日）"
    row = row + 1
    ws.Cells(row, 2).Value = "・種別：「入庫」「出庫」「新規登録」のいずれか"
    row = row + 1
    ws.Cells(row, 2).Value = "・記録者：操作を行った担当者名"
    row = row + 1
    ws.Cells(row, 2).Value = "・品名：対象物品の名称"
    row = row + 1
    ws.Cells(row, 2).Value = "・個数：入庫または出庫した数量"
    row = row + 1
    ws.Cells(row, 2).Value = "・備考：補足情報（納品先、払出先、発注番号など）"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) Webアプリから入出庫登録を行うと、このシートに自動記録されます"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 手動で追記する場合は、必ず全項目を正確に入力してください"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 過去のデータは削除せず保存することで、使用量分析に活用できます"
    row = row + 1
    ws.Cells(row, 2).Value = "4) 大量のデータが蓄積した場合は、年度ごとにアーカイブを検討"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 4. 発注管理シート
    ws.Cells(row, 1).Value = "4. 発注管理シート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "発注業務を管理し、納品状況を追跡します。"
    row = row + 1

    ws.Cells(row, 1).Value = "【主な項目】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "・発注日：発注を行った日付"
    row = row + 1
    ws.Cells(row, 2).Value = "・物品名：プルダウンから選択（マスター設定の物品リストから選択）"
    row = row + 1
    ws.Cells(row, 2).Value = "・管理番号：物品名を選択すると自動的に表示されます"
    row = row + 1
    ws.Cells(row, 2).Value = "・発注数：発注した数量を入力"
    row = row + 1
    ws.Cells(row, 2).Value = "・単位：物品名を選択すると自動的に表示されます（マスター設定の最小単位）"
    row = row + 1
    ws.Cells(row, 2).Value = "・納期：納品予定日を入力"
    row = row + 1
    ws.Cells(row, 2).Value = "・ステータス：プルダウンから選択（発注済／納品済／キャンセル）"
    row = row + 1
    ws.Cells(row, 2).Value = "・発注先：発注した業者名を入力"
    row = row + 1
    ws.Cells(row, 2).Value = "・担当者：発注処理を行った担当者を入力"
    row = row + 1
    ws.Cells(row, 2).Value = "・備考：発注番号、見積番号、特記事項などを入力"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) マスター設定シートで「要発注」と表示された物品を確認"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 発注日を入力し、物品名をプルダウンから選択（管理番号と単位は自動表示）"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 発注数、納期、発注先、担当者を入力"
    row = row + 1
    ws.Cells(row, 2).Value = "4) ステータスはデフォルトで「発注済」、必要に応じてプルダウンから変更"
    row = row + 1
    ws.Cells(row, 2).Value = "5) 納品されたら、ステータスを「納品済」に更新し、入庫登録を実施"
    row = row + 1
    ws.Cells(row, 2).Value = "6) 納期遅延がある場合は、備考欄に理由を記録"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 5. ダッシュボードシート
    ws.Cells(row, 1).Value = "5. ダッシュボードシート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "在庫状況を一目で把握できる統合ビューを提供します。"
    row = row + 1

    ws.Cells(row, 1).Value = "【表示内容】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "・在庫状況サマリー：総在庫数、要発注品目数、発注済品目数"
    row = row + 1
    ws.Cells(row, 2).Value = "・発注アラート一覧：発注点を下回っている物品のリスト"
    row = row + 1
    ws.Cells(row, 2).Value = "・最近の入出庫履歴：直近10件の入出庫記録"
    row = row + 1
    ws.Cells(row, 2).Value = "・グラフ：在庫推移、カテゴリ別在庫、使用量トレンドなど"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 毎日の業務開始時に確認し、要発注品目をチェック"
    row = row + 1
    ws.Cells(row, 2).Value = "2) データは他のシートから自動集計されるため、手動入力は不要"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 印刷して会議資料として活用することも可能"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 6. 差異分析シート
    ws.Cells(row, 1).Value = "6. 差異分析シート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "棚卸時の差異を詳細に分析し、在庫管理の精度向上に役立てます。"
    row = row + 1

    ws.Cells(row, 1).Value = "【分析内容】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "・差異の大きい物品のランキング"
    row = row + 1
    ws.Cells(row, 2).Value = "・差異率の計算（差異÷理論在庫×100）"
    row = row + 1
    ws.Cells(row, 2).Value = "・過去の棚卸との比較"
    row = row + 1
    ws.Cells(row, 2).Value = "・傾向分析（特定物品で常に差異が発生していないか）"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 棚卸完了後、このシートで差異状況を確認"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 差異率が高い物品は、管理方法の見直しを検討"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 継続的に差異が発生する場合は、発注点や保管方法の改善が必要"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 7. 前回棚卸シート
    ws.Cells(row, 1).Value = "7. 前回棚卸シート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "過去の棚卸データを保存し、履歴として参照できるようにします。"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 新しい棚卸を開始する前に、現在の棚卸データがここに自動保存されます"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 過去の棚卸データと比較する際に参照"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 手動での編集は原則不要（履歴保存用）"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 8. 使用量分析シート
    ws.Cells(row, 1).Value = "8. 使用量分析シート"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Font.Size = 12
    ws.Cells(row, 1).Interior.Color = RGB(255, 242, 204)
    row = row + 1

    ws.Cells(row, 1).Value = "【目的】"
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 2).Value = "物品ごとの使用量を分析し、適正在庫や発注サイクルの最適化に活用します。"
    row = row + 1

    ws.Cells(row, 1).Value = "【分析内容】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "・月別使用量の集計"
    row = row + 1
    ws.Cells(row, 2).Value = "・平均使用量の計算"
    row = row + 1
    ws.Cells(row, 2).Value = "・使用量トレンド（増加傾向、減少傾向）"
    row = row + 1
    ws.Cells(row, 2).Value = "・季節変動の把握"
    row = row + 1

    ws.Cells(row, 1).Value = "【使い方】"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 定期的にこのシートを確認し、使用量パターンを把握"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 平均使用量に基づいて、発注点を適切に設定"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 使用量が大きく変動した場合は、原因を調査"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 運用フロー
    ws.Cells(row, 1).Value = "【基本的な運用フロー】"
    ws.Cells(row, 1).Font.Size = 14
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Interior.Color = RGB(217, 225, 242)
    row = row + 1

    ws.Cells(row, 1).Value = "日次作業"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) ダッシュボードで在庫状況を確認"
    row = row + 1
    ws.Cells(row, 2).Value = "2) Webアプリから入出庫を登録（自動的に履歴シートに記録）"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 要発注品目がある場合は発注手続きを実施"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ws.Cells(row, 1).Value = "週次作業"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 発注管理シートで納品状況を確認"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 納品された物品は入庫登録を実施"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 使用量分析シートで消費トレンドを確認"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ws.Cells(row, 1).Value = "月次作業"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "1) 実地棚卸を実施（棚卸データシートに記録）"
    row = row + 1
    ws.Cells(row, 2).Value = "2) 差異分析シートで在庫差異を確認・分析"
    row = row + 1
    ws.Cells(row, 2).Value = "3) 大きな差異があれば原因を調査し、改善策を実施"
    row = row + 1
    ws.Cells(row, 2).Value = "4) 必要に応じてマスターデータ（発注点など）を見直し"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' トラブルシューティング
    ws.Cells(row, 1).Value = "【よくある質問・トラブルシューティング】"
    ws.Cells(row, 1).Font.Size = 14
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Interior.Color = RGB(217, 225, 242)
    row = row + 1

    ws.Cells(row, 1).Value = "Q1. 在庫数が合わない場合"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "A: 入出庫履歴シートで最近の記録を確認してください。記録漏れや誤入力がないかチェックします。"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ws.Cells(row, 1).Value = "Q2. 発注点をどう設定すれば良いか"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "A: 使用量分析シートで平均使用量を確認し、「平均使用量 × 調達リードタイム（日数） + 安全在庫」で計算します。"
    row = row + 1
    ws.Cells(row, 2).Value = "   例：1日10個使用、調達7日、安全在庫30個の場合 → 10×7+30=100個"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ws.Cells(row, 1).Value = "Q3. Webアプリと連携できない"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "A: Google Apps Scriptの設定を確認してください。スクリプトIDとシート名が正しく設定されているか確認が必要です。"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ws.Cells(row, 1).Value = "Q4. データが多くなって動作が重い"
    ws.Cells(row, 1).Font.Bold = True
    row = row + 1
    ws.Cells(row, 2).Value = "A: 古い入出庫履歴データを別ファイルにアーカイブすることを検討してください。年度ごとに分けると良いでしょう。"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' 注意事項
    ws.Cells(row, 1).Value = "【注意事項】"
    ws.Cells(row, 1).Font.Size = 14
    ws.Cells(row, 1).Font.Bold = True
    ws.Cells(row, 1).Interior.Color = RGB(255, 199, 206)
    row = row + 1

    ws.Cells(row, 2).Value = "⚠ ヘッダー行（各シートの1行目）は削除・変更しないでください"
    row = row + 1
    ws.Cells(row, 2).Value = "⚠ 数式が設定されているセルは、上書きしないよう注意してください"
    row = row + 1
    ws.Cells(row, 2).Value = "⚠ 定期的にファイルのバックアップを取ることを推奨します"
    row = row + 1
    ws.Cells(row, 2).Value = "⚠ 複数人で同時編集する場合は、Google Sheetsの使用を推奨します"
    row = row + 1
    ws.Cells(row, 2).Value = "⚠ マスター設定の管理番号は、一度使用したら変更しないでください"
    row = row + 1
    ws.Cells(row, 1).Value = ""
    row = row + 1

    ' フッター
    ws.Cells(row, 1).Value = "更新日: " & Format(Now, "yyyy/mm/dd hh:mm")
    ws.Cells(row, 1).Font.Size = 9
    ws.Cells(row, 1).Font.Italic = True

    ' 列幅調整
    ws.Columns("A:A").ColumnWidth = 30
    ws.Columns("B:F").ColumnWidth = 80

    ' 全体のフォント設定
    ws.Cells.Font.Name = "メイリオ"
    ws.Cells.Font.Size = 10

    ' 文字の折り返し
    ws.Columns("B:F").WrapText = True

    ' シート保護（編集不可）
    ws.Protect DrawingObjects:=True, Contents:=True, Scenarios:=True

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
    Dim wsMaster As Worksheet
    Dim lastRow As Long

    Set ws = ThisWorkbook.Sheets(INVENTORY_SHEET)
    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)

    With ws
        .Cells(1, 1).Value = "棚卸日"
        .Cells(1, 2).Value = "物品名"
        .Cells(1, 3).Value = "管理番号"
        .Cells(1, 4).Value = "実地棚卸数"
        .Cells(1, 5).Value = "理論在庫"
        .Cells(1, 6).Value = "差異"
        .Cells(1, 7).Value = "備考"

        .Range("A1:G1").Font.Bold = True
        .Range("A1:G1").Interior.Color = RGB(237, 125, 49)
        .Range("A1:G1").Font.Color = RGB(255, 255, 255)
        .Columns("A:G").AutoFit

        ' B列（物品名）にデータ入力規則を設定
        lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row
        If lastRow > 1 Then
            ' 物品名のプルダウンリスト設定（2行目以降の100行分）
            With .Range("B2:B1000").Validation
                .Delete
                .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
                     Formula1:="=" & MASTER_SHEET & "!$B$2:$B$" & lastRow
                .IgnoreBlank = True
                .InCellDropdown = True
            End With

            ' C列（管理番号）に自動取得の数式を設定
            .Range("C2").Formula = "=IF(B2="""","""",IFERROR(INDEX(" & MASTER_SHEET & "!$A:$A,MATCH(B2," & MASTER_SHEET & "!$B:$B,0)),""""))"
            .Range("C2").Copy .Range("C3:C1000")

            ' E列（理論在庫）に数式を設定
            .Range("E2").Formula = "=IF(B2="""","""",IFERROR(INDEX(" & MASTER_SHEET & "!$G:$G,MATCH(B2," & MASTER_SHEET & "!$B:$B,0)),""""))"
            .Range("E2").Copy .Range("E3:E1000")

            ' F列（差異）に数式を設定
            .Range("F2").Formula = "=IF(D2="""","""",D2-E2)"
            .Range("F2").Copy .Range("F3:F1000")
        End If
    End With
End Sub

'-------------------------------------------------------------------------------
' 発注管理シートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupOrderSheet()
    Dim ws As Worksheet
    Dim wsMaster As Worksheet
    Dim lastRow As Long

    Set ws = ThisWorkbook.Sheets(ORDER_SHEET)
    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)

    With ws
        .Cells(1, 1).Value = "発注日"
        .Cells(1, 2).Value = "物品名"
        .Cells(1, 3).Value = "管理番号"
        .Cells(1, 4).Value = "発注数"
        .Cells(1, 5).Value = "単位"
        .Cells(1, 6).Value = "納期"
        .Cells(1, 7).Value = "ステータス"
        .Cells(1, 8).Value = "発注先"
        .Cells(1, 9).Value = "担当者"
        .Cells(1, 10).Value = "備考"

        .Range("A1:J1").Font.Bold = True
        .Range("A1:J1").Interior.Color = RGB(165, 165, 165)
        .Range("A1:J1").Font.Color = RGB(255, 255, 255)
        .Columns("A:J").AutoFit

        ' B列（物品名）にデータ入力規則を設定
        lastRow = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row
        If lastRow > 1 Then
            ' 物品名のプルダウンリスト設定（2行目以降の1000行分）
            With .Range("B2:B1000").Validation
                .Delete
                .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
                     Formula1:="=" & MASTER_SHEET & "!$B$2:$B$" & lastRow
                .IgnoreBlank = True
                .InCellDropdown = True
            End With

            ' C列（管理番号）に自動取得の数式を設定
            .Range("C2").Formula = "=IF(B2="""","""",IFERROR(INDEX(" & MASTER_SHEET & "!$A:$A,MATCH(B2," & MASTER_SHEET & "!$B:$B,0)),""""))"
            .Range("C2").Copy .Range("C3:C1000")

            ' E列（単位）に最小単位を自動取得
            .Range("E2").Formula = "=IF(B2="""","""",IFERROR(INDEX(" & MASTER_SHEET & "!$D:$D,MATCH(B2," & MASTER_SHEET & "!$B:$B,0)),""""))"
            .Range("E2").Copy .Range("E3:E1000")

            ' G列（ステータス）にデフォルト値を設定
            .Range("G2").Value = "発注済"

            ' G列にステータスのプルダウンリストを設定
            With .Range("G2:G1000").Validation
                .Delete
                .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
                     Formula1:="発注済,納品済,キャンセル"
                .IgnoreBlank = True
                .InCellDropdown = True
            End With
        End If
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

'===============================================================================
' 差異分析・補完機能
'===============================================================================

'-------------------------------------------------------------------------------
' 差異分析シートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupDiscrepancySheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(DISCREPANCY_SHEET)

    With ws
        .Cells(1, 1).Value = "品名"
        .Cells(1, 2).Value = "前回棚卸"
        .Cells(1, 3).Value = "入庫合計"
        .Cells(1, 4).Value = "出庫合計"
        .Cells(1, 5).Value = "理論在庫"
        .Cells(1, 6).Value = "今回棚卸"
        .Cells(1, 7).Value = "差異"
        .Cells(1, 8).Value = "差異率%"
        .Cells(1, 9).Value = "推定原因"
        .Cells(1, 10).Value = "補正種別"
        .Cells(1, 11).Value = "補正数量"

        .Range("A1:K1").Font.Bold = True
        .Range("A1:K1").Interior.Color = RGB(192, 0, 0)
        .Range("A1:K1").Font.Color = RGB(255, 255, 255)
        .Columns("A:K").AutoFit
    End With
End Sub

'-------------------------------------------------------------------------------
' 前回棚卸シートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupPrevInventorySheet()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets(PREV_INVENTORY_SHEET)

    With ws
        .Cells(1, 1).Value = "棚卸日"
        .Cells(1, 2).Value = "品名"
        .Cells(1, 3).Value = "数量"

        .Range("A1:C1").Font.Bold = True
        .Range("A1:C1").Interior.Color = RGB(128, 128, 128)
        .Range("A1:C1").Font.Color = RGB(255, 255, 255)
        .Columns("A:C").AutoFit
    End With
End Sub

'-------------------------------------------------------------------------------
' 前回棚卸データをインポート
'-------------------------------------------------------------------------------
Public Sub ImportPreviousInventoryCSV()
    Dim filePath As String
    Dim ws As Worksheet
    Dim line As String
    Dim fields() As String
    Dim fileNum As Integer
    Dim rowNum As Long

    filePath = Application.GetOpenFilename("CSVファイル (*.csv), *.csv", , "前回棚卸CSVファイルを選択")

    If filePath = "False" Then Exit Sub

    Set ws = ThisWorkbook.Sheets(PREV_INVENTORY_SHEET)

    ' 既存データをクリア
    If ws.Cells(ws.Rows.Count, 1).End(xlUp).Row > 1 Then
        ws.Range("A2:C" & ws.Cells(ws.Rows.Count, 1).End(xlUp).Row).ClearContents
    End If

    fileNum = FreeFile
    Open filePath For Input As #fileNum

    rowNum = 2

    Do While Not EOF(fileNum)
        Line Input #fileNum, line
        fields = ParseCSVLine(line)

        If UBound(fields) >= 2 Then
            ws.Cells(rowNum, 1).Value = fields(0)
            ws.Cells(rowNum, 2).Value = fields(1)
            ws.Cells(rowNum, 3).Value = Val(fields(2))
            rowNum = rowNum + 1
        End If
    Loop

    Close #fileNum

    ws.Columns("A:C").AutoFit

    MsgBox "前回棚卸データのインポートが完了しました。" & vbCrLf & _
           "インポート件数: " & (rowNum - 2) & "件", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 棚卸差異分析を実行
'-------------------------------------------------------------------------------
Public Sub AnalyzeInventoryDiscrepancy()
    Dim wsPrev As Worksheet
    Dim wsCurrent As Worksheet
    Dim wsTrans As Worksheet
    Dim wsDisc As Worksheet
    Dim lastRowPrev As Long
    Dim lastRowCurrent As Long
    Dim lastRowTrans As Long
    Dim i As Long, j As Long
    Dim itemName As String
    Dim prevQty As Double
    Dim currentQty As Double
    Dim inbound As Double
    Dim outbound As Double
    Dim theoretical As Double
    Dim discrepancy As Double
    Dim discRate As Double
    Dim rowNum As Long
    Dim discCount As Long

    Set wsPrev = ThisWorkbook.Sheets(PREV_INVENTORY_SHEET)
    Set wsCurrent = ThisWorkbook.Sheets(INVENTORY_SHEET)
    Set wsTrans = ThisWorkbook.Sheets(TRANSACTION_SHEET)
    Set wsDisc = ThisWorkbook.Sheets(DISCREPANCY_SHEET)

    ' 差異分析シートをクリア
    If wsDisc.Cells(wsDisc.Rows.Count, 1).End(xlUp).Row > 1 Then
        wsDisc.Range("A2:K" & wsDisc.Cells(wsDisc.Rows.Count, 1).End(xlUp).Row).ClearContents
    End If

    lastRowPrev = wsPrev.Cells(wsPrev.Rows.Count, 2).End(xlUp).Row
    lastRowCurrent = wsCurrent.Cells(wsCurrent.Rows.Count, 2).End(xlUp).Row
    lastRowTrans = wsTrans.Cells(wsTrans.Rows.Count, 5).End(xlUp).Row

    Application.ScreenUpdating = False

    rowNum = 2
    discCount = 0

    ' 前回棚卸の各品目について分析
    For i = 2 To lastRowPrev
        itemName = wsPrev.Cells(i, 2).Value

        If itemName <> "" Then
            prevQty = wsPrev.Cells(i, 3).Value

            ' 今回棚卸数量を取得
            currentQty = 0
            For j = 2 To lastRowCurrent
                If wsCurrent.Cells(j, 2).Value = itemName Then
                    currentQty = wsCurrent.Cells(j, 3).Value
                    Exit For
                End If
            Next j

            ' 入出庫履歴から合計を計算
            inbound = 0
            outbound = 0
            For j = 2 To lastRowTrans
                If wsTrans.Cells(j, 5).Value = itemName Then
                    If wsTrans.Cells(j, 3).Value = "入庫" Then
                        inbound = inbound + wsTrans.Cells(j, 6).Value
                    ElseIf wsTrans.Cells(j, 3).Value = "出庫" Then
                        outbound = outbound + wsTrans.Cells(j, 6).Value
                    End If
                End If
            Next j

            ' 理論在庫を計算
            theoretical = prevQty + inbound - outbound

            ' 差異を計算
            discrepancy = currentQty - theoretical

            ' 差異率を計算
            If theoretical <> 0 Then
                discRate = (discrepancy / theoretical) * 100
            Else
                If currentQty <> 0 Then
                    discRate = 100
                Else
                    discRate = 0
                End If
            End If

            ' 結果を書き込み
            wsDisc.Cells(rowNum, 1).Value = itemName
            wsDisc.Cells(rowNum, 2).Value = prevQty
            wsDisc.Cells(rowNum, 3).Value = inbound
            wsDisc.Cells(rowNum, 4).Value = outbound
            wsDisc.Cells(rowNum, 5).Value = theoretical
            wsDisc.Cells(rowNum, 6).Value = currentQty
            wsDisc.Cells(rowNum, 7).Value = discrepancy
            wsDisc.Cells(rowNum, 8).Value = Round(discRate, 1)

            ' 推定原因を判定
            If discrepancy = 0 Then
                wsDisc.Cells(rowNum, 9).Value = "一致"
                wsDisc.Cells(rowNum, 9).Interior.Color = RGB(198, 239, 206)
            ElseIf discrepancy > 0 Then
                wsDisc.Cells(rowNum, 9).Value = "入庫漏れ可能性"
                wsDisc.Cells(rowNum, 9).Interior.Color = RGB(255, 235, 156)
                wsDisc.Cells(rowNum, 10).Value = "入庫"
                wsDisc.Cells(rowNum, 11).Value = discrepancy
                discCount = discCount + 1
            Else
                wsDisc.Cells(rowNum, 9).Value = "出庫漏れ可能性"
                wsDisc.Cells(rowNum, 9).Interior.Color = RGB(255, 199, 206)
                wsDisc.Cells(rowNum, 10).Value = "出庫"
                wsDisc.Cells(rowNum, 11).Value = Abs(discrepancy)
                discCount = discCount + 1
            End If

            ' 差異セルの書式設定
            If discrepancy <> 0 Then
                wsDisc.Cells(rowNum, 7).Font.Bold = True
                If discrepancy > 0 Then
                    wsDisc.Cells(rowNum, 7).Font.Color = RGB(0, 112, 192)
                Else
                    wsDisc.Cells(rowNum, 7).Font.Color = RGB(192, 0, 0)
                End If
            End If

            rowNum = rowNum + 1
        End If
    Next i

    wsDisc.Columns("A:K").AutoFit

    Application.ScreenUpdating = True

    MsgBox "差異分析が完了しました。" & vbCrLf & _
           "分析件数: " & (rowNum - 2) & "件" & vbCrLf & _
           "差異検出: " & discCount & "件", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 差異を補正データとして入出庫履歴に追加
'-------------------------------------------------------------------------------
Public Sub ApplyDiscrepancyCompensation()
    Dim wsDisc As Worksheet
    Dim wsTrans As Worksheet
    Dim lastRowDisc As Long
    Dim lastRowTrans As Long
    Dim i As Long
    Dim compensationCount As Long
    Dim response As VbMsgBoxResult

    Set wsDisc = ThisWorkbook.Sheets(DISCREPANCY_SHEET)
    Set wsTrans = ThisWorkbook.Sheets(TRANSACTION_SHEET)

    lastRowDisc = wsDisc.Cells(wsDisc.Rows.Count, 1).End(xlUp).Row

    If lastRowDisc < 2 Then
        MsgBox "差異分析データがありません。" & vbCrLf & _
               "先に「差異分析」を実行してください。", vbExclamation, "エラー"
        Exit Sub
    End If

    ' 確認ダイアログ
    response = MsgBox("差異データを入出庫履歴に補正レコードとして追加しますか？" & vbCrLf & vbCrLf & _
                      "この操作により、差異を解消するための" & vbCrLf & _
                      "入庫/出庫レコードが自動生成されます。", _
                      vbYesNo + vbQuestion, "補正データ追加確認")

    If response = vbNo Then Exit Sub

    Application.ScreenUpdating = False

    compensationCount = 0

    For i = 2 To lastRowDisc
        Dim itemName As String
        Dim compType As String
        Dim compQty As Double

        itemName = wsDisc.Cells(i, 1).Value
        compType = wsDisc.Cells(i, 10).Value
        compQty = Val(wsDisc.Cells(i, 11).Value)

        If compType <> "" And compQty > 0 Then
            lastRowTrans = wsTrans.Cells(wsTrans.Rows.Count, 1).End(xlUp).Row + 1

            wsTrans.Cells(lastRowTrans, 1).Value = Now ' タイムスタンプ
            wsTrans.Cells(lastRowTrans, 2).Value = Date ' 記録日
            wsTrans.Cells(lastRowTrans, 3).Value = compType ' 種別
            wsTrans.Cells(lastRowTrans, 4).Value = "差異補正" ' 記録者
            wsTrans.Cells(lastRowTrans, 5).Value = itemName ' 品名
            wsTrans.Cells(lastRowTrans, 6).Value = compQty ' 個数

            ' 補正済みの行を色付け
            wsDisc.Range(wsDisc.Cells(i, 1), wsDisc.Cells(i, 11)).Interior.Color = RGB(221, 235, 247)

            compensationCount = compensationCount + 1
        End If
    Next i

    wsTrans.Columns("A:F").AutoFit

    Application.ScreenUpdating = True

    MsgBox compensationCount & "件の補正レコードを追加しました。" & vbCrLf & vbCrLf & _
           "「全処理を実行」で在庫を再計算してください。", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 差異レポートをCSV出力
'-------------------------------------------------------------------------------
Public Sub ExportDiscrepancyReport()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim filePath As String
    Dim fileNum As Integer
    Dim discCount As Long

    Set ws = ThisWorkbook.Sheets(DISCREPANCY_SHEET)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        MsgBox "差異分析データがありません。", vbExclamation, "エラー"
        Exit Sub
    End If

    filePath = Application.GetSaveAsFilename( _
        InitialFileName:="差異分析レポート_" & Format(Date, "yyyy-mm-dd") & ".csv", _
        FileFilter:="CSVファイル (*.csv), *.csv", _
        Title:="差異分析レポートを保存")

    If filePath = "False" Then Exit Sub

    fileNum = FreeFile
    Open filePath For Output As #fileNum

    ' ヘッダー
    Print #fileNum, "品名,前回棚卸,入庫合計,出庫合計,理論在庫,今回棚卸,差異,差異率%,推定原因,補正種別,補正数量"

    discCount = 0
    For i = 2 To lastRow
        Print #fileNum, ws.Cells(i, 1).Value & "," & _
                       ws.Cells(i, 2).Value & "," & _
                       ws.Cells(i, 3).Value & "," & _
                       ws.Cells(i, 4).Value & "," & _
                       ws.Cells(i, 5).Value & "," & _
                       ws.Cells(i, 6).Value & "," & _
                       ws.Cells(i, 7).Value & "," & _
                       ws.Cells(i, 8).Value & "," & _
                       ws.Cells(i, 9).Value & "," & _
                       ws.Cells(i, 10).Value & "," & _
                       ws.Cells(i, 11).Value

        If ws.Cells(i, 7).Value <> 0 Then
            discCount = discCount + 1
        End If
    Next i

    Close #fileNum

    MsgBox "差異分析レポートを出力しました。" & vbCrLf & _
           "差異件数: " & discCount & "件" & vbCrLf & _
           filePath, vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 現在の棚卸データを前回棚卸にコピー（次回分析用）
'-------------------------------------------------------------------------------
Public Sub ArchiveCurrentInventory()
    Dim wsCurrent As Worksheet
    Dim wsPrev As Worksheet
    Dim lastRow As Long
    Dim response As VbMsgBoxResult

    Set wsCurrent = ThisWorkbook.Sheets(INVENTORY_SHEET)
    Set wsPrev = ThisWorkbook.Sheets(PREV_INVENTORY_SHEET)

    lastRow = wsCurrent.Cells(wsCurrent.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        MsgBox "現在の棚卸データがありません。", vbExclamation, "エラー"
        Exit Sub
    End If

    response = MsgBox("現在の棚卸データを「前回棚卸」にアーカイブしますか？" & vbCrLf & vbCrLf & _
                      "既存の前回棚卸データは上書きされます。", _
                      vbYesNo + vbQuestion, "アーカイブ確認")

    If response = vbNo Then Exit Sub

    ' 前回棚卸をクリア
    If wsPrev.Cells(wsPrev.Rows.Count, 1).End(xlUp).Row > 1 Then
        wsPrev.Range("A2:C" & wsPrev.Cells(wsPrev.Rows.Count, 1).End(xlUp).Row).ClearContents
    End If

    ' 現在の棚卸をコピー
    wsCurrent.Range("A2:C" & lastRow).Copy wsPrev.Range("A2")

    wsPrev.Columns("A:C").AutoFit

    MsgBox "現在の棚卸データを前回棚卸にアーカイブしました。" & vbCrLf & _
           "件数: " & (lastRow - 1) & "件", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 差異分析ワークフロー（一括実行）
'-------------------------------------------------------------------------------
Public Sub RunDiscrepancyAnalysisWorkflow()
    Dim response As VbMsgBoxResult

    response = MsgBox("差異分析ワークフローを実行します。" & vbCrLf & vbCrLf & _
                      "1. 差異分析を実行" & vbCrLf & _
                      "2. 補正データの確認" & vbCrLf & vbCrLf & _
                      "続行しますか？", vbYesNo + vbQuestion, "差異分析ワークフロー")

    If response = vbNo Then Exit Sub

    ' 差異分析を実行
    AnalyzeInventoryDiscrepancy

    ' 差異分析シートをアクティブに
    ThisWorkbook.Sheets(DISCREPANCY_SHEET).Activate

    MsgBox "差異分析が完了しました。" & vbCrLf & vbCrLf & _
           "「差異分析」シートを確認し、" & vbCrLf & _
           "必要に応じて「差異補正を適用」を実行してください。", vbInformation, "確認"
End Sub

'===============================================================================
' 使用量予測・発注点自動調整
'===============================================================================

'-------------------------------------------------------------------------------
' 使用量分析シートのセットアップ
'-------------------------------------------------------------------------------
Private Sub SetupUsageAnalysisSheet()
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(USAGE_ANALYSIS_SHEET)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
        ws.Name = USAGE_ANALYSIS_SHEET
    End If

    With ws
        .Cells(1, 1).Value = "品名"
        .Cells(1, 2).Value = "分析期間(日)"
        .Cells(1, 3).Value = "出庫回数"
        .Cells(1, 4).Value = "出庫合計"
        .Cells(1, 5).Value = "日平均使用量"
        .Cells(1, 6).Value = "週平均使用量"
        .Cells(1, 7).Value = "月平均使用量"
        .Cells(1, 8).Value = "使用頻度"
        .Cells(1, 9).Value = "リードタイム(日)"
        .Cells(1, 10).Value = "安全在庫係数"
        .Cells(1, 11).Value = "推奨発注点"
        .Cells(1, 12).Value = "現在発注点"
        .Cells(1, 13).Value = "調整要否"

        .Range("A1:M1").Font.Bold = True
        .Range("A1:M1").Interior.Color = RGB(112, 48, 160)
        .Range("A1:M1").Font.Color = RGB(255, 255, 255)
        .Columns("A:M").AutoFit
    End With
End Sub

'-------------------------------------------------------------------------------
' 使用量予測分析を実行
'-------------------------------------------------------------------------------
Public Sub AnalyzeUsagePatterns()
    Dim wsTrans As Worksheet
    Dim wsMaster As Worksheet
    Dim wsUsage As Worksheet
    Dim lastRowTrans As Long
    Dim lastRowMaster As Long
    Dim i As Long, j As Long
    Dim itemName As String
    Dim outboundCount As Long
    Dim outboundTotal As Double
    Dim minDate As Date
    Dim maxDate As Date
    Dim analysisDays As Long
    Dim dailyAvg As Double
    Dim weeklyAvg As Double
    Dim monthlyAvg As Double
    Dim rowNum As Long
    Dim frequency As String

    ' 使用量分析シートを作成/取得
    SetupUsageAnalysisSheet

    Set wsTrans = ThisWorkbook.Sheets(TRANSACTION_SHEET)
    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)
    Set wsUsage = ThisWorkbook.Sheets(USAGE_ANALYSIS_SHEET)

    ' 使用量分析シートをクリア
    If wsUsage.Cells(wsUsage.Rows.Count, 1).End(xlUp).Row > 1 Then
        wsUsage.Range("A2:M" & wsUsage.Cells(wsUsage.Rows.Count, 1).End(xlUp).Row).ClearContents
    End If

    lastRowTrans = wsTrans.Cells(wsTrans.Rows.Count, 5).End(xlUp).Row
    lastRowMaster = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    ' 分析期間を計算
    minDate = Date
    maxDate = DateSerial(1900, 1, 1)

    For i = 2 To lastRowTrans
        Dim transDate As Date
        On Error Resume Next
        transDate = CDate(wsTrans.Cells(i, 2).Value)
        On Error GoTo 0

        If transDate > DateSerial(1900, 1, 1) Then
            If transDate < minDate Then minDate = transDate
            If transDate > maxDate Then maxDate = transDate
        End If
    Next i

    analysisDays = maxDate - minDate + 1
    If analysisDays < 1 Then analysisDays = 1

    Application.ScreenUpdating = False

    rowNum = 2

    ' 各品目の使用量を分析
    For i = 2 To lastRowMaster
        itemName = wsMaster.Cells(i, 2).Value

        If itemName <> "" Then
            outboundCount = 0
            outboundTotal = 0

            ' 出庫履歴を集計
            For j = 2 To lastRowTrans
                If wsTrans.Cells(j, 5).Value = itemName And _
                   wsTrans.Cells(j, 3).Value = "出庫" Then
                    outboundCount = outboundCount + 1
                    outboundTotal = outboundTotal + wsTrans.Cells(j, 6).Value
                End If
            Next j

            ' 平均使用量を計算
            dailyAvg = outboundTotal / analysisDays
            weeklyAvg = dailyAvg * 7
            monthlyAvg = dailyAvg * 30

            ' 使用頻度を判定
            If outboundCount = 0 Then
                frequency = "未使用"
            ElseIf dailyAvg >= 1 Then
                frequency = "高頻度"
            ElseIf weeklyAvg >= 1 Then
                frequency = "中頻度"
            Else
                frequency = "低頻度"
            End If

            ' 結果を書き込み
            wsUsage.Cells(rowNum, 1).Value = itemName
            wsUsage.Cells(rowNum, 2).Value = analysisDays
            wsUsage.Cells(rowNum, 3).Value = outboundCount
            wsUsage.Cells(rowNum, 4).Value = outboundTotal
            wsUsage.Cells(rowNum, 5).Value = Round(dailyAvg, 2)
            wsUsage.Cells(rowNum, 6).Value = Round(weeklyAvg, 2)
            wsUsage.Cells(rowNum, 7).Value = Round(monthlyAvg, 2)
            wsUsage.Cells(rowNum, 8).Value = frequency

            ' デフォルトのリードタイムと安全在庫係数
            wsUsage.Cells(rowNum, 9).Value = 7 ' リードタイム7日
            wsUsage.Cells(rowNum, 10).Value = 1.5 ' 安全在庫係数1.5

            ' 現在の発注点を取得
            wsUsage.Cells(rowNum, 12).Value = wsMaster.Cells(i, 3).Value

            ' 頻度に応じた色付け
            Select Case frequency
                Case "高頻度"
                    wsUsage.Cells(rowNum, 8).Interior.Color = RGB(255, 199, 206)
                Case "中頻度"
                    wsUsage.Cells(rowNum, 8).Interior.Color = RGB(255, 235, 156)
                Case "低頻度"
                    wsUsage.Cells(rowNum, 8).Interior.Color = RGB(198, 239, 206)
                Case "未使用"
                    wsUsage.Cells(rowNum, 8).Interior.Color = RGB(221, 221, 221)
            End Select

            rowNum = rowNum + 1
        End If
    Next i

    wsUsage.Columns("A:M").AutoFit

    Application.ScreenUpdating = True

    MsgBox "使用量分析が完了しました。" & vbCrLf & _
           "分析期間: " & Format(minDate, "yyyy/mm/dd") & " ～ " & Format(maxDate, "yyyy/mm/dd") & vbCrLf & _
           "(" & analysisDays & "日間)" & vbCrLf & vbCrLf & _
           "「使用量分析」シートでリードタイムと安全在庫係数を" & vbCrLf & _
           "調整後、「発注点自動調整」を実行してください。", vbInformation, "完了"

    ' 使用量分析シートをアクティブに
    wsUsage.Activate
End Sub

'-------------------------------------------------------------------------------
' 発注点を自動調整
'-------------------------------------------------------------------------------
Public Sub AutoAdjustReorderPoints()
    Dim wsUsage As Worksheet
    Dim wsMaster As Worksheet
    Dim lastRowUsage As Long
    Dim lastRowMaster As Long
    Dim i As Long, j As Long
    Dim itemName As String
    Dim dailyAvg As Double
    Dim leadTime As Double
    Dim safetyFactor As Double
    Dim recommendedROP As Double
    Dim currentROP As Double
    Dim adjustCount As Long
    Dim response As VbMsgBoxResult

    On Error Resume Next
    Set wsUsage = ThisWorkbook.Sheets(USAGE_ANALYSIS_SHEET)
    On Error GoTo 0

    If wsUsage Is Nothing Then
        MsgBox "使用量分析データがありません。" & vbCrLf & _
               "先に「使用量予測分析」を実行してください。", vbExclamation, "エラー"
        Exit Sub
    End If

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)

    lastRowUsage = wsUsage.Cells(wsUsage.Rows.Count, 1).End(xlUp).Row
    lastRowMaster = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    If lastRowUsage < 2 Then
        MsgBox "使用量分析データがありません。", vbExclamation, "エラー"
        Exit Sub
    End If

    Application.ScreenUpdating = False

    adjustCount = 0

    ' 推奨発注点を計算
    For i = 2 To lastRowUsage
        itemName = wsUsage.Cells(i, 1).Value
        dailyAvg = Val(wsUsage.Cells(i, 5).Value)
        leadTime = Val(wsUsage.Cells(i, 9).Value)
        safetyFactor = Val(wsUsage.Cells(i, 10).Value)
        currentROP = Val(wsUsage.Cells(i, 12).Value)

        ' リードタイム期間の使用量 × 安全在庫係数
        If dailyAvg > 0 Then
            recommendedROP = Application.WorksheetFunction.Ceiling(dailyAvg * leadTime * safetyFactor, 1)
        Else
            recommendedROP = 0
        End If

        wsUsage.Cells(i, 11).Value = recommendedROP

        ' 調整要否を判定
        If recommendedROP = 0 Then
            wsUsage.Cells(i, 13).Value = "-"
            wsUsage.Cells(i, 13).Interior.ColorIndex = xlNone
        ElseIf Abs(recommendedROP - currentROP) > currentROP * 0.2 Then
            ' 20%以上の差がある場合は調整を推奨
            If recommendedROP > currentROP Then
                wsUsage.Cells(i, 13).Value = "↑要増加"
                wsUsage.Cells(i, 13).Interior.Color = RGB(255, 199, 206)
            Else
                wsUsage.Cells(i, 13).Value = "↓要減少"
                wsUsage.Cells(i, 13).Interior.Color = RGB(198, 239, 206)
            End If
            adjustCount = adjustCount + 1
        Else
            wsUsage.Cells(i, 13).Value = "適正"
            wsUsage.Cells(i, 13).Interior.Color = RGB(221, 235, 247)
        End If
    Next i

    wsUsage.Columns("A:M").AutoFit

    Application.ScreenUpdating = True

    If adjustCount = 0 Then
        MsgBox "発注点の計算が完了しました。" & vbCrLf & _
               "全ての品目が適正な発注点です。", vbInformation, "完了"
        Exit Sub
    End If

    ' 適用確認
    response = MsgBox("推奨発注点の計算が完了しました。" & vbCrLf & _
                      "調整推奨: " & adjustCount & "件" & vbCrLf & vbCrLf & _
                      "推奨発注点をマスター設定に反映しますか？", _
                      vbYesNo + vbQuestion, "発注点更新確認")

    If response = vbYes Then
        ApplyRecommendedReorderPoints
    Else
        MsgBox "「使用量分析」シートで推奨発注点を確認できます。" & vbCrLf & _
               "必要に応じて手動でマスター設定を更新してください。", vbInformation, "確認"
    End If
End Sub

'-------------------------------------------------------------------------------
' 推奨発注点をマスター設定に反映
'-------------------------------------------------------------------------------
Public Sub ApplyRecommendedReorderPoints()
    Dim wsUsage As Worksheet
    Dim wsMaster As Worksheet
    Dim lastRowUsage As Long
    Dim lastRowMaster As Long
    Dim i As Long, j As Long
    Dim itemName As String
    Dim recommendedROP As Double
    Dim updateCount As Long

    On Error Resume Next
    Set wsUsage = ThisWorkbook.Sheets(USAGE_ANALYSIS_SHEET)
    On Error GoTo 0

    If wsUsage Is Nothing Then
        MsgBox "使用量分析データがありません。", vbExclamation, "エラー"
        Exit Sub
    End If

    Set wsMaster = ThisWorkbook.Sheets(MASTER_SHEET)

    lastRowUsage = wsUsage.Cells(wsUsage.Rows.Count, 1).End(xlUp).Row
    lastRowMaster = wsMaster.Cells(wsMaster.Rows.Count, 2).End(xlUp).Row

    Application.ScreenUpdating = False

    updateCount = 0

    For i = 2 To lastRowUsage
        itemName = wsUsage.Cells(i, 1).Value
        recommendedROP = Val(wsUsage.Cells(i, 11).Value)

        ' 調整要の品目のみ更新
        If wsUsage.Cells(i, 13).Value Like "*要*" And recommendedROP > 0 Then
            ' マスター設定で該当品目を検索して更新
            For j = 2 To lastRowMaster
                If wsMaster.Cells(j, 2).Value = itemName Then
                    wsMaster.Cells(j, 3).Value = recommendedROP
                    updateCount = updateCount + 1
                    Exit For
                End If
            Next j
        End If
    Next i

    wsMaster.Columns("A:I").AutoFit

    Application.ScreenUpdating = True

    MsgBox updateCount & "件の発注点を更新しました。" & vbCrLf & vbCrLf & _
           "「全処理を実行」で発注判定を再実行してください。", vbInformation, "完了"
End Sub

'-------------------------------------------------------------------------------
' 使用量予測レポートをCSV出力
'-------------------------------------------------------------------------------
Public Sub ExportUsageAnalysisReport()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim filePath As String
    Dim fileNum As Integer

    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(USAGE_ANALYSIS_SHEET)
    On Error GoTo 0

    If ws Is Nothing Then
        MsgBox "使用量分析データがありません。", vbExclamation, "エラー"
        Exit Sub
    End If

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        MsgBox "使用量分析データがありません。", vbExclamation, "エラー"
        Exit Sub
    End If

    filePath = Application.GetSaveAsFilename( _
        InitialFileName:="使用量分析レポート_" & Format(Date, "yyyy-mm-dd") & ".csv", _
        FileFilter:="CSVファイル (*.csv), *.csv", _
        Title:="使用量分析レポートを保存")

    If filePath = "False" Then Exit Sub

    fileNum = FreeFile
    Open filePath For Output As #fileNum

    ' ヘッダー
    Print #fileNum, "品名,分析期間(日),出庫回数,出庫合計,日平均,週平均,月平均,頻度,リードタイム,安全係数,推奨発注点,現在発注点,調整要否"

    For i = 2 To lastRow
        Print #fileNum, ws.Cells(i, 1).Value & "," & _
                       ws.Cells(i, 2).Value & "," & _
                       ws.Cells(i, 3).Value & "," & _
                       ws.Cells(i, 4).Value & "," & _
                       ws.Cells(i, 5).Value & "," & _
                       ws.Cells(i, 6).Value & "," & _
                       ws.Cells(i, 7).Value & "," & _
                       ws.Cells(i, 8).Value & "," & _
                       ws.Cells(i, 9).Value & "," & _
                       ws.Cells(i, 10).Value & "," & _
                       ws.Cells(i, 11).Value & "," & _
                       ws.Cells(i, 12).Value & "," & _
                       ws.Cells(i, 13).Value
    Next i

    Close #fileNum

    MsgBox "使用量分析レポートを出力しました。" & vbCrLf & _
           filePath, vbInformation, "完了"
End Sub
