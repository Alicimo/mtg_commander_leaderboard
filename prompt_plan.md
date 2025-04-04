# Blueprint Breakdown & Implementation Prompts

## **Phase 1: Core Infrastructure**
**Objective:** Set up database, authentication, and admin basics.

---

### **Step 1.1: Database Initialization**
```text
Create SQLite database with schema. Write Python functions to:
1. Initialize database if not exists
2. Create tables: players, commanders, games, game_players
3. Add test connection check
4. Write pytest to verify table structure

Requirements:
- Use SQLAlchemy Core (not ORM)
- Store DB in `data/commander.db`
- Tables must match spec's "Database Schema"
```

---

### **Step 1.2: Basic Authentication**
```text
Implement Streamlit password protection:
1. Password check via st.secrets or environment variable
2. Session state persistence
3. Logout button in sidebar
4. Graceful handling of failed attempts

Requirements:
- No user roles - single password for all access
- Secure password comparison
- Session cookie lifetime 8 hours
- Unit test for auth flow (mocked)
```

---

## **Phase 2: Admin Foundations**
**Objective:** Player management and backup tools.

---

### **Step 2.1: Player CRUD Operations**
```text
Create admin page (/admin) with:
1. Add player form (name only)
2. Delete player selector
3. Player list display
4. DB integration for all operations

Requirements:
- Password-protect /admin route
- Prevent duplicate player names
- Cascading delete for player-related records
- Confirmation dialogs for deletions
```

---

### **Step 2.2: Data Export**
```text
Add admin export functionality:
1. Button to dump SQLite → .db file
2. Button to export JSON of all tables
3. Error handling for file ops
4. Streamlit downloader integration

Requirements:
- JSON export uses ISO date formatting
- Exports include schema version
- Test backup/restore cycle
```

---

## **Phase 3: Game Submission**
**Objective:** Robust game logging with validation.

---

### **Step 3.1: Base Game Form**
```text
Create game submission form with:
1. Date picker (default today)
2. Player multi-select from DB
3. Winner dropdown (subset of players)
4. Basic validation (min 2 players)

Requirements:
- Form resets on success
- Success/error toasts
- Transactional DB writes
- Unit test form validation
```

---

### **Step 3.2: Commander Selection**
```text
Enhance game form with:
1. Commander dropdown per player
2. Cached Scryfall API lookup
3. Local commander cache (SQLite)
4. Autocomplete prioritizes player's past commanders

Requirements:
- Rate limit Scryfall calls
- Cache commanders for 7 days
- Fallback to cached data on API failure
- Test API/cache integration
```

---

## **Phase 4: Ranking System**
**Objective:** Implement ELO calculations.

---

### **Step 4.1: ELO Core Algorithm**
```text
Write ELO calculation module:
1. Handle 2-player and multiplayer cases
2. Pure functions with DB integration
3. Unit tests with known scenarios
4. History tracking in game_players

Requirements:
- Match spec's multiplayer formula
- Decimal precision to 2 places
- Test K-factor variations
- Benchmark performance
```

---

### **Step 4.2: Leaderboard Views**
```text
Create leaderboard displays:
1. Player-only ranking table
2. Player+commander ranking
3. Toggle between views
4. Real-time updates on submit

Requirements:
- Optimize SQL window functions
- Handle ties properly
- Mobile-responsive tables
- Performance testing
```

---

## **Phase 5: Game History & Player Stats**
**Objective:** Historical data exploration.

---

### **Step 5.1: Paginated History**
```text
Implement game history table:
1. Sort by date (oldest first)
2. 20-item pagination
3. Column formatting per spec
4. ELO change indicators

Requirements:
- Server-side pagination
- Preserve sort on page change
- CSV export button
- Load testing
```

---

### **Step 5.2: Player Profile Page**
```text
Build /player page with:
1. URL parameter handling
2. Summary stats section
3. Commander performance breakdown
4. ELO trend line chart

Requirements:
- Handle missing players
- Cached chart rendering
- Responsive layout
- Cross-linking from leaderboards
```

---

## **Phase 6: Final Integration**
**Objective:** Polish and cross-feature testing.

---

### **Step 6.1: Matchup Analysis**
```text
Add matchup section to player page:
1. Opponent+commander filters
2. Win rate calculation
3. Filtered game history subset
4. ELO delta summary

Requirements:
- Dynamic query params
- Empty state handling
- Shared component with main history
- Integration tests
```

---

### **Step 6.2: Streak Tracking**
```text
Implement streak calculations:
1. Current win/loss streak
2. Longest historical streaks
3. Streak type indicators
4. Cached for performance

Requirements:
- Materialized view for streaks
- Refresh on game submit
- Edge case tests (ties? not applicable)
```

---

## **Implementation Strategy**
1. Execute phases in order
2. Each step includes:
   - Feature code
   - DB migrations
   - Unit + integration tests
   - Documentation updates
3. Final QA checklist:
   - 100% test coverage of core logic
   - Performance audit
   - Security review
   - Backup/restore validation

**Next Steps:** Generate code for Phase 1.1 (Database Initialization) first. Confirm implementation approach before proceeding.