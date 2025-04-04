import streamlit as st
from auth import login_form, logout_button


def main():
    st.set_page_config(
        page_title="MTG Commander Leaderboard",
        page_icon="🎲",
        layout="wide",
    )

    # Handle authentication
    if not login_form():
        st.stop()  # Don't proceed unless authenticated

    logout_button()

    st.title("MTG Commander Leaderboard")
    st.write("Welcome to the Commander leaderboard system!")


if __name__ == "__main__":
    main()
