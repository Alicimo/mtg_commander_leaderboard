# Magic: The Gathering Commander Leaderboard - Project Checklist

## **Phase 1: Core Infrastructure**

### Database Initialization
- [ ] Create `data/` directory with proper permissions
- [ ] Initialize SQLite database at `data/commander.db`
- [ ] Implement SQLAlchemy Core schema for:
  - [ ] `players` table
  - [ ] `commanders` table
  - [ ] `games` table
  - [ ] `game_players` table
- [ ] Write database connection singleton class
- [ ] Add database versioning system
- [ ] Create migration script for initial schema
- [ ] Write pytest suite for:
  - [ ] Table existence verification
  - [ ] Column type validation
  - [ ] Foreign key relationships
- [ ] Implement connection health check

### Authentication
- [ ] Create password configuration loader:
  - [ ] Environment variable support
  - [ ] Streamlit secrets support
- [ ] Implement session state management:
  - [ ] Login status persistence
  - [ ] Session timeout handling (8 hours)
- [ ] Build login UI component:
  - [ ] Password input field
  - [ ] Error message display
  - [ ] Logout button in sidebar
- [ ] Write authentication tests:
  - [ ] Successful login/logout
  - [ ] Invalid password handling
  - [ ] Session expiration test

## **Phase 2: Admin Foundations**

### Player Management
- [ ] Create admin route (`/admin`) with:
  - [ ] Password gate
  - [ ] Navigation menu
- [ ] Implement player CRUD operations:
  - [ ] Add player form with validation
  - [ ] Delete player with confirmation dialog
  - [ ] Player list display with sorting
- [ ] Add database constraints:
  - [ ] Unique player names
  - [ ] Cascading deletes
- [ ] Write tests for:
  - [ ] Duplicate player prevention
  - [ ] Delete propagation

### Data Export
- [ ] Implement SQLite backup:
  - [ ] File copy functionality
  - [ ] Timestamped filenames
- [ ] Create JSON exporter:
  - [ ] Table serialization
  - [ ] Relationship resolution
- [ ] Add export UI components:
  - [ ] Backup button group
  - [ ] Download handlers
- [ ] Write restoration tests:
  - [ ] Backup/restore cycle verification
  - [ ] Data integrity checks

## **Phase 3: Game Submission**

### Base Game Form
- [ ] Create form UI components:
  - [ ] Date picker with validation
  - [ ] Player multi-select
  - [ ] Winner dropdown
- [ ] Implement form validation:
  - [ ] Minimum 2 players
  - [ ] Winner must be in players list
- [ ] Add database transaction logic:
  - [ ] Game record insertion
  - [ ] Atomic commits
- [ ] Write submission tests:
  - [ ] Valid/invalid submissions
  - [ ] DB state verification

### Commander Selection
- [ ] Integrate Scryfall API:
  - [ ] Commander search endpoint
  - [ ] Response caching
- [ ] Build commander cache system:
  - [ ] Local SQLite storage
  - [ ] TTL expiration (7 days)
- [ ] Create prioritized dropdowns:
  - [ ] Player-specific commander history
  - [ ] Autocomplete search
- [ ] Implement rate limiting:
  - [ ] API call throttling
  - [ ] Fallback to cache
- [ ] Write cache tests:
  - [ ] Cache hit/miss scenarios
  - [ ] API failure handling

## **Phase 4: Ranking System**

### ELO Algorithm
- [ ] Implement core calculations:
  - [ ] 2-player ELO
  - [ ] Multiplayer distribution
- [ ] Create rating history tracker:
  - [ ] Per-player ELO snapshots
  - [ ] Game relationship linking
- [ ] Write comprehensive test suite:
  - [ ] Known outcome verification
  - [ ] Precision testing
  - [ ] Edge cases (same ELO, many players)
- [ ] Add performance benchmarks

### Leaderboards
- [ ] Build player-only ranking:
  - [ ] SQL window functions
  - [ ] Dynamic sorting
- [ ] Implement player+commander view:
  - [ ] Composite key handling
  - [ ] Joint ELO calculations
- [ ] Create UI components:
  - [ ] Toggle switch
  - [ ] Responsive tables
  - [ ] ELO change indicators
- [ ] Optimize queries:
  - [ ] Indexing strategy
  - [ ] Query caching

## **Phase 5: Game History & Stats**

### Game History
- [ ] Implement pagination system:
  - [ ] Server-side sorting
  - [ ] Page size controls
- [ ] Build history table:
  - [ ] Column formatting
  - [ ] ELO change display
- [ ] Add export functionality:
  - [ ] CSV generation
  - [ ] Date range selection
- [ ] Write pagination tests:
  - [ ] Page navigation
  - [ ] Sort preservation

### Player Profiles
- [ ] Create profile route system:
  - [ ] URL parameter handling
  - [ ] 404 handling
- [ ] Implement stats modules:
  - [ ] Win rate calculator
  - [ ] Commander performance
  - [ ] ELO trend aggregation
- [ ] Build visualization components:
  - [ ] Matplotlib/Plotly graphs
  - [ ] Responsive layout
- [ ] Add cross-linking:
  - [ ] Leaderboard → profiles
  - [ ] History → profiles

## **Phase 6: Final Integration**

### Matchup Analysis
- [ ] Create filter components:
  - [ ] Opponent selector
  - [ ] Commander selector
- [ ] Implement matchup calculator:
  - [ ] Head-to-head stats
  - [ ] Filtered game history
- [ ] Add visualization:
  - [ ] Win rate pie chart
  - [ ] ELO delta summary

### Streak Tracking
- [ ] Implement streak detection:
  - [ ] Current streak calculator
  - [ ] Historical max finder
- [ ] Create materialized view:
  - [ ] Performance optimization
  - [ ] Refresh trigger
- [ ] Add UI components:
  - [ ] Streak type indicators
  - [ ] Historical timeline

## **Deployment Preparation**
- [ ] Dockerize application
- [ ] Configure environment variables
- [ ] Set up logging:
  - [ ] Application logs
  - [ ] Error tracking
- [ ] Write deployment docs:
  - [ ] Streamlit Cloud setup
  - [ ] VPS deployment guide
- [ ] Implement health checks:
  - [ ] Database status
  - [ ] API connectivity

## **Documentation**
- [ ] Write user guide:
  - [ ] Game submission
  - [ ] Leaderboard interpretation
- [ ] Create admin manual:
  - [ ] Player management
  - [ ] Backup procedures
- [ ] Generate API docs:
  - [ ] Scryfall integration
  - [ ] Internal data model

## **Final QA**
- [ ] Security audit:
  - [ ] SQL injection prevention
  - [ ] Session hardening
- [ ] Performance test:
  - [ ] 1000-game load
  - [ ] Concurrent user simulation
- [ ] Cross-browser testing:
  - [ ] Mobile responsiveness
  - [ ] Browser compatibility
- [ ] Accessibility check:
  - [ ] Screen reader support
  - [ ] Color contrast

## **Optional/Post-Launch**
- [ ] Game notes field
- [ ] Commander tier rankings
- [ ] Automated backup to cloud
- [ ] Player avatars
- [ ] Seasonal reset system