"""
検査測定状況管理記録登録ページ
"""

# ライブラリのインポート
import sqlite3  # SQLiteデータベースを操作するためのライブラリ
import pandas as pd  # データ操作のためのライブラリ
import streamlit as st  # Webアプリケーションを作成するためのライブラリ
from datetime import datetime

# ラジオボタンをカラムに分けて配置
col1, col2 = st.columns(2)  # 2つのカラムを作成

# 標準物質の使用状況
with col1:
    st.markdown("### 標準物質の使用状況")  # 標準物質の見出しを表示
    standard_usage = st.radio(
        '標準物質の使用状況を選択してください',
        ('使用なし', '継続使用', '開封/Lot変更なし', '開封/Lot変更あり')
    )

    st.markdown("### 管理試料の使用状況")
    control_usage = st.radio(
        '管理試料の使用状況を選択してください',
        ('継続使用', '開封/Lot変更なし', '開封/Lot変更あり')
    )

with col2:
    st.markdown("### 検査試薬の使用状況")
    reagents_usage = st.radio(
        '検査試薬の使用状況を選択してください',
        ('継続使用', '開封/Lot変更なし', '開封/Lot変更あり')
    )

    st.markdown("### 測定機器の使用状況")
    measuring_instrument_usage = st.radio(
        '測定機器の使用状況を選択してください。'
        '異常等がある場合は機器保守参照を選択してください。',
        ('異常なし', '異常あり/機器保守参照', 'メンテナンス/機器保守参照')
    )


# 検査項目のマスターデータの読み込みと初期化
def load_item_codes():
    """検査項目のマスターデータを読み込む関数"""
    try:
        item_code_select = pd.read_excel('master_folder/measurement_item.xlsx')
        column_mapping = {
            'Item_Code': next(
                (col for col in item_code_select.columns if col in [
                    'Item_Code', 'ItemCode', '項目コード']),
                None),
            'Measurement Item': next(
                (col for col in item_code_select.columns if col in [
                    'Measurement Item',
                    'Measurement_Item',
                    'MeasurementItem',
                    '測定項目',
                    '項目名']),
                None)
        }

        for target, col in column_mapping.items():
            if col is None:
                st.error(
                    f"必要な列 '{target}' が見つかりません。利用可能な列: \
                        {', '.join(item_code_select.columns)}")
                st.stop()

        item_code_select = item_code_select.rename(columns=column_mapping)
        return item_code_select
    except FileNotFoundError:
        st.error("measurement_item.xlsxファイルが見つかりません")
        st.error("ファイルエラーが発生しました。")
        st.stop()


# サイドバーコンポーネント
with st.sidebar:
    st.markdown('### 検査実施状況登録')
    ITEM_CODE_SELECT = load_item_codes()

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
        st.error(
            f"ファイルエラー: {str(e)}"
        )
        st.stop()

    # 検査項目の選択
    selected_item_code = st.selectbox(
        '検査項目を選択してください',
        ITEM_CODE_SELECT['Item_Code'],
        format_func=lambda x: (
            x if x in ITEM_CODE_SELECT['Item_Code'] else 'Unknown'
        )
    )
    st.session_state['item_code'] = selected_item_code

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
            WHERE Date_Time = ? AND Batch = ?
            AND Item_Code = ? AND type = ?
        """, (
            st.session_state.get('date_time', ''),
            st.session_state.get('batch', ''),
            st.session_state.get('item_code', ''),
            st.session_state.get('type_variable', '')
        ))
        if db_cursor.fetchone()[0] > 0:
            st.error("このレコードは既に登録されています。")
            st.stop()  # returnの代わりにst.stop()を使用

        try:
            df_check_list.to_sql(
                'table_qc_act_log',
                con=st.session_state.conn,
                if_exists='append', index=False
            )
            st.session_state.form_submitted = True
            st.success("データベースに正常に登録されました。")
            st.balloons()
        except sqlite3.IntegrityError:
            st.error("データが重複しています。既に登録されています。")
        except sqlite3.Error as e:
            st.error(
                f"データベース登録中にエラーが発生しました: {e}"
            )


# メイン関数の実行
if __name__ == "__main__":
    pass  # main関数が定義されていないため、passを使用


async def qc_info_log(
    item_code: str,
    batch: str,
    model: str,
    date_time: datetime,
    measurer: str,
    event_type: str,
    details: str,
    db_path: str
) -> None:
    """
    QC情報をログとしてデータベースに記録する関数

    Args:
        item_code (str): 項目コード
        batch (str): バッチ番号
        model (str): モデル
        date_time (datetime): 日時
        measurer (str): 測定者
        event_type (str): イベントタイプ
        details (str): 詳細情報
        db_path (str): データベースパス
    """
    try:
        # セッション状態の更新
        if 'item_code' not in st.session_state:
            st.session_state['item_code'] = item_code
        if 'batch' not in st.session_state:
            st.session_state['batch'] = batch
        if 'model' not in st.session_state:
            st.session_state['model'] = model
        if 'measurer' not in st.session_state:
            st.session_state['measurer'] = measurer

        # データベースに接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # テーブルが存在しない場合は作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_qc_info_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT NOT NULL,
                batch TEXT NOT NULL,
                model TEXT NOT NULL,
                date_time TIMESTAMP NOT NULL,
                measurer TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ログを挿入
        cursor.execute("""
            INSERT INTO table_qc_info_log (
                item_code, batch, model, date_time,
                measurer, event_type, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item_code, batch, model, date_time,
            measurer, event_type, details
        ))

        # 変更を確定
        conn.commit()

    except sqlite3.Error as e:
        st.error(f"データベースエラー: {str(e)}")
        raise

    except Exception as e:
        st.error(f"予期しないエラーが発生しました: {str(e)}")
        raise

    finally:
        if 'conn' in locals():
            conn.close()
