"""品質チェック"""

# Streamlitの設定を最初に配置
import streamlit as st
st.set_page_config(page_title="QCチェック", layout="wide")
# 他のインポートはその後に配置
import asyncio
from src.utils.file_processing import QCDataApp
from src.config import Config
from src.database.connection import (
    get_db_connection,
    check_duplicate_records,
    import_to_database
)


async def run_qc_check():
    """品質チェックを実行する関数"""
    try:
        # ファイル処理の実行
        app = QCDataApp()
        processed_data = await app.run()

        if processed_data:
            # データベースに取り込むデータの確認表示
            st.write("### データベース取り込み前の確認")
            
            # File Information
            st.write("#### ファイル情報")
            st.dataframe(processed_data.file_info, use_container_width=True)
            
            # IC Data
            if not processed_data.ic_data.empty:
                st.write("#### ICデータ")
                st.dataframe(processed_data.ic_data, use_container_width=True)
            
            # NC Data
            if not processed_data.nc_data.empty:
                st.write("#### NCデータ")
                st.dataframe(processed_data.nc_data, use_container_width=True)
            
            # PC Data
            if not processed_data.pc_data.empty:
                st.write("#### PCデータ")
                st.dataframe(processed_data.pc_data, use_container_width=True)

            # ボタンの表示
            col1, col2 = st.columns(2)
            with col1:
                if st.button("データベースに保存"):
                    try:
                        async with get_db_connection(Config.DATABASE_PATH) as conn:
                            await import_to_database(
                                processed_data.file_info,
                                processed_data.ic_data,
                                processed_data.nc_data,
                                processed_data.pc_data
                            )
                            st.success("データベースへの保存が完了しました")
                    except Exception as e:
                        st.error(f"データベース保存中にエラーが発生しました: {str(e)}")

            with col2:
                if st.button("重複チェック"):
                    if processed_data.file_info is not None:
                        try:
                            async with get_db_connection(Config.DATABASE_PATH) as conn:
                                is_duplicate = await check_duplicate_records(
                                    conn,
                                    'file_info',
                                    processed_data.file_info
                                )
                                if is_duplicate:
                                    st.warning("重複するレコードが存在します")
                                else:
                                    st.success("重複するレコードは存在しません")
                        except Exception as e:
                            st.error(f"重複チェック中にエラーが発生しました: {str(e)}")
                    else:
                        st.error("ファイル情報が存在しません")

    except (ValueError, TypeError) as e:
        st.error(f"エラーが発生しました: {str(e)}")
        return None
    except RuntimeError as e:
        st.error(f"予期せぬエラーが発生しました: {str(e)}")
        return None
    except Exception as e:
        st.error(f"不明なエラーが発生しました: {str(e)}")
        return None


if __name__ == "__main__":
    asyncio.run(run_qc_check())
