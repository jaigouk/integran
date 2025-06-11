# Integran

A comprehensive, terminal-based training application for the German Integration Exam (Leben in Deutschland Test). Features multilingual support, AI-powered explanations, and intelligent learning techniques to maximize exam success.

*Future versions will include mobile and desktop applications.*

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

### Quick Start

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

## 🚀 Features

### 1. **Multilingual Learning Experience**
- **5 Language Support**: English (primary), German, Turkish, Ukrainian, Arabic
- **Cultural Context**: Explanations adapted for different backgrounds
- **Language Selection**: Choose your preferred explanation language

### 2. **Advanced Question Types**
- **Text Questions**: Traditional multiple-choice questions
- **Image Questions**: Visual questions with detailed image descriptions
- **State-Specific Questions**: Federal state questions for regional exams
- **AI-Enhanced Descriptions**: Automatic image analysis and context

### 3. **Multiple Practice Modes**
- **Random Practice**: Questions shuffled for varied learning
- **Sequential Practice**: Work through questions in order
- **Targeted Practice**: Jump to specific question numbers
- **Category Practice**: Focus on specific topics (e.g., Grundrechte, Geschichte)

### 4. **Intelligent Learning System**
- **Failure Tracking**: Automatically saves incorrectly answered questions
- **Spaced Repetition**: Review difficult questions more frequently
- **Performance Analytics**: Track your progress over time
- **Category Insights**: Identify weak areas for focused study

### 5. **Enhanced Terminal UI**
- Color-coded feedback (✅ correct / ❌ incorrect)
- **Image Display**: Shows relevant images for visual questions
- **Multilingual Explanations**: Switch between explanation languages
- Clear navigation menus
- Progress indicators
- Unicode support for German characters
- Responsive design for various terminal sizes

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

## 📋 Prerequisites

- Conda (Anaconda or Miniconda)
- Terminal with UTF-8 support
- 100MB free disk space (includes images and multilingual data)

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

**Note**: The app comes with pre-built multilingual data - no additional setup required.

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

