# Integran

> ⚠️ **DEVELOPMENT STATUS WARNING** ⚠️
> 
> **This project is currently under heavy development and the terminal application is NOT READY for end users yet.**
> 
> - 📋 Dataset generation and processing tools are functional
> - 🚧 Terminal trainer interface is still being developed  
> - 🔧 Core application features are being implemented
> - 📱 Mobile and desktop versions are planned for future releases
>
> **For Developers**: The dataset building tools (`integran-build-dataset`, `integran-direct-extract`) are working and can be used to generate question datasets from PDF sources.

A comprehensive, terminal-based training application for the German Integration Exam (Leben in Deutschland Test) *currently in development*. Features an intelligent study system that learns from your performance and schedules review sessions at the optimal time to maximize long-term memory retention and exam success.

## 🎯 Purpose

The "Leben in Deutschland" test consists of 460 questions (300 general + 160 state-specific) covering German society, laws, culture, and history. This trainer helps you master all questions through:

- **🧠 Smart Learning System**: Uses scientifically-proven spaced repetition to review questions at the perfect time when you're about to forget them
- **📊 Personalized Scheduling**: The system learns from your performance and adapts to your memory patterns
- **🌍 Multilingual Support**: Explanations in 5 languages (English, German, Turkish, Ukrainian, Arabic)
- **🖼️ Image Question Support**: Visual questions with detailed AI-generated descriptions
- **🤖 AI-Powered Explanations**: Comprehensive explanations for all questions with memory aids
- **📈 Progress Tracking**: See your learning progress and retention rates in real-time
- **🎯 Intelligent Review**: Focus more time on difficult questions, less on easy ones

## 🧠 How the Smart Learning System Works

### The Science Behind Spaced Repetition

Most people forget 50% of new information within an hour and 90% within a week. Traditional studying fights this by cramming, but that's inefficient. Our app uses **spaced repetition** - a scientifically-proven method that schedules reviews at the exact moment you're about to forget something.

### What Makes Our System Special

**🤖 FSRS Algorithm**: We use the Free Spaced Repetition Scheduler (FSRS), the most advanced spaced repetition algorithm available. It's 20-30% more efficient than traditional methods.

**🧪 How It Works**:
1. **Learn New Questions**: Start with any question from the 460-question database
2. **Rate Your Performance**: After each answer, tell us how difficult it was (Again/Hard/Good/Easy)
3. **Smart Scheduling**: The system calculates the perfect time to review each question based on:
   - How well you knew it
   - How many times you've seen it
   - Your personal forgetting patterns
4. **Adaptive Learning**: Questions you struggle with appear more often, easy ones less frequently
5. **Long-term Retention**: Achieve 90%+ retention rate with minimal study time

### Why This Works Better Than Traditional Study

- **No Wasted Time**: Don't review things you already know well
- **Perfect Timing**: Review questions just before you forget them
- **Personalized**: Adapts to YOUR memory, not average students
- **Proven Results**: Based on decades of memory research
- **Efficient**: Learn more in less time

### Real-World Example

Instead of reviewing all 460 questions repeatedly:
- Day 1: Learn 20 new questions
- Day 2: Review 5 from yesterday + 15 new ones
- Day 7: Review the questions you're starting to forget
- Day 30: Quick review of older material to maintain retention

The system handles all the scheduling automatically - you just study what it shows you!

## 🎮 Usage

> **Note**: The terminal training interface is currently under development. The commands below show the planned functionality.

### Quick Start (When Ready)

1. **Install and Setup** (see installation section below)
2. **Start the trainer:**
   ```bash
   integran
   ```
3. **Choose your practice mode** from the interactive menu

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

### Command Line Options

```bash
# Planned Command Line Options (not yet implemented):
# integran --mode random          # Start in a specific mode
# integran --review               # Review only failed questions  
# integran --category "Grundrechte"  # Practice specific category
# integran --export-stats         # Export progress report
```

## 🚀 Features (Planned & In Development)

### ✅ **Currently Implemented**
- **Complete Dataset**: ✅ All 460 questions with multilingual explanations (EN/DE/TR/UK/AR) and images
- **Dataset Generation**: ✅ Extraction tools from official BAMF PDF
- **AI Processing**: ✅ Multilingual explanations using Google Gemini
- **Image Processing**: ✅ Visual question analysis and descriptions  
- **Data Validation**: ✅ Comprehensive question and answer validation
- **Database Schema**: ✅ SQLite backend with progress tracking ready

### 🚧 **In Development** 

#### 1. **Multilingual Learning Experience**
- **5 Language Support**: English (primary), German, Turkish, Ukrainian, Arabic
- **Cultural Context**: Explanations adapted for different backgrounds
- **Language Selection**: Choose your preferred explanation language

#### 2. **Advanced Question Types**
- **Text Questions**: Traditional multiple-choice questions
- **Image Questions**: Visual questions with detailed image descriptions
- **State-Specific Questions**: Federal state questions for regional exams
- **AI-Enhanced Descriptions**: Automatic image analysis and context

#### 3. **Multiple Practice Modes**
- **Random Practice**: Questions shuffled for varied learning
- **Sequential Practice**: Work through questions in order
- **Targeted Practice**: Jump to specific question numbers
- **Category Practice**: Focus on specific topics (e.g., Grundrechte, Geschichte)

#### 4. **Intelligent Learning System (FSRS-Powered)**
- **Smart Scheduling**: Questions appear at the perfect time to maximize retention
- **Difficulty Tracking**: System learns which questions are hard for YOU specifically  
- **Automatic Review**: No need to manually decide what to study - the system knows
- **Performance Analytics**: See your retention rate, learning velocity, and progress trends
- **Leech Detection**: Identifies questions you repeatedly struggle with and provides targeted help
- **Category Insights**: Discover your weak areas and get personalized study recommendations

#### 5. **Enhanced Terminal UI**
- Color-coded feedback (✅ correct / ❌ incorrect)
- **Image Display**: Shows relevant images for visual questions
- **Multilingual Explanations**: Switch between explanation languages
- Clear navigation menus
- Progress indicators
- Unicode support for German characters
- Responsive design for various terminal sizes

## 📈 Progress Tracking & Analytics (Coming Soon)

The system provides detailed insights into your learning:

### Real-Time Metrics
- **📊 Retention Rate**: Your current memory retention percentage (target: 90%+)
- **🎯 Questions Mastered**: How many questions you can reliably answer
- **⚡ Learning Velocity**: How quickly you're progressing through material
- **📅 Study Streak**: Consecutive days of consistent practice

### Smart Insights
- **🔥 Weak Areas**: Categories where you need more practice
- **🏆 Strong Areas**: Topics you've mastered
- **📈 Learning Curve**: Visual progress over time
- **🎲 Recommended Daily Reviews**: Personalized study load suggestions

### Advanced Features
- **🩺 Leech Detection**: Identifies consistently difficult questions
- **🔄 Review Forecast**: Shows upcoming study sessions
- **🎚️ Difficulty Adjustment**: Automatic optimization based on your performance
- **📊 Category Breakdown**: Detailed performance by topic (Politik, Geschichte, etc.)

## 📋 Prerequisites

- Conda (Anaconda or Miniconda)
- Terminal with UTF-8 support
- 100MB free disk space (includes images and multilingual data)

## 🛠️ Installation

> **Current Status**: Installation sets up the development environment and dataset building tools. The main training application is not yet functional.

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

### What Works Currently
- ✅ **Complete Dataset**: All 460 questions with multilingual explanations available in `data/final_dataset.json`
- ✅ **Dataset Scripts**: Full pipeline in `scripts/` directory for dataset processing
- ✅ **PDF Processing**: Questions extracted from official BAMF PDF
- ✅ **AI Integration**: Multilingual explanations generated using Google Gemini
- ✅ **Database Setup**: `integran-setup` initializes SQLite database
- 🚧 **Terminal Trainer**: Under development
- 🚧 **Practice Sessions**: Coming soon

**Note**: The complete dataset (460 questions with 5-language explanations) is ready. Only the terminal trainer interface needs implementation.

## 🔧 Configuration

### Basic Configuration

Edit `data/config.json` to customize:
```json
{
  "repetition_interval": 3,
  "max_daily_questions": 50,
  "show_explanations": true,
  "show_images": true,
  "explanation_language": "en",
  "color_mode": "auto"
}
```

### Language Settings

Available explanation languages:
- `"en"` - English (default)
- `"de"` - German (Deutsch)
- `"tr"` - Turkish (Türkçe)
- `"uk"` - Ukrainian (Українська)
- `"ar"` - Arabic (العربية)

### Developer Configuration

For developers working with the dataset building:

```bash
# Environment variables for dataset building (developers only)
export GEMINI_API_KEY="your-key"              # Required: For dataset building
export GCP_PROJECT_ID="your-project"          # Required: For AI processing
```

## 🔄 CI/CD

This project supports multiple CI/CD platforms:

### GitHub Actions (`.github/workflows/`)
- **Main CI Pipeline**: Automated testing, linting, and type checking
- **Security Checks**: Weekly security scans and dependency vulnerability checks  
- **Release Automation**: Automated releases when tags are pushed
- **Dependabot**: Automatic dependency updates

### Gitea Actions (`.gitea/workflows/`)
- **Self-hosted CI**: Runs on custom DietPi runner
- **Docker Testing**: Full Docker build and test pipeline
- **Fallback Testing**: Local Python environment if Docker unavailable

### Available Make Commands
```bash
# Quality checks
make lint          # Run ruff linter and formatting checks
make typecheck     # Run mypy type checking  
make test          # Run pytest test suite
make coverage      # Run tests with coverage report
make check-all     # Run all quality checks

# Docker workflows
make docker-build  # Build production Docker image
make docker-test   # Run tests in Docker container
make docker-run    # Run application in Docker

# Environment management
make env-create    # Create conda environment
make install       # Install dependencies with uv
make clean         # Remove build artifacts
```

Both CI systems exclude slow integration tests that require API calls, ensuring fast and reliable builds.

## 🙏 Acknowledgments

- Questions sourced from the official BAMF exam catalog
- AI-powered explanations using Google Gemini
- Multilingual translations for diverse communities
- Inspired by Anki's spaced repetition algorithm
- Built with love for the integration community

## 👩‍💻 For Developers

If you're contributing to this project or want to modify the dataset building process, see our comprehensive [Developer Guide](docs/developer-guide.md).

The developer guide covers:
- 📊 Data structure and database schema
- 🏗️ Complete dataset building with `integran-build-dataset`
- 🤖 PDF question extraction and AI processing
- 🌍 Multilingual explanation generation
- 🖼️ Image processing and description system
- 🔧 Development environment setup
- 🧪 Testing and code quality
- 📝 Contributing guidelines

### Quick Developer Commands

```bash
# Available Commands:
integran-setup                        # Database initialization and setup

# Planned Commands (not yet implemented):
# integran-build-dataset --status      # Check dataset build status
# integran-build-dataset --verbose     # Build complete multilingual dataset  
# integran-backup-data backup          # Backup existing data
```

## 📝 License

This project is licensed under the Apache License 2.0 

---

**Good luck with your exam! 🍀**

---

