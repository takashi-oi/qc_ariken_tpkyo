from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from src.reagent_db import ReagentDatabaseManager
from src.reagent_ui_components import (
    render_kpi_cards,
    show_error_message,
    show_success_message,
    show_warning_message,
)

# Initialize DB Manager
db = ReagentDatabaseManager()


def main():
    st.set_page_config(layout="wide")
    st.title("検査資材・試薬管理システム")

    # --- Sidebar Navigation ---
    st.sidebar.title("メニュー")
    menu = st.sidebar.radio(
        "画面切替",
        [
            "ダッシュボード",
            "発注登録",
            "納品登録",
            "使用登録",  # 出庫・開封
            "在庫一覧",
            "有効期限アラート",
            "マスタ管理",
            "ログ・履歴",
        ],
    )

    if menu == "ダッシュボード":
        show_dashboard()
    elif menu == "発注登録":
        show_order_page()
    elif menu == "納品登録":
        show_delivery_page()
    elif menu == "使用登録":
        show_usage_page()
    elif menu == "在庫一覧":
        show_stock_list()
    elif menu == "有効期限アラート":
        show_alerts_page()
    elif menu == "マスタ管理":
        show_master_page()
    elif menu == "ログ・履歴":
        show_logs_page()


# --- Page Functions ---


def show_dashboard():
    st.header("ダッシュボード")
    kpi_data = db.get_kpi_data()
    render_kpi_cards(kpi_data)

    st.subheader("有効期限アラート（30日以内）")
    stock_df = db.get_active_stock()
    if not stock_df.empty:
        today = datetime.now().date()
        date_30d = today + timedelta(days=30)
        stock_df["expiry_date"] = pd.to_datetime(stock_df["expiry_date"]).dt.date

        # expiry_date is nullable in DB but logically should be there effectively for reagents that expire.
        # Check if null handling is needed? Assuming yes for now.
        near_expiry = stock_df[
            (stock_df["expiry_date"].notna()) & (stock_df["expiry_date"] <= date_30d)
        ]

        if not near_expiry.empty:
            st.dataframe(
                near_expiry[
                    ["reagent_name", "lot_no", "current_quantity", "expiry_date"]
                ]
            )
        else:
            st.info("期限切れ間近の在庫はありません")
    else:
        st.info("在庫がありません")

    st.subheader("在庫状況")
    if not stock_df.empty:
        chart_data = (
            stock_df.groupby("reagent_name")["current_quantity"].sum().reset_index()
        )
        st.bar_chart(chart_data, x="reagent_name", y="current_quantity")


def show_order_page():
    st.header("発注登録")

    reagents = db.get_all_reagents(active_only=True)
    if reagents.empty:
        st.warning(
            "マスタに登録された試薬がありません。先にマスタ登録を行ってください。"
        )
        return

    with st.form("order_form"):
        col1, col2 = st.columns(2)
        with col1:
            order_date = st.date_input("発注日", value=datetime.now())
            reagent_name = st.selectbox("資材名", reagents["name"].tolist())
        with col2:
            quantity = st.number_input("発注数量", min_value=1, value=1)
            requester = st.text_input(
                "実施者ID"
            )  # Using text input for ID as requested

        submitted = st.form_submit_button("発注登録")

        if submitted:
            if not requester:
                show_error_message("実施者IDを入力してください")
            else:
                r_id = reagents[reagents["name"] == reagent_name].iloc[0]["id"]
                try:
                    db.create_order(r_id, order_date, quantity, requester)
                    db.add_log(
                        "ORDER", r_id, None, quantity, requester, f"Order registered"
                    )
                    show_success_message("発注を登録しました")
                except Exception as e:
                    show_error_message(f"登録エラー: {e}")

    st.subheader("発注履歴（未納品）")
    pending = db.get_pending_orders()
    if not pending.empty:
        st.dataframe(pending)
    else:
        st.info("未納品の発注はありません")


def show_delivery_page():
    st.header("納品登録")

    pending = db.get_pending_orders()
    if pending.empty:
        st.info("未納品の発注はありません")
        return

    # Select pending order
    order_options = pending.apply(
        lambda x: f"ID:{x['id']} | {x['reagent_name']} | {x['quantity']}個 | {x['order_date']}",
        axis=1,
    ).tolist()
    selected_order_str = st.selectbox("納品対象の発注を選択", order_options)

    if selected_order_str:
        order_id = int(selected_order_str.split("|")[0].replace("ID:", "").strip())
        order_data = pending[pending["id"] == order_id].iloc[0]

        with st.form("delivery_form"):
            st.info(
                f"対象: {order_data['reagent_name']} (発注数: {order_data['quantity']})"
            )

            col1, col2 = st.columns(2)
            with col1:
                delivery_date = st.date_input("納品日", value=datetime.now())
                lot_no = st.text_input("Lot No.")
            with col2:
                # Default to order quantity but allow change (partial delivery not handled in detail in spec, assuming full for now or as is)
                qty = st.number_input(
                    "納品数量", min_value=1, value=int(order_data["quantity"])
                )
                operator = st.text_input("実施者ID")

            has_expiry = st.checkbox("有効期限あり", value=True)
            expiry_date = None
            if has_expiry:
                expiry_date = st.date_input("有効期限")

            note = st.text_area("納品時状態 / メーカー指示")

            submitted = st.form_submit_button("納品登録")

            if submitted:
                if not lot_no or not operator:
                    show_error_message("Lot No.と実施者IDは必須です")
                elif has_expiry and not expiry_date:
                    show_error_message(
                        "有効期限を入力してください"
                    )  # Validation check for expiry
                else:
                    try:
                        db.add_stock(
                            lot_no,
                            order_data["reagent_id"],
                            expiry_date,
                            qty,
                            delivery_date,
                        )
                        db.mark_order_delivered(order_id)
                        db.add_log(
                            "DELIVER",
                            order_data["reagent_id"],
                            lot_no,
                            qty,
                            operator,
                            f"Delivery: {note}",
                        )
                        show_success_message("納品を登録しました")
                        st.rerun()
                    except Exception as e:
                        show_error_message(f"登録エラー: {e}")


def show_usage_page():
    st.header("使用登録 (出庫・開封)")

    stock_df = db.get_active_stock()
    if stock_df.empty:
        st.warning("在庫がありません")
        return

    reagents = stock_df["reagent_name"].unique().tolist()
    selected_reagent = st.selectbox("資材選択", reagents)

    # Filter lots by selected reagent
    reagent_stock = stock_df[stock_df["reagent_name"] == selected_reagent]

    # Create Lot selection options
    lot_options = reagent_stock.apply(
        lambda x: f"{x['lot_no']} (残: {x['current_quantity']}, 期限: {x['expiry_date']})",
        axis=1,
    ).tolist()
    selected_lot_str = st.selectbox("Lot選択", lot_options)

    if selected_lot_str:
        lot_no = selected_lot_str.split(" (")[0]
        current_lot_data = reagent_stock[reagent_stock["lot_no"] == lot_no].iloc[0]

        with st.form("usage_form"):
            st.info(f"現在在庫: {current_lot_data['current_quantity']}")
            usage_type = st.radio("使用区分", ["使用", "出庫"])

            col1, col2 = st.columns(2)
            with col1:
                use_date = st.date_input("使用日", value=datetime.now())
                use_qty = st.number_input(
                    "数量",
                    min_value=1,
                    max_value=int(current_lot_data["current_quantity"]),
                    value=1,
                )
            with col2:
                operator = st.text_input("実施者ID")

            # Realtime calc preview
            new_qty = current_lot_data["current_quantity"] - use_qty
            st.metric("使用後残数", new_qty)

            if (
                current_lot_data["expiry_date"]
                and pd.to_datetime(current_lot_data["expiry_date"]).date()
                < datetime.now().date()
            ):
                st.warning("⚠️ このLotは有効期限が切れています！")

            submitted = st.form_submit_button("登録確定")

            if submitted:
                if not operator:
                    show_error_message("実施者IDを入力してください")
                else:
                    try:
                        db.update_stock_quantity(
                            lot_no, current_lot_data["reagent_id"], use_qty
                        )
                        db.add_log(
                            "USE",
                            current_lot_data["reagent_id"],
                            lot_no,
                            use_qty,
                            operator,
                            f"Type: {usage_type}",
                        )
                        show_success_message("使用を登録しました")
                        st.rerun()
                    except Exception as e:
                        show_error_message(f"登録エラー: {e}")


def show_stock_list():
    st.header("在庫一覧")

    stock_df = db.get_active_stock()

    # Filter
    reagents = (
        ["All"] + list(stock_df["reagent_name"].unique())
        if not stock_df.empty
        else ["All"]
    )
    filter_reagent = st.selectbox("資材フィルタ", reagents)

    display_df = stock_df.copy()
    if filter_reagent != "All":
        display_df = display_df[display_df["reagent_name"] == filter_reagent]

    # Status coloring logic could be applied here or just basic display
    st.dataframe(display_df)

    # CSV Download
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "CSVダウンロード", csv, "stock_list.csv", "text/csv", key="download-csv"
    )


def show_alerts_page():
    st.header("有効期限アラート")

    stock_df = db.get_active_stock()
    if stock_df.empty:
        st.info("在庫なし")
        return

    stock_df["expiry_date"] = pd.to_datetime(stock_df["expiry_date"])
    today = datetime.now()

    expired = stock_df[stock_df["expiry_date"] < today]
    near = stock_df[
        (stock_df["expiry_date"] >= today)
        & (stock_df["expiry_date"] <= today + timedelta(days=30))
    ]

    st.subheader("❌ 期限切れ")
    if not expired.empty:
        st.error(f"{len(expired)}件の期限切れ在庫があります")
        st.dataframe(expired)
    else:
        st.success("期限切れ在庫はありません")

    st.subheader("⚠️ 30日以内")
    if not near.empty:
        st.warning(f"{len(near)}件の期限間近在庫があります")
        st.dataframe(near)
    else:
        st.success("期限間近在庫はありません")


def show_master_page():
    st.header("マスタ管理")

    st.subheader("資材登録・編集")
    with st.form("master_form"):
        col1, col2 = st.columns(2)
        with col1:
            r_id = st.text_input("資材コード")
            name = st.text_input("資材名")
        with col2:
            group = st.text_input("検査グループ")
            limit = st.number_input("基準在庫数", min_value=0, value=0)

        submitted = st.form_submit_button("登録 / 更新")

        if submitted:
            if not r_id or not name:
                show_error_message("資材コードと資材名は必須です")
            else:
                try:
                    db.upsert_reagent(r_id, name, group, limit)
                    db.add_log(
                        "UPDATE_MASTER", r_id, None, None, "ADMIN", f"Upserted {name}"
                    )
                    show_success_message("マスタを更新しました")
                except Exception as e:
                    show_error_message(f"DB Error: {e}")

    st.subheader("登録済み資材一覧")
    current = db.get_all_reagents(active_only=False)
    st.dataframe(current)


def show_logs_page():
    st.header("ログ・履歴")
    limit = st.selectbox("表示件数", [100, 500, 1000], index=0)
    logs = db.get_logs(limit)
    st.dataframe(logs)


if __name__ == "__main__":
    main()
