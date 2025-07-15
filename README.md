# Integran

Pass your German Integration Exam (Leben in Deutschland Test) with confidence! This smart terminal app helps you master all 460 exam questions using scientifically-proven spaced repetition learning.

## 🎯 About the Exam

The "Leben in Deutschland" test is required for German citizenship and permanent residency:
- **33 Questions**: 30 general + 3 state-specific
- **Passing Score**: 17 correct answers (51%)
- **Topics**: German society, laws, culture, history, and democratic values
- **Format**: Multiple choice (4 options per question)

## ✨ Why Integran?

### 🧠 Smart Learning That Works
- **Never forget what you learn**: Reviews questions at the perfect time before you forget
- **Study less, remember more**: Focus only on what you need, not what you already know
- **Personalized to YOUR memory**: Adapts to how fast YOU learn and forget

### 📚 Everything You Need
- **All 460 Official Questions**: Complete exam pool from BAMF
- **5 Languages**: Explanations in English, German, Turkish, Ukrainian, and Arabic
- **Visual Learning**: Images with memory aids for visual questions
- **AI Explanations**: Understand WHY each answer is correct

### 📈 Track Your Progress
- See your improvement day by day
- Know exactly when you'll be exam-ready
- Focus on your weak areas automatically

## 🚀 Getting Started

### Requirements
- Python 3.12+
- Conda (Miniconda or Anaconda)
- Terminal with UTF-8 support

### Install in 3 Steps

```bash
# 1. Clone the repository
git clone https://github.com/jaigouk/integran.git
cd integran

# 2. Set up environment
conda create -n integran python=3.12 -y
conda activate integran
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install -e ".[dev]"

# 3. Start learning!
integran
```

The app will set up everything on first run.

## 📱 Using the App

When you start Integran, choose how you want to study:

1. **📚 Smart Practice** - Let the AI decide what you need to study
2. **🎯 Category Practice** - Focus on specific topics (Politik, Geschichte, etc.)
3. **🔄 Failed Questions** - Review what you got wrong
4. **📈 View Progress** - See your learning statistics
5. **⚙️ Settings** - Choose your language and preferences

## 🧠 How It Works

### Smart Spaced Repetition

Forget cramming! Integran uses the scientifically-proven FSRS algorithm to help you remember 90%+ of what you learn:

1. **Answer a question** → Rate how hard it was (1-4)
2. **The app schedules your review** → Just before you'd forget
3. **Build permanent memory** → With less study time

### Example Study Pattern
- **Day 1**: Learn 20 new questions (30 min)
- **Day 2**: Quick review of 5 + 15 new (25 min)  
- **Week 1**: Review only what you're forgetting (20 min/day)
- **Month 1**: 150 questions mastered (15 min/day)
- **Month 3**: All 460 questions ready! 🎉

## 💡 Pro Tips

### Rate Honestly
After each question, rate 1-4:
- **1 (Again)**: Got it wrong → Review tomorrow
- **2 (Hard)**: Struggled but correct → Review in 2-3 days
- **3 (Good)**: Normal effort → Review in ~1 week
- **4 (Easy)**: Knew it instantly → Review in 2+ weeks

### Daily Practice Beats Cramming
- **15 minutes daily** > 3 hours weekly
- **Consistency** builds lasting memory
- **Trust the schedule** - it knows what you need

### Use Failed Questions
Questions you get wrong are learning opportunities. The app tracks these separately so you can focus on your weak spots.

## ⚙️ Settings & Options

### Languages Available
- 🇬🇧 English (default)
- 🇩🇪 German (Deutsch)
- 🇹🇷 Turkish (Türkçe)
- 🇺🇦 Ukrainian (Українська)
- 🇸🇦 Arabic (العربية)

### Command Line Options
```bash
integran                           # Start interactive menu
integran --mode random             # Random practice
integran --review                  # Failed questions only
integran --category "Politik"      # Practice specific topic
integran --stats                   # View your progress
```



## 🔧 Troubleshooting

**Installation issues?**
- Make sure you have Python 3.12+ and Conda installed
- Try `conda update conda` before installing

**App won't start?**
- Check your terminal supports UTF-8: `echo $LANG`
- On Windows, use Windows Terminal or Git Bash

**Questions not loading?**
- The app will initialize the database on first run
- If issues persist, try `integran --reset`

---

## 👩‍💻 For Developers

Want to contribute or customize? Check our [Developer Guide](docs/developer-guide.md) for:
- Architecture overview (DDD, CQRS, Event-Driven)
- Development setup
- Testing guidelines
- Contributing process

### Quick Dev Setup
```bash
git clone https://github.com/jaigouk/integran.git
cd integran
make env-create
conda activate integran
make install
make test  # Run tests
```

## 📝 License

Apache License 2.0

---

**Ready to pass your exam? Start learning with Integran today! 🍀**

