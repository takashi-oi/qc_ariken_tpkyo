"""品質チェック"""

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
        print(f"エラーが発生しました: {str(e)}")
        return None
    except RuntimeError as e:
        print(f"予期せぬエラーが発生しました: {str(e)}")
        return None
    except Exception as e:
        print(f"不明なエラーが発生しました: {str(e)}")
        return None


async def check_duplicate_entry(Date_Time: str,
                                Batch: str,
                                Item_Code: str) -> bool:
    """重複チェック"""
    # データベースに接続
    is_duplicate = await check_duplicate_entry(Date_Time,
                                               Batch,
                                               Item_Code)
    
    return is_duplicate


if __name__ == "__main__":
    asyncio.run(run_qc_check())
