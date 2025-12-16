"""
QCメインアプリケーションモジュール
"""

import pandas as pd
import streamlit as st

from src.data_import.data_importer import DataImporter
from src.utils.file_processing import ProcessedData
from src.utils.master_loader import MasterDataLoader

from .qc_database import QCDatabase
from .qc_display import QCDisplay
from .qc_westgard import QCWestgard


class QCCheckApp:
    """品質チェックアプリケーションクラス"""

    def __init__(self):
        self.data_importer = DataImporter()
        self.display = QCDisplay()
        self.database = QCDatabase()
        self.westgard = QCWestgard()

    async def run(self) -> None:
        """アプリケーションのメイン実行関数"""
        async with self.database.error_handler():
            with st.sidebar:  # type: ignore[attr-defined]
                uploaded_file = st.file_uploader(
                    "QCデータファイルをアップロード", type=["xlsx"]
                )

                employee_data = MasterDataLoader.load_employee_data()
                measurer_list = [""] + employee_data["Member's_Name"].tolist()
                measurer = st.selectbox("測定者名を選択", measurer_list, index=0)

            if uploaded_file and measurer and measurer != "":
                qc_data = await self.data_importer.process_and_display(
                    uploaded_file, measurer
                )
                if (
                    qc_data
                    and isinstance(qc_data.file_info, pd.DataFrame)
                    and not qc_data.file_info.empty
                ):
                    st.write("### IC、NC、PCのデータの確認")
                    data = ProcessedData(
                        file_info=qc_data.file_info,
                        ic_data=qc_data.ic_data,
                        nc_data=qc_data.nc_data,
                        pc_data=qc_data.pc_data,
                    )
                    await self.display.display_data_summary(data)
                    await self.display.display_detailed_data(data)
                    await self.database.handle_database_operations(data)
                else:
                    st.warning("有効なデータが読み込まれていません")
            else:
                st.info("ファイルと測定者名の両方を入力してください")
