"""品質チェック"""

import asyncio
from src.utils.file_processing import QCDataApp


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


if __name__ == "__main__":
    asyncio.run(run_qc_check())
