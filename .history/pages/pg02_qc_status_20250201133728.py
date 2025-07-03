"""検査測定状況管理記録登録ページ"""
import sqlite3
import pandas as pd
import streamlit as st
from src.config import Config
from src.database.connection import DatabaseManager

# ページ設定
st.set_page_config(page_title="検査測定状況管理記録", layout="wide")


# データベース接続の初期化
@st.cache_resource(ttl=3600)
def init_connection():
    """データベース接続を初期化し、キャッシュする"""
    return sqlite3.connect(Config.DATABASE_PATH)


@st.cache_resource(ttl=3600)
def get_database_manager():
    """DatabaseManagerインスタンスを初期化し、キャッシュする"""
    return DatabaseManager(Config.DATABASE_PATH)


# セッション状態の初期化
def init_session_state():
    """セッション状態を初期化する"""
    if 'conn' not in st.session_state:
        st.session_state.conn = init_connection()
        st.session_state.db_manager = get_database_manager()
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    if 'implementor' not in st.session_state:
        st.session_state.implementor = None
    if 'File_Name' not in st.session_state:
        st.session_state.File_Name = None
    if 'date_time' not in st.session_state:
        st.session_state.date_time = None
    if 'batch' not in st.session_state:
        st.session_state.batch = None
    if 'Item_Code' not in st.session_state:
        st.session_state.Item_Code = None


# セッション状態の初期化
init_session_state()  # セッション状態を初期化

# connが初期化されていない場合は初期化する
if 'conn' not in st.session_state:
    st.session_state.conn = init_connection()
    st.session_state.db_manager = get_database_manager()

# connが初期化された後にファイル情報を取得
QUERY = """
    SELECT File_Name, Date_Time, Batch, Item_Code
    FROM table_qc_file_info
    ORDER BY Date_Time DESC
    LIMIT 5
"""
file_info_df = pd.read_sql(QUERY, st.session_state.conn)  # ここでconnを使用


# 終了時のクリーンアップを登録（ページの最後に移動）
def cleanup():
    """クリーンアップ処理を実行する関数。
    キャッシュデータをクリアし、セッション状態をリセットします。
    """
    st.cache_data.clear()  # 以前のキャッシュクリアメソッドを更新
    st.session_state.clear()  # セッション状態のクリア


# タイトルを表示
st.markdown("### 測定状況登録")


# ラジオボタンをカラムに分けて配置
col1, col2 = st.columns(2)

# 標準物質の使用状況
with col1:
    st.markdown("#### 標準物質の使用状況")
    standard_usage = st.radio(
        '標準物質の使用状況を選択してください',
        ('使用なし', '継続使用', '開封 / Lot変更なし', '開封 / Lot変更あり')
    )

    st.markdown("#### 管理試料の使用状況")
    control_usage = st.radio(
        '管理試料の使用状況を選択してください',
        ('開封済み / 継続使用', '開封 / Lot変更なし', '開封 / Lot変更あり')
    )

with col2:
    st.markdown("#### 検査試薬の使用状況")
    reagents_usage = st.radio(
        '検査試薬の使用状況を選択してください',
        ('開封済み/ 継続使用', '開封 / Lot変更なし', '開封 / Lot変更あり')
    )

    st.markdown("#### 測定機器の使用状況")
    measuring_instrument_usage = st.radio(
        '測定機器の使用状況を選択してください。'
        '異常等がある場合は機器保守参照を選択してください。',
        ('異常なし', '異常あり / 機器保守参照', '')
    )


# サイドバーコンポーネント
with st.sidebar:
    st.markdown('### 検査実施状況登録')

    # 実施者名の入力と保存
    try:
        employee_data = pd.read_excel("master_folder/employee_code.xlsx")
        selected_measurer = st.selectbox(
            "測定者名", employee_data["Member's_Name"].tolist())
        st.session_state['implementor'] = selected_measurer
    except FileNotFoundError:
        st.error(
            "master_folder/employee_code.xlsxファイルが"
            "見つかりません"
        )
        st.stop()
    except (pd.errors.EmptyDataError,
            pd.errors.ParserError,
            PermissionError) as e:
        st.error(f"ファイルエラー: {str(e)}")
        st.stop()

    # ファイル名の選択
    selected_file = st.selectbox(
        '測定ファイル名を選択して下さい',
        file_info_df['File_Name'].tolist(),
        format_func=lambda x: (
            x if x in file_info_df['File_Name'].tolist() else 'Unknown'
        )
    )

    # 選択されたファイルの情報をセッションに保存
    if selected_file:
        selected_row = file_info_df[
            file_info_df['File_Name'] == selected_file].iloc[0]
        st.session_state['File_Name'] = selected_file
        st.session_state['date_time'] = selected_row['Date_Time']
        st.session_state['batch'] = selected_row['Batch']
        st.session_state['Item_Code'] = selected_row['Item_Code']

if st.button("データの確認 / 登録"):
    df_check_list = pd.DataFrame({
        'Measurer': [st.session_state.get('implementor', '')],
        'File_Name': [st.session_state.get('File_Name', '')],
        'Date_Time': [st.session_state.get('date_time', '')],
        'Batch': [st.session_state.get('batch', '')],
        'Item_Code': [st.session_state.get('Item_Code', '')],
        'standard_usage': [standard_usage],
        'control_usage': [control_usage],
        'reagents_usage': [reagents_usage],
        'measuring_instrument_usage': [measuring_instrument_usage],
    })

    # データ確認表示
    st.write(df_check_list)

    # 重複チェックとデータベースへの登録
    try:
        # 重複チェック
        db_cursor = st.session_state.conn.cursor()
        db_cursor.execute("""
            SELECT COUNT(*) FROM table_qc_status_log
            WHERE Date_Time = ? AND Batch = ? AND File_Name = ? AND \
                          Item_Code = ?
        """, (
            st.session_state.get('date_time', ''),
            st.session_state.get('batch', ''),
            st.session_state.get('File_Name', ''),
            st.session_state.get('Item_Code', '')
        ))

        if db_cursor.fetchone()[0] > 0:
            st.error("このレコードは既に登録されています。")
            st.stop()

        # データ登録
        df_check_list.to_sql(
            'table_qc_status_log',
            con=st.session_state.conn,
            if_exists='append',
            index=False
        )
        st.session_state.form_submitted = True
        st.success("データベースに正常に登録されました。")
        st.balloons()

    except sqlite3.IntegrityError:
        st.error("データが重複しています。既に登録されています。")
    except sqlite3.Error as e:
        st.error(f"データベース登録中にエラーが発生しました: {e}")
