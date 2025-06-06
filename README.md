# Integran

A terminal-based training application for the German Integration Exam (Leben in Deutschland Test). Built with spaced repetition and intelligent progress tracking to maximize learning efficiency.

*Future versions will include mobile and desktop applications.*

## 🎯 Purpose

The "Leben in Deutschland" test consists of 310 questions covering German society, laws, culture, and history. This trainer helps you master all questions through:

- Interactive practice sessions
- Smart failure tracking
- Spaced repetition learning
- Progress monitoring

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

## 🙏 Acknowledgments

- Questions sourced from the official BAMF exam catalog
- Inspired by Anki's spaced repetition algorithm
- Built with love for the integration community

## 👩‍💻 For Developers

If you're contributing to this project or want to modify the question extraction process, see our comprehensive [Developer Guide](docs/developer-guide.md).

The developer guide covers:
- 📊 Data structure and database schema
- 🤖 PDF question extraction setup
- 🔧 Development environment setup
- 🧪 Testing and code quality
- 📝 Contributing guidelines

## 📝 License

This project is licensed under the MIT License 

---

**Good luck with your exam! 🍀**

---

