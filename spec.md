# **Magic: The Gathering Commander Leaderboard - Technical Specification**
**Version:** 1.0
**Last Updated:** [Today's Date]

---

## **1. Overview**
A **password-protected Streamlit app** for tracking Commander games among a closed group, featuring:
- **Leaderboards** (player-only and player+commander ELO rankings).
- **Game history** with pagination.
- **Player-specific stats**, including matchup analysis and ELO trends.
- **Admin tools** for managing players and backups.

---

## **2. Technical Stack**
- **Frontend/Backend:** Streamlit (Python).
- **Data Storage:** SQLite (local file) + manual JSON/CSV export for backups.
- **APIs:** Scryfall (for commander autocomplete).
- **Hosting:** TBD (compatible with Streamlit Cloud, Hugging Face, or VPS).

---

## **3. Detailed Requirements**

### **3.1 Authentication & Access**
- Single password (hardcoded or env variable) to access the app.
- No user accounts; all submissions are anonymous.

### **3.2 Admin Interface**
- **Password-protected page** (`/admin`):
  - **Add/remove players** (predefined list stored in SQLite).
  - **Export data** (button to download SQLite/JSON backup).

### **3.3 Game Submission**
- **Form fields (validated):**
  - `Date`: Prefilled to today, editable (YYYY-MM-DD).
  - `Players`: Multi-select dropdown (predefined list).
  - `Commanders`: Dropdown per player:
    - Fetched from **Scryfall API** (cached locally).
    - Previously used commanders for that player appear first.
  - `Winner`: Single-select dropdown (must be one of the selected players).
- **Submit action:**
  - Calculates ELO changes (see *Ranking System*).
  - Saves to SQLite `games` table.

### **3.4 Leaderboards**
#### **Player Ranking View**
| Column       | Description              |
|--------------|--------------------------|
| Player Name  | Sorted by ELO (high→low) |
| ELO          | Current score            |

#### **Player+Commander Ranking View**
| Column               | Description                     |
|----------------------|---------------------------------|
| Player + Commander   | Sorted by ELO (high→low)        |
| ELO                 | Score for this combo            |

- **Toggle between views** via Streamlit button.

### **3.5 Game History Table**
- **Columns:**
  - Date | Winner (Name + Commander) | Losers (Names + Commanders) | ELO Changes (e.g., "+10").
- **Sort:** Oldest → newest.
- **Pagination:** 20 games per page.

### **3.6 Player-Specific Page**
- **URL:** `/player?name=NAME`.
- **Sections:**
  1. **Summary Stats:**
     - Current ELO, total games, win rate.
     - List of commanders played (with ELO/win rate for each).
  2. **Streaks:**
     - Current/longest win or loss streaks.
  3. **Matchup Analysis:**
     - Dropdowns:
       - *Opponent* (required).
       - *Commander* (optional, filters to games with that commander).
     - Output: Win rate, ELO delta, filtered game history.
  4. **ELO Graph:**
     - Static line chart (time vs. ELO).

### **3.7 Ranking System**
- **2-player games:** Standard ELO (K=32).
- **Multiplayer games:**
  - Winner gains `(sum of losers' ELO adjustments) / num_losers`.
  - Each loser loses `(winner's ELO adjustment) / num_losers`.
  - *Formula example:*
    ```python
    # Pseudo-code for multiplayer ELO
    def update_elo(winner, losers):
        expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
        winner_delta = K * (1 - expected_win)  # K=32
        loser_delta = -K * expected_win
        # Distribute deltas
        winner.elo += winner_delta / len(losers)
        for loser in losers:
            loser.elo += loser_delta / len(losers)
    ```

---

## **4. Data Handling**

### **4.1 Database Schema (SQLite)**
#### **Tables:**
- `players`: `[id, name, elo]`
- `commanders`: `[id, name (from Scryfall), scryfall_id]`
- `games`: `[id, date, winner_id, winner_commander_id]`
- `game_players`: `[game_id, player_id, commander_id, elo_change]`

### **4.2 Error Handling**
- **Form validation:** Ensure all fields are filled; show Streamlit warnings.
- **Scryfall API failures:** Fall back to cached commander list.
- **Database errors:** Log to console; show user-friendly message.

### **4.3 Backup Strategy**
- Admin interface includes "Export Data" button (generates SQLite/JSON dump).

---

## **5. Testing Plan**

### **5.1 Unit Tests**
- ELO calculations (2-player and multiplayer).
- SQLite CRUD operations.
- Scryfall API caching.

### **5.2 Manual Tests**
1. Submit games (2+ players).
2. Verify leaderboard sorting.
3. Test admin tools (add player, export data).
4. Validate player-specific stats (matchup filters, graphs).

---

## **6. Deployment Notes**
- **Streamlit Cloud:** Set `STREAMLIT_PASSWORD` env variable.
- **Local/VPS:** Ensure SQLite file is writeable.

---

## **7. Open Questions**
- Hosting preferences (will inform CI/CD setup).
- Whether to add a "game notes" field (currently excluded).

---
