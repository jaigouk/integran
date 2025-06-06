# Integran

A terminal-based training application for the German Integration Exam (Leben in Deutschland Test). Built with spaced repetition and intelligent progress tracking to maximize learning efficiency.

*Future versions will include mobile and desktop applications.*

## 🎯 Purpose

The "Leben in Deutschland" test consists of 310 questions covering German society, laws, culture, and history. This trainer helps you master all questions through:

- Interactive practice sessions
- Smart failure tracking
- Spaced repetition learning
- Progress monitoring

## 🚀 Features

### 1. **Multiple Practice Modes**
- **Random Practice**: Questions shuffled for varied learning
- **Sequential Practice**: Work through questions in order
- **Targeted Practice**: Jump to specific question numbers
- **Category Practice**: Focus on specific topics (e.g., Grundrechte, Geschichte)

### 2. **Intelligent Learning System**
- **Failure Tracking**: Automatically saves incorrectly answered questions
- **Spaced Repetition**: Review difficult questions more frequently
- **Performance Analytics**: Track your progress over time
- **Category Insights**: Identify weak areas for focused study

### 3. **Enhanced Terminal UI**
- Color-coded feedback (✅ correct / ❌ incorrect)
- Clear navigation menus
- Progress indicators
- Unicode support for German characters
- Responsive design for various terminal sizes

## 📋 Prerequisites

- Conda (Anaconda or Miniconda)
- Terminal with UTF-8 support
- 50MB free disk space

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/integran.git
cd integran
```

2. Create and activate conda environment:
```bash
conda create -n integran python=3.12 -y
conda activate integran
```

3. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

4. Install dependencies:
```bash
uv pip install -e ".[dev]"
```

### Alternative: Using Makefile
```bash
# Quick setup with make
make env-create
conda activate integran
make install
```

5. Run the setup script to initialize the database:
```bash
integran-setup
```

## 🎮 Usage

### Basic Usage

Start the trainer:
```bash
integran
```

### Command Line Options

```bash
# Start in a specific mode
integran --mode random

# Review only failed questions
integran --review

# Practice specific category
integran --category "Grundrechte"

# Export progress report
integran --export-stats
```

### Interactive Menu

Upon starting, you'll see:
```
╔════════════════════════════════════════╗
║        Integran - Exam Trainer         ║
╚════════════════════════════════════════╝

1. 📚 Practice Mode (Random)
2. 📖 Sequential Practice
3. 🎯 Practice by Question Number
4. 📊 Category Practice
5. 🔄 Review Failed Questions
6. 📈 View Statistics
7. ⚙️  Settings
8. 🚪 Exit

Select option:
```

## 📊 Data Structure

Questions are stored in `questions.json`:
```json
{
  "id": 1,
  "question": "In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
  "options": [
    "hier Religionsfreiheit gilt.",
    "die Menschen Steuern zahlen.",
    "die Menschen das Wahlrecht haben.",
    "hier Meinungsfreiheit gilt."
  ],
  "correct": "hier Meinungsfreiheit gilt.",
  "category": "Grundrechte",
  "difficulty": "medium"
}
```

## 🗄️ Database Schema

The app uses SQLite to track your progress:

- **failures**: Tracks incorrectly answered questions
- **sessions**: Records practice session data
- **progress**: Monitors overall improvement
- **categories**: Stores category-specific performance

## 🔧 Configuration

### Basic Configuration

Edit `data/config.json` to customize:
```json
{
  "repetition_interval": 3,
  "max_daily_questions": 50,
  "show_explanations": true,
  "color_mode": "auto"
}
```

### Environment Variables (Optional)

These environment variables are **ONLY needed for developers** who want to extract questions from the PDF using AI. **End users don't need these** as the app comes with pre-extracted question data.

#### Question Extraction (Developer Only)

The application supports **two authentication methods** for Google Gemini AI:

##### Method 1: Vertex AI with Service Account (Recommended)
```bash
# Required variables
export USE_VERTEX_AI=true                           # Enable Vertex AI authentication (default)
export GCP_PROJECT_ID="your-gcp-project"           # Google Cloud Project ID
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"  # Service account JSON file
export GCP_REGION="us-central1"                    # Google Cloud region (optional)
export GEMINI_MODEL="gemini-2.5-pro-preview-06-05" # Model version (optional)
```

##### Method 2: API Key (Legacy)
```bash
# Required variables  
export USE_VERTEX_AI=false                         # Disable Vertex AI, use API key instead
export GEMINI_API_KEY="your-gemini-api-key"        # Google AI API key
export GCP_PROJECT_ID="your-gcp-project"           # Google Cloud Project ID
export GCP_REGION="us-central1"                    # Google Cloud region (optional)
export GEMINI_MODEL="gemini-2.5-pro-preview-06-05" # Model version (optional)
```

##### Required vs Optional Variables:

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

⚠️ **Important Notes:**
- **Cost Warning**: Using the Gemini API will incur charges on your Google Cloud account
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

## 📈 Progress Tracking

View your progress with:
```bash
integran --stats
```

This shows:
- Total questions mastered
- Success rate by category
- Learning curve visualization
- Recommended focus areas

## 📝 License

This project is licensed under the MIT License 

## 🙏 Acknowledgments

- Questions sourced from the official BAMF exam catalog
- Inspired by Anki's spaced repetition algorithm
- Built with love for the integration community

---

**Good luck with your exam! 🍀**