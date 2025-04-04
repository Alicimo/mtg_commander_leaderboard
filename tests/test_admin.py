import pytest
import sqlalchemy as sa
from unittest.mock import patch, MagicMock

from app.db import get_engine, init_db
from app.admin import show_admin_page


@pytest.fixture
def test_db():
    """Fixture to initialize test database."""
    engine = get_engine()
    init_db(engine)
    yield engine
    # Cleanup
    engine.dispose()
    import os
    if os.path.exists("data/commander.db"):
        os.remove("data/commander.db")


def test_add_player(test_db):
    """Test adding a new player."""
    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.text_input", return_value="Test Player"):
            with patch("streamlit.success") as mock_success:
                show_admin_page(test_db)
                mock_success.assert_called_once_with("Added player: Test Player")

    # Verify player was added
    with test_db.connect() as conn:
        result = conn.execute(sa.text("SELECT name FROM players")).scalar()
        assert result == "Test Player"


def test_duplicate_player(test_db):
    """Test duplicate player prevention."""
    # Add initial player
    with test_db.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES ('Test Player', 1000)")
        )

    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.text_input", return_value="Test Player"):
            with patch("streamlit.error") as mock_error:
                show_admin_page(test_db)
                mock_error.assert_called_once_with("Player 'Test Player' already exists")


def test_delete_player(test_db):
    """Test player deletion."""
    # Add test player
    with test_db.begin() as conn:
        conn.execute(
            sa.text("INSERT INTO players (name, elo) VALUES ('Test Player', 1000)")
        )

    with patch("streamlit.form_submit_button", return_value=True):
        with patch("streamlit.selectbox", return_value="Test Player (ID: 1)"):
            with patch("streamlit.checkbox", return_value=True):
                with patch("streamlit.success") as mock_success:
                    show_admin_page(test_db)
                    mock_success.assert_called_once_with("Deleted player: Test Player (ID: 1)")

    # Verify player was deleted
    with test_db.connect() as conn:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM players")).scalar()
        assert result == 0
