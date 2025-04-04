import sqlalchemy as sa
import streamlit as st

from app.auth import logout_button


def show_admin_page(engine: sa.engine.Engine) -> None:
    """Render the admin interface."""
    st.title("Admin Dashboard")
    logout_button()

    tab1, tab2 = st.tabs(["Manage Players", "View All Players"])

    with tab1:
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

        st.header("Delete Player")
        with st.form("delete_player"):
            with engine.connect() as conn:
                players = conn.execute(
                    sa.text("SELECT id, name FROM players")
                ).fetchall()

            if not players:
                st.warning("No players to delete")
            else:
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

    with tab2:
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
