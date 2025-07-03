"""
QC_Wsdtgard multi Rule
"""
import numpy as np
from typing import List, Dict, Any, Optional
import pandas as pd


class WestgardMultiRule:
    """Westgardマルチルール分析を実行するクラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: 設定パラメータを含む辞書
        """
        self.config = config

    def apply_rules(
        self,
        values: List[float],
        sd_values: List[float],
        lot_numbers: List[str],
        types: List[str],
        item_codes: List[str],
        dates: List[str],
        batches: List[str],
        models: List[str]
    ) -> pd.DataFrame:
        """
        Westgardマルチルールを適用する

        Args:
            values: 測定値のリスト
            sd_values: 標準偏差値のリスト
            lot_numbers: ロット番号のリスト
            types: タイプのリスト
            item_codes: 品目コードのリスト
            dates: 日付のリスト
            batches: バッチ番号のリスト
            models: モデル名のリスト

        Returns:
            pd.DataFrame: 分析結果を含むDataFrame
        """
        results = []
        n = len(values)

        for i in range(n):
            result = {
                'date': dates[i],
                'batch': batches[i],
                'model': models[i],
                'Type': types[i],
                'Lot Number': lot_numbers[i],
                'item_code': item_codes[i],
                'sd_conversion': sd_values[i],
                'violations': []
            }

            # 1-2s ルール
            if abs(sd_values[i]) > 2:
                result['violations'].append('1-2s')

            # 1-3s ルール
            if abs(sd_values[i]) > 3:
                result['violations'].append('1-3s')

            # 2-2s ルール
            if i > 0 and abs(sd_values[i]) > 2 and abs(sd_values[i-1]) > 2:
                result['violations'].append('2-2s')

            # R-4s ルール
            if i > 0 and abs(sd_values[i] - sd_values[i-1]) > 4:
                result['violations'].append('R-4s')

            # 4-1s ルール
            if i > 2:
                if all(abs(x) > 1 for x in sd_values[i-3:i+1]):
                    result['violations'].append('4-1s')

            # 10x ルール
            if i > 8:
                if all(x > 0 for x in sd_values[i-9:i+1]) or \
                   all(x < 0 for x in sd_values[i-9:i+1]):
                    result['violations'].append('10x')

            results.append(result)

        return pd.DataFrame(results)
