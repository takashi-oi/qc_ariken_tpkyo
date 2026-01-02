import streamlit as st


def render_kpi_cards(kpi_data):
    """ダッシュボードのKPIカードを表示"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("総在庫数", kpi_data.get("total_stock", 0))

    with col2:
        val = kpi_data.get("near_expiry_count", 0)
        st.metric(
            "期限切れ間近 (30日以内)",
            val,
            delta=-val if val > 0 else None,
            delta_color="inverse",
        )

    with col3:
        val = kpi_data.get("expired_count", 0)
        st.metric(
            "期限切れ", val, delta=-val if val > 0 else None, delta_color="inverse"
        )


def show_success_message(message):
    st.success(message)


def show_error_message(message):
    st.error(message)


def show_warning_message(message):
    st.warning(message)
