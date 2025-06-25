# Integran

A comprehensive, terminal-based training application for the German Integration Exam (Leben in Deutschland Test) that helps you master all 460 exam questions through intelligent spaced repetition learning.

🚧 **Status**: In active development - Terminal UI complete, core learning system functional

## ✨ Features

### 🧠 Smart Learning System
- **Scientific Spaced Repetition**: Uses FSRS algorithm to review questions at the optimal time for long-term retention
- **Personalized Scheduling**: Adapts to your memory patterns and learning speed
- **Automatic Reviews**: No need to decide what to study - the system knows what you need

### 🌍 Complete Question Database
- **460 Official Questions**: All 300 general + 160 state-specific questions from the official exam
- **5 Language Support**: Explanations in English, German, Turkish, Ukrainian, and Arabic
- **Visual Questions**: Image-based questions with detailed descriptions and mnemonic images
- **AI-Generated Explanations**: Comprehensive explanations with memory aids for every question

### 📊 Progress Tracking
- **Real-time Analytics**: Track your retention rate, mastered questions, and learning velocity
- **Weak Area Detection**: Identifies topics where you need more practice
- **Study Streak Tracking**: Maintain consistent daily practice
- **Performance Insights**: Detailed statistics by category and difficulty

### 🎯 Multiple Practice Modes
- **Smart Review**: AI-scheduled reviews based on your memory patterns
- **Random Practice**: Varied question selection for comprehensive coverage
- **Category Focus**: Target specific topics like Politik, Geschichte, or Grundrechte
- **Failed Questions**: Review only questions you got wrong

## 🚀 Quick Start

### Installation

1. **Install Conda** (if not already installed):
   ```bash
   # Download and install Miniconda from https://docs.conda.io/en/latest/miniconda.html
   ```

2. **Clone and Setup**:
   ```bash
   git clone https://github.com/jaigouk/integran.git
   cd integran
   
   # Create environment and install
   conda create -n integran python=3.12 -y
   conda activate integran
   
   # Install uv package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install dependencies
   uv pip install -e ".[dev]"
   ```

3. **Start Learning**:
   ```bash
   integran
   ```

That's it! The app will automatically initialize the database on first run.

### Using the App

When you start Integran, you'll see an interactive menu:

```
╔════════════════════════════════════════╗
║        Integran - Exam Trainer         ║
╚════════════════════════════════════════╝

1. 📚 Practice Mode (Random)
2. 📖 Sequential Practice
3. 🎯 Practice by Category
4. 🔄 Review Failed Questions
5. 📈 View Statistics
6. ⚙️  Settings
7. 🚪 Exit

Select option:
```

Simply choose your practice mode and start learning!

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

### Command Line Options

```bash
# Available options:
integran                           # Start interactive menu
integran --mode random             # Start in random practice mode
integran --review                  # Review only failed questions  
integran --category "Grundrechte"  # Practice specific category
integran --stats                   # Display learning statistics
integran --reset                   # Reset all progress data
```

## 🎯 About the Exam

The "Leben in Deutschland" (LiD) test consists of:
- **33 Questions Total**: 30 general + 3 state-specific questions
- **Multiple Choice Format**: Select from 4 answer options
- **Passing Score**: 17 correct answers (just over 50%)
- **Topics Covered**: German society, laws, culture, history, and democratic values

This app includes all 460 possible questions from the official question pool, ensuring you're fully prepared for any combination that appears on your exam.

## 📋 System Requirements

- Python 3.12+
- Conda (Anaconda or Miniconda)
- Terminal with UTF-8 support
- 100MB free disk space


## ⚙️ Settings

### Language Options

Choose your preferred explanation language in the app settings:
- 🇬🇧 English (default)
- 🇩🇪 German (Deutsch)
- 🇹🇷 Turkish (Türkçe)
- 🇺🇦 Ukrainian (Українська)
- 🇸🇦 Arabic (العربية)

### Study Preferences

Configure your learning experience:
- **Daily Question Limit**: Set how many new questions to learn per day
- **Show Explanations**: Toggle detailed explanations after each answer
- **Image Display**: Enable/disable visual questions
- **Color Theme**: Auto, light, or dark mode


## 🙏 Acknowledgments

- Questions sourced from the official BAMF exam catalog
- AI-powered explanations using Google Gemini
- Multilingual translations for diverse communities
- Inspired by Anki's spaced repetition algorithm
- Built with love for the integration community

---

## 👩‍💻 For Developers

See our comprehensive [Developer Guide](docs/developer-guide.md) for:
- Architecture details (DDD, CQRS, Event-Driven)
- Development setup and environment
- Testing and code quality standards
- Dataset building process
- Contributing guidelines

### Quick Developer Setup

```bash
# Clone and setup development environment
git clone https://github.com/jaigouk/integran.git
cd integran
make env-create
conda activate integran
make install

# Run tests
make test

# Run all quality checks
make check-all
```

### Project Structure

```
src/
├── domain/         # Business logic (FSRS algorithm, domain services)
├── application/    # Commands, queries, event handlers
├── infrastructure/ # Database, external APIs, repositories
├── presentation/   # Terminal UI (Textual/Rich)
└── main.py        # Entry point
```

Architecture Flow:
```
  Presentation Layer (UI, Controllers)
       ↓ calls (via commands/queries)
  Application Layer (Command/Query Handlers)  
       ↓ uses (via interfaces)
  Domain Layer (Business Logic, defines interfaces)
       ↑ implemented by (Dependency Inversion)
  Infrastructure Layer (Database, External APIs)
```

## 📝 License

This project is licensed under the Apache License 2.0 

---

**Good luck with your exam! 🍀**

---

