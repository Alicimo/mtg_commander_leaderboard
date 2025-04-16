import datetime

import sqlalchemy as sa
import streamlit as st

from app.auth import logout_button
from app.db import DB_PATH, backup_sqlite_db, export_db_to_json


def show_admin_page(engine: sa.engine.Engine) -> None:
    """Render the admin interface."""
    st.title("Admin Dashboard")
    logout_button()

    tab_manage, tab_view, tab_export = st.tabs(
        ["Manage Players", "View All Players", "Data Export"]
    )

    with tab_manage:
        form_add_player(engine)
        form_delete_player(engine)

    with tab_view:
        tab_list_players(engine)

    with tab_export:
        tab_data_export(engine)


def tab_list_players(engine):
    st.header("All Players")
    with engine.connect() as conn:
        players = conn.execute(
            sa.text("SELECT id, name, elo FROM players ORDER BY elo DESC")
        ).fetchall()
    if not players:
        st.info("No players yet")
    else:
        st.dataframe(
            players,
            column_config={
                "id": "ID",
                "name": "Name",
                "elo": "ELO",
            },
            hide_index=True,
            use_container_width=True,
        )


def form_delete_player(engine):
    with engine.connect() as conn:
        players = conn.execute(sa.text("SELECT id, name FROM players")).fetchall()
    if players:
        st.header("Delete Player")
        with st.form("delete_player"):
            player_options = {f"{p.name} (ID: {p.id})": p.id for p in players}
            selected = st.selectbox(
                "Select player to delete",
                options=list(player_options.keys()),
                key="delete_player_select",
            )
            submitted = st.form_submit_button("Delete Player")
            if submitted:
                player_id = player_options[selected]
                confirm = st.checkbox(
                    f"Confirm deletion of {selected} and all their game records",
                    key=f"confirm_delete_{player_id}",
                )
                if confirm:
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                sa.text("DELETE FROM players WHERE id = :id"),
                                {"id": player_id},
                            )
                        st.success(f"Deleted player: {selected}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting player: {e}")


def form_add_player(engine):
    st.header("Add New Player")
    with st.form("add_player"):
        name = st.text_input("Player Name", max_chars=100)
        submitted = st.form_submit_button("Add Player")
        if submitted:
            if not name:
                st.error("Player name cannot be empty")
            else:
                try:
                    with engine.begin() as conn:
                        conn.execute(
                            sa.text(
                                "INSERT INTO players (name, elo) VALUES (:name, 1000)"
                            ),
                            {"name": name},
                        )
                    st.success(f"Added player: {name}")
                except sa.exc.IntegrityError:
                    st.error(f"Player '{name}' already exists")
                except Exception as e:
                    st.error(f"Error adding player: {e}")


def tab_data_export(engine: sa.engine.Engine):
    """Render the data export tab."""
    st.header("Export Data")

    st.subheader("SQLite Backup")
    st.write(f"Current database file: `{DB_PATH}`")
    if st.button("Create SQLite Backup"):
        try:
            backup_path = backup_sqlite_db()
            st.success(f"SQLite database backed up to: `{backup_path}`")
            with open(backup_path, "rb") as fp:
                st.download_button(
                    label="Download SQLite Backup",
                    data=fp,
                    file_name=backup_path.name,
                    mime="application/vnd.sqlite3",
                )
        except Exception as e:
            st.error(f"Failed to create SQLite backup: {e}")

    st.divider()

    st.subheader("JSON Export")
    st.write("Export all tables to a single JSON file.")
    if st.button("Generate JSON Export"):
        try:
            json_data = export_db_to_json(engine)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"commander_export_{timestamp}.json"
            st.success("JSON data generated successfully.")
            st.download_button(
                label="Download JSON Export",
                data=json_data,
                file_name=file_name,
                mime="application/json",
            )
        except Exception as e:
            st.error(f"Failed to generate JSON export: {e}")
