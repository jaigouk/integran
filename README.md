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

A comprehensive, terminal-based training application for the German Integration Exam (Leben in Deutschland Test) *currently in development*. Will feature multilingual support, AI-powered explanations, and intelligent learning techniques to maximize exam success.

## 🎯 Purpose

The "Leben in Deutschland" test consists of 460 questions (300 general + 160 state-specific) covering German society, laws, culture, and history. This trainer helps you master all questions through:

- **Multilingual Support**: Explanations in 5 languages (English, German, Turkish, Ukrainian, Arabic)
- **Image Question Support**: Visual questions with detailed image descriptions
- **AI-Powered Explanations**: Comprehensive explanations for all questions
- **Interactive Practice Sessions**: Multiple learning modes
- **Smart Failure Tracking**: Adaptive learning system
- **Spaced Repetition Learning**: Optimize retention
- **Progress Monitoring**: Track your improvement

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
# Start in a specific mode
integran --mode random

# Review only failed questions
integran --review

# Practice specific category
integran --category "Grundrechte"

# Export progress report
integran --export-stats
```

## 🚀 Features (Planned & In Development)

### ✅ **Currently Implemented**
- **Dataset Generation**: Extract questions from official BAMF PDF
- **AI Processing**: Generate multilingual explanations using Google Gemini
- **Image Processing**: Analyze and describe visual questions
- **Data Validation**: Comprehensive question and answer validation
- **Database Schema**: SQLite backend with progress tracking

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

#### 4. **Intelligent Learning System**
- **Failure Tracking**: Automatically saves incorrectly answered questions
- **Spaced Repetition**: Review difficult questions more frequently
- **Performance Analytics**: Track your progress over time
- **Category Insights**: Identify weak areas for focused study

#### 5. **Enhanced Terminal UI**
- Color-coded feedback (✅ correct / ❌ incorrect)
- **Image Display**: Shows relevant images for visual questions
- **Multilingual Explanations**: Switch between explanation languages
- Clear navigation menus
- Progress indicators
- Unicode support for German characters
- Responsive design for various terminal sizes

## 📈 Progress Tracking (Coming Soon)

View your progress with:
```bash
integran --stats  # Not yet functional
```

This will show:
- Total questions mastered
- Success rate by category
- Learning curve visualization
- Recommended focus areas

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
- ✅ **Dataset Building Tools**: `integran-build-dataset`, `integran-direct-extract`
- ✅ **PDF Processing**: Extract questions from official BAMF PDF
- ✅ **AI Integration**: Generate multilingual explanations
- 🚧 **Terminal Trainer**: Under development
- 🚧 **Practice Sessions**: Coming soon

**Note**: The dataset building tools are functional for developers working with question extraction and processing.

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
# Check dataset build status
integran-build-dataset --status

# Build complete multilingual dataset
integran-build-dataset --verbose

# Backup existing data
integran-backup-data backup
```

## 📝 License

This project is licensed under the MIT License 

---

**Good luck with your exam! 🍀**

---

