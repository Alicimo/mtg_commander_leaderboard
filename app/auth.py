import os
import time
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_password() -> Optional[str]:
    """Get password from environment or Streamlit secrets."""
    try:
        return os.getenv("COMMANDER_PASSWORD") or st.secrets["COMMANDER_PASSWORD"]
    except (AttributeError, KeyError):
        return None

def check_password(password: str) -> bool:
    """Securely compare input password with stored password."""
    stored_pw = get_password()
    if not stored_pw:
        st.error("Password not configured")
        return False
    
    # Use constant-time comparison to prevent timing attacks
    if len(password) != len(stored_pw):
        return False
    result = 0
    for a, b in zip(password, stored_pw):
        result |= ord(a) ^ ord(b)
    return result == 0

def init_session() -> None:
    """Initialize session state for authentication."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "login_time" not in st.session_state:
        st.session_state.login_time = 0

def is_session_valid() -> bool:
    """Check if session is still valid (8 hour lifetime)."""
    if not st.session_state.get("authenticated"):
        return False
    return time.time() - st.session_state.login_time < 8 * 3600

def login_form() -> bool:
    """Render login form and handle authentication."""
    init_session()
    
    if is_session_valid():
        return True

    with st.form("login"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if check_password(password):
                st.session_state.authenticated = True
                st.session_state.login_time = time.time()
                st.rerun()
            else:
                st.error("Incorrect password")
    
    return False

def logout_button() -> None:
    """Render logout button in sidebar."""
    if st.session_state.get("authenticated"):
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.login_time = 0
            st.rerun()
