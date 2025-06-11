# Developer Guide

This guide is for developers and contributors working on the Integran project. Regular users don't need this information.

## 🎯 Phase 3.0 Architecture Overview - Spaced Repetition Learning System

As of 2025-01-11, Integran has evolved into a scientifically-backed spaced repetition learning system. The architecture is designed around **local-first principles** with SQLite as the primary data store, supporting terminal, desktop, and mobile platforms.

### Core Design Principles

1. **Local-First**: All learning data stored locally in SQLite - no cloud dependencies
2. **Scientific Learning**: FSRS algorithm for optimal spaced repetition scheduling  
3. **Cross-Platform**: Unified core supporting terminal, desktop, and mobile UIs
4. **Multilingual**: 5-language support (EN/DE/TR/UK/AR) for diverse learners
5. **Privacy-Focused**: User learning patterns stay on device

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        UI LAYER                             │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Terminal UI    │   Desktop UI    │     Mobile UI           │
│  (Rich/Textual) │   (Future)      │     (Future)            │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                    CORE LEARNING ENGINE                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Session Manager │ FSRS Scheduler  │  Progress Analytics     │
│ - Question Flow │ - Memory States │  - Retention Tracking   │
│ - User Input    │ - Intervals     │  - Category Analysis    │
│ - Feedback      │ - Difficulty    │  - Leech Detection      │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     DATA ACCESS LAYER                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Learning Data  │  Question Data  │    User Settings        │
│  - FSRS States  │  - Multilingual │  - Preferences          │
│  - Review Hist. │  - Images       │  - Algorithm Config     │
│  - Analytics    │  - Categories   │  - UI Themes            │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                  SQLITE DATABASE (Local)                    │
│  📊 Learning Tables    📋 Content Tables  ⚙️ Config Tables  │
│  - fsrs_cards         - questions         - user_settings   │
│  - review_history     - categories        - algorithm_config│
│  - learning_sessions  - images_metadata   - ui_preferences  │
│  - user_analytics     - multilingual_data - export_data     │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **FSRS Learning Engine** - Core spaced repetition algorithm with memory modeling
2. **Session Manager** - Orchestrates learning sessions and user interactions  
3. **Progress Analytics** - Real-time learning insights and retention tracking
4. **Leech Detection** - Identifies and manages difficult questions intelligently
5. **Multilingual Content** - Serves explanations in user's preferred language

## 📊 Enhanced Data Structure

Questions are now stored in `questions.json` with the new Phase 1.8 multilingual format:

```json
{
  "id": 21,
  "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
  "options": ["Bild 1", "Bild 2", "Bild 3", "Bild 4"],
  "correct": "Bild 1",
  "category": "Symbols",
  "difficulty": "easy",
  "images": [
    {
      "path": "images/page_9_img_2.png",
      "description": "German federal eagle on yellow background with red claws and beak",
      "context": "Official coat of arms of Germany since 1950"
    }
  ],
  "answers": {
    "en": {
      "explanation": "The German federal eagle is the official coat of arms of Germany...",
      "why_others_wrong": {
        "B": "This shows a different coat of arms...",
        "C": "This is not the federal eagle...",
        "D": "This image shows a state symbol..."
      },
      "key_concept": "German federal symbols and constitutional emblems",
      "mnemonic": "Eagle = Germany (like USA has eagle too)"
    },
    "de": {
      "explanation": "Der Bundesadler ist das offizielle Wappen Deutschlands...",
      "why_others_wrong": {
        "B": "Das zeigt ein anderes Wappen...",
        "C": "Das ist nicht der Bundesadler...",
        "D": "Dieses Bild zeigt ein Landeswappen..."
      },
      "key_concept": "Deutsche Staatssymbole und Verfassungsembleme",
      "mnemonic": "Adler = Deutschland"
    },
    "tr": { "explanation": "...", "why_others_wrong": {...}, "key_concept": "...", "mnemonic": "..." },
    "uk": { "explanation": "...", "why_others_wrong": {...}, "key_concept": "...", "mnemonic": "..." },
    "ar": { "explanation": "...", "why_others_wrong": {...}, "key_concept": "...", "mnemonic": "..." }
  },
  "rag_sources": ["grundgesetz.de", "bundesregierung.de"]
}
```

## 🗄️ SQLite Database Schema - FSRS Learning System

The app uses SQLite for **local-first** storage with tables optimized for spaced repetition learning:

### Learning Engine Tables (FSRS Core)

#### `fsrs_cards` - Individual Card Learning States
```sql
CREATE TABLE fsrs_cards (
    card_id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL,
    user_id INTEGER DEFAULT 1,
    
    -- FSRS Core State (DSR Model)
    difficulty REAL NOT NULL DEFAULT 5.0,        -- D: Inherent difficulty (0-10)
    stability REAL NOT NULL DEFAULT 1.0,         -- S: Memory strength (days)
    retrievability REAL NOT NULL DEFAULT 1.0,    -- R: Current recall probability (0-1)
    
    -- Learning Progress
    state INTEGER NOT NULL DEFAULT 0,            -- 0:New, 1:Learning, 2:Review, 3:Relearning
    step_number INTEGER DEFAULT 0,               -- Current learning step
    last_review_date REAL,                       -- Unix timestamp
    next_review_date REAL,                       -- Scheduled review time
    
    -- Performance Tracking
    review_count INTEGER DEFAULT 0,              -- Total reviews
    lapse_count INTEGER DEFAULT 0,               -- Number of times forgotten
    success_count INTEGER DEFAULT 0,             -- Successful recalls
    
    -- Metadata
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
```

#### `review_history` - Complete Review Log
```sql
CREATE TABLE review_history (
    review_id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    
    -- Review Details
    review_date REAL NOT NULL,                   -- Unix timestamp
    rating INTEGER NOT NULL,                     -- 1:Again, 2:Hard, 3:Good, 4:Easy
    response_time_ms INTEGER,                    -- Time to answer
    
    -- FSRS State Before Review
    difficulty_before REAL,
    stability_before REAL,
    retrievability_before REAL,
    
    -- FSRS State After Review
    difficulty_after REAL,
    stability_after REAL,
    retrievability_after REAL,
    next_interval_days REAL,
    
    -- Session Context
    session_id INTEGER,
    review_type TEXT,                            -- 'learn', 'review', 'relearn', 'cram'
    
    FOREIGN KEY (card_id) REFERENCES fsrs_cards(card_id),
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
);
```

#### `learning_sessions` - Study Session Tracking
```sql
CREATE TABLE learning_sessions (
    session_id INTEGER PRIMARY KEY,
    user_id INTEGER DEFAULT 1,
    
    -- Session Details
    start_time REAL NOT NULL,
    end_time REAL,
    duration_seconds INTEGER,
    
    -- Session Stats
    questions_reviewed INTEGER DEFAULT 0,
    questions_correct INTEGER DEFAULT 0,
    new_cards_learned INTEGER DEFAULT 0,
    
    -- Session Configuration
    session_type TEXT,                           -- 'review', 'learn', 'weak_focus', 'quiz'
    target_retention REAL DEFAULT 0.9,          -- User's retention goal
    max_reviews INTEGER DEFAULT 50,
    
    -- Performance Metrics
    average_response_time_ms INTEGER,
    retention_rate REAL,
    
    created_at REAL NOT NULL
);
```

### Content Tables (Question Data)

#### `questions` - Enhanced Question Model
```sql
CREATE TABLE questions (
    id INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    options TEXT NOT NULL,                       -- JSON: ["A", "B", "C", "D"]
    correct TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT DEFAULT 'medium',            -- Content difficulty estimate
    
    -- Question Metadata
    question_type TEXT DEFAULT 'general',       -- 'general' or 'state_specific'
    state TEXT,                                  -- For state-specific questions
    page_number INTEGER,
    is_image_question BOOLEAN DEFAULT FALSE,
    
    -- Multilingual Content (JSON)
    images_data TEXT,                            -- Image paths and descriptions
    multilingual_answers TEXT,                   -- 5-language explanations
    rag_sources TEXT,                           -- Source references
    
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
```

#### `categories` - Learning Categories
```sql
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    total_questions INTEGER DEFAULT 0,
    color_hex TEXT DEFAULT '#3498db'
);
```

### Analytics & Configuration Tables

#### `user_analytics` - Learning Analytics
```sql
CREATE TABLE user_analytics (
    analytics_id INTEGER PRIMARY KEY,
    user_id INTEGER DEFAULT 1,
    date TEXT NOT NULL,                          -- YYYY-MM-DD format
    
    -- Daily Statistics
    reviews_due INTEGER DEFAULT 0,
    reviews_completed INTEGER DEFAULT 0,
    new_cards_learned INTEGER DEFAULT 0,
    retention_rate REAL,
    
    -- Category Performance (JSON)
    category_stats TEXT,                         -- Per-category performance
    
    -- Streak Tracking
    study_streak_days INTEGER DEFAULT 0,
    
    created_at REAL NOT NULL
);
```

#### `algorithm_config` - FSRS Parameters
```sql
CREATE TABLE algorithm_config (
    config_id INTEGER PRIMARY KEY,
    user_id INTEGER DEFAULT 1,
    
    -- FSRS Algorithm Parameters (19 parameters for FSRS-5)
    parameters TEXT NOT NULL,                    -- JSON array of 19 floats
    target_retention REAL DEFAULT 0.9,
    maximum_interval_days INTEGER DEFAULT 365,
    
    -- Learning Steps Configuration
    learning_steps TEXT DEFAULT '[1, 10]',      -- JSON: minutes for new cards
    relearning_steps TEXT DEFAULT '[10]',       -- JSON: minutes for forgotten cards
    
    -- Optimization Settings
    optimization_enabled BOOLEAN DEFAULT TRUE,
    min_reviews_for_optimization INTEGER DEFAULT 1000,
    
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
```

#### `user_settings` - User Preferences
```sql
CREATE TABLE user_settings (
    setting_id INTEGER PRIMARY KEY,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,                -- JSON for complex values
    setting_type TEXT DEFAULT 'string',         -- 'string', 'integer', 'boolean', 'json'
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
```

### Leech Detection & Management

#### `leech_cards` - Difficult Question Tracking
```sql
CREATE TABLE leech_cards (
    leech_id INTEGER PRIMARY KEY,
    card_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    
    -- Leech Metrics
    lapse_count INTEGER NOT NULL,               -- Number of times forgotten
    leech_threshold INTEGER DEFAULT 8,         -- Threshold for leech status
    detected_at REAL NOT NULL,
    
    -- Management Actions
    action_taken TEXT,                          -- 'suspend', 'note_added', 'modified'
    action_date REAL,
    is_suspended BOOLEAN DEFAULT FALSE,
    
    -- User Notes
    user_notes TEXT,
    
    FOREIGN KEY (card_id) REFERENCES fsrs_cards(card_id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
```

### Database Indexes (Performance Optimization)

```sql
-- FSRS Performance Indexes
CREATE INDEX idx_fsrs_cards_next_review ON fsrs_cards(next_review_date);
CREATE INDEX idx_fsrs_cards_question ON fsrs_cards(question_id);
CREATE INDEX idx_fsrs_cards_state ON fsrs_cards(state);

-- Review History Indexes  
CREATE INDEX idx_review_history_date ON review_history(review_date);
CREATE INDEX idx_review_history_card ON review_history(card_id);
CREATE INDEX idx_review_history_session ON review_history(session_id);

-- Analytics Indexes
CREATE INDEX idx_user_analytics_date ON user_analytics(date);
CREATE INDEX idx_leech_cards_detected ON leech_cards(detected_at);
```

## 🧠 FSRS Learning System Implementation

### Core FSRS Algorithm Components

The system implements the **Free Spaced Repetition Scheduler (FSRS)** algorithm, which models memory using three key variables:

#### DSR Memory Model
- **D (Difficulty)**: How hard it is to increase memory stability for this item (0-10)
- **S (Stability)**: Memory strength measured in days until 90% retention probability
- **R (Retrievability)**: Current probability of successful recall (0-1)

#### Learning State Machine
```
New Card → Learning → Review ↔ Relearning
    ↓         ↓         ↓         ↓
   [1]       [2]      [3]       [4]
```

**States:**
- **0 (New)**: Never studied before
- **1 (Learning)**: Initial learning phase with short intervals  
- **2 (Review)**: Successfully learned, scheduled for spaced review
- **3 (Relearning)**: Previously learned but forgotten, needs reinforcement

### Core Learning Engine Classes

#### `FSRSScheduler` - Main Algorithm Implementation
```python
class FSRSScheduler:
    """Core FSRS algorithm for spaced repetition scheduling."""
    
    def __init__(self, parameters: List[float], target_retention: float = 0.9):
        self.parameters = parameters  # 19 FSRS parameters
        self.target_retention = target_retention
    
    def schedule_card(self, card: FSRSCard, rating: int) -> ScheduleResult:
        """Calculate next review date based on user rating."""
        # Algorithm implementation details...
        
    def calculate_retrievability(self, card: FSRSCard, days_elapsed: float) -> float:
        """Calculate current recall probability."""
        
    def optimize_parameters(self, review_history: List[Review]) -> List[float]:
        """Optimize FSRS parameters based on user's review history."""
```

#### `SessionManager` - Learning Session Orchestration
```python
class SessionManager:
    """Manages learning sessions and question flow."""
    
    def __init__(self, db: Database, scheduler: FSRSScheduler):
        self.db = db
        self.scheduler = scheduler
        
    def start_session(self, session_type: str, max_reviews: int) -> Session:
        """Start a new learning session with specified parameters."""
        
    def get_next_question(self, session: Session) -> Optional[Question]:
        """Get next question based on FSRS scheduling and session settings."""
        
    def process_answer(self, question_id: int, rating: int, response_time: int):
        """Process user answer and update FSRS states."""
        
    def get_session_stats(self, session: Session) -> SessionStats:
        """Calculate real-time session statistics."""
```

#### `ProgressAnalytics` - Learning Insights
```python
class ProgressAnalytics:
    """Provides learning analytics and progress tracking."""
    
    def get_retention_rate(self, user_id: int, days: int = 30) -> float:
        """Calculate user's retention rate over specified period."""
        
    def get_category_performance(self, user_id: int) -> Dict[str, CategoryStats]:
        """Analyze performance by question category."""
        
    def detect_leeches(self, user_id: int) -> List[LeechCard]:
        """Identify cards that need special attention."""
        
    def calculate_forecast(self, user_id: int, days: int = 30) -> ReviewForecast:
        """Predict future review workload."""
```

### Learning Session Flow

#### 1. Session Initialization
```python
# User starts a review session
session = session_manager.start_session(
    session_type="review",  # or "learn", "weak_focus", "quiz"
    max_reviews=50,
    target_retention=0.9
)
```

#### 2. Question Selection Algorithm
```python
def get_next_question(self) -> Question:
    """Intelligent question selection based on:
    - FSRS scheduling (due dates)
    - User preferences (weak areas, categories)
    - Session limits and goals
    - Interleaving for related topics
    """
    # Priority 1: Overdue reviews
    overdue = self.get_overdue_cards()
    if overdue:
        return self.select_by_urgency(overdue)
    
    # Priority 2: Due reviews  
    due = self.get_due_cards()
    if due:
        return self.select_with_interleaving(due)
        
    # Priority 3: New cards (if daily limit not reached)
    if self.can_learn_new():
        return self.get_new_card()
        
    return None  # Session complete
```

#### 3. Answer Processing & FSRS Update
```python
def process_answer(self, question_id: int, rating: int, response_time: int):
    """Complete FSRS update cycle:
    1. Calculate new DSR values
    2. Update card state and next review date
    3. Log review in history
    4. Update session statistics
    5. Check for leech detection
    """
    card = self.db.get_fsrs_card(question_id)
    
    # Calculate new FSRS state
    result = self.scheduler.schedule_card(card, rating)
    
    # Update database
    self.db.update_card_state(card.id, result)
    self.db.log_review(card.id, rating, response_time, result)
    
    # Analytics
    self.check_leech_threshold(card)
    self.update_session_stats()
```

### Advanced Features

#### Leech Detection & Management
```python
class LeechDetector:
    """Identifies and manages difficult questions."""
    
    def detect_leech(self, card: FSRSCard) -> bool:
        """Check if card qualifies as a leech (default: 8+ lapses)."""
        return card.lapse_count >= self.threshold
        
    def suggest_intervention(self, leech: LeechCard) -> List[str]:
        """Provide suggestions for handling leeches:
        - Break into smaller concepts
        - Add visual memory aids  
        - Create mnemonics
        - Suspend temporarily
        """
```

#### Interleaved Practice
```python
class InterleavingManager:
    """Implements interleaved practice for better discrimination."""
    
    def select_interleaved_questions(self, due_cards: List[Card]) -> List[Card]:
        """Mix related topics to improve conceptual understanding."""
        # Group by similar categories
        # Alternate between groups
        # Maintain cognitive load balance
```

#### Parameter Optimization
```python
class ParameterOptimizer:
    """Optimizes FSRS parameters based on user's review history."""
    
    def should_optimize(self, user_id: int) -> bool:
        """Check if user has enough review data (1000+ reviews)."""
        
    def optimize_parameters(self, user_id: int) -> List[float]:
        """Use machine learning to find optimal FSRS parameters."""
        # Analyze review history
        # Minimize prediction error
        # Return personalized parameters
```

### Local-First Data Synchronization

#### Export/Import System
```python
class DataPortability:
    """Handle data export/import for cross-device sync."""
    
    def export_user_data(self, user_id: int) -> str:
        """Export complete learning state to JSON."""
        return {
            "fsrs_cards": self.export_cards(user_id),
            "review_history": self.export_history(user_id), 
            "settings": self.export_settings(user_id),
            "analytics": self.export_analytics(user_id)
        }
        
    def import_user_data(self, data: str) -> bool:
        """Import learning state, handling conflicts intelligently."""
        # Merge review histories
        # Update FSRS states
        # Preserve newer settings
```

## 🤖 PDF Question Extraction

### Overview

The application includes a sophisticated PDF extraction system using Google's Gemini AI to extract questions from the official BAMF PDF. This is a **developer-only feature** - end users never need to set this up.

### Environment Variables

These environment variables are **ONLY needed for developers** who want to extract questions from the PDF using AI. **End users don't need these** as the app comes with pre-extracted question data.

The application supports **two authentication methods** for Google Gemini AI:

#### Method 1: Vertex AI with Service Account (Recommended)
```bash
# Required variables
export USE_VERTEX_AI=true                           # Enable Vertex AI authentication (default)
export GCP_PROJECT_ID="your-gcp-project"           # Google Cloud Project ID
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"  # Service account JSON file
export GCP_REGION="us-central1"                    # Google Cloud region (optional)
export GEMINI_MODEL="gemini-2.5-pro-preview-06-05" # Model version (optional)
```

#### Method 2: API Key (Legacy)
```bash
# Required variables  
export USE_VERTEX_AI=false                         # Disable Vertex AI, use API key instead
export GEMINI_API_KEY="your-gemini-api-key"        # Google AI API key
export GCP_PROJECT_ID="your-gcp-project"           # Google Cloud Project ID
export GCP_REGION="us-central1"                    # Google Cloud region (optional)
export GEMINI_MODEL="gemini-2.5-pro-preview-06-05" # Model version (optional)
```

#### Required vs Optional Variables:

**Always Required:**
- `GCP_PROJECT_ID` - Your Google Cloud Project ID

**Required for Vertex AI (Method 1):**
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON file
- `USE_VERTEX_AI=true` (or omit, as this is the default)

**Required for API Key (Method 2):**
- `GEMINI_API_KEY` - Google AI Studio API key
- `USE_VERTEX_AI=false`

**Optional (have sensible defaults):**
- `GCP_REGION` - Defaults to "us-central1"
- `GEMINI_MODEL` - Defaults to "gemini-2.5-pro-preview-06-05"

### Important Notes

⚠️ **Cost Warning**: Using the Gemini API will incur charges on your Google Cloud account
- **Not Required**: The app works perfectly without these variables using pre-extracted data
- **For Developers Only**: Only needed if you want to re-extract questions from the PDF
- **One-Time Use**: Question extraction is typically done once during development
- **Vertex AI Recommended**: More secure and scalable than API keys

#### When You Need These Variables:
- ✅ You're a developer modifying the question extraction process
- ✅ You want to re-extract questions from a new PDF version
- ✅ You're contributing to the project's question database

#### When You DON'T Need These Variables:
- ❌ You're just using the app to study for the exam
- ❌ You're running the trainer for practice sessions
- ❌ You're a regular end user

The application automatically uses pre-extracted question data from `data/questions.json` and will never call external APIs during normal usage.

### Developer Commands (Phase 1.8)

```bash
# PRIMARY COMMAND: Build complete multilingual dataset
integran-build-dataset

# Database setup with language preference
integran-setup --language en

# Backup and restore data
integran-backup-data backup
integran-backup-data restore --suffix 20250609_124243

# Direct PDF extraction (developers only):
integran-direct-extract  # Single-question extraction with checkpointing
```

## 🏗️ Current Data Pipeline (2025-06-11 Update)

⚠️ **Important**: The unified `integran-build-dataset` command is outdated. Use the new step-by-step process documented in the [Dataset Generation Guide](./dataset-generation-guide.md).

### Current Workflow (Multi-Step Process)

The current system uses multiple scripts for different phases:

```bash
# STEP 0: Extract from PDF (usually already done)
python src/cli/direct_extract.py

# STEP 1: Extract images (already done)  
python scripts/extract_images.py

# STEP 2: Fix image answers (already done)
python scripts/fix_image_answers.py

# STEP 3: Generate explanations (main task)
python scripts/generate_explanations.py
python scripts/retry_failed_questions.py

# STEP 4: Create final dataset
python scripts/finalize_dataset.py
```

### Quick Start for Most Developers

Most developers only need to run the final step:

```bash
# Create final dataset from existing progress
python scripts/finalize_dataset.py
```

📖 **For complete details, see**: [Dataset Generation Guide](./dataset-generation-guide.md)

### Advanced Options

```bash
# Force rebuild everything from scratch
integran-build-dataset --force-rebuild

# Disable RAG enhancement for faster processing
integran-build-dataset --no-rag

# Skip multilingual generation (testing only)
integran-build-dataset --no-multilingual

# Use larger batch size for faster processing
integran-build-dataset --batch-size 20

# Check current build status
integran-build-dataset --status

# Enable verbose logging
integran-build-dataset --verbose
```

### Prerequisites

Before running `integran-build-dataset`, ensure:

1. **Extraction completed**: `data/extraction_checkpoint.json` must exist and be completed
2. **Gemini API configured**: Required for image descriptions and multilingual answers
3. **Images extracted**: `data/images/` directory contains extracted PDF images
4. **Optional**: Firecrawl API key for enhanced RAG content fetching

### Output Structure

The generated `data/questions.json` includes:

```json
{
  "id": 21,
  "question": "Welches ist das Wappen der Bundesrepublik Deutschland?",
  "options": ["Bild 1", "Bild 2", "Bild 3", "Bild 4"],
  "correct": "Bild 1",
  "category": "Symbols",
  "difficulty": "easy",
  "images": [
    {
      "path": "images/page_9_img_2.png",
      "description": "German federal eagle on yellow background with red claws and beak",
      "context": "Official coat of arms of Germany since 1950"
    }
  ],
  "answers": {
    "en": {
      "explanation": "The German federal eagle is the official coat of arms...",
      "why_others_wrong": {"B": "This shows...", "C": "This is..."},
      "key_concept": "German federal symbols",
      "mnemonic": "Eagle = Germany (like USA)"
    },
    "de": {
      "explanation": "Der Bundesadler ist das offizielle Wappen...",
      "why_others_wrong": {"B": "Das zeigt...", "C": "Das ist..."},
      "key_concept": "Deutsche Staatssymbole",
      "mnemonic": "Adler = Deutschland"
    },
    "tr": "...",
    "uk": "...",
    "ar": "..."
  },
  "rag_sources": ["grundgesetz.de", "bundestag.de"]
}
```

### Progress Tracking

The command uses checkpoint system for resumability:

```bash
# View build progress
integran-build-dataset --status

# Resume interrupted build
integran-build-dataset  # Automatically resumes from checkpoint
```

Progress is saved in `data/dataset_checkpoint.json`.

## 🔧 Data Generation Overview

The application uses AI-powered explanations generated with Google Gemini for all exam questions. The RAG system was removed as it was not used in the final dataset generation.

## 🎓 AI Explanation Generation ✨ **NEW**

The system generates comprehensive explanations for all exam questions using Google's Gemini AI.

### Explanation Generation Process

#### Basic Explanation Generation

```bash
# Generate explanations for all 460 questions
integran-generate-explanations

# Use specific batch size (default: 10)
integran-generate-explanations --batch-size 15

# Start fresh (ignore existing checkpoint)
integran-generate-explanations --no-resume

# Enable verbose logging
integran-generate-explanations --verbose
```


### Explanation Structure

Each generated explanation includes:

```json
{
  "question_id": 1,
  "question_text": "In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
  "correct_answer": "hier Meinungsfreiheit gilt.",
  "explanation": "Detailed explanation of why this answer is correct...",
  "why_others_wrong": {
    "incorrect_option_1": "Why this option is wrong...",
    "incorrect_option_2": "Why this option is wrong..."
  },
  "key_concept": "Meinungsfreiheit (Artikel 5 Grundgesetz)",
  "mnemonic": "Memory aid to remember the concept",
}
```

### Checkpoint System

The explanation generation includes robust checkpoint support:

- **Resume Capability**: Automatically resumes from last successful batch
- **Progress Tracking**: Saves progress in `data/explanations_checkpoint.json`
- **Error Handling**: Continues with next batch if one fails
- **Cost Optimization**: Never re-generates existing explanations

### Cost and Performance

- **Total Questions**: 460 explanations
- **Estimated Cost**: $10-20 USD for complete generation
- **Time**: ~1-2 hours for all questions
- **API Calls**: ~50-100 requests (depending on batch size)
- **Rate Limiting**: Built-in throttling to respect API limits

### Output Files

- **Final Output**: `data/explanations.json` (used by the application)
- **Checkpoint**: `data/explanations_checkpoint.json` (for resume capability)
- **Progress Tracking**: Detailed batch completion logs

## 🔧 Development Setup

### Prerequisites

- Python 3.12+
- Conda environment
- uv package manager
- Git

### Development Installation

1. Clone and setup:
```bash
git clone https://github.com/yourusername/integran.git
cd integran
make env-create
conda activate integran
make install
```

2. Run tests:
```bash
pytest
```

3. Run linting:
```bash
ruff check .
ruff format .
```

### Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_database.py

# Run with coverage
pytest --cov=src

# Run tests with verbose output
pytest -v
```

### Code Quality

The project uses several tools for code quality:

- **Ruff**: Linting and formatting
- **MyPy**: Type checking
- **Pytest**: Testing with coverage reporting

### Making Changes

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Run linting: `ruff check . --fix && ruff format .`
5. Commit and push
6. Create a pull request

### Complete Developer Workflow ✨ **NEW**

For developers working on the AI-enhanced question system:

#### 1. Initial Setup
```bash
# Clone and setup environment
git clone https://github.com/yourusername/integran.git
cd integran
make env-create
conda activate integran
make install

# Setup environment variables (if working with AI features)
cp .env.example .env
# Edit .env with your Google Cloud credentials
```

# Knowledge base building removed as RAG was not used

#### 3. Working with Explanations
```bash
# Generate explanations for all questions (if needed)
integran-generate-explanations --batch-size 10

# RAG enhancement removed as it was not used

# Check progress during generation
tail -f data/explanations_checkpoint.json
```

#### 4. Development Cycle
```bash
# Make your changes
# ...

# Run full test suite
make check-all

# Or individually:
make lint        # Linting
make typecheck   # Type checking  
make test        # Tests
make coverage    # Coverage report
```

#### 5. Quality Assurance
```bash
# Before committing, ensure:
pytest --cov=src --cov-report=term-missing  # 80%+ coverage required
ruff check . --fix && ruff format .         # Code quality
mypy src/                                    # Type checking
```

# RAG system removed as it was not used in final dataset generation

### Updated Project Structure (Phase 3.0 - FSRS Learning System)

```
src/
├── core/                           # Core Learning Engine
│   ├── __init__.py
│   ├── models.py                   # FSRS data models (Card, Review, Session)
│   ├── database.py                 # SQLite operations with FSRS schema
│   ├── settings.py                 # Configuration management
│   ├── fsrs_scheduler.py           # ✨ NEW: FSRS algorithm implementation
│   ├── session_manager.py          # ✨ NEW: Learning session orchestration
│   ├── progress_analytics.py       # ✨ NEW: Learning insights and statistics
│   ├── leech_detector.py           # ✨ NEW: Difficult question identification
│   ├── interleaving_manager.py     # ✨ NEW: Interleaved practice implementation
│   ├── image_processor.py          # AI vision & question-image mapping
│   ├── answer_engine.py            # Multilingual answer generation
│   └── data_builder.py             # Dataset pipeline orchestrator
├── spaced_repetition/              # ✨ NEW: Spaced Repetition System
│   ├── __init__.py
│   ├── algorithms/                 # Different SR algorithms
│   │   ├── __init__.py
│   │   ├── fsrs.py                 # Main FSRS implementation
│   │   ├── sm2.py                  # Legacy SM-2 for comparison
│   │   └── optimizer.py            # Parameter optimization
│   ├── memory_models.py            # DSR memory modeling
│   ├── scheduling.py               # Review scheduling logic
│   └── parameter_optimizer.py      # ML-based parameter tuning
├── ui/                             # Terminal UI Framework (Rich/Textual)
│   ├── __init__.py
│   ├── terminal/                   # ✨ NEW: Terminal-specific UI
│   │   ├── __init__.py
│   │   ├── main_menu.py            # Enhanced dashboard
│   │   ├── question_display.py     # Question presentation
│   │   ├── progress_display.py     # Analytics visualization
│   │   ├── settings_menu.py        # User preferences
│   │   ├── leech_manager.py        # Leech management interface
│   │   └── image_renderer.py       # Terminal image display
│   ├── components/                 # Reusable UI components
│   │   ├── __init__.py
│   │   ├── progress_bars.py        # Progress visualization
│   │   ├── charts.py               # Analytics charts
│   │   └── dialogs.py              # User input dialogs
│   └── themes.py                   # Color themes and styling
├── cli/                            # Command-line interfaces
│   ├── __init__.py
│   ├── backup_data.py              # Data backup/restore
│   ├── build_dataset.py            # Dataset building
│   ├── direct_extract.py           # PDF extraction
│   └── export_data.py              # ✨ NEW: Learning data export
├── utils/                          # Utility functions
│   ├── __init__.py
│   ├── question_loader.py          # Question data loading
│   ├── gemini_client.py            # AI client utilities
│   ├── data_portability.py         # ✨ NEW: Export/import functionality
│   └── timezone_utils.py           # ✨ NEW: Timezone handling
├── trainer.py                      # ✨ UPDATED: Main application entry point
├── setup.py                        # ✨ UPDATED: FSRS schema initialization
└── direct_pdf_processor.py         # PDF extraction system
```

### Key Architecture Changes

**🧠 Learning-First Design**: Core architecture now centers around spaced repetition learning rather than simple question display.

**📊 Local Analytics**: Comprehensive learning analytics stored locally in SQLite for privacy.

**🎨 Rich Terminal UI**: Advanced terminal interface using Rich/Textual for modern CLI experience.

**⚙️ Modular Algorithms**: Plugin architecture for different spaced repetition algorithms (FSRS, SM-2).

**📱 Cross-Platform Ready**: Unified core logic can support terminal, desktop, and mobile UIs.

### Data Directory Structure (Phase 1.8)

```
data/
├── questions.json                 # ✨ UPDATED: Phase 1.8 multilingual format
├── extraction_checkpoint.json     # Source of truth (460 questions)
├── dataset_checkpoint.json        # ✨ NEW: Build progress tracking
├── images/                        # All extracted question images (42 image questions)
# knowledge_base/ and vector_store/ removed as RAG was not used
├── trainer.db                     # SQLite database (created by setup)
└── gesamtfragenkatalog-lebenindeutschland.pdf

# REMOVED in Phase 1.8 cleanup:
# ├── questions.csv              # REMOVED: Replaced by unified format
# ├── explanations.json          # REMOVED: Integrated into questions.json
# ├── explanations_checkpoint.json # REMOVED: Replaced by dataset_checkpoint.json
```

## 🧪 Testing Strategy (Phase 1.8)

The refactored codebase includes comprehensive test coverage (169 tests) with specific focus on the image mapping issues that prompted the refactor.

### Test Structure

```
tests/
├── unit/
│   ├── core/                        # Core component tests
│   │   ├── test_image_processor.py      # Image processing validation
│   │   ├── test_answer_engine.py        # Multilingual answer generation
│   │   ├── test_data_builder.py         # Pipeline orchestration
│   │   ├── test_image_mapping_validation.py  # ✨ Critical mapping tests
│   │   ├── test_data_builder_validation.py   # End-to-end validation
│   │   ├── test_database.py             # Database operations
│   │   └── test_models.py               # Data models
# knowledge_base/ tests removed as RAG was not used
│   └── cli/                        # CLI command tests
│       └── test_build_dataset.py
├── integration/                    # End-to-end tests
│   └── test_cli_integration.py
└── conftest.py                     # Test configuration
```

### Critical Validation Tests

The image mapping validation tests specifically target the issues that caused the refactor:

```python
# tests/unit/core/test_image_mapping_validation.py
def test_known_image_question_validation():
    """Test validation against known problematic image questions."""
    # Tests specific question IDs: 21, 22, 209, 226, 275, etc.
    # Ensures all 42 image questions are properly detected and mapped
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/core/                    # Core component tests
pytest tests/unit/core/test_image_*        # Image mapping tests only
pytest tests/integration/                  # Integration tests

# Run with coverage (required: 80%+)
pytest --cov=src --cov-report=term-missing

# Run specific critical tests
pytest tests/unit/core/test_image_mapping_validation.py -v
pytest tests/unit/core/test_data_builder_validation.py -v
```

## 🔧 Updated Development Workflow (Phase 1.8)

### For New Contributors

1. **Clone and Setup**:
```bash
git clone https://github.com/yourusername/integran.git
cd integran
make env-create
conda activate integran
make install
```

2. **Run Tests** (should all pass):
```bash
pytest  # All 169 tests should pass
```

3. **Try the Application**:
```bash
integran-setup --language en  # Setup with English preference
integran --stats              # View current status
```

### For Core Development

If you're working on the data pipeline or core components:

1. **Understand the Architecture**:
   - Review `src/core/data_builder.py` - main orchestrator
   - Check `src/core/image_processor.py` - image mapping logic
   - Study `src/core/answer_engine.py` - multilingual generation

2. **Work with Test Data**:
```bash
# The tests use mock data, but you can check real data:
ls data/extraction_checkpoint.json  # Source of truth
ls data/images/                     # Extracted images
```

3. **Build Complete Dataset** (requires API keys):
```bash
# Only if you have Gemini API configured
integran-build-dataset --status     # Check current status
# integran-build-dataset --force-rebuild  # Full rebuild (~$80 cost)
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass (169 tests)
5. Run quality checks: `make check-all`
6. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write docstrings for modules and classes
- Maintain test coverage above 80%
- Use descriptive commit messages

## 🚀 Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag
4. Push to GitHub
5. GitHub Actions will handle the release

## 📚 Additional Resources

- **[Dataset Generation Guide](./dataset-generation-guide.md)** - Complete workflow for generating final_dataset.json
- [Integration Exam Research](./integration_exam_research.md) - Background research

For questions or support, please open an issue on GitHub.

---

## 📋 Phase 1.8 Summary for Developers

### What Changed in the Refactor

**Problem Solved**: Fixed critical image mapping issues where 25/42 image questions had broken image paths.

**Solution**: Complete architecture refactor with three new core components:
1. **ImageProcessor** - AI vision for accurate image descriptions and mapping
2. **AnswerEngine** - Multilingual answer generation in 5 languages
3. **DataBuilder** - Unified pipeline replacing scattered broken utilities

### Key Developer Benefits

✅ **Single Command**: `integran-build-dataset` replaces 5+ broken commands  
✅ **Comprehensive Tests**: 169 tests including critical image mapping validation  
✅ **Quality Assurance**: All 42 image questions now properly mapped and described  
✅ **Multilingual Support**: English, German, Turkish, Ukrainian, Arabic  
✅ **Enhanced RAG**: Official German government sources via Firecrawl  
✅ **Future-Ready**: Clean architecture for UI and feature development  

### For Different Developer Types

**End Users**: No changes needed - app works out of the box with pre-extracted data  
**Contributors**: Focus on tests and quality - all critical mapping issues resolved  
**Core Developers**: Use `integran-build-dataset` for complete pipeline (requires API keys)  
**UI Developers**: New multilingual data format ready for display in terminal UI  

## 🎯 Phase 3.0 Architecture Summary

### Why This Architecture for Spaced Repetition?

The new architecture addresses the core requirements for an effective spaced repetition learning system:

#### 1. **Scientific Learning Foundation**
- **FSRS Algorithm**: 20-30% more efficient than traditional SM-2
- **Memory Modeling**: DSR model tracks individual learning patterns
- **Evidence-Based**: Built on cognitive psychology research

#### 2. **Local-First Privacy**
- **SQLite Storage**: All learning data stays on user's device  
- **No Cloud Dependencies**: Works completely offline
- **Data Portability**: Export/import for cross-device sync

#### 3. **Adaptive Intelligence**
- **Leech Detection**: Identifies problematic questions automatically
- **Parameter Optimization**: Personalizes algorithm to user's memory
- **Interleaved Practice**: Improves conceptual understanding

#### 4. **User Experience Excellence**
- **Rich Terminal UI**: Modern CLI with progress visualization
- **Real-Time Analytics**: Immediate feedback on learning progress
- **Multilingual Support**: 5-language explanations

#### 5. **Developer-Friendly Design**
- **Modular Architecture**: Easy to extend and maintain
- **Comprehensive Testing**: 169+ tests for reliability
- **Clean Separation**: UI, logic, and data layers clearly separated

### Implementation Priorities

**Phase 3.1 (Current)**: Terminal UI Framework with Rich/Textual
**Phase 3.2**: FSRS algorithm implementation and database integration  
**Phase 3.3**: Advanced features (analytics, leech management, interleaving)
**Phase 3.4**: Performance optimization and user testing

### For Different Developer Types

**🎯 UI Developers**: Focus on `src/ui/terminal/` - clean interfaces to learning engine
**🧠 Algorithm Developers**: Work in `src/spaced_repetition/` - modular algorithm design  
**📊 Data Developers**: Concentrate on `src/core/` - SQLite schema and analytics
**🔧 Platform Developers**: Extend architecture for desktop/mobile in future phases

This architecture transforms Integran from a simple quiz app into a scientifically-backed learning system that optimizes long-term knowledge retention through proven spaced repetition techniques.

**Last Updated**: January 11, 2025 - Phase 3.0 Spaced Repetition Architecture Complete