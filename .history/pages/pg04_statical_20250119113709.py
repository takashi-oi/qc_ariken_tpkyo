"""
統計学的精度管理　確認・台帳作成
"""

import calendar
from io import BytesIO
import sqlite3
import pandas as pd
import streamlit as st


# データベースからQCデータを読み込む
@st.cache_data  # Streamlitのキャッシュ機能を使用してデータの読み込みを高速化
def load_qc_data(implementation_date_time, conn):
    """データベースからQCデータを読み込んで処理する"""
    qc_data_query = f"""
    SELECT `Date_Time`, `Batch`, `Item_Code`, `Model`, `type`, `Lot Number`,
           `SD_Conversion`, `Ct`, `judgment`, `Error_type`, `Violated_rule`
    FROM table_qc_mulch_rule
    WHERE `Date_Time` <= '{implementation_date_time}'
    ORDER BY `Date_Time` DESC
    """
    df_qc_query = pd.read_sql_query(qc_data_query, conn)
    return df_qc_query.sort_values(['Date_Time', 'Batch'], ascending=True)


# 基本統計量を計算する関数
@st.cache_data
def calculate_statistics(df_qc_data):
    """Calculate basic statistics for QC data"""
    # マルチインデックスを作成 - CtとSD変換値それぞれに対して N,平均,標準偏差,変動係数を設定
    column_names = pd.MultiIndex.from_product([['Ct', 'SD_Conversion'],
                                               ['N', 'MEAN', 'STD', 'CV']])

    # ロット番号でグループ化してCtとSD変換値の基本統計量を計算
    grouped = df_qc_data.groupby('Lot Number')[['Ct', 'SD_Conversion']]
    # データ数、平均値、標準偏差を一括計算
    agg_stats = grouped.agg(['count', 'mean', 'std'])

    # 変動係数(CV)を計算 = 標準偏差/平均値
    cv = agg_stats.xs('std', axis=1, level=1) / agg_stats.xs(
        'mean', axis=1, level=1)

    # すべての統計量を1つのデータフレームに結合
    stats = pd.concat([
        agg_stats.xs('count', axis=1, level=1),  # データ数(N)
        agg_stats.xs('mean', axis=1, level=1),   # 平均値(MEAN)
        agg_stats.xs('std', axis=1, level=1),    # 標準偏差(STD)
        cv                                        # 変動係数(CV)
    ], axis=1, keys=['N', 'MEAN', 'STD', 'CV'])

    # 小数点以下3桁に丸める
    stats = stats.round(3)
    # 列名を設定
    stats.columns = column_names

    # 工程能力指数(Cp)の計算
    # UCL(上限管理限界)とLCL(下限管理限界)の差を計算してDataFrameを作成
    ucl_lcl = pd.DataFrame({
        # Ct値の管理幅を計算
        'Ct': (df_qc_data['UCL 1'].mean() - df_qc_data['LCL 1'].mean()),
        # SD変換値の管理幅を計算
        'SD_Conversion': (
            df_qc_data['UCL 2'].mean() - df_qc_data['LCL 2'].mean())
    })

    # 標準偏差の値を取得
    std_values = stats.xs('STD', axis=1, level=1)  # 統計量から標準偏差の列を抽出

    # Cp値を計算 (管理幅 / (6 × 標準偏差))して小数点以下3桁に丸める
    cp_values = (ucl_lcl / (std_values * 6)).round(3)

    # 計算したCp値を統計量のデータフレームに追加
    # Ct値のCp値を追加
    stats[('Ct', 'Cp')] = cp_values['Ct']
    # SD変換値のCp値を追加
    stats[('SD_Conversion', 'Cp')] = cp_values['SD_Conversion']

    # 完成した統計量のデータフレームを返す
    return stats


# Excelレポートを作成する関数
# キャッシュ機能を使用して高速化
@st.cache_data
def create_excel_report(dfs):
    """QCデータのExcelレポートを作成"""
    # バイトストリームを作成してメモリ上にExcelファイルを保存
    excel_buffer = BytesIO()

    # ExcelWriterでファイルを作成
    with pd.ExcelWriter(excel_buffer, engine='openpyxl', mode='w') as writer:
        # 各データフレームの書き込み設定をリストで定義
        write_tasks = [
            (dfs['basic_stats'], 'Sheet1', 25, 1),  # 基本統計量を25行目、B列から書き込み
            (dfs['qc_results'], 'Sheet1', 7, 0),    # QC結果を7行目、A列から書き込み
            (dfs['abnormal_records'], 'Sheet1', 32, 0),  # 異常記録を32行目、A列から書き込み
            (dfs['measurement_status'], 'Sheet1', 38, 1)  # 測定状況を38行目、B列から書き込み
        ]

        # 各データフレームをExcelファイルに書き込み
        for df, sheet, row, col in write_tasks:
            df.to_excel(writer, sheet_name=sheet, startrow=row, startcol=col)

    # 作成したExcelバッファを返す
    return excel_buffer


# メインの処理を行う関数
def main():
    """メイン関数"""
    # サイドバーとメイン画面にタイトルを表示
    st.sidebar.markdown('### 統計学的精度管理　確認・台帳作成')
    st.markdown('## 統計学的精度管理　確認・台帳作成')

    # サイドバーで年月を入力
    year = st.sidebar.text_input('西暦', placeholder='西暦をここに入力')
    month = st.sidebar.text_input('月', placeholder='月（MM）をここに入力')

    # 年月が入力された場合の処理
    if year and month:
        # 指定された年月の最終日を取得
        _, last_day = calendar.monthrange(int(year), int(month))
        implementation_date_time = f"{year}-{month.zfill(2)}-{last_day}"

        # データベースに接続してデータを取得
        with sqlite3.connect('db_folder/qc_data_base.db', timeout=30) as conn:
            conn.execute('PRAGMA journal_mode=WAL')  # データベースの書き込みモードを最適化
            conn.execute('PRAGMA cache_size=-2000')  # キャッシュサイズを増やして処理を高速化

            # QCデータを読み込み、基本統計量を計算
            df_qc_data = load_qc_data(implementation_date_time, conn)
            basic_stats = calculate_statistics(df_qc_data)
        # Excelレポートを作成
        excel_buffer = create_excel_report({
            'basic_stats': basic_stats,  # 基本統計量
            'qc_results': df_qc_data,    # QC結果
            'abnormal_records': pd.DataFrame(),  # 異常記録（空のデータフレーム）
            'measurement_status': pd.DataFrame()  # 測定状況（空のデータフレーム）
        }, month)

        # Excelファイルのダウンロードボタンを表示
        st.download_button(label="Excelファイルをダウンロード",
                           data=excel_buffer,
                           file_name=f"統計学的精度管理レポート_{year}_{month}.xlsx",
                           mime='application/vnd.openxmlformats-officedocument.\
                            spreadsheetml.sheet')


# メイン関数を実行
if __name__ == "__main__":
    main()
