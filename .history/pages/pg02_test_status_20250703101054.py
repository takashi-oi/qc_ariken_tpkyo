"""検査測定状況管理記録登録ページ"""

# SQLite3をインポート
import sqlite3

# Pandasをインポート
import pandas as pd

# Streamlitをインポート
import streamlit as st

# Configクラスをインポート
from src.config import Config

# DatabaseManagerクラスをインポート
from src.database.connection import DatabaseManager

# ページ設定
st.set_page_config(page_title="測定状況登録", layout="wide")


# データベース接続の初期化
# データベース接続をキャッシュ（1時間）
@st.cache_resource(ttl=3600)
# データベース接続を取得する関数
def get_connection():
    """データベース接続を取得する（スレッドセーフ）"""
    # データベースに接続
    conn = sqlite3.connect(Config.DATABASE_PATH, check_same_thread=False)
    # 接続を返す
    return conn


# DatabaseManagerインスタンスをキャッシュ（1時間）
@st.cache_resource(ttl=3600)
# DatabaseManagerインスタンスを取得する関数
def get_database_manager():
    """DatabaseManagerインスタンスを初期化し、キャッシュする"""
    # DatabaseManagerインスタンスを返す
    return DatabaseManager(Config.DATABASE_PATH)


# セッション状態の初期化
# セッション状態を初期化する関数
def init_session_state():
    """セッション状態を初期化する"""
    # セッション状態に'db_manager'がない場合
    if "db_manager" not in st.session_state:
        st.session_state.form_submitted = False
    # セッション状態に'implementor'がない場合
    if "implementor" not in st.session_state:
        # 'implementor'をNoneに設定
        st.session_state.implementor = None
    # セッション状態に'File_Name'がない場合
    if "File_Name" not in st.session_state:
        # 'File_Name'をNoneに設定
        st.session_state.File_Name = None
    # セッション状態に'date_time'がない場合
    if "date_time" not in st.session_state:
        # 'date_time'をNoneに設定
        st.session_state.date_time = None
    # セッション状態に'batch'がない場合
    if "batch" not in st.session_state:
        # 'batch'をNoneに設定
        st.session_state.batch = None
    if "Item_Code" not in st.session_state:  # セッション状態に'Item_Code'がない場合
        st.session_state.Item_Code = None  # 'Item_Code'をNoneに設定


# セッション状態の初期化
init_session_state()  # セッション状態の初期化


# データベースの接続後、テーブルが存在するか確認し、なければ作成する
def ensure_table_exists():  # テーブルが存在することを確認し、なければ作成する関数
    """データベースに必要なテーブルが存在することを確認し、なければ作成する"""
    table_conn = get_connection()  # データベースに接続
    create_table_query = """  -- テーブル作成クエリ
    -- table_qc_file_infoテーブルが存在しない場合、作成
    CREATE TABLE IF NOT EXISTS table_qc_file_info (
        File_Name TEXT,  -- File_Nameカラム
        Date_Time DATETIME,  -- Date_Timeカラム
        Batch TEXT,  -- Batchカラム
        Item_Code TEXT  -- Item_Codeカラム
    )
    """
    table_conn.execute(create_table_query)  # テーブル作成クエリを実行
    table_conn.commit()  # 変更をコミット


# テーブルの存在を確認してから読み込む
ensure_table_exists()  # テーブルの存在を確認してから読み込む

# データの読み込み
try:  # データの読み込みを試みる
    read_conn = get_connection()  # データベースに接続
    QUERY = """  -- データ取得クエリ
        -- File_Name, Date_Time, Batch, Item_Codeを取得
        SELECT File_Name, Date_Time, Batch, Item_Code
        -- table_qc_file_infoテーブルから
        FROM table_qc_file_info
        -- Date_Timeで降順に並べ替え
        ORDER BY Date_Time DESC
        -- 上位5件のみ取得
        LIMIT 5
    """
    # データベースからデータを取得
    file_info_df = pd.read_sql(QUERY, read_conn)
# データの読み込みに失敗した場合
except (pd.errors.EmptyDataError, sqlite3.Error):
    # エラーメッセージを表示
    st.error("テーブルの読み込みに失敗しました。テーブルが空の可能性があります。")
    # 空のデータフレームを作成
    file_info_df = pd.DataFrame(
        columns=["File_Name", "Date_Time", "Batch", "Item_Code"]
    )


# 終了時のクリーンアップを登録（ページの最後に移動）
# クリーンアップ処理を実行する関数
def cleanup():
    """クリーンアップ処理を実行する関数。
    キャッシュデータをクリアし、セッション状態をリセットします。
    """
    # 以前のキャッシュクリアメソッドを更新
    st.cache_data.clear()
    # セッション状態のクリア
    st.session_state.clear()


# タイトルを表示
st.markdown("### 測定状況登録")


# ラジオボタンをカラムに分けて配置
col1, col2 = st.columns(2)

# 標準物質の使用状況
# col1にウィジェットを配置
with col1:
    # セクションのタイトル
    st.markdown("#### 標準物質の使用状況")
    # ラジオボタン
    standard_usage = st.radio(
        # ラベル
        "標準物質の使用状況を選択してください",
        # 選択肢
        (
            "該当なし / 使用なし",
            "開封済み / 継続使用",
            "開封 / Lot変更なし",
            "開封 / Lot変更あり",
        ),
    )

    # セクションのタイトル
    st.markdown("#### 管理試料の使用状況")
    # ラジオボタン
    control_usage = st.radio(
        # ラベル
        "管理試料の使用状況を選択してください",
        # 選択肢
        ("開封済み / 継続使用", "開封 / Lot変更なし", "開封 / Lot変更あり"),
    )

# col2にウィジェットを配置
with col2:
    # セクションのタイトル
    st.markdown("#### 検査試薬の使用状況")
    # ラジオボタン
    reagents_usage = st.radio(
        # ラベル
        "検査試薬の使用状況を選択してください",
        # 選択肢
        ("開封済み/ 継続使用", "開封 / Lot変更なし", "開封 / Lot変更あり"),
    )

    # セクションのタイトル
    st.markdown("#### 測定機器の使用状況")
    # ラジオボタン
    measuring_instrument_usage = st.radio(
        # ラベル
        "測定機器の使用状況を選択してください。"
        # 説明
        "異常等がある場合は機器保守参照を選択してください。",
        # 選択肢
        ("異常なし", "異常あり / 機器保守参照"),
    )


# サイドバーコンポーネント
with st.sidebar:  # サイドバーにウィジェットを配置
    st.markdown("### 検査実施状況登録")  # セクションのタイトル

    # 実施者名の入力と保存
    try:  # 実施者名の入力と保存を試みる
        # 検査要員データをExcelファイルから読み込む
        employee_data = pd.read_excel("data/master/employee_code.xlsx")
        selected_measurer = st.selectbox(  # ドロップダウンリスト
            "測定者名", employee_data["Member's_Name"].tolist()
        )  # ラベルと選択肢
        # 選択された測定者をセッション状態に保存
        st.session_state["implementor"] = selected_measurer
    except FileNotFoundError:  # ファイルが見つからない場合
        st.error(  # エラーメッセージ
             "data/master/employee_code.xlsxファイルが" "見つかりません"
        )
        st.stop()  # プログラムを停止
    except (
        pd.errors.EmptyDataError,  # データの読み込みに失敗した場合
        pd.errors.ParserError,
        PermissionError,
    ) as e:
        st.error(f"ファイルエラー: {str(e)}")  # エラーメッセージ
        st.stop()  # プログラムを停止

    # ファイル名の選択
    selected_file = st.selectbox(  # ドロップダウンリスト
        "測定ファイル名を選択して下さい",  # ラベル
        file_info_df["File_Name"].tolist(),  # 選択肢
        format_func=lambda x: (  # 選択肢の表示フォーマット
            # 選択肢がリストに含まれている場合はそのまま、そうでない場合は'Unknown'
            x
            if x in file_info_df["File_Name"].tolist()
            else "Unknown"
        ),
    )

    # 選択されたファイルの情報をセッションに保存
    if selected_file:  # ファイルが選択された場合
        selected_row = file_info_df[  # 選択されたファイルの情報を取得
            file_info_df["File_Name"] == selected_file
        ].iloc[0]
        # 選択されたファイル名をセッション状態に保存
        st.session_state["File_Name"] = selected_file
        # 選択されたファイルの日時をセッション状態に保存
        st.session_state["date_time"] = selected_row["Date_Time"]
        # 選択されたファイルのバッチをセッション状態に保存
        st.session_state["batch"] = selected_row["Batch"]
        # 選択されたファイルの項目コードをセッション状態に保存
        st.session_state["Item_Code"] = selected_row["Item_Code"]

if st.button("データの確認 / 登録"):  # データの確認 / 登録ボタンが押された場合
    df_check_list = pd.DataFrame(
        {  # データ確認リストを作成
            "File_Name": [st.session_state.get("File_Name", "")],  # ファイル名
            "Measurer": [st.session_state.get("implementor", "")],  # 測定者
            "Date_Time": [st.session_state.get("date_time", "")],  # 日時
            "Item_Code": [st.session_state.get("Item_Code", "")],  # 項目コード
            "Batch": [st.session_state.get("batch", "")],  # バッチ
            "standard_usage": [standard_usage],  # 標準物質の使用状況
            "control_usage": [control_usage],  # 管理試料の使用状況
            "reagents_usage": [reagents_usage],  # 検査試薬の使用状況
            # 測定機器の使用状況
            "measuring_instrument_usage": [measuring_instrument_usage],
        }
    )

    # データ確認表示
    st.write(df_check_list)  # データ確認リストを表示

    # 重複チェックとデータベースへの登録
    # 重複チェックとデータベースへの登録を試みる
    try:
        # 重複チェック
        # データベースに接続
        write_conn = get_connection()
        # カーソルを作成
        db_cursor = write_conn.cursor()
        # 重複チェッククエリ
        db_cursor.execute(
            """
            -- table_qc_status_logテーブルから
            SELECT COUNT(*) FROM table_qc_status_log
            -- 日時、バッチ、ファイル名、項目コードが一致するレコードがあるか
            WHERE Date_Time = ? AND Batch = ? AND File_Name = ? AND \
                          Item_Code = ?
        """,
            (
                # 日時
                st.session_state.get("date_time", ""),
                # バッチ
                st.session_state.get("batch", ""),
                # ファイル名
                st.session_state.get("File_Name", ""),
                # 項目コード
                st.session_state.get("Item_Code", ""),
            ),
        )

        # 重複するレコードがある場合
        if db_cursor.fetchone()[0] > 0:
            # エラーメッセージを表示
            st.error("このレコードは既に登録されています。")
            # プログラムを停止
            st.stop()

        # データ登録
        # データをデータベースに登録
        df_check_list.to_sql(
            # テーブル名
            "table_qc_status_log",
            # データベース接続
            con=write_conn,
            if_exists="append",
            index=False,
        )
        st.session_state.form_submitted = True
        st.success("データベースに正常に登録されました。")
        st.balloons()

    except sqlite3.IntegrityError:
        st.error("データが重複しています。既に登録されています。")
    except sqlite3.Error as e:
        st.error(f"データベース登録中にエラーが発生しました: {str(e)}")
