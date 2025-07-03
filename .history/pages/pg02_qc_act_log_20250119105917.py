"""
検査測定状況管理記録登録ページ
"""

# ライブラリのインポート
import sqlite3
import queue
import pandas as pd
import streamlit as st

# ページの設定
st.set_page_config(
    page_title="検査測定状況管理記録登録",
    layout="wide"
)

# データキュー
data_queue = queue.Queue()


# データ取得関数
def producer():
    """データ取得関数"""
    # データを取得してキューに追加
    data = pd.read_csv('data.csv')
    data_queue.put(data)


# データベースへの保存関数
def consumer():
    """データベースへの保存関数"""
    # メインスレッドでDBアクセス
    while True:
        data = data_queue.get()
        # save_to_db関数が定義されていないため、仮の処理を追加
        st.write("データをデータベースに保存します:", data)


# データベース接続をコンテキストマネージャーで管理
@st.cache_resource
def get_database_connection():
    """データベース接続を管理する関数"""
    return sqlite3.connect(
        'db_folder/qc_data_base.db',
        check_same_thread=sqlite3.threadsafety == 3
    )


# セッション状態の初期化
if 'conn' not in st.session_state:
    st.session_state.conn = get_database_connection()


# テーブル存在確認関数
def check_table_exists(conn, table_name):
    """テーブル存在確認"""
    # カーソルの取得
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{table_name}'
        """)
        # テーブル存在確認
        return cur.fetchone() is not None


# 必要なテーブルの作成
def create_tables_if_not_exist():
    """テーブルの作成"""
    # カーソルの取得
    create_cursor = st.session_state.conn.cursor()

    # QCルールテーブル
    create_cursor.execute("""
        CREATE TABLE IF NOT EXISTS qc_multi_rule (
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            type TEXT,
            PRIMARY KEY (Date_Time, Batch, Item_Code, type)
        )
    """)

    # QC結果テーブル
    create_cursor.execute("""
        CREATE TABLE IF NOT EXISTS qc_multi_rule (
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            QC_RESULTS TEXT,
            PRIMARY KEY (Date_Time, Batch, Item_Code)
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
            PRIMARY KEY (Date_Time, Batch, Item_Code, type)
        )
    """)

    # コミット
    st.session_state.conn.commit()


# テーブル作成の実行
create_tables_if_not_exist()

# 検査項目のマスターデータの読み込み
try:
    Measurement = pd.read_excel('master_folder/measurement_item.xlsx')
    Item_Code_select = Measurement
except ImportError:
    st.error("openpyxlがインストールされていません。pipまたはcondaを使用してopenpyxlをインストールしてください。")
    st.stop()

# ページのタイトル
st.markdown("## 検査測定状況管理記録登録 🎈")
# サイドバーコンポーネント
with st.sidebar:
    # 検査実施状況登録
    st.markdown('### 検査実施状況登録')
    # 実施者名の入力
    # Excelファイルから実施者名を読み込む
    try:
        employee_data = pd.read_excel(
            "master_folder/employee_code.xlsx"
        )
        measurer = st.selectbox(
            "測定者名",
            employee_data["Member's_Name"].tolist()
        )
        st.stop()

    # Item_CodeとMeasurement Itemのマッピング辞書を生成
    item_mapping = dict(zip(Item_Code_select['Item_Code'],
                            Item_Code_select['Measurement Item']))

    # 検査項目の選択
    Item_Code = st.selectbox('検査項目を選択してください',
                             Item_Code_select['Item_Code'],
                             format_func=lambda x: item_mapping[x])

    # 初期化
    result_Date_Time_list = []
    BATCH = None
    TYPE_VARIABLE = None
    QC_RESULTS = None

    # 日付リストの取得
    cursor = st.session_state.conn.cursor()
    cursor.execute("""
        SELECT DISTINCT `Date_Time`
        FROM table_qc_mulch_rule
        WHERE `Item_Code` = ?
        ORDER BY `Date_Time` DESC
        LIMIT 5
    """, (Item_Code,))
    result_Date_Time_list = [Date_Time[0] for Date_Time in cursor.fetchall()]

    # 日付リストが存在する場合のみ表示
    if result_Date_Time_list:
        DATE_TIME = st.selectbox('実施日を選択して下さい', result_Date_Time_list)
    else:
        DATE_TIME = None

    # 選択された日付に基づく時間リストの取得
    if DATE_TIME:
        cursor.execute("""
            SELECT DISTINCT `Batch`
            FROM table_qc_mulch_rule
            WHERE `Date_Time` = ?
            ORDER BY `Batch` DESC
        """, (DATE_TIME,))
        result_time_list = [time[0] for time in cursor.fetchall()]
        if result_time_list:
            BATCH = st.selectbox('測定「Batch」を選択して下さい', result_time_list)

    # 選択されたバッチに基づく検査項目の取得
    if BATCH:
        cursor.execute("""
            SELECT DISTINCT `type`
            FROM table_qc_mulch_rule
            WHERE `Date_Time` = ? AND `Batch` = ?
        """, (DATE_TIME, BATCH))
        result_types_list = [
            TYPE_VARIABLE[0] for TYPE_VARIABLE in cursor.fetchall()]
        if result_types_list:
            TYPE_VARIABLE = st.selectbox('検査項目のtypeを選択して下さい',
                                         result_types_list)

    # QC結果の取得を最適化
    if DATE_TIME and BATCH and TYPE_VARIABLE:
        cursor.execute("""
            SELECT DISTINCT `Violated_rule`
            FROM table_qc_mulch_rule
            WHERE `Date_Time` = ? AND `Batch` = ? AND
                  `Item_Code` = ? AND `type` = ?
        """, (DATE_TIME, BATCH, Item_Code, TYPE_VARIABLE))
        # 検査項目のtypeの結果リストの取得
        result_results_list = [result[0] for result in cursor.fetchall()]

        # 結果が存在する場合のみ表示
        if result_results_list:
            # 検査項目のtypeの結果の選択
            if 'Violated_rule' not in st.session_state:
                # 検査項目のtypeの結果の初期化
                st.session_state.Violated_rule = None

            # 検査項目のtypeの結果の選択
            Violated_rule = st.selectbox('Multi Ruleの判定結果を選択してください',
                                         result_results_list)
            # 検査項目のtypeの結果のセッション状態の更新
            st.session_state.Violated_rule = Violated_rule


# ラジオボタンをカラムに分けて配置
col1, col2 = st.columns(2)
# 標準物質の使用状況
with col1:
    # 標準物質の使用状況
    st.markdown("### 標準物質の使用状況")
    # 標準物質の使用状況の選択
    standard_usage = st.radio('標準物質の使用状況を選択してください',
                              ('使用なし', '開封/Lot変更あり', '開封/Lot変更なし'))

    # 管理試料の使用状況
    st.markdown("### 管理試料の使用状況")
    # 管理試料の使用状況の選択
    control_usage = st.radio('管理試料の使用状況を選択してください',
                             ('継続使用', '開封/Lot変更あり', '開封/Lot変更なし'))

with col2:
    st.markdown("### 検査試薬の使用状況")
    # 検査試薬の使用状況の選択
    reagents_usage = st.radio('検査試薬の使用状況を選択してください',
                              ('継続使用', '開封/Lot変更あり', '開封/Lot変更なし'))

    # 測定機器の使用状況
    st.markdown("### 測定機器の使用状況")
    # 測定機器の使用状況の選択
    measuring_instrument_usage = st.radio('測定機器の使用状況を選択してください。\
                                          異常等がある場合は機器保守参照を選択してください。',
                                          ('異常なし', '異常あり/機器保守参照',
                                           'メンテナンス/部品交換後'))

# 精度管理（Multi-Rule)判定結果及び対応
st.markdown('### 精度管理（Multi-Rule)判定結果及び対応')
# 異常判定になった原因または推測の入力
cause = st.text_input(
        '異常判定になった原因または推測を入力してください',
        placeholder='異常判定の起因となった原因をここに入力してください。'
    )

# 是正処置・予防処置（CAPA）の入力
capa = st.text_input(
        '是正処置・予防処置（CAPA）を入力して下さい',
        placeholder='CAPAをここに入力してください。'
    )


# データの登録
def main():
    """メイン関数"""
    try:
        if not all([DATE_TIME, BATCH, Item_Code, TYPE_VARIABLE, implementor]):
            st.warning("すべての必須フィールドを入力してください。")
            return

        if st.button("データの確認"):
            df_check_list = pd.DataFrame({
                'Measurer': [implementor],
                'Item_Code': [Item_Code],
                'Date_Time': [DATE_TIME],
                'Batch': [BATCH],
                'type': [TYPE_VARIABLE],
                'Violated_rule': [st.session_state.get('Violated_rule')],
                'standard_usage': [standard_usage],
                'control_usage': [control_usage],
                'reagents_usage': [reagents_usage],
                'measuring_instrument_usage': [measuring_instrument_usage],
                'cause': [cause],
                'capa': [capa],
            })

            st.write(df_check_list)

            # トランザクション処理の追加
            with st.session_state.conn:
                cursor = st.session_state.conn.cursor()

                # 重複チェック
                cursor.execute("""
                    SELECT COUNT(*) FROM table_qc_act_log
                    WHERE Date_Time = ? AND Batch = ?
                    AND Item_Code = ? AND type = ?
                """, (DATE_TIME, BATCH, Item_Code, TYPE_VARIABLE))

                if cursor.fetchone()[0] > 0:
                    st.error("このレコードは既に登録されています。")
                    return

                # データの登録
                df_check_list.to_sql(
                    'table_qc_act_log',
                    con=st.session_state.conn,
                    if_exists='append',
                    index=False
                )

                st.success("データベースに正常に登録されました。")
                st.balloons()

    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        st.session_state.conn.rollback()


# メイン関数の実行
if __name__ == "__main__":
    main()
