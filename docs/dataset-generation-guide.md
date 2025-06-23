# Dataset Generation Guide

This guide explains the complete German Integration Exam dataset generation process. **The dataset is now 100% complete** with all 460 questions and multilingual explanations.

## 📊 Current Status

✅ **COMPLETE**: 460/460 questions with full multilingual explanations  
✅ **All Issues Resolved**: JSON parsing errors fixed, missing questions recovered  
✅ **Production Ready**: `final_dataset.json` contains the complete dataset  

## 🗂️ File Structure

### Essential Files (Production)
| File | Purpose | Status |
|------|---------|--------|
| `final_dataset.json` | **Complete dataset for app** | ✅ 460/460 questions |
| `gesamtfragenkatalog-lebenindeutschland.pdf` | Source PDF document | ✅ Complete |
| `images/*.png` | Question images (92 files) | ✅ Complete |
| `direct_extraction.json` | Original PDF extraction (backup) | ✅ 460 questions |

### Optional Files (Features)
| File | Purpose | Status |
|------|---------|--------|
| `config.json` | Application configuration | ✅ Optional |
| `knowledge_base/` | RAG knowledge base | ✅ Optional |
| `vector_store/` | Vector embeddings | ✅ Optional |

## 🛠️ Core Scripts (Maintained)

### Essential Scripts
| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/finalize_dataset.py` | Create final dataset | After any data changes |
| `scripts/verify_dataset.py` | Validate dataset integrity | After modifications |
| `scripts/generate_explanations_single.py` | Process individual questions | Fix specific questions |

### Development Scripts  
| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/extract_images.py` | Extract images from PDF | New PDF versions |
| `scripts/fix_image_answers.py` | AI-powered answer verification | Image question issues |
| `scripts/create_working_dataset.py` | Create working dataset from sources | Development setup |

## 📊 Complete Data Pipeline

```
┌─────────────────────────┐
│  PDF Source Document    │
│ gesamtfragenkatalog-    │  ✅ Complete
│ lebenindeutschland.pdf  │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐    ┌──────────────────────┐
│    Extract Questions    │───▶│ direct_extraction.   │  ✅ 460 questions
│    from PDF             │    │ json                 │
└─────────────────────────┘    └──────────────────────┘
           │
           ▼
┌─────────────────────────┐    ┌──────────────────────┐
│    Extract Images       │───▶│ data/images/*.png    │  ✅ 92 images
│    from PDF             │    │                      │
└─────────────────────────┘    └──────────────────────┘
           │
           ▼
┌─────────────────────────┐    ┌──────────────────────┐
│    Fix Image Answers    │───▶│ Verified answers     │  ✅ All correct
│    using AI Vision      │    │                      │
└─────────────────────────┘    └──────────────────────┘
           │
           ▼
┌─────────────────────────┐    ┌──────────────────────┐
│    Generate             │───▶│ final_dataset.json   │  ✅ 460/460 complete
│    Multilingual         │    │ (READY FOR APP)      │
│    Explanations         │    │                      │
└─────────────────────────┘    └──────────────────────┘
```

## 🚀 Quick Start (Most Users)

**For App Development** (No API keys needed):
```bash
# 1. Setup environment
conda create -n integran python=3.12 -y
conda activate integran
uv pip install -e ".[dev]"

# 2. Use existing complete dataset
ls -la data/final_dataset.json  # Should show ~4.5MB file with 460 questions

# 3. Run the app
integran
```

## 🔧 Maintenance Tasks

### Verify Dataset Integrity
```bash
# Check dataset completeness
python scripts/verify_dataset.py

# Quick status check
echo "Dataset has $(jq '.questions | length' data/final_dataset.json) questions"
echo "Missing: $(jq '.metadata.missing_count' data/final_dataset.json) questions"
```

### Regenerate Final Dataset (if needed)
```bash
# Only needed if source data is modified
python scripts/finalize_dataset.py
```

### Fix Individual Questions (Advanced)
```bash
# Process a specific question with AI explanations
python scripts/generate_explanations_single.py --question-id 123

# Re-finalize dataset after fixes
python scripts/finalize_dataset.py
```

## 🧑‍💻 Developer Workflow

### Full Regeneration (Requires API Keys)

**Prerequisites:**
```bash
# Required environment variables
export GCP_PROJECT_ID="your-gcp-project"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Optional for enhanced RAG features
export FIRECRAWL_API_KEY="your-firecrawl-key"
```

**Complete Regeneration Process:**
```bash
# 1. Extract questions from PDF (if starting fresh)
python src/cli/direct_extract.py

# 2. Extract images for visual questions
python scripts/extract_images.py

# 3. Verify and fix image question answers
python scripts/fix_image_answers.py

# 4. Generate multilingual explanations (takes 2-3 hours)
for i in {1..460}; do
    python scripts/generate_explanations_single.py --question-id $i
done

# 5. Create final dataset
python scripts/finalize_dataset.py

# 6. Verify result
python scripts/verify_dataset.py
```

## 🏗️ Dataset Structure

The complete `final_dataset.json` contains:

```json
{
  "questions": {
    "1": {
      "question_id": 1,
      "question": "In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil ...",
      "options": ["hier Religionsfreiheit gilt.", "die Menschen Steuern zahlen.", "die Menschen das Wahlrecht haben.", "hier Meinungsfreiheit gilt."],
      "correct": "hier Meinungsfreiheit gilt.",
      "correct_answer_letter": "D",
      "category": "Politik",
      "explanations": {
        "en": "The correct answer is D because Germany's Basic Law guarantees freedom of expression...",
        "de": "Die richtige Antwort ist D, weil das Grundgesetz die Meinungsfreiheit garantiert...",
        "tr": "Doğru cevap D çünkü Almanya'nın Temel Yasası ifade özgürlüğünü garanti eder...",
        "uk": "Правильна відповідь D, тому що Основний Закон Німеччини гарантує свободу слова...",
        "ar": "الإجابة الصحيحة هي د لأن القانون الأساسي الألماني يضمن حرية التعبير..."
      },
      "why_others_wrong": {
        "en": {
          "A": "Religious freedom protects belief, not political criticism...",
          "B": "Paying taxes doesn't grant the right to criticize government...",
          "C": "Voting rights don't automatically include free speech..."
        }
      },
      "key_concept": {
        "en": "Freedom of expression as a fundamental democratic right",
        "de": "Meinungsfreiheit als grundlegendes demokratisches Recht"
      },
      "mnemonic": {
        "en": "Meinung = Opinion, Germans can voice their Meinung freely",
        "de": "Meinungsfreiheit = Meinung + Freiheit = freie Meinungsäußerung"
      },
      "images": [],
      "is_image_question": false
    }
  },
  "metadata": {
    "step": "final_dataset",
    "total_questions": 460,
    "missing_questions": [],
    "missing_count": 0,
    "success_rate": 100.0,
    "complete": true,
    "languages": ["en", "de", "tr", "uk", "ar"]
  }
}
```

## 🎯 Key Features

### Multilingual Support
- **English (en)**: Primary explanations
- **German (de)**: Native language context
- **Turkish (tr)**: Large immigrant community
- **Ukrainian (uk)**: Recent refugees
- **Arabic (ar)**: Immigrant community

### Question Types
- **Text Questions**: 368 questions with text-only content
- **Image Questions**: 92 questions with visual components
  - Single image questions (contextual images)
  - Multiple choice image questions (4 images per question)

### Educational Features
- **Detailed Explanations**: Why the correct answer is right
- **Wrong Answer Analysis**: Why each incorrect option is wrong
- **Key Concepts**: Core principles being tested
- **Mnemonics**: Memory aids for retention
- **Cultural Context**: German-specific legal and cultural background

## 💡 Pro Tips

1. **Use the complete dataset**: `final_dataset.json` is production-ready
2. **No regeneration needed**: All questions are complete with explanations
3. **Cost efficient**: Full regeneration costs ~$50-80 in AI API calls
4. **Modular scripts**: Each script handles one specific task
5. **Robust error handling**: Scripts include retry logic and validation

## 🚨 Troubleshooting

### Common Issues

**Q: Dataset file seems corrupted**
```bash
# Verify integrity
python scripts/verify_dataset.py

# Check JSON format
jq empty data/final_dataset.json && echo "Valid JSON" || echo "Invalid JSON"
```

**Q: Missing explanations for specific questions**
```bash
# Process individual question
python scripts/generate_explanations_single.py --question-id <ID>

# Rebuild final dataset
python scripts/finalize_dataset.py
```

**Q: Images not displaying**
```bash
# Check image files exist
ls -la data/images/q*_*.png | wc -l  # Should show 92 files

# Re-extract images if needed (requires API keys)
python scripts/extract_images.py
```

## 📈 Project Statistics

- **Total Questions**: 460 (300 general + 160 state-specific)
- **Image Questions**: 92 with visual components
- **Languages**: 5 (EN, DE, TR, UK, AR)
- **Dataset Size**: ~4.5MB (final_dataset.json)
- **Completion Rate**: 100%
- **Accuracy**: AI-verified image question answers
- **Development Time**: 6 months (now complete)

---

**Last Updated**: 2025-01-17  
**Status**: ✅ Production Ready (100% Complete)  
**Next Steps**: Use `final_dataset.json` in the Integran app