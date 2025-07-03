"""Westgardマルチルールのモデル"""

import pandas as pd
import numpy as np


class WestgardMultiRule:
    """Westgardマルチルールのモデル"""
    def __init__(self, config):
        self.config = config

    def apply_rules(self,
                    ct_values,
                    sd_values,
                    lot_numbers,
                    types,
                    item_codes,
                    dates,
                    batches,
                    models):
        """
        Westgardマルチルールを適用するメソッド

        Args:
            ct_values (list): Ctの値のリスト
            sd_values (list): SD変換値のリスト
            lot_numbers (list): ロット番号のリスト
            types (list): タイプのリスト
            item_codes (list): アイテムコードのリスト
            dates (list): 日付のリスト
            batches (list): バッチのリスト
            models (list): モデルのリスト

        Returns:
            pd.DataFrame: マルチルール分析結果
        """
        results = pd.DataFrame({
            'Ct': ct_values,
            'SD_conversion': sd_values,
            'Lot Number': lot_numbers,
            'Type': types,
            'item_code': item_codes,
            'date': dates,
            'batch': batches,
            'model': models
        })

        # デフォルトの判定を追加
        results['judgment'] = 'OK'
        results['Error_type'] = ''
        results['Violated_rule'] = ''

        # 簡単な1-2s, 1-3sルールの例
        mean = np.mean(ct_values)
        std = np.std(ct_values)

        for i, (ct, sd_conversion) in enumerate(zip(ct_values, sd_values)):
            # 1-2sルールの適用
            if abs(ct - mean) > 2 * std:
                results.loc[i, 'judgment'] = 'NG'
                results.loc[i, 'Error_type'] = '1-2s違反'
                results.loc[i, 'Violated_rule'] = '1-2s'

            # 1-3sルールの適用
            if abs(ct - mean) > 3 * std:
                results.loc[i, 'judgment'] = 'NG'
                results.loc[i, 'Error_type'] = '1-3s違反'
                results.loc[i, 'Violated_rule'] = '1-3s'

            # 2-2sルールの適用
            if abs(ct - mean) > 2 * std:
                results.loc[i, 'judgment'] = 'NG'
                results.loc[i, 'Error_type'] = '2-2s違反'
                results.loc[i, 'Violated_rule'] = '2-2s'

            # R-4sルールの適用
            if abs(ct - mean) > 4 * std:
                results.loc[i, 'judgment'] = 'NG'
                results.loc[i, 'Error_type'] = 'R-4s違反'
                results.loc[i, 'Violated_rule'] = 'R-4s'
                

        # 追加のルールを必要に応じて実装
        results['1-2s'] = np.where(abs(results['Ct'] - mean) > 2 * std, 1, 0)
        results['1-3s'] = np.where(abs(results['Ct'] - mean) > 3 * std, 1, 0)
        results['2-2s'] = 0  # 実際の実装では複雑になります
        results['R-4s'] = 0
        results['4-1s'] = 0
        results['8x'] = 0

        return results
