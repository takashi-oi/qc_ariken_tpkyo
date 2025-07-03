"""品質チェック"""

import asyncio
import streamlit as st
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
        print(f"エラーが発生しました: {str(e)}")
        return None
    except RuntimeError as e:
        print(f"予期せぬエラーが発生しました: {str(e)}")
        return None
    except Exception as e:
        print(f"不明なエラーが発生しました: {str(e)}")
        return None


    if st.button("重複チェック"):
        check_duplicate_entry()
    
if __name__ == "__main__":
    asyncio.run(run_qc_check())
