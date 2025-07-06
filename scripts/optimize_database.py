#!/usr/bin/env python3
"""データベース最適化スクリプト"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from src.config import Config
from src.database.optimized_tables import create_optimized_database


def main():
    """データベース最適化のメイン処理"""
    st.title("データベース最適化ツール")

    st.markdown(
        """
    ## 最適化内容

    ### 1. テーブル構造の正規化
    - 重複するカラム構造を統合
    - 外部キー制約の追加
    - データ型の最適化

    ### 2. インデックスの追加
    - 検索パフォーマンス向上
    - 複合インデックスの作成

    ### 3. データ移行
    - 既存データの新しい構造への移行
    - データ整合性の確保
    """
    )

    if st.button("最適化を実行"):
        try:
            # データベースパスの設定
            db_path = Config.DATABASE_PATH

            st.info("最適化されたデータベース構造を作成中...")

            # 最適化されたデータベースマネージャーを作成
            optimized_db = create_optimized_database(db_path)

            st.success("✅ 最適化されたテーブル構造が作成されました")

            st.info("既存データの移行を開始中...")

            # 既存データの移行
            optimized_db.migrate_existing_data()

            st.success("✅ データ移行が完了しました")

            # 最適化統計の表示
            stats = optimized_db.get_optimization_stats()

            st.markdown("## 最適化結果")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### テーブル統計")
                for key, value in stats.items():
                    if key.endswith("_count"):
                        table_name = key.replace("_count", "")
                        st.write(f"{table_name}: {value} レコード")

            with col2:
                st.markdown("### インデックス情報")
                st.write(f"作成されたインデックス数: {stats['index_count']}")
                st.write("インデックス一覧:")
                for index in stats["indexes"]:
                    st.write(f"- {index}")

            st.success("🎉 データベース最適化が完了しました！")

        except Exception as e:
            st.error(f"最適化中にエラーが発生しました: {str(e)}")
            st.exception(e)


if __name__ == "__main__":
    main()
