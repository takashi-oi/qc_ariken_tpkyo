"""
精度管理：マルチルール

このモジュールは、品質チェックアプリケーションの実装を提供します。
データの処理、データベース操作、Westgardルールのチェックを行います。
"""

# asyncioモジュールのインポート
import asyncio

# sqlite3モジュールのインポート
import sqlite3

# asynccontextmanager関数のインポート
from contextlib import asynccontextmanager

# pandasモジュールのインポート
import pandas as pd

# streamlitモジュールのインポート
import streamlit as st

# 自作モジュールのインポート
from src.config import Config
from src.data_import.data_importer import DataImporter
from src.database.connection import DatabaseManager, get_db_connection
from src.models.westgard_rules import MultiRule, check_westgard_rules
from src.utils.file_processing import ProcessedData

# ページ設定
st.set_page_config(page_title="精度管理資料結果確認", layout="wide")


# タイトルを表示
st.markdown("### 管理試料測定結果登録・確認")


class QCCheckApp:
    """品質チェックアプリケーションクラス"""

    # エラーメッセージを定数として定義
    ERROR_MESSAGES = {
        "database": "データベース操作中にエラーが発生しました: {}",
        "data_processing": "データ処理中にエラーが発生しました: {}",
        "io": "入出力処理中にエラーが発生しました: {}",
        "runtime": "実行時エラーが発生しました: {}",
    }

    # 初期化関数
    def __init__(self):
        self.data_importer = DataImporter()
        self.db_manager = DatabaseManager(Config.DATABASE_PATH)
        # MultiRule インスタンスの初期化は使用直前に行う (db_connection を適切に設定するため)

    # データベース接続を持つ MultiRule インスタンスを取得する非同期関数
    async def get_westgard_checker(self):
        """データベース接続を持つ MultiRule インスタンスを取得"""
        async with get_db_connection(Config.DATABASE_PATH) as conn:
            return MultiRule(
                type_conditions={
                    "IC": [{"Type": "sd_conversion", "value": 2.0}],
                    "NC": [{"Type": "sd_conversion", "value": 3.0}],
                    "PC": [{"Type": "sd_conversion", "value": 2.5}],
                },
                db_connection=conn,
            )

    # データの一括処理を行う非同期関数
    async def process_data_batch(self, data: ProcessedData) -> dict:
        """データの一括処理を行う"""
        results = {}
        westgard_checker = await self.get_westgard_checker()

        for data_type, df in [
            ("IC", data.ic_data),
            ("NC", data.nc_data),
            ("PC", data.pc_data),
        ]:
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue

            try:
                required_columns = [
                    "Ct",
                    "SD_Conversion",
                    "Type",
                    "Item_Code",
                    "Dye",
                    "Batch",
                    "Model",
                    "Date_Time",
                ]
                # 必要なカラムが全て存在するか確認
                missing_columns = [
                    col for col in required_columns if col not in df.columns
                ]

                if missing_columns:
                    st.warning(
                        f"{data_type
                           }データには次のカラムが欠けています: {
                               ', '.join(missing_columns)}"
                    )
                    continue

                # 必要なカラムの存在確認と安全な取得
                df_dict = {
                    "qc_data": df["Ct"].tolist(),
                    "sd_conversions": df["SD_Conversion"].tolist(),
                    "types": df["Type"].tolist(),
                    "item_codes": df["Item_Code"].tolist(),
                    "dyes": df["Dye"].tolist(),
                    "batch": df["Batch"].tolist(),
                    "model": df["Model"].tolist(),
                    "date": df["Date_Time"].tolist(),
                }

                # 全てのリストが同じ長さであることを確認
                if not all(len(v) == len(df) for v in df_dict.values()):
                    st.warning(f"{data_type}データの一部のカラムが欠落しています")
                    continue

                results[data_type] = westgard_checker.apply_rules(**df_dict)

            except KeyError as e:
                st.warning(
                    f"{data_type}データの処理中にエラーが発生しました: キー '{e}' が見つかりません"
                )
            except (ValueError, TypeError, AttributeError) as e:
                st.error(f"実行時エラーが発生しました: {str(e)}")

        return results

    # データ概要の表示（最適化版）を行う非同期関数
    async def display_data_summary(self, data: ProcessedData) -> None:
        """データ概要の表示（最適化版）"""
        metrics = {
            "ファイル情報": (
                len(data.file_info) if isinstance(data.file_info, pd.DataFrame) else 0
            ),
            "ICデータ": (
                len(data.ic_data) if isinstance(data.ic_data, pd.DataFrame) else 0
            ),
            "NCデータ": (
                len(data.nc_data) if isinstance(data.nc_data, pd.DataFrame) else 0
            ),
            "PCデータ": (
                len(data.pc_data) if isinstance(data.pc_data, pd.DataFrame) else 0
            ),
        }

        cols = st.columns(len(metrics))
        for col, (label, value) in zip(cols, metrics.items()):
            with col:
                st.metric(label, f"{value}件")

    # 詳細データの表示（最適化版）を行う非同期関数
    async def display_detailed_data(self, data: ProcessedData) -> None:
        """詳細データの表示（最適化版）"""
        data_sections = {
            "ファイル情報": data.file_info,
            "Inner Control Data": data.ic_data,
            "Negative Control Data": data.nc_data,
            "Positive Control Data": data.pc_data,
        }
        for title, df in data_sections.items():
            with st.expander(title, expanded=True):
                if isinstance(df, pd.DataFrame) and not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"{title.split('の', maxsplit=1)[0]}はありません")

    # エラーハンドリング用コンテキストマネージャを作成する非同期関数
    @asynccontextmanager
    async def error_handler(self):
        """エラーハンドリング用コンテキストマネージャ"""
        try:
            yield
        except sqlite3.IntegrityError as e:
            st.error(f"データベース整合性エラー: {str(e)}")
        except sqlite3.Error as e:
            st.error(f"データベースエラー: {str(e)}")
        except (ValueError, TypeError) as e:
            st.error(f"値または型に関するエラーが発生しました: {str(e)}")
        except (OSError, IOError) as e:
            st.error(f"入出力エラーが発生しました: {str(e)}")
        except (sqlite3.Error, RuntimeError) as e:
            st.error(f"予期しないエラーが発生しました: {str(e)}")

    # データベースの重複チェックを行う非同期関数
    async def check_for_duplicates(self, data: ProcessedData) -> bool:
        """データベースの重複チェックを行う"""
        if not isinstance(data.file_info, pd.DataFrame) or data.file_info.empty:
            st.error("処理するデータのファイル情報が存在しません")
            return True

        try:
            # 重複チェック用のデータを準備
            duplicate_checks = {
                "table_qc_file_info": {
                    "Date_Time": data.file_info["Date_Time"].iloc[0],
                    "Item_Code": data.file_info["Item_Code"].iloc[0],
                    "Model": data.file_info["Model"].iloc[0],
                    "Measurer": data.file_info["Measurer"].iloc[0],
                    **(
                        {"Lot_Number": data.file_info["Lot_Number"].iloc[0]}
                        if "Lot_Number" in data.file_info.columns
                        else {}
                    ),
                },
                "table_qc_nc": {
                    "Date_Time": data.file_info["Date_Time"].iloc[0],
                },
                "table_qc_pc": {
                    "Date_Time": data.file_info["Date_Time"].iloc[0],
                },
            }

            # 各テーブルの重複チェック
            duplicate_found = False
            for table, check_data in duplicate_checks.items():
                if await self.db_manager.check_duplicate_records(table, check_data):
                    st.warning(f"{table}に重複するレコードが存在します")
                    duplicate_found = True

            return duplicate_found

        except IndexError:
            st.error("ファイル情報データが不完全です")
            return True
        except KeyError as e:
            st.error(f"必要なデータカラムがありません: {e}")
            return True

    # データベース操作の処理（最適化版）を行う非同期関数
    async def handle_database_operations(self, data: ProcessedData) -> None:
        """データベース操作の処理（最適化版）"""
        if st.button("データベース登録／マルチルールチェック開始"):
            if not isinstance(data.file_info, pd.DataFrame) or data.file_info.empty:
                st.error("処理するデータが存在しません")
                return

            async with self.error_handler():
                # 重複チェック
                if await self.check_for_duplicates(data):
                    return

                # データベースへの保存
                await self.db_manager.import_qc_data(
                    file_info=data.file_info,
                    ic_data=(
                        data.ic_data
                        if isinstance(data.ic_data, pd.DataFrame)
                        else pd.DataFrame()
                    ),
                    nc_data=(
                        data.nc_data
                        if isinstance(data.nc_data, pd.DataFrame)
                        else pd.DataFrame()
                    ),
                    pc_data=(
                        data.pc_data
                        if isinstance(data.pc_data, pd.DataFrame)
                        else pd.DataFrame()
                    ),
                )
                st.success("データベースへの保存が完了しました")

                # データベース保存後にマルチルールチェックを実行
                st.markdown("### マルチルールチェック結果")
                await self.process_and_display_westgard_results(data)

    # Westgardルールチェックの処理と表示を行う非同期関数
    async def process_and_display_westgard_results(self, data: ProcessedData) -> None:
        """Westgardルールチェックの処理と表示"""
        async with self.error_handler():
            data_types = {"PC": data.pc_data}

            for data_type, df in data_types.items():
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue

                st.markdown(f"#### {data_type} Control Multi Rule Results")

                # PC データは過去データと比較
                if data_type == "PC":
                    async with get_db_connection(Config.DATABASE_PATH) as conn:
                        try:
                            item_code = data.file_info["Item_Code"].iloc[0]
                            historical_query = """
                            SELECT * FROM table_qc_pc
                            WHERE Item_Code = ?
                            ORDER BY Date_Time DESC
                            """
                            historical_data = (
                                pd.read_sql_query(
                                    historical_query, conn, params=(item_code,)
                                )
                                .groupby("Type")
                                .head(10)
                            )

                            if historical_data.empty:
                                st.warning(
                                    "過去データが存在しないため、"
                                    "マルチルールチェックを実行できません"
                                )
                                return

                            # 基本統計量の表示
                            st.write("### データの基本統計量 (Type別)")
                            grouped_stats = historical_data.groupby("Type")[
                                ["SD_Conversion", "Ct"]
                            ].describe()
                            st.dataframe(grouped_stats)

                            # マルチルールチェック結果の表示
                            st.markdown("### マルチルールチェック結果")
                            for type_name, group in historical_data.groupby("Type"):
                                st.write(f"#### {type_name} 解析結果")
                                try:
                                    rule_results = check_westgard_rules(group)
                                    # File_Name列を追加
                                    rule_results["File_Name"] = data.file_info[
                                        "File_Name"
                                    ].iloc[0]
                                    st.write("マルチルールチェック結果:")
                                    if not rule_results.empty:
                                        st.dataframe(rule_results)
                                    else:
                                        st.info(
                                            "マルチルールチェックの結果はありません。"
                                        )
                                    rule_results.to_sql(
                                        "table_qc_multi_rule",
                                        conn,
                                        if_exists="append",
                                        index=False,
                                    )
                                except ValueError as e:
                                    st.error(
                                        f"{type_name}データの処理中にエラーが発生しました: {e}"
                                    )
                                    continue
                        except (
                            sqlite3.Error,
                            pd.errors.EmptyDataError,
                            ValueError,
                            TypeError,
                            AttributeError,
                            OSError,
                            IOError,
                            RuntimeError,
                        ) as e:
                            st.error(
                                f"{data_type}データの処理中にエラーが発生しました: {e}"
                            )

    # 特定のエラータイプに応じたエラーメッセージを表示する非同期関数
    def _handle_specific_error(self, error: Exception) -> None:
        """特定のエラータイプに応じたエラーメッセージを表示"""
        if isinstance(error, (pd.errors.EmptyDataError, sqlite3.Error)):
            st.error(self.ERROR_MESSAGES["database"].format(error))
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            st.error(self.ERROR_MESSAGES["data_processing"].format(error))
        elif isinstance(error, (OSError, IOError)):
            st.error(self.ERROR_MESSAGES["io"].format(error))
        elif isinstance(error, RuntimeError):
            st.error(self.ERROR_MESSAGES["runtime"].format(error))
        else:
            st.error(f"予期しないエラーが発生しました: {error}")

    # データベースからファイル一覧を取得する非同期関数
    async def get_file_list_from_db(self) -> pd.DataFrame:
        """データベースからファイル一覧を取得"""
        try:
            async with get_db_connection(Config.DATABASE_PATH) as conn:
                query = """
                SELECT DISTINCT 
                    File_Name,
                    Date_Time,
                    Item_Code,
                    Model,
                    Measurer
                FROM table_qc_file_info
                ORDER BY Date_Time DESC
                """
                return pd.read_sql_query(query, conn)
        except Exception as e:
            st.error(f"ファイル一覧の取得中にエラーが発生しました: {e}")
            return pd.DataFrame()

    # 選択されたファイルのレコードを抽出する非同期関数
    async def get_file_records(self, file_name: str) -> dict:
        """選択されたファイルのレコードを抽出"""
        try:
            async with get_db_connection(Config.DATABASE_PATH) as conn:
                # ファイル情報を取得
                file_info_query = """
                SELECT * FROM table_qc_file_info
                WHERE File_Name = ?
                """
                file_info = pd.read_sql_query(
                    file_info_query, conn, params=(file_name,)
                )

                # ICデータを取得
                ic_query = """
                SELECT * FROM table_qc_ic
                WHERE File_Name = ?
                """
                ic_data = pd.read_sql_query(ic_query, conn, params=(file_name,))

                # NCデータを取得
                nc_query = """
                SELECT * FROM table_qc_nc
                WHERE File_Name = ?
                """
                nc_data = pd.read_sql_query(nc_query, conn, params=(file_name,))

                # PCデータを取得
                pc_query = """
                SELECT * FROM table_qc_pc
                WHERE File_Name = ?
                """
                pc_data = pd.read_sql_query(pc_query, conn, params=(file_name,))

                return {
                    "file_info": file_info,
                    "ic_data": ic_data,
                    "nc_data": nc_data,
                    "pc_data": pc_data,
                }
        except Exception as e:
            st.error(f"ファイルレコードの取得中にエラーが発生しました: {e}")
            return {
                "file_info": pd.DataFrame(),
                "ic_data": pd.DataFrame(),
                "nc_data": pd.DataFrame(),
                "pc_data": pd.DataFrame(),
            }

    async def run(self) -> None:
        """アプリケーションのメイン実行関数"""
        async with self.error_handler():
            with st.sidebar:
                st.markdown("### データ入力方法")
                
                # タブを作成してファイルアップロードとデータベース選択を分ける
                tab1, tab2 = st.tabs(["ファイルアップロード", "データベース選択"])
                
                with tab1:
                    uploaded_file = st.file_uploader(
                        "QCデータファイルをアップロード", type=["xlsx"]
                    )
                    employee_data = pd.read_excel("data/master/employee_code.xlsx")
                    measurer = st.selectbox(
                        "測定者名を選択", 
                        employee_data["Member's_Name"].tolist(),
                        key="measurer_upload"
                    )
                
                with tab2:
                    st.markdown("#### データベースからファイルを選択")
                    
                    # データベースからファイル一覧を取得
                    file_list = await self.get_file_list_from_db()
                    
                    if not file_list.empty:
                        # ファイル選択用のドロップダウンを作成
                        file_options = []
                        for _, row in file_list.iterrows():
                            display_text = (
                                f"{row['File_Name']} - "
                                f"{row['Date_Time']} - "
                                f"{row['Item_Code']} - "
                                f"{row['Model']}"
                            )
                            file_options.append((display_text, row['File_Name']))
                        
                        if file_options:
                            selected_file_display = st.selectbox(
                                "ファイルを選択",
                                options=[opt[0] for opt in file_options],
                                key="file_selector"
                            )
                            
                            # 選択されたファイル名を取得
                            selected_file_name = None
                            for display, filename in file_options:
                                if display == selected_file_display:
                                    selected_file_name = filename
                                    break
                            
                            if selected_file_name and st.button("選択したファイルのデータを表示"):
                                # 選択されたファイルのレコードを取得
                                file_records = await self.get_file_records(selected_file_name)
                                
                                if not file_records["file_info"].empty:
                                    st.session_state.selected_file_data = file_records
                                    st.success(f"ファイル '{selected_file_name}' のデータを読み込みました")
                                else:
                                    st.warning("選択されたファイルのデータが見つかりませんでした")
                    else:
                        st.info("データベースにファイルが登録されていません")
            
            # ファイルアップロードからの処理
            if 'uploaded_file' in locals() and uploaded_file and measurer:
                qc_data = await self.data_importer.process_and_display(
                    uploaded_file, measurer
                )
                if (
                    qc_data
                    and isinstance(qc_data.file_info, pd.DataFrame)
                    and not qc_data.file_info.empty
                ):
                    st.write("### IC、NC、PCのデータの確認")
                    data = ProcessedData(
                        file_info=qc_data.file_info,
                        ic_data=qc_data.ic_data,
                        nc_data=qc_data.nc_data,
                        pc_data=qc_data.pc_data,
                    )
                    await self.display_data_summary(data)
                    await self.display_detailed_data(data)
                    await self.handle_database_operations(data)
                else:
                    st.warning("有効なデータが読み込まれていません")
            
            # データベース選択からの処理
            elif 'selected_file_data' in st.session_state:
                file_records = st.session_state.selected_file_data
                st.write("### 選択されたファイルのデータ確認")
                
                # ファイル情報の表示
                if not file_records["file_info"].empty:
                    st.markdown("#### ファイル情報")
                    st.dataframe(file_records["file_info"], use_container_width=True)
                
                # データ概要の表示
                data = ProcessedData(
                    file_info=file_records["file_info"],
                    ic_data=file_records["ic_data"],
                    nc_data=file_records["nc_data"],
                    pc_data=file_records["pc_data"],
                )
                await self.display_data_summary(data)
                await self.display_detailed_data(data)
                
                # マルチルールチェックの実行ボタン
                if st.button("マルチルールチェック実行"):
                    await self.process_and_display_westgard_results(data)
            
            # 初期状態のメッセージ
            elif not ('uploaded_file' in locals() and uploaded_file and measurer):
                st.info("サイドバーからファイルをアップロードするか、データベースからファイルを選択してください")


# メイン実行関数
if __name__ == "__main__":
    app = QCCheckApp()
    asyncio.run(app.run())
