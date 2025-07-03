"""
Westgardマルチルールのモデル
"""  # Westgardマルチルールを適用するためのモデルを定義します。

# Standard library imports
import sqlite3  # SQLiteデータベースを操作するためのライブラリをインポートします。

# 型ヒントを使用するための型をインポートします。
from typing import Dict, List, Optional, Tuple, Union

import numpy as np  # 数値計算のためのNumPyライブラリをインポートします。

# Third-party library imports
import pandas as pd  # データ操作のためのPandasライブラリをインポートします。
import streamlit as st  # Webアプリケーションを作成するためのStreamlitライブラリをインポートします。


# WestgardMultiRuleクラスの定義
class MultiRule:
    """SD変換値を使用してWestgardマルチルールを適用するクラス"""  # Westgardマルチルールを適用するためのクラスです。

    # 各タイプの条件を辞書形式で受け取ります。
    def __init__(
        self,
        type_conditions: Dict[str, List[Dict[str, Union[float, str]]]],
        db_connection,
    ):  # データベース接続を受け取ります。
        # タイプごとの条件を初期化
        self.type_conditions = (
            type_conditions  # タイプごとの条件をインスタンス変数に保存します。
        )
        self.db_connection = (
            db_connection  # データベース接続をインスタンス変数に保存します。
        )

    def check_duplicates(self, data: pd.DataFrame, table_name: str) -> bool:
        """
        データベースの重複をチェックする  # データベース内の重複データを確認するメソッドです。

        Args:
            data: チェックするデータフレーム  # チェック対象のデータフレームを引数に取ります。
            table_name: テーブル名  # チェック対象のテーブル名を引数に取ります。

        Returns:
            bool: 重複がある場合True  # 重複が見つかった場合はTrueを返します。
        """
        query = f"""
        SELECT COUNT(*) FROM {table_name}
        WHERE item_code = %s AND batch = %s AND date = %s AND model = %s
        """

        for _, row in data.iterrows():  # データフレームの各行をループ処理します。
            cursor = self.db_connection.cursor()  # データベースカーソルを作成します。
            cursor.execute(
                query,
                (
                    row["item_code"],  # SQLクエリを実行し、行のデータを渡します。
                    row["batch"],
                    row["date"],
                    row["model"],
                ),
            )
            count = cursor.fetchone()[0]  # クエリの結果からカウントを取得します。
            if count > 0:  # 重複が見つかった場合
                return True  # Trueを返します。
        return False  # 重複がなかった場合はFalseを返します。

    def import_to_database(
        self,
        file_info: pd.DataFrame,
        ic_data: pd.DataFrame,
        nc_data: pd.DataFrame,
        pc_data: pd.DataFrame,
    ) -> bool:
        """
        データをデータベースにインポートする  # データをデータベースにインポートするメソッドです。

        Returns:
            bool: インポート成功時True  # インポートが成功した場合はTrueを返します。
        """
        try:
            # 重複チェック
            tables = {  # インポートするテーブルとデータを辞書形式で定義します。
                "table_qc_file_info": file_info,
                "table_qc_ic": ic_data,
                "table_qc_nc": nc_data,
                "table_qc_pc": pc_data,
            }

            for (
                table_name,
                data,
            ) in tables.items():  # 各テーブルに対してループ処理します。
                if self.check_duplicates(data, table_name):  # 重複があれば
                    return False  # Falseを返します。

            # データのインポート
            for (
                table_name,
                data,
            ) in tables.items():  # 各テーブルに対してループ処理します。
                if not data.empty:  # データが空でない場合
                    columns = ", ".join(
                        data.columns
                    )  # カラム名をカンマ区切りで取得します。
                    # プレースホルダーを作成します。
                    placeholders = ", ".join(["%s"] * len(data.columns))
                    query = f"""
                    INSERT INTO {table_name} ({columns})
                    VALUES ({placeholders})
                    """

                    cursor = (
                        self.db_connection.cursor()
                    )  # データベースカーソルを作成します。
                    # データを一括挿入します。
                    cursor.executemany(query, data.values.tolist())
                    self.db_connection.commit()  # 変更をコミットします。

            return True  # インポートが成功した場合はTrueを返します。

        except pd.errors.EmptyDataError:  # 空のデータフレームが渡された場合
            print(
                "空のデータフレームが検出されました"
            )  # エラーメッセージを表示します。
            self.db_connection.rollback()  # トランザクションをロールバックします。
            return False  # Falseを返します。
        except sqlite3.Error as e:  # SQLiteエラーが発生した場合
            print(f"データベースエラー: {str(e)}")  # エラーメッセージを表示します。
            self.db_connection.rollback()  # トランザクションをロールバックします。
            return False  # Falseを返します。
        except ValueError as e:  # 値のエラーが発生した場合
            print(f"データ形式エラー: {str(e)}")  # エラーメッセージを表示します。
            self.db_connection.rollback()  # トランザクションをロールバックします。
            return False  # Falseを返します。

    def apply_type_specific_rules(
        self, qc_type: str, sd_conversion_value: float
    ) -> Tuple[bool, str]:
        """
        各タイプに固有のルールを適用する関数  # 各QCタイプに特有のルールを適用するメソッドです。

        Args:
            qc_type: QCタイプ（'IC', 'NC', 'PC'など）  # QCタイプを引数に取ります。
            sd_conversion_value: SD変換値  # SD変換値を引数に取ります。

        Returns:
            Tuple[bool, str]: (エラーの有無, エラーメッセージ)  # エラーの有無とエラーメッセージを返します。
        """
        # エラーフラグとメッセージを初期化
        error = False  # エラーフラグを初期化します。
        error_message = ""  # エラーメッセージを初期化します。

        # タイプに対応する条件が存在するか確認
        if (
            qc_type not in self.type_conditions
        ):  # 指定されたQCタイプが条件に存在しない場合
            return error, error_message  # エラーなしで返します。

        # タイプごとの条件をチェック
        conditions = self.type_conditions[
            qc_type
        ]  # QCタイプに対応する条件を取得します。
        if not isinstance(conditions, list):  # 条件がリストでない場合
            conditions = [conditions]  # リストに変換します。

        for condition in conditions:  # 各条件に対してループ処理します。
            try:
                if condition["Type"] == "sd_conversion":
                    limit_value = float(condition["value"])
                    if abs(sd_conversion_value) > limit_value:
                        error = True
                        error_message += f"{qc_type}の値が{limit_value}を超えています; "
            except (KeyError, ValueError) as e:
                st.write(f"条件チェックエラー: {str(e)}")
                continue

        return error, error_message.strip("; ")

    # Westgardマルチルールを評価する関数
    def evaluate_rules(self, sd_conversions):
        """
        Westgardルールを評価する
        Args:
            sd_conversions: SD変換値のリストまたは列

        Returns:
            dict: 各ルールの評価結果
        """
        # sd_conversionsが単一の値の場合、リストに変換
        if not isinstance(sd_conversions, (list, np.ndarray)):
            sd_conversions = [sd_conversions]

        # 最新のデータポイントのインデックス
        latest_idx = len(sd_conversions) - 1

        # 各ルールの評価結果を格納する辞書
        results = {
            "1-2s": 0,
            "1-3s": 0,
            "2-2s": 0,
            "R-4s": 0,
            "4-1s": 0,
            "8x": 0,
        }

        # 最新のポイントに対する1-2sと1-3sルールの評価
        latest_sd = abs(sd_conversions[latest_idx])
        results["1-2s"] = 1 if 2 <= latest_sd <= 3 else 0
        results["1-3s"] = 1 if latest_sd > 3 else 0

        # 直近2点での2-2sルールの評価
        if len(sd_conversions) >= 2:
            last_two = sd_conversions[-2:]
            results["2-2s"] = (
                1
                if (all(sd < -2 for sd in last_two) or
                    all(sd > 2 for sd in last_two))
                else 0
            )

        # 直近2点でのR-4sルールの評価
        if len(sd_conversions) >= 2:
            last_two = sd_conversions[-2:]
            results["R-4s"] = 1 if (abs(last_two[0] - last_two[1]) > 4) else 0

        # 直近4点での4-1sルールの評価
        if len(sd_conversions) >= 4:
            last_four = sd_conversions[-4:]
            results["4-1s"] = (
                1
                if (all(sd < -1 for sd in last_four) or
                    all(sd > 1 for sd in last_four))
                else 0
            )

        # 直近8点での8xルールの評価
        if len(sd_conversions) >= 8:
            last_eight = sd_conversions[-8:]
            results["8x"] = (
                1
                if (
                    all(sd > 0 for sd in last_eight) or
                    all(sd < 0 for sd in last_eight)
                )
                else 0
            )

        return results

    # マルチルールを適用する関数
    def apply_rules(
        self,
        qc_data: List[float],
        sd_conversions: List[float],
        types: List[str],
        item_codes: List[str],
        dye: List[str],
        batch: List[str],
        model: List[str],
        date: List[str],
        measurer: List[str] | None = None,
        lot_number: List[str] | None = None,
        historical_sd_conversions: List[float] | None = None,
    ) -> pd.DataFrame:
        """QCデータにWestgardマルチルールを適用"""
        results = []
        measurer_list = measurer or ["-"] * len(qc_data)
        lot = lot_number or ["-"] * len(qc_data)
        dyes = dye or ["-"] * len(qc_data)

        for i, (value,
                sd_conv,
                qc_type, item_code, dye, b, m, d, meas, l) in enumerate(
            zip(
                qc_data,
                sd_conversions,
                types,
                item_codes,
                dyes,
                batch,
                model,
                date,
                measurer_list,
                lot,
            )
        ):
            result = {
                "Item_Code": item_code,
                "Batch": b,
                "Model": m,
                "Date_Time": d,
                "Measurer": meas,
                "Type": qc_type,
                "Dye": dye,
                "Ct": value,
                "SD_Conversion": sd_conv,
                "Lot_Number": l,
                "Judgment": "Pass",
                "Error_type": "-",
                "Type_error": "-",
                "Violated_rule": "-",
            }

            # 履歴データと現在のデータを組み合わせてルール評価
            if historical_sd_conversions is not None:
                # 履歴データ + 現在までのデータを使用
                combined_sd = historical_sd_conversions + sd_conversions[: i + 1]
            else:
                # 現在のデータのみを使用
                combined_sd = sd_conversions[: i + 1]

            # Westgardルールの評価（履歴データを含む）
            westgard_rules = self.evaluate_rules(combined_sd)

            # Westgardルールの結果を追加
            result.update(westgard_rules)

            # タイプ固有のルールを適用
            error_type, error_type_message = self.apply_type_specific_rules(
                qc_type, sd_conv
            )

            # タイプ固有のエラーがある場合
            if error_type:
                result["Judgment"] = "Fail"
                result["Type_error"] = error_type_message

            # Westgardルールまたはタイプ固有のエラーがある場合
            if any(westgard_rules.values()) or error_type:
                result["Judgment"] = "Fail"
                # 違反したルールを抽出
                error_rules = [
                    rule for rule, violated in westgard_rules.items() if violated
                ]
                if error_type:
                    error_rules.append("Type_error")

                # エラータイプを設定
                if westgard_rules["1-3s"] or westgard_rules["R-4s"]:
                    result["Error_type"] = "偶発誤差"
                elif (
                    westgard_rules["2-2s"]
                    or westgard_rules["4-1s"]
                    or westgard_rules["8x"]
                ):
                    result["Error_type"] = "系統誤差"
                elif westgard_rules["1-2s"]:
                    result["Error_type"] = "注意"
                else:
                    result["Error_type"] = "-"

                # 違反したルールをカンマ区切りで結合
                result["Violated_rule"] = ", ".join(error_rules)

            # 結果をリストに追加
            results.append(result)

        # 結果をDataFrameに変換して返す
        df = pd.DataFrame(results)
        # 指定のカラム順に並べ替え
        column_order = [
            "Measurer",
            "Date_Time",
            "Item_Code",
            "Batch",
            "Model",
            "Judgment",
            "Error_type",
            "Type_error",
            "Violated_rule",
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
            "File_Name",
        ]
        # File_Nameがなければ空文字で追加
        if "File_Name" not in df.columns:
            df["File_Name"] = ""
        # 存在しないカラムは無視して並べ替え
        column_order = [col for col in column_order if col in df.columns]
        df = df[column_order]
        return df

    def check_consecutive_violations(
        self, sd_conversions: List[float], n_consecutive: int, sd_limit: float
    ) -> bool:
        """
        連続したSD違反をチェックする

        Parameters:
        -----------
        sd_conversions : list
            SD変換値のリスト
        n_consecutive : int
            チェックする連続回数
        sd_limit : float
            SDの限値

        Returns:
        --------
        bool
            ルール違反があればTrue、なければFalse
        """
        # データが不足している場合はFalseを返す
        if len(sd_conversions) < n_consecutive:
            return False

        # 正負それぞれの制限値を超える連続値をチェック
        for i in range(len(sd_conversions) - n_consecutive + 1):
            consecutive_values = sd_conversions[i : i + n_consecutive]

            # 全ての値が+sd_limit以上
            if all(x >= sd_limit for x in consecutive_values):
                return True

            # 全ての値が-sd_limit以下
            if all(x <= -sd_limit for x in consecutive_values):
                return True

        return False

    # R4sルールのチェックメソッドを追加
    def check_range_violation(self, sd_conversions, threshold):
        """
        R4sルール違反をチェックする

        Args:
            sd_conversions (list): SD変換値のリスト
            threshold (int): 閾値 (通常4)

        Returns:
            bool: R4s違反があればTrue、なければFalse
        """
        if len(sd_conversions) < 2:
            return False

        max_value = max(sd_conversions)
        min_value = min(sd_conversions)

        return (max_value - min_value) >= threshold

    def check_consecutive_trend(self, sd_conversions, n):
        """
        連続したn個の測定値が平均値の同じ側にあるかをチェックする

        Args:
            sd_conversions (list): SD変換値のリスト
            n (int): チェックする連続点数

        Returns:
            bool: 違反があればTrue、なければFalse
        """
        if len(sd_conversions) < n:
            return False

        # 最新のn点を取得
        recent_values = sd_conversions[-n:]

        # すべての値が正か負かをチェック
        all_positive = all(x > 0 for x in recent_values)
        all_negative = all(x < 0 for x in recent_values)

        return all_positive or all_negative


def check_westgard_rules(
    data: pd.DataFrame, historical_data: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Westgardルールに基づいてQCデータをチェックする関数"""

    # Date_Timeカラムの存在確認
    if "Date_Time" not in data.columns:
        raise ValueError("データフレームに'Date_Time'カラムが存在しません")

    # MultiRuleインスタンスを作成
    westgard_checker = MultiRule(
        type_conditions={"PC": [{"Type": "sd_conversion", "value": 2.5}]},
        db_connection=None,
    )

    # 履歴データのSD変換値を取得
    historical_sd_conversions = None
    if historical_data is not None:
        if "Date_Time" not in historical_data.columns:
            raise ValueError("履歴データに'Date_Time'カラムが存在しません")
        if "SD_Conversion" in historical_data.columns:
            historical_sd_conversions = historical_data["SD_Conversion"].tolist()

    # データを処理用に整形
    processed_data = {
        "qc_data": data.get("Ct", pd.Series()).tolist(),
        "sd_conversions": data.get("SD_Conversion", pd.Series()).tolist(),
        "types": data.get("Type", pd.Series()).tolist(),
        "item_codes": data.get("Item_Code", pd.Series()).tolist(),
        "batch": data.get("Batch", pd.Series()).tolist(),
        "model": data.get("Model", pd.Series()).tolist(),
        "date": data.get("Date_Time", pd.Series()).tolist(),
        "measurer": data.get("Measurer", pd.Series()).tolist(),
        "lot_number": data.get("Lot_Number", pd.Series()).tolist(),
        "dye": ["-"] * len(data),
        "historical_sd_conversions": historical_sd_conversions,
    }

    # Westgardルールを適用
    results_df = westgard_checker.apply_rules(**processed_data)

    return results_df
