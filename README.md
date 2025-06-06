# IntegRate

Interactive trainer for the German Integration Exam (Leben in Deutschland Test)

A terminal-based interactive application designed to help people prepare for the German Integration Exam (Leben in Deutschland Test). This app uses spaced repetition and intelligent tracking to maximize learning efficiency.

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
git clone https://github.com/yourusername/integrate.git
cd integrate
```

2. Create and activate conda environment:
```bash
conda create -n integrate python=3.12 -y
conda activate integrate
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
conda activate integrate
make install
```

5. Run the setup script to initialize the database:
```bash
integrate-setup
```

## 🎮 Usage

### Basic Usage

Start the trainer:
```bash
integrate
```

### Command Line Options

```bash
# Start in a specific mode
integrate --mode random

# Review only failed questions
integrate --review

# Practice specific category
integrate --category "Grundrechte"

# Export progress report
integrate --export-stats
```

### Interactive Menu

Upon starting, you'll see:
```
╔════════════════════════════════════════╗
║           IntegRate - Exam Trainer     ║
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

Edit `data/config.json` to customize:
```json
{
  "repetition_interval": 3,
  "max_daily_questions": 50,
  "show_explanations": true,
  "color_mode": "auto"
}
```

## 📈 Progress Tracking

View your progress with:
```bash
integrate --stats
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