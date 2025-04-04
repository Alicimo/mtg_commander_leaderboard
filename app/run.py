import streamlit as st

from app.admin import show_admin_page
from app.auth import login_form, logout_button
from app.db import get_engine


def main():
    st.set_page_config(
        page_title="MTG Commander Leaderboard",
        page_icon="🎲",
        layout="wide",
    )

    # Handle authentication
    if not login_form():
        st.stop()  # Don't proceed unless authenticated

    engine = get_engine()

    if "admin" in st.query_params:
        show_admin_page(engine)
    else:
        logout_button()
        st.title("MTG Commander Leaderboard")
        st.write("Welcome to the Commander leaderboard system!")
        if st.button("Go to Admin Dashboard"):
            st.query_params["admin"] = True
            st.rerun()


if __name__ == "__main__":
    main()
