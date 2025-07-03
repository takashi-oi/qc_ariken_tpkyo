"""
検査測定状況管理記録登録ページ
"""

# ライブラリのインポート
import sqlite3  # SQLiteデータベースを操作するためのライブラリ
import queue  # キューを扱うためのライブラリ
import pandas as pd  # データ操作のためのライブラリ
import streamlit as st  # Webアプリケーションを作成するためのライブラリ

# データキュー
data_queue = queue.Queue()  # データを格納するためのキューを作成


# データベース接続をセッション状態として保持
def init_db_connection():
    """データベース接続を初期化する関数"""
    st.session_state.conn = sqlite3.connect(
        'db_folder/qc_data_base.db',  # データベースファイルへの接続
        check_same_thread=sqlite3.threadsafety == 3  # スレッド安全性の確認
    )


# テーブル作成の実行
def create_tables_if_not_exist():
    """必要なテーブルを作成する関数"""
    create_cursor = st.session_state.conn.cursor()
    tables = {
        "qc_mulch_rule": """
            CREATE TABLE IF NOT EXISTS qc_mulch_rule (
                Date_Time TEXT,
                Batch TEXT,
                Item_Code TEXT,
                type TEXT,
                Violated_rule TEXT,
                PRIMARY KEY (Date_Time, Batch, Item_Code, type)
            )
        """,
        "qc_multi_rule": """
            CREATE TABLE IF NOT EXISTS qc_multi_rule (
                Date_Time TEXT,
                Batch TEXT,
                Item_Code TEXT,
                QC_RESULTS TEXT,
                PRIMARY KEY (Date_Time, Batch, Item_Code)
            )
        """,
        "table_qc_act_log": """
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
                Violated_rule TEXT,
                PRIMARY KEY (Date_Time, Batch, Item_Code, type)
            )
        """
    }
    for table_name, create_query in tables.items():
        create_cursor.execute(create_query)
    st.session_state.conn.commit()


# 検査項目のマスターデータの読み込みと初期化
def load_item_codes():
    """検査項目のマスターデータを読み込む関数"""
    try:
        item_code_select = pd.read_excel('master_folder/measurement_item.xlsx')
        columns = item_code_select.columns.tolist()
        column_pairs = [
            ('Item_Code', ['Item_Code', 'ItemCode', '項目コード']),
            ('Measurement Item',
             ['Measurement Item',
              'Measurement_Item',
              'MeasurementItem',
              '測定項目',
              '項目名'])
        ]
        column_mapping = {
            target: next((col for col in possibilities if col in columns),
                         None) for target, possibilities in column_pairs}

        for target in column_mapping:
            if column_mapping[target] is None:
                st.error(
                    f"必要な列 '{target}' が見つかりません。利用可能な列: {', '.join(columns)}")
                st.stop()

        item_code_select = item_code_select.rename(columns={
            column_mapping['Item_Code']: 'Item_Code',
            column_mapping['Measurement Item']: 'Measurement Item'
        })
        return item_code_select
    except FileNotFoundError:
        st.error("measurement_item.xlsxファイルが見つかりません")
        st.stop()
    except pd.errors.EmptyDataError:
        st.error("measurement_item.xlsxファイルが空です")
        st.stop()
    except pd.errors.ParserError:
        st.error("measurement_item.xlsxファイルの解析に失敗しました")
        st.stop()
    except PermissionError:
        st.error("measurement_item.xlsxファイルにアクセスする権限がありません")
        st.stop()


# ページのタイトル
st.markdown("## 検査測定状況管理記録登録 🎈")  # ページタイトルを表示

# サイドバーコンポーネント
with st.sidebar:
    st.markdown('### 検査実施状況登録')
    init_db_connection()
    create_tables_if_not_exist()
    ITEM_CODE_SELECT = load_item_codes()

    # 実施者名の入力と保存
    try:
        employee_data = pd.read_excel("master_folder/employee_code.xlsx")
        measurer = st.selectbox(
            "測定者名", employee_data["Member's_Name"].tolist())
        st.session_state['implementor'] = measurer
    except FileNotFoundError:
        st.error("master_folder/employee_code.xlsxファイルが見つかりません")
        st.stop()
    except pd.errors.EmptyDataError:
        st.error("employee_code.xlsxファイルが空です")
        st.stop()
    except pd.errors.ParserError:
        st.error("employee_code.xlsxファイルの解析に失敗しました")
        st.stop()
    except PermissionError:
        st.error("employee_code.xlsxファイルにアクセスする権限がありません")
        st.stop()

    # 検査項目の選択と保存
    item_code = st.selectbox(
        '検査項目を選択してください',
        ITEM_CODE_SELECT['Item_Code'],
        format_func=lambda x: ITEM_MAPPING.get(x, 'Unknown'))
    st.session_state['item_code'] = item_code

# データの登録
def main():
    """メイン関数"""
    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False

    if st.button("データの確認"):
        df_check_list = pd.DataFrame({
            '実施者名': [st.session_state.get('implementor', '')],
            '検査項目': [st.session_state.get('item_code', '')],
            '実施日': [st.session_state.get('date_time', '')],
            '測定「Batch」': [st.session_state.get('batch', '')],
            '標準物質の使用状況': [standard_usage],
            '管理試料の使用状況': [control_usage],
            '検査試薬の使用状況': [reagents_usage],
            '測定機器の使用状況': [measuring_instrument_usage],
        })
        st.write(df_check_list.rename(columns={
            '実施者名': 'Measurer',
            '検査項目': 'Item_Code',
            '実施日': 'Date_Time',
            '測定「Batch」': 'Batch',
            '標準物質の使用状況': 'standard_usage',
            '管理試料の使用状況': 'control_usage',
            '検査試薬の使用状況': 'reagents_usage',
            '測定機器の使用状況': 'measuring_instrument_usage',
        }))

        # 重複チェックとデータベースへの登録
        db_cursor = st.session_state.conn.cursor()
        db_cursor.execute("""
            SELECT COUNT(*) FROM table_qc_act_log
            WHERE Date_Time = ? AND Batch = ? AND Item_Code = ? AND type = ?
        """, (st.session_state.get('date_time', ''),
              st.session_state.get('batch', ''),
              st.session_state.get('item_code', ''),
              st.session_state.get('type_variable', '')))
        if db_cursor.fetchone()[0] > 0:
            st.error("このレコードは既に登録されています。")
            return

        try:
            df_check_list.to_sql('table_qc_act_log', con=st.session_state.conn, if_exists='append', index=False)
            st.session_state.form_submitted = True
            st.success("データベースに正常に登録されました。")
            st.balloons()
        except sqlite3.IntegrityError:
            st.error("データが重複しています。既に登録されています。")
        except sqlite3.Error as e:
            st.error(f"データベース登録中にエラーが発生しました: {e}")

# メイン関数の実行
if __name__ == "__main__":
    main()  # メイン関数を実行
