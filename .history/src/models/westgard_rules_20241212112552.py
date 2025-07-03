"""Westgardマルチルールのモデル"""

# Standard library imports
from typing import List, Dict, Union, Tuple

# Third-party library imports
import pandas as pd
import numpy as np


# WestgardMultiRuleクラスの定義
class WestgardMultiRule:
    """SD変換値を使用してWestgardマルチルールを適用するクラス"""
    def __init__(self,
                 type_conditions: Dict[str,
                                       List[Dict[str,
                                                 Union[float, str]]]]):
        # タイプごとの条件を初期化
        self.type_conditions = type_conditions

    def apply_type_specific_rules(
        self, qc_type: str, sd_conversion_value: float
    ) -> Tuple[bool, str]:
        """各タイプに固有のルールを適用する関数"""
        # エラーフラグを初期化
        error = False
        # エラーメッセージを初期化
        error_message = ""

        # タイプごとの条件をチェック
        for condition in self.type_conditions.get(qc_type, []):
            # sd_conversionの値が上限を超えている場合
            if (condition['Type'] == 'sd_conversion' and
                    sd_conversion_value > float(condition['value'])):
                error = True
                error_message += f"{qc_type} > {condition['value']}; "
            # 値が下限を下回っている場合
            elif (condition['Type'] == 'sd_conversion' and
                    sd_conversion_value < float(condition['value'])):
                error = True
                error_message += f"{qc_type} < {condition['value']}; "
        # エラー状態とメッセージを返す
        return error, error_message.strip('; ')

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
        return {
            # 1-2sルール: SD変換値の絶対値が2以上3以下の値が1つでもある場合True
            '1-2s': any(2 <= abs(sd) <= 3 for sd in sd_conversions),
            # 1-3sルール: SD変換値の絶対値が3を超える値が1つでもある場合True
            '1-3s': any(abs(sd) > 3 for sd in sd_conversions),
            # 2-2sルール: 2SD以上の値が2回連続で発生した場合True
            '2-2s': self.check_consecutive_violations(list(sd_conversions),
                                                      2, 2),
            # R-4sルール: 最大値と最小値の差4SD以上の場合True
            'R-4s': self.check_range_violation(sd_conversions, 4),
            # 4-1sルール: 1SD以上の値が4回連続で発生した場合True
            '4-1s': self.check_consecutive_violations(list(sd_conversions),
                                                      4, 1),
            # 8xルール: 平均値の同じ側に8回連続でプロットされた場合True
            '8x': self.check_consecutive_trend(sd_conversions, 8)}

    # マルチルールを適用する関数
    def apply_rules(self,
                    qc_data: List[float],
                    sd_conversions: List[float],
                    types: List[str],
                    item_codes: List[str],
                    dyes: List[str],
                    batch: List[str],
                    model: List[str],
                    date: List[str]) -> pd.DataFrame:
        """QCデータにWestgardマルチルールを適用"""
        # 結果を格納するリストを初期化
        results = []

        # 各データポイントに対して処理
        for _, (value,
                sd_conversion,
                qc_type,
                item_code,
                batch,
                model,
                date,
                dye) in enumerate(zip(qc_data,
                                      sd_conversions,
                                      types,
                                      item_codes,
                                      batch,
                                      model,
                                      date,
                                      dyes)):
            # Westgardルールを評価
            westgard_rules = self.evaluate_rules(sd_conversion)

            # 結果の初期値を設定
            result = {
                'item_code': item_code,
                'batch': batch,
                'model': model,
                'date': date,
                'Type': qc_type,
                'Dye': dye,
                'Ct': value,
                'SD_conversion': sd_conversion,
                'judgment': 'Pass',
                'Error_type': None,  # エラータイプを初期化
                'Violated_rule': 'ー'  # 違反したルールを初期化
            }

            # Westgardルールの結果を追加
            result.update(westgard_rules)

            # タイプ固有のルールを適用
            error_type, error_type_message = self.apply_type_specific_rules(
                sd_conversion, qc_type)

            # タイプ固有のエラーがある場合
            if error_type:
                result['judgment'] = '不適'
                result['Error_type'] = error_type_message

            # Westgardルールまたはタイプ固有のエラーがある場合
            if any(westgard_rules.values()) or error_type:
                result['judgment'] = '不適'
                # 違反したルールを抽出
                error_rules = [rule for rule,
                               violated in westgard_rules.items() if violated]
                if error_type:
                    error_rules.append('Error_type')

                # エラータイプを設定
                if '1-3s' in error_rules or 'R-4s' in error_rules:
                    result['Error_type'] = "偶発誤差"
                elif ('2-2s' in error_rules or '4-1s' in error_rules or
                      '8x' in error_rules):
                    result['Error_type'] = "系統誤差"
                elif '1-2s' in error_rules:
                    result['Error_type'] = "注意"
                else:
                    result['Error_type'] = None

                # 違反したルールをカンマ区切りで結合
                result['Violated_rule'] = ', '.join(error_rules)

            # 結果をリストに追加
            results.append(result)

        # 結果をDataFrameに変換して返す
        return pd.DataFrame(results)

    def check_consecutive_violations(self,
                                     sd_conversions: List[float],
                                     n_consecutive: int,
                                     sd_limit: float) -> bool:
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
            consecutive_values = sd_conversions[i:i + n_consecutive]

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
