"""_summary_
qc check
"""

import sqlite3
import pandas as pd
import streamlit as st


# データベース管理クラス
class DatabaseManager:
    """データベース管理クラス"""
    def __init__(self, db_path):
        self.db_path = db_path

    # コネクション取得
    def get_connection(self):
        """コネクション取得"""
        try:
            # セッションステートにコネクションがない場合、作成
            if 'conn' not in st.session_state:
                st.session_state.conn = sqlite3.connect(self.db_path)
            return st.session_state.conn
        except sqlite3.Error as e:
            st.error(f"データベース接続エラー: {str(e)}")

        return None

    def fetch_qc_data(self):
        """QCデータ取得"""
        try:
            query = """
            SELECT
                date_time,
                type,
                SD_conversion
            FROM table_qc_mulch_rule
            WHERE date_time >= datetime('now', '-30 days')
            GROUP BY type, date_time
            ORDER BY date_time DESC
            """
            conn = self.get_connection()
            if conn is not None:
                return pd.read_sql_query(query, conn)
            return pd.DataFrame()
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            st.error(f"データ取得エラー: {str(e)}")
            return pd.DataFrame()

    # チェックログ保存
    def save_check_log(self, check_log_df):
        """チェックログ保存"""
        try:
            conn = self.get_connection()
            if conn is None:
                return False

            # データ型の変換と検証
            check_log_df['date_time'] = pd.to_datetime(
                check_log_df['date_time']).dt.to_pydatetime()

            # 必須フィールドの検証
            required_fields = [
                'date_time',
                'Measurement',
                'Measurer',
                'Type',
                'comment_check',
                'comment'
            ]
            if not all(field in check_log_df.columns for field
                       in required_fields):
                st.error("必要なデータフィールドが不足しています")
                return False

            check_log_df.to_sql(
                'table_qc_check_log',
                conn,
                if_exists='append',
                index=False
            )
            return True
        # エラー
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            st.error(f"データ保存エラー: {str(e)}")
            return False


# UIクラス
class QCCheckUI:
    """UIクラス"""
    def __init__(self, db_manager):
        """初期化"""
        self.db_manager = db_manager
        self.initialize_session_state()

    # セッションステートの初期化
    def initialize_session_state(self):
        """セッションステートの初期化"""
        if 'check_data' not in st.session_state or st.session_state.get(
           'refresh_data', False):
            # QCデータ取得
            data = self.db_manager.fetch_qc_data()
            # データが取得できた場合、セッションステートに保存
            if not data.empty:
                st.session_state.check_data = data
                st.session_state.refresh_data = False
            else:
                st.error("QCデータの取得に失敗しました")

    # サイドバーのレンダリング
    def render_sidebar(self):
        """サイドバーのレンダリング"""
        with st.sidebar:
            # 日付選択（未来日付を制限）
            date_time = st.date_input(
                "日付を選択してください",
                value=pd.to_datetime('today').date(),
                max_value=pd.to_datetime('today').date(),
                key="date_time_input"
            )

            # 責任者区分の選択
            options = [
                "精度管理責任者",
                "遺伝子関連・染色体検査の精度の確保に係る責任者",
                "管理者",
                "指導監督医"
            ]
            # 責任者区分の選択
            measurement = st.selectbox(
                "責任者区分を選択してください",
                options,
                key="measurement_select"
            )

            # 測定者の入力
            measurer = st.text_input(
                label=measurement,
                placeholder='フルネームを入力してください。',
                key="measurer_input"
            ).strip()

            return date_time, measurement, measurer

    # チャートのレンダリング
    def render_charts(self, date_time, measurement, measurer):
        """チャートのレンダリング"""
        if 'check_data' not in st.session_state:
            # データが読み込まれていない場合、警告メッセージを表示
            st.warning("データが読み込まれていません")
            return []

        # チェックログの初期化
        check_logs = []
        # チェックログの作成
        for type_name in st.session_state.check_data['Type'].unique():
            # チェックログの展開
            with st.expander(f"Type: {type_name}", expanded=True):
                # チェックログのデータ取得
                type_data = st.session_state.check_data[
                    st.session_state.check_data['Type'] == type_name
                ].copy()

                # データが取得できた場合、チャートを表示
                if not type_data.empty:
                    # 日付順にソート
                    type_data = type_data.sort_values('date_time')
                    st.line_chart(
                        type_data,
                        x='date_time',
                        y='SD_conversion'
                    )

                # コメントチェックのカラムを表示
                col1, col2 = st.columns([1, 3])
                # コメントチェックのラジオボタン
                with col1:
                    comment_check = st.radio(
                        '精度管理コメント',
                        ['問題なし', '問題あり'],
                        key=f"comment_check_{type_name}"
                    )

                with col2:
                    comment = st.text_input(
                        label='コメント',
                        placeholder='必要に応じてコメントを入力してください。',
                        key=f"comment_{type_name}"
                    ).strip()

                    if comment_check == '問題あり' and not comment:
                        st.warning("問題ありの場合はコメントを入力してください")

                check_logs.append({
                    'Type': type_name,
                    'comment_check': comment_check,
                    'comment': comment if comment else "コメントなし"
                })

                df_act_log = pd.DataFrame({
                    'date_time': [date_time],
                    'Measurement': [measurement],
                    'Measurer': [measurer],
                    'Type': [type_name],
                    'comment_check': [comment_check],
                    'comment': [comment if comment else "コメントなし"]
                })

                st.caption("現在のチェック状況")
                st.dataframe(df_act_log, hide_index=True)

        return check_logs


# メイン関数
def main():
    """メイン関数"""
    st.set_page_config(
        page_title="精度管理状況確認",
        layout="wide"
    )

    st.title("精度管理状況確認")

    # データベース管理クラスのインスタンスを作成
    try:
        db_manager = DatabaseManager('db_folder/qc_data_base.db')
        ui = QCCheckUI(db_manager)

        # サイドバーのレンダリング
        Date_Time, Measurement, Measurer = ui.render_sidebar()

        # 測定者が入力されていない場合、警告メッセージを表示
        if not Measurer:
            st.warning("責任者名を入力してください")
            return

        check_logs = ui.render_charts(Date_Time, Measurement, Measurer)

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("データベースに登録", key="save_button", type="primary"):
                if not check_logs:
                    st.warning('保存するデータがありません')
                    return

                # 問題ありのケースでコメントが必須
                if any(log['comment_check'] == '問題あり' and
                       log['comment'] == "コメントなし"
                       for log in check_logs):
                    st.error("問題ありの項目にはコメントの入力が必要です")
                    return

                # データベースに登録するためのデータフレームの作成
                final_check_log_df = pd.DataFrame([{
                    'Date_Time': Date_Time,
                    'Measurement': Measurement,
                    'Measurer': Measurer,
                    'Type': log['Type'],
                    'comment_check': log['comment_check'],
                    'comment': log['comment']
                } for log in check_logs])

                # 登録データの確認
                st.write("### 登録データの確認")
                st.dataframe(final_check_log_df, hide_index=True)

                if db_manager.save_check_log(final_check_log_df):
                    st.success('データが正常に保存されました')
                    st.session_state.refresh_data = True
                    st.balloons()

        with col2:
            # リセットボタン
            if st.button("リセット", key="cancel_button"):
                st.session_state.clear()
                st.rerun()

    # エラー
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        st.error(f"アプリケーションエラー: {str(e)}")


if __name__ == "__main__":
    main()
