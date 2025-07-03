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

        # 重複チェックボタンを表示
        if st.button("重複チェックを実行"):
            # 必要な引数を取得（例として固定値を使用）
            Date_Time = "2023-10-01 12:00:00"  # 実際の値に置き換えてください
            Batch = "Batch001"  # 実際の値に置き換えてください
            Item_Code = "Item001"  # 実際の値に置き換えてください
            
            is_duplicate = await check_duplicate_entry(Date_Time, Batch, Item_Code)
            if is_duplicate:
                st.warning("重複するレコードが存在します。")
            else:
                st.success("重複するレコードは存在しません。")

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
    # ボタンをクリックして実行
    conn = await get_db_connection()
    is_duplicate = await check_duplicate_records(conn,
                                                 Date_Time,
                                                 Batch,
                                                 Item_Code)
    # データベースに接続を閉じる
    await conn.close()
    return is_duplicate


if __name__ == "__main__":
    asyncio.run(run_qc_check())
