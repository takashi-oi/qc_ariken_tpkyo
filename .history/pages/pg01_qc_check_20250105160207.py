"""品質チェック"""

# Streamlitの設定を最初に配置
import streamlit as st
st.set_page_config(page_title="QCチェック", layout="wide")

import asyncio
from src.utils.file_processing import QCDataApp
from src.database.connection import check_duplicate_entry


async def run_qc_check():
    """品質チェックを実行する関数"""
    try:
        # ファイル処理の実行
        app = QCDataApp()
        # QCDataAppのインスタンスを作成し、runメソッドを実行
        await app.run()
        return None

    except (ValueError, TypeError) as e:
        st.error(f"エラーが発生しました: {str(e)}")
        return None
    except RuntimeError as e:
        st.error(f"予期せぬエラーが発生しました: {str(e)}")
        return None
    except Exception as e:
        st.error(f"不明なエラーが発生しました: {str(e)}")
        return None


if st.button("データベースにインポート"):
    Date_Time = st.session_state.get('Date_Time', '')
    Batch = st.session_state.get('Batch', '')
    Item_Code = st.session_state.get('Item_Code', '')

    if Date_Time and Batch and Item_Code:
        is_duplicate = check_duplicate_entry(Date_Time, Batch, Item_Code)
        if is_duplicate:
            st.warning("重複するレコードが存在します")
        else:
            st.success("重複するレコードは存在しません")
            # データベースにインポートする処理をここに追加
            # 例: await import_to_database(file_info, df_ic, df_nc, df_pc)
    else:
        st.error("日付、バッチ、品目コードを入力してください")


if __name__ == "__main__":
    asyncio.run(run_qc_check())
