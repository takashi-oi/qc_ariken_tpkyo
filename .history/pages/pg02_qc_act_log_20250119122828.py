"""
検査測定状況管理記録登録ページ
"""

# ライブラリのインポート
import sqlite3  # SQLiteデータベースを操作するためのライブラリ
import queue  # キューを扱うためのライブラリ
import pandas as pd  # データ操作のためのライブラリ
import streamlit as st  # Webアプリケーションを作成するためのライブラリ

# ページの設定
st.set_page_config(
    page_title="検査測定状況管理記録登録",  # ページタイトルの設定
    layout="wide"  # ページレイアウトの設定
)

# データキュー
data_queue = queue.Queue()  # データを格納するためのキューを作成


# データ取得関数
def producer():
    """データ取得関数"""
    # データを取得してキューに追加
    data = pd.read_csv('data.csv')  # CSVファイルからデータを読み込む
    data_queue.put(data)  # 読み込んだデータをキューに追加


# データベースへの保存関数
def consumer():
    """データベースへの保存関数"""
    # メインスレッドでDBアクセス
    while True:
        data = data_queue.get()  # キューからデータを取得
        # save_to_db関数が定義されていないため、仮の処理を追加
        st.write("データをデータベースに保存します:", data)  # データをデータベースに保存する処理


# データベース接続をセッション状態として保持
st.session_state.conn = sqlite3.connect(
    'db_folder/qc_data_base.db',  # データベースファイルへの接続
    check_same_thread=sqlite3.threadsafety == 3  # スレッド安全性の確認
)


# テーブル存在確認関数
def check_table_exists(conn, table_name):
    """テーブル存在確認"""
    # カーソルの取得
    with conn.cursor() as cur:  # データベースのカーソルを取得
        cur.execute(f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{table_name}'
        """)  # テーブルの存在を確認するSQLクエリ
        # テーブル存在確認
        return cur.fetchone() is not None  # テーブルが存在するかどうかを返す


# 必要なテーブルの作成
def create_tables_if_not_exist():
    """テーブルの作成"""
    # カーソルの取得
    create_cursor = st.session_state.conn.cursor()  # データベースのカーソルを取得

    # QCルールテーブル
    create_cursor.execute("""
        CREATE TABLE IF NOT EXISTS qc_multi_rule (
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            type TEXT,
            PRIMARY KEY (Date_Time, Batch, Item_Code, type)  # 主キーの設定
        )
    """)

    # QC結果テーブル
    create_cursor.execute("""
        CREATE TABLE IF NOT EXISTS qc_multi_rule (
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            QC_RESULTS TEXT,
            PRIMARY KEY (Date_Time, Batch, Item_Code)  # 主キーの設定
        )
    """)

    # QCアクションログテーブル
    create_cursor.execute("""
        CREATE TABLE IF NOT EXISTS table_qc_act_log (
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            type TEXT,
            implementor TEXT,
            standard_usage TEXT,
            control_usage TEXT,
            reagents_usage TEXT,
            measuring_instrument_usage TEXT,
            cause TEXT,
            capa TEXT,
            QC_RESULTS TEXT,
            PRIMARY KEY (Date_Time, Batch, Item_Code, type)  # 主キーの設定
        )
    """)

    # コミット
    st.session_state.conn.commit()  # 変更をデータベースに保存


# テーブル作成の実行
create_tables_if_not_exist()  # 必要なテーブルを作成


# 検査項目のマスターデータの読み込みと初期化
ITEM_CODE_SELECT = None  # 検査項目の選択肢を初期化
ITEM_MAPPING = {}  # 検査項目のマッピングを初期化

try:
    # Excelファイルから検査項目を読み込む
    ITEM_CODE_SELECT = pd.read_excel('master_folder/measurement_item.xlsx')
    # 列名のリストを取得
    columns = ITEM_CODE_SELECT.columns.tolist()  # 列名のリストを取得

    # 想定される列名のペア
    column_pairs = [
        ('Item_Code', ['Item_Code', 'ItemCode', '項目コード']),  # 検査項目コードの列名の候補
        ('Measurement Item', [
            'Measurement Item', 'Measurement_Item', 'MeasurementItem',
            '測定項目', '項目名'  # 測定項目の列名の候補
        ])
    ]

    # 実際の列名をマッピング
    column_mapping = {}
    for target, possibilities in column_pairs:
        # 実際の列名を見つける
        found = next((col for col in possibilities if col in columns), None)
        if not found:
            st.error(
                f"必要な列 '{target}' が見つかりません。"
                f"利用可能な列: {', '.join(columns)}"  # エラーメッセージを表示
            )
            st.stop()  # 処理を停止
        column_mapping[target] = found  # 列名をマッピング

    # 列名を標準化
    ITEM_CODE_SELECT = ITEM_CODE_SELECT.rename(columns={
        column_mapping['Item_Code']: 'Item_Code',  # 列名を標準化
        column_mapping['Measurement Item']: 'Measurement Item'
    })

    # マッピング辞書を生成
    ITEM_MAPPING = dict(zip(
        ITEM_CODE_SELECT['Item_Code'],
        ITEM_CODE_SELECT['Measurement Item']  # 検査項目のマッピング辞書を作成
    ))
except FileNotFoundError:
    # ファイルが見つからない場合のエラーメッセージ
    st.error("measurement_item.xlsxファイルが見つかりません")
    st.stop()  # 処理を停止
except pd.errors.EmptyDataError:
    # ファイルが空の場合のエラーメッセージ
    st.error("measurement_item.xlsxファイルが空です")
    st.stop()  # 処理を停止
except pd.errors.ParserError:
    # 解析エラーの場合のエラーメッセージ
    st.error("measurement_item.xlsxファイルの解析に失敗しました")
    st.stop()  # 処理を停止
except PermissionError:
    # アクセス権限エラーの場合のエラーメッセージ
    st.error("measurement_item.xlsxファイルにアクセスする権限がありません")
    st.stop()  # 処理を停止

# ページのタイトル
st.markdown("## 検査測定状況管理記録登録 🎈")  # ページタイトルを表示
# サイドバーコンポーネント
with st.sidebar:
    # 検査実施状況登録
    st.markdown('### 検査実施状況登録')  # サイドバーの見出しを表示
    # 実施者名の入力
    try:
        # 実施者名のデータを読み込む
        employee_data = pd.read_excel("master_folder/employee_code.xlsx")
        measurer = st.selectbox(
            "測定者名",  # セレクトボックスのラベル
            employee_data["Member's_Name"].tolist()  # 実施者名のリストを表示
        )
    except FileNotFoundError:
        # ファイルが見つからない場合のエラーメッセージ
        st.error("master_folder/employee_code.xlsxファイルが見つかりません")
        st.stop()  # 処理を停止
    except pd.errors.EmptyDataError:
        # ファイルが空の場合のエラーメッセージ
        st.error("employee_code.xlsxファイルが空です")
        st.stop()  # 処理を停止
    except pd.errors.ParserError:
        # 解析エラーの場合のエラーメッセージ
        st.error("employee_code.xlsxファイルの解析に失敗しました")
        st.stop()  # 処理を停止
    except PermissionError:
        st.error("employee_code.xlsxファイルにアクセスする権限がありません")  # アクセス権限エラーの場合のエラーメッセージ
        st.stop()  # 処理を停止

    # 検査項目の選択（ITEM_MAPPINGは既に定義済み）
    try:
        item_code = st.selectbox(
            '検査項目を選択してください',  # セレクトボックスのラベル
            ITEM_CODE_SELECT['Item_Code'],  # 検査項目のリストを表示
            format_func=lambda x: ITEM_MAPPING.get(x, 'Unknown')  # 表示名をマッピング
        )
    except (AttributeError, KeyError):
        st.error("検査項目の読み込みに失敗しました")  # 読み込みエラーの場合のエラーメッセージ
        st.stop()  # 処理を停止

    # 初期化
    result_date_time_list = []  # 実施日リストを初期化
    BATCH = None  # バッチを初期化
    TYPE_VARIABLE = None  # 検査項目のタイプを初期化
    QC_RESULTS = None  # QC結果を初期化

    # 日付リストの取得
    cursor = st.session_state.conn.cursor()  # データベースのカーソルを取得
    cursor.execute("""
        SELECT DISTINCT `Date_Time`
        FROM table_qc_mulch_rule
        WHERE `Item_Code` = ?
        ORDER BY `Date_Time` DESC
        LIMIT 5
    """, (item_code,))  # 検査項目に基づく実施日を取得
    result_date_time_list = [date_time[0] for date_time in cursor.fetchall()]  # 実施日リストを作成

    # 日付リストが存在する場合のみ表示
    if result_date_time_list:
        DATE_TIME = st.selectbox('実施日を選択して下さい', result_date_time_list)  # 実施日を選択
    else:
        DATE_TIME = None  # 実施日がない場合はNoneに設定

    # 選択された日付に基づく時間リストの取得
    if DATE_TIME:
        cursor.execute("""
            SELECT DISTINCT `Batch`
            FROM table_qc_mulch_rule
            WHERE `Date_Time` = ?
            ORDER BY `Batch` DESC
        """, (DATE_TIME,))  # 選択された実施日に基づくバッチを取得
        result_time_list = [time[0] for time in cursor.fetchall()]  # バッチリストを作成
        if result_time_list:
            batch = st.selectbox('測定「Batch」を選択して下さい', result_time_list)  # バッチを選択

    # 選択されたバッチに基づく検査項目の取得
    if BATCH:
        cursor.execute("""
            SELECT DISTINCT `type`
            FROM table_qc_mulch_rule
            WHERE `Date_Time` = ? AND `Batch` = ?
        """, (DATE_TIME, BATCH))  # 選択された実施日とバッチに基づく検査項目のタイプを取得
        result_types_list = [
            type_variable[0] for type_variable in cursor.fetchall()]  # タイプリストを作成
        if result_types_list:
            type_variable = st.selectbox('検査項目のtypeを選択して下さい', result_types_list)  # タイプを選択

    # QC結果の取得を最適化
    if DATE_TIME and BATCH and TYPE_VARIABLE:
        cursor.execute("""
            SELECT DISTINCT `Violated_rule`
            FROM table_qc_mulch_rule
            WHERE `Date_Time` = ? AND `Batch` = ? AND
                  `Item_Code` = ? AND `type` = ?
        """, (DATE_TIME, BATCH, item_code, TYPE_VARIABLE))  # QC結果を取得
        # 検査項目のtypeの結果リストの取得
        result_results_list = [result[0] for result in cursor.fetchall()]  # 結果リストを作成

        # 結果が存在する場合のみ表示
        if result_results_list:
            # 検査項目のtypeの結果の選択
            if 'Violated_rule' not in st.session_state:
                # 検査項目のtypeの結果の初期化
                st.session_state.Violated_rule = None  # 初期化

            # 検査項目のtypeの結果の選択
            Violated_rule = st.selectbox('Multi Ruleの判定結果を選択してください', result_results_list)  # 判定結果を選択
            # 検査項目のtypeの結果のセッション状態の更新
            st.session_state.Violated_rule = Violated_rule  # セッション状態を更新


# ラジオボタンをカラムに分けて配置
col1, col2 = st.columns(2)  # 2つのカラムを作成
# 標準物質の使用状況
with col1:
    # 標準物質の使用状況
    st.markdown("### 標準物質の使用状況")  # 標準物質の見出しを表示
    # 標準物質の使用状況の選択
    standard_usage = st.radio('標準物質の使用状況を選択してください',
                              ('使用なし', '継続使用', '開封/Lot変更なし', '開封/Lot変更あり'))  # 標準物質の選択肢

    # 管理試料の使用状況
    st.markdown("### 管理試料の使用状況")  # 管理試料の見出しを表示
    # 管理試料の使用状況の選択
    control_usage = st.radio('管理試料の使用状況を選択してください',
                             ('継続使用', '開封/Lot変更なし', '開封/Lot変更あり'))  # 管理試料の選択肢

with col2:
    st.markdown("### 検査試薬の使用状況")  # 検査試薬の見出しを表示
    # 検査試薬の使用状況の選択
    reagents_usage = st.radio('検査試薬の使用状況を選択してください',
                              ('継続使用', '開封/Lot変更なし', '開封/Lot変更あり'))  # 検査試薬の選択肢

    # 測定機器の使用状況
    st.markdown("### 測定機器の使用状況")  # 測定機器の見出しを表示
    # 測定機器の使用状況の選択
    measuring_instrument_usage = st.radio('測定機器の使用状況を選択してください。\
                                          異常等がある場合は機器保守参照を選択してください。',
                                          ('異常なし', '異常あり/機器保守参照',
                                           'メンテナンス/機器保守参照'))  # 測定機器の選択肢

# 精度管理（Multi-Rule)判定結果及び対応
st.markdown('### 精度管理（Multi-Rule)判定結果及び対応')  # 精度管理の見出しを表示
# 異常判定になった原因または推測の入力
cause = st.text_input(
        '異常判定になった原因または推測を入力してください',
        placeholder='異常判定の起因となった原因をここに入力してください。'  # 入力フィールドのプレースホルダー
    )

# 是正処置・予防処置（CAPA）の入力
capa = st.text_input(
        '是正処置・予防処置（CAPA）を入力して下さい',
        placeholder='CAPAをここに入力してください。'  # 入力フィールドのプレースホルダー
    )


# データの登録
def main():
    """メイン関数"""

    # フォームデータのセッション状態を管理
    if "form_submitted" not in st.session_state:
        # フォームデータのセッション状態の初期化
        st.session_state.form_submitted = False  # フォームが送信されていない状態を初期化

    # create_form()とinsert_qc_data()の定義が見つからないため、仮の関数を定義します。
    def create_form():
        # 仮のフォームデータを返す関数
        return {"form_data": "仮のデータ"}  # 仮のデータを返す

    # フォームデータの確認
    form_data = create_form()  # フォームデータを作成

    # フォームデータの確認
    if st.button("データの確認", disabled=not form_data):  # データ確認ボタン
        # フォームデータが存在する場合のみ確認
        if form_data:
            df_check_list = pd.DataFrame({
                '実施者名': [st.session_state.get('implementor', '')],  # 実施者名
                '検査項目': [st.session_state.get('item_code', '')],  # 検査項目
                '実施日': [st.session_state.get('date_time', '')],  # 実施日
                '測定「Batch」': [st.session_state.get('batch', '')],  # バッチ
                '検査項目のtype': [st.session_state.get('type_variable', '')],  # 検査項目のタイプ
                'Multi Rule判定結果': [st.session_state.get('Violated_rule', '')],  # 判定結果
                '標準物質の使用状況': [standard_usage],  # 標準物質の使用状況
                '管理試料の使用状況': [control_usage],  # 管理試料の使用状況
                '検査試薬の使用状況': [reagents_usage],  # 検査試薬の使用状況
                '測定機器の使用状況': [measuring_instrument_usage],  # 測定機器の使用状況
                '異常判定になった原因または推測': [cause],  # 異常判定の原因
                '是正処置・予防処置（CAPA）': [capa],  # CAPA
            })
            st.write(df_check_list)  # 確認用データフレームを表示
            df_check_list = df_check_list.rename(columns={
                '実施者名': 'Measurer',  # 列名を英語に変更
                '検査項目': 'Item_Code',
                '実施日': 'Date_Time',
                '測定「Batch」': 'Batch',
                '検査項目のtype': 'type',
                'Multi Rule判定結果': 'Violated_rule',
                '標準物質の使用状況': 'standard_usage',
                '管理試料の使用状況': 'control_usage',
                '検査試薬の使用状況': 'reagents_usage',
                '測定機器の使用状況': 'measuring_instrument_usage',
                '異常判定になった原因または推測': 'cause',
                '是正処置・予防処置（CAPA）': 'capa',
            })

            # 重複チェック
            db_cursor = st.session_state.conn.cursor()  # データベースのカーソルを取得
            # 重複チェック
            db_cursor.execute("""
                SELECT COUNT(*) FROM table_qc_act_log
                WHERE Date_Time = ? AND Batch = ?
                AND Item_Code = ? AND type = ?
            """, (st.session_state.get('date_time', ''),
                  st.session_state.get('batch', ''),
                  st.session_state.get('item_code', ''),
                  st.session_state.get('type_variable', ''),
                  st.session_state.get('Violated_rule', '')))  # 重複チェックのSQLクエリ
            result = db_cursor.fetchone()  # 結果を取得

            # 重複チェック
            if result[0] > 0:
                st.error("このレコードは既に登録されています。")  # 重複エラーメッセージ
                return  # 処理を終了
            # データベースへの登録
            try:
                # データベースへの登録
                df_check_list.to_sql('table_qc_act_log',
                                     con=st.session_state.conn,
                                     if_exists='append',
                                     index=False)  # データをデータベースに追加
                # フォームデータの確認
                st.session_state.form_submitted = True  # フォームが送信された状態に更新
                # successメッセージ
                st.success("データベースに正常に登録されました。")  # 成功メッセージ
                st.success("登録が完了しました。新しいデータを入力してください。")  # 次の入力を促すメッセージ
                # バルーン表示
                st.balloons()  # バルーンを表示
                # successメッセージ
                st.success("table_qc_act_logへのインポートが完了しました。")  # インポート完了メッセージ
            except sqlite3.IntegrityError:
                # エラーメッセージ
                st.error("データが重複しています。既に登録されています。")  # 重複エラーメッセージ
            except sqlite3.Error as e:
                st.error(f"データベース登録中にエラーが発生しました: {e}")  # エラーメッセージ


# メイン関数の実行
if __name__ == "__main__":
    main()  # メイン関数を実行
