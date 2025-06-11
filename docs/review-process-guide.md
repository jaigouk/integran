# Dataset Review Process Guide

This guide explains how non-technical contributors can review and verify the answers and explanations in the German Integration Exam dataset.

## Overview

The Integran project contains 310+ questions for the German Integration Exam (Leben in Deutschland Test). Each question includes:
- Question text and multiple choice options
- Correct answer and explanations in 5 languages (English, German, Turkish, Ukrainian, Arabic)
- Explanations for why incorrect options are wrong
- Key concepts and memory aids (mnemonics)
- Some questions include images

## Review Process Workflow

### 1. Data Export

The technical team will run the export script to generate CSV files:
```bash
cd /path/to/integran
python scripts/export_for_review.py --output-dir review_export
```

This creates 4 CSV files for different review aspects:
- `main_content.csv` - Core questions and primary explanations
- `wrong_answers.csv` - Explanations for incorrect options
- `multilingual_content.csv` - All content in all languages
- `image_questions.csv` - Questions with images and descriptions

### 2. Google Sheets Setup

**For Project Maintainers:**
1. Create a new Google Sheets document
2. Import each CSV file as a separate sheet:
   - File → Import → Upload → Select CSV file
   - Choose "Insert new sheet(s)" for each file
3. Set up sharing permissions for reviewers
4. Create a master tracking sheet (see template below)

### 3. Reviewer Assignment

**Recommended reviewer distribution:**
- **German native speakers**: Focus on German explanations and cultural context
- **Subject matter experts**: Focus on factual accuracy and legal/historical content
- **Language specialists**: Focus on specific language translations
- **General reviewers**: Overall clarity and comprehensiveness

### 4. Review Guidelines for Contributors

#### What to Review

**Content Accuracy:**
- ✅ Are the correct answers actually correct?
- ✅ Are explanations factually accurate?
- ✅ Do explanations align with current German law/practice?
- ✅ Are historical facts correct?

**Language Quality:**
- ✅ Is the language clear and understandable?
- ✅ Are translations accurate and natural?
- ✅ Is terminology consistent?
- ✅ Are there any grammatical errors?

**Comprehensiveness:**
- ✅ Do explanations sufficiently explain why the answer is correct?
- ✅ Do "wrong answer" explanations clearly explain why options are incorrect?
- ✅ Are key concepts helpful for understanding?
- ✅ Are mnemonics memorable and appropriate?

#### How to Provide Feedback

**In Google Sheets:**
1. Use the `Review_Status` column with these values:
   - `APPROVED` - Content is correct and well-written
   - `NEEDS_REVISION` - Issues found, needs changes
   - `UNCLEAR` - Needs clarification or more information
   - `SKIP` - Unable to review (language barrier, etc.)

2. Use the `Reviewer_Comments` column for:
   - Specific corrections needed
   - Suggestions for improvement
   - Questions or clarifications
   - Alternative wording suggestions

**Comment Examples:**
```
NEEDS_REVISION: The explanation mentions Article 4 but should be Article 5 of the Basic Law.

NEEDS_REVISION: German translation sounds unnatural. Suggest: "Das Grundgesetz garantiert..." instead of "Das Grundgesetz gewährleistet..."

UNCLEAR: Is this referring to federal or state law? Please clarify.

APPROVED: Clear and accurate explanation.
```

### 5. Review Sheet Templates

#### Master Tracking Sheet
Create a summary sheet to track overall progress:

| Question_ID | German_Review | English_Review | Subject_Expert | Final_Status | Notes |
|-------------|---------------|----------------|----------------|--------------|-------|
| 1           | APPROVED      | APPROVED       | APPROVED       | COMPLETE     |       |
| 2           | NEEDS_REVISION| PENDING        | PENDING        | IN_PROGRESS  | See comments |

#### Review Assignment Sheet
Track who is reviewing what:

| Reviewer_Name | Language/Expertise | Assigned_Questions | Status | Deadline |
|---------------|-------------------|-------------------|--------|----------|
| Maria Schmidt | German Native     | 1-50              | In Progress | 2024-01-15 |
| Dr. Weber     | Legal Expert      | All Politics      | Pending | 2024-01-20 |

### 6. Quality Assurance Process

**Phase 1: Initial Review (1-2 weeks)**
- Reviewers complete their assigned sections
- Focus on obvious errors and major issues

**Phase 2: Cross-Check (1 week)**
- Second reviewer checks items marked as "NEEDS_REVISION"
- Resolve conflicting feedback
- Verify corrections are accurate

**Phase 3: Final Approval (3-5 days)**
- Project maintainer reviews all feedback
- Makes final decisions on disputed items
- Marks questions as "FINAL_APPROVED"

### 7. Incorporating Feedback

**For Technical Team:**
1. Export the reviewed CSV files from Google Sheets
2. Use a script to merge approved changes back into the JSON dataset
3. Validate the updated dataset structure
4. Run tests to ensure no data corruption

**Change Log:**
Maintain a record of all changes made:
```
Question 15: Updated German explanation to clarify Article 5 reference
Question 23: Fixed typo in English mnemonic
Question 67: Revised Turkish translation for cultural appropriateness
```

## Communication Guidelines

### For Reviewers
- **Ask questions early**: If something is unclear, ask rather than guess
- **Be specific**: Provide exact corrections rather than vague comments
- **Consider your audience**: Remember these are for exam preparation
- **Respect cultural context**: Consider how explanations work for different backgrounds

### For Project Maintainers
- **Provide clear deadlines**: Set realistic timeframes for review
- **Be responsive**: Answer reviewer questions quickly
- **Show appreciation**: Acknowledge reviewer contributions
- **Document decisions**: Explain why certain feedback was or wasn't incorporated

## Common Review Issues

### Typical Problems Found:
1. **Legal/Historical Inaccuracies**: Laws change, historical details need verification
2. **Translation Nuances**: Technical terms may not translate directly
3. **Cultural Context**: Some concepts need additional explanation for non-Germans
4. **Clarity Issues**: Academic language that could be simplified
5. **Consistency**: Different questions explaining similar concepts differently

### Red Flags to Watch For:
- ⚠️ Outdated legal references
- ⚠️ Inconsistent terminology between questions
- ⚠️ Explanations that don't actually explain the correct answer
- ⚠️ Cultural assumptions that exclude immigrant perspectives
- ⚠️ Overly complex language for exam preparation material

## Tools and Resources

### Helpful References for Reviewers:
- [German Basic Law (Grundgesetz)](https://www.gesetze-im-internet.de/gg/)
- [Federal Office for Migration and Refugees](https://www.bamf.de/)
- [Official Integration Course Materials](https://www.bamf.de/DE/Themen/Integration/ZugewanderteTeilnehmende/Integrationskurse/integrationskurse-node.html)

### Technical Support:
- Contact project maintainer for Google Sheets access issues
- Use GitHub issues for reporting systematic problems
- Email for urgent clarifications during review period

## Timeline Example

**Week 1-2: Setup and Initial Review**
- Export data and set up Google Sheets
- Assign reviewers and provide access
- Begin initial content review

**Week 3: Cross-checking and Discussion**
- Address items marked for revision
- Resolve conflicting reviewer feedback
- Clarify ambiguous cases

**Week 4: Finalization**
- Incorporate approved changes
- Validate updated dataset
- Document all changes made

**Post-Review: Implementation**
- Import reviewed CSV files back to JSON format
- Validate all changes and generate change report
- Update source JSON files
- Run full test suite
- Deploy updated dataset

## Importing Reviewed Changes

After reviewers complete their work in Google Sheets, the technical team imports the changes back into the dataset:

### 1. Download CSV Files
Download the reviewed spreadsheets as CSV files:
- File → Download → Comma-separated values (.csv)
- Save each sheet separately (main_content.csv, wrong_answers.csv, etc.)

### 2. Run Import Script
```bash
# Import reviewed changes
python scripts/import_from_review.py \
  --input-dir path/to/downloaded/csvs \
  --original-dataset data/final_dataset.json \
  --output data/final_dataset_reviewed.json \
  --backup \
  --report review_changes_report.md
```

### 3. Review Change Report
The import script generates a detailed report showing:
- All changes applied
- Validation errors (if any)
- Summary statistics
- Questions that were updated

### 4. Quality Assurance
```bash
# Validate the updated dataset
python scripts/verify_dataset.py data/final_dataset_reviewed.json

# Run tests to ensure no regression
pytest

# Check for any data structure issues
python -c "import json; json.load(open('data/final_dataset_reviewed.json'))"
```

### 5. Apply Changes
If all validations pass:
```bash
# Replace the original dataset
mv data/final_dataset_reviewed.json data/final_dataset.json

# Commit changes
git add data/final_dataset.json
git commit -m "Apply reviewer feedback

- Updated X explanations
- Fixed Y translation issues
- Improved Z key concepts

Co-authored-by: [Reviewer Names]"
```

## Import Script Features

The import script (`scripts/import_from_review.py`) provides:

### Smart Change Detection
- Only applies changes marked as "APPROVED" 
- Preserves original data for non-reviewed items
- Handles missing or corrupted CSV data gracefully

### Validation
- Checks for invalid review status values
- Validates question IDs exist in original dataset
- Reports data inconsistencies

### Change Tracking
- Detailed logging of all modifications
- Reviewer comments preserved in metadata
- Audit trail for all changes

### Safety Features
- Automatic backup creation
- Rollback capability
- Comprehensive error reporting

### Supported Review Statuses
- `APPROVED`: Changes will be applied
- `NEEDS_REVISION`: Flagged for further review, not applied
- `UNCLEAR`: Flagged for clarification, not applied  
- `SKIP`: Reviewer unable to review, not applied
- Empty: No review performed, not applied

## Success Metrics

A successful review process should achieve:
- ✅ 95%+ of questions reviewed by at least one domain expert
- ✅ All "NEEDS_REVISION" items addressed
- ✅ Consistent terminology across all questions
- ✅ Cultural sensitivity review completed
- ✅ Zero technical/legal inaccuracies in final dataset
- ✅ Clear documentation of all changes made

---

*This review process ensures the highest quality educational content for German integration exam preparation while maintaining efficiency and clear communication among all contributors.*