"""
QCデータ処理モジュール
"""

import sqlite3
from typing import Any, Dict

import pandas as pd
import streamlit as st

from src.config import Config
from src.data_import.data_importer import DataImporter
from src.database.connection import get_db_connection
from src.models.westgard_rules import MultiRule, check_westgard_rules
from src.utils.file_processing import ProcessedData


class QCDataProcessor:
    """QCデータ処理クラス"""

    def __init__(self):
        self.data_importer = DataImporter()

    async def process_data_batch(self, data: ProcessedData) -> Dict[str, Any]:
        """データの一括処理を行う"""
        results = {}

        # MultiRule インスタンスの取得
        async with get_db_connection(Config.DATABASE_PATH) as conn:
            westgard_checker = MultiRule(
                type_conditions={
                    "IC": [{"Type": "sd_conversion", "value": 2.0}],
                    "NC": [{"Type": "sd_conversion", "value": 3.0}],
                    "PC": [{"Type": "sd_conversion", "value": 2.5}],
                },
                db_connection=conn,
            )

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
                        f"{data_type}データには次のカラムが欠けています: "
                        f"{', '.join(missing_columns)}"
                    )
                    continue

                # 必要なカラムの存在確認と安全な取得
                df_dict = {
                    "qc_data": df["Ct"].tolist(),
                    "sd_conversions": df["SD_Conversion"].tolist(),
                    "types": df["Type"].tolist(),
                    "item_codes": df["Item_Code"].tolist(),
                    "dye": df["Dye"].tolist(),  # ←ここを修正
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
                    f"{data_type}データの処理中にエラーが発生しました: "
                    f"キー '{e}' が見つかりません"
                )
            except (ValueError, TypeError, AttributeError) as e:
                st.error(f"実行時エラーが発生しました: {str(e)}")

        return results

    async def process_and_display_westgard_results(self,
                                                   data: ProcessedData
                                                   ) -> None:
        """Westgardルールチェックの処理と表示"""

        async with get_db_connection(Config.DATABASE_PATH) as conn:
            try:
                data_types = {"PC": data.pc_data}

                for data_type, df in data_types.items():
                    if not isinstance(df, pd.DataFrame) or df.empty:
                        continue

                    st.markdown(f"#### {data_type} Control Multi Rule Results")

                    # PC データは過去データと比較
                    if data_type == "PC":
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

                            # 直近アップロードデータのマルチルール判定
                            # st.markdown("### マルチルールチェック判定結果")

                            # 1. マルチルール判定＆登録
                            for type_name, group in df.groupby("Type"):
                                # 履歴データを取得してWestgardルールチェックに渡す
                                type_historical_data = historical_data[
                                    historical_data["Type"] == type_name
                                ]
                                result_df = check_westgard_rules(
                                    group, historical_data=type_historical_data
                                )
                                result_df["File_Name"] = data.file_info[
                                    "File_Name"
                                ].iloc[0]

                                # 重複除外
                                existing_keys = pd.read_sql_query(
                                    """
                                    SELECT Item_Code, Date_Time, Batch, Model,
                                    Type, Lot_Number
                                    FROM table_qc_multi_rule
                                    WHERE Item_Code = ?
                                    """,
                                    conn,
                                    params=(item_code,),
                                )
                                merge_cols = [
                                    "Item_Code",
                                    "Date_Time",
                                    "Batch",
                                    "Model",
                                    "Type",
                                    "Lot_Number",
                                ]
                                if all(col in result_df.columns for
                                       col in merge_cols):
                                    merged = result_df.merge(
                                        existing_keys,
                                        on=merge_cols,
                                        how="left",
                                        indicator=True,
                                    )
                                    new_records = merged[
                                        merged["_merge"] == "left_only"
                                    ].drop(columns=["_merge"])
                                else:
                                    new_records = result_df

                                if not new_records.empty:
                                    new_records.to_sql(
                                        "table_qc_multi_rule",
                                        conn,
                                        if_exists="append",
                                        index=False,
                                    )

                            # 2. table_qc_multi_ruleからデータ取得
                            multi_rule_query = """
                            SELECT * FROM table_qc_multi_rule
                            WHERE Item_Code = ?
                            ORDER BY Date_Time DESC
                            LIMIT 100
                            """
                            multi_rule_data = pd.read_sql_query(
                                multi_rule_query, conn, params=(item_code,)
                            )
                            if multi_rule_data.empty:
                                st.warning("table_qc_multi_ruleにデータがありません")
                                return

                            # データの基本統計量 (Type別)
                            st.write("### データの基本統計量 (Type別)")
                            grouped_stats = multi_rule_data.groupby("Type")[
                                ["SD_Conversion", "Ct"]
                            ].describe()
                            st.dataframe(grouped_stats, hide_index=True)

                            # Typeごとに直近10件のグラフ・データ一覧
                            for type_name in multi_rule_data["Type"].unique():
                                type_hist = multi_rule_data[
                                    multi_rule_data["Type"] == type_name
                                ]
                                # 最新10件を取得（最大10レコード）
                                type_hist = type_hist.sort_values(
                                    "Date_Time", ascending=False
                                ).head(10)
                                st.write(f"#### {type_name} 解析結果（最大10レコード）")

                                if not type_hist.empty:
                                    # グラフ表示用データの準備
                                    chart_df = type_hist.copy()
                                    if "Date_Time" in chart_df.columns:
                                        chart_df["Date_Time"] = pd.to_datetime(
                                            chart_df["Date_Time"],
                                            errors="coerce"
                                        )
                                        chart_df = chart_df.dropna(subset=[
                                            "Date_Time"])
                                        chart_df = chart_df.sort_values(
                                            "Date_Time", ascending=True
                                        )
                                        chart_df["Date_Time"] = chart_df[
                                            "Date_Time"
                                        ].dt.strftime("%y/%m/%d")

                                        if "Batch" in chart_df.columns:
                                            chart_df["Date_Time"] = (
                                                chart_df["Date_Time"]
                                                + ":"
                                                + chart_df["Batch"].astype(str)
                                            )

                                        if not chart_df.empty:
                                            # グラフ表示
                                            chart_plot_df = chart_df.set_index(
                                                "Date_Time"
                                            )
                                            chart_plot = chart_plot_df[
                                                "SD_Conversion"]
                                            st.line_chart(chart_plot)

                                            # データ一覧表示（最大10レコード）
                                            st.write(
                                                "##### データ一覧（最大10レコード）"
                                            )
                                            # カラム順を指定
                                            display_columns = [
                                                "Item_Code",
                                                "Date_Time",
                                                "Batch",
                                                "Model",
                                                "Type",
                                                "Lot_Number",
                                                "Judgment",
                                                "SD_Conversion",
                                            ]
                                            display_columns = [
                                                col
                                                for col in display_columns
                                                if col in chart_df.columns
                                            ]
                                            chart_df = chart_df[
                                                display_columns]
                                            sort_cols = ["Date_Time"]
                                            if "Batch" in chart_df.columns:
                                                sort_cols.append("Batch")
                                            chart_df = chart_df.sort_values(
                                                sort_cols, ascending=True
                                            )
                                            chart_df = chart_df.drop_duplicates()
                                            # 最大10レコードに制限
                                            chart_df = chart_df.head(10)
                                            st.dataframe(
                                                chart_df,
                                                use_container_width=True,
                                                hide_index=True
                                            )
                                        else:
                                            st.info(
                                                "グラフ・データ一覧の表示対象データがありません。"
                                            )
                                    else:
                                        st.info("Date_Timeカラムが存在しません。")

                                    # QCチェックログ（Failのみ、最大10レコード）
                                    st.write(
                                        "##### QCチェックログ（異常のみ、最大10レコード）"
                                    )
                                    fail_log = type_hist[
                                        type_hist["Judgment"] == "Fail"
                                    ].head(10)
                                    if not fail_log.empty:
                                        # カラム順を指定
                                        display_columns = [
                                            "Judgment",
                                            "Error_type",
                                            "Type_error",
                                            "Violated_rule",
                                            "Item_Code",
                                            "Batch",
                                            "Model",
                                            "Date_Time",
                                            "Type",
                                            "Dye",
                                            "Ct",
                                            "SD_Conversion",
                                            "Lot_Number",
                                            "1-2s",
                                            "1-3s",
                                            "2-2s",
                                            "R-4s",
                                            "4-1s",
                                            "8x",
                                            "Measurer",
                                            "File_Name",
                                        ]
                                        # 存在するカラムのみ選択
                                        available_columns = [
                                            col
                                            for col in display_columns
                                            if col in fail_log.columns
                                        ]
                                        fail_log_display = fail_log[
                                            available_columns
                                        ].copy()

                                        st.dataframe(
                                            fail_log_display,
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                    else:
                                        st.info("異常なQCチェックログはありません。")
                                else:
                                    st.info(f"{type_name}のデータがありません。")

                            # 過去データのマルチルール判定（従来通り）
                            st.markdown("### 登録終了しました")

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
            except Exception as e:
                st.error(f"Westgardルール処理中にエラーが発生しました: {e}")
