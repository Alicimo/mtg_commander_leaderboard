from unittest.mock import patch

import pytest
import streamlit as st

from app.auth import (
    check_password,
    get_password,
    init_session,
    is_session_valid,
    login_form,
    logout_button,
)


@pytest.fixture
def mock_env_password(monkeypatch):
    monkeypatch.setenv("COMMANDER_PASSWORD", "test123")


@pytest.fixture
def mock_secrets_password(monkeypatch):
    # Mock the entire secrets module
    mock_secrets = {"COMMANDER_PASSWORD": "test123"}
    monkeypatch.setattr(st, "secrets", mock_secrets)
    monkeypatch.setenv("COMMANDER_PASSWORD", "")


def test_get_password_env(mock_env_password):
    assert get_password() == "test123"


def test_get_password_secrets(mock_secrets_password):
    assert get_password() == "test123"


def test_check_password_correct(mock_env_password):
    assert check_password("test123") is True


def test_check_password_incorrect(mock_env_password):
    assert check_password("wrong") is False


def test_init_session():
    init_session()
    assert st.session_state.authenticated is False
    assert st.session_state.login_time == 0


def test_is_session_valid():
    st.session_state.authenticated = True
    st.session_state.login_time = 0  # Very old session
    assert is_session_valid() is False


def test_login_form_success(mock_env_password):
    init_session()  # Reset session state
    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.text_input", return_value="test123"):
            with patch("streamlit.error") as mock_error:
                result = login_form()
                assert result is True
                assert st.session_state.authenticated is True
                mock_error.assert_not_called()


def test_login_form_failure(mock_env_password):
    init_session()  # Reset session state
    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.text_input", return_value="wrong"):
            with patch("streamlit.error") as mock_error:
                result = login_form()
                assert result is False
                assert st.session_state.authenticated is False
                mock_error.assert_called_once()


def test_logout_button():
    st.session_state.authenticated = True
    with patch("streamlit.sidebar.button", return_value=True):
        logout_button()
        assert st.session_state.authenticated is False
