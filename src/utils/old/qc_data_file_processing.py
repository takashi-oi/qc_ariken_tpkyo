"""QCデータファイル処理関連"""
import typing
import datetime
import pandas as pd
import streamlit as st

# ロガーのインポート
from src.config import global_logger as logger


# サイドバー入力の処理
def setup_sidebar():
    """サイドバー入力の処理"""
    measurer = st.sidebar.text_input(
        "測定者",
        placeholder="フルネームで登録して下さい"
    )

    if not measurer:
        st.error("測定者が登録されていません。")
        st.stop()

    uploaded_files = st.sidebar.file_uploader(
        "検査結果エクセルファイルをアップロードしてください",
        accept_multiple_files=True
    )
    if not uploaded_files:
        st.error("検査結果エクセルファイルがアップロードされていません。")
        st.stop()

    return measurer, uploaded_files


def get_file_info(file: typing.Any, measurer: str) -> pd.DataFrame:
    """アップロードされたファイルから情報を取得"""
    try:
        file_name = file.name
        if not file_name:
            logger.error("ファイル名が取得できません")
            return pd.DataFrame()

        # ファイル名から情報を抽出（エラーハンドリングを追加）
        try:
            parts = file_name.split('-')
            if len(parts) < 2:
                raise ValueError("ファイル名のフォーマットが不正です")

            item_code = parts[0][0]
            batch = parts[0][1]
            model = parts[0][3]

            # 日付部分の抽出を改善
            date_str = parts[1][:14]
            # YYYYMMDDHHMMSSの形式を想定
            date = datetime.datetime.strptime(date_str, "%Y%m%d%H%M%S")

            file_info = pd.DataFrame({
                "file_name": [file_name],
                "item_code": [item_code],
                "batch": [batch],
                "model": [model],
                "date": [date],
                "measurer": [measurer],
            })
            return file_info

        except (IndexError, ValueError) as e:
            logger.error("ファイル名の解析エラー - file: %s, error: %s",
                         file_name, str(e))
            st.error(f"ファイル名のフォーマットが不正です: {file_name}")
            return pd.DataFrame()

    except (AttributeError, TypeError) as e:
        logger.error("ファイル処理エラー - error: %s", str(e))
        st.error("ファイルの処理中にエラーが発生しました。")
        return pd.DataFrame()


def upload_files(files: typing.List[typing.Any],
                 file_info: pd.DataFrame) -> pd.DataFrame:
    """
    アップロードされたファイルからQCデータを読み込む

    Args:
        files: アップロードされたファイルのリスト
        file_info: ファイル情報のDataFrame

    Returns:
        pd.DataFrame: 読み込んだQCデータ
    """
    try:
        if not files or file_info.empty:
            return pd.DataFrame()

        # エクセルファイルを読み込む
        df = pd.read_excel(files[0])

        # ファイル情報をQCデータに結合
        result_df = pd.concat([
            pd.DataFrame([file_info.iloc[0].to_dict()] * len(df)),
            df
        ], axis=1)

        return result_df

    except Exception as e:
        logger.error("QCデータの読み込みエラー - error: %s", str(e))
        st.error("QCデータの読み込み中にエラーが発生しました。")
        return pd.DataFrame()


def main():
    """メイン処理"""
    measurer, uploaded_files = setup_sidebar()

    # アップロードされた各ファイルに対してfile_infoを取得
    for file in uploaded_files:
        file_info = get_file_info(file, measurer)

        # file_infoが空でない場合のみ表示
        if not file_info.empty:
            st.write(f"ファイル情報: {file.name}", file_info)

        # file_infoを追加してupload_filesを呼び出す
        qc_file_data = upload_files([file], file_info)

        # QCデータが存在する場合のみ表示
        if not qc_file_data.empty:
            st.write(f"QCデータ - {file.name}", qc_file_data)


# メイン処理
if __name__ == "__main__":
    main()
