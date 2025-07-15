# FSRS Lapse System: Understanding Memory Failures in Spaced Repetition

## Overview

The **lapse system** in FSRS (Free Spaced Repetition Scheduler) is a core mechanism for tracking when you forget previously learned information. This document explains how lapses work, why they matter, and how they affect your learning experience in Integran.

## What is a Lapse?

### Definition
A **lapse** occurs when you forget a piece of information that you had previously learned successfully. In the context of exam questions, this means:

- You answered a question correctly in the past (proving you knew it)
- Time passed, and the question appeared again for review
- You answered it incorrectly (showing you forgot it)

### Lapse vs. Initial Learning Mistakes

It's crucial to understand the difference:

| Scenario | Is it a Lapse? | Explanation |
|----------|----------------|-------------|
| NEW question answered wrong | ❌ No | You're still learning this for the first time |
| LEARNING question answered wrong | ❌ No | Still in the initial learning phase |
| REVIEW question answered wrong | ✅ **YES** | You forgot something you had mastered |
| RELEARNING question answered wrong | ✅ **YES** | You forgot it again after relearning |

## FSRS Rating System and Lapses

### The Four Ratings

When you answer a question, you (or the system) assigns a rating:

1. **AGAIN (1)** = Wrong answer → **Triggers a lapse** (if card was in REVIEW state)
2. **HARD (2)** = Correct but difficult → No lapse
3. **GOOD (3)** = Correct → No lapse  
4. **EASY (4)** = Correct and easy → No lapse

### Key Insight
**Only rating 1 (AGAIN) can trigger a lapse.** Ratings 2-4 all indicate correct answers, even if the question felt difficult.

## Card State Progression and Lapses

```
┌─────┐    correct    ┌──────────┐    correct    ┌────────┐
│ NEW │ ────────────→ │ LEARNING │ ────────────→ │ REVIEW │
└─────┘               └──────────┘               └────────┘
                                                      │
                                                      │ AGAIN (wrong)
                                                      │ ← LAPSE OCCURS
                                                      ▼
                                              ┌─────────────┐
                                              │ RELEARNING  │
                                              └─────────────┘
```

### State Transitions Explained

1. **NEW → LEARNING**: First correct answer (no lapse possible)
2. **LEARNING → REVIEW**: Graduated after multiple correct answers (no lapse possible)
3. **REVIEW → RELEARNING**: Wrong answer = **LAPSE!** (lapse_count++)
4. **RELEARNING → REVIEW**: Correct answer after relearning (no new lapse)

## Lapse Count Tracking

### Database Implementation
```python
# This code runs when you answer a question
if request.rating == FSRSRating.AGAIN:  # Only wrong answers (rating 1)
    await self._increment_lapse_count(request.card_id)
    lapse_count_updated = True
```

### What the Numbers Mean
- **lapse_count = 0**: Never forgotten this question after learning it
- **lapse_count = 1**: Forgotten once after learning it  
- **lapse_count = 3**: Forgotten three times - this is a "difficult" question for you
- **lapse_count = 8+**: Considered a "leech" - extremely problematic question

## How Lapses Affect Your Learning

### 1. Scheduling Changes
When you lapse on a question:
- **Interval decreases**: You'll see it again much sooner
- **Difficulty increases**: The algorithm recognizes this as hard for you
- **Future intervals**: Will be more conservative (shorter gaps between reviews)

### 2. Failed Questions Menu
Questions appear in "Review Failed Questions" if:
- `lapse_count > 0` (has been forgotten at least once)
- OR `state == RELEARNING` (currently relearning after a lapse)

### 3. Progress Tracking
- High lapse counts identify your weakest knowledge areas
- Help prioritize study time on genuinely difficult content
- Track improvement over time as lapse rates decrease

## Real-World Example

Let's follow a German integration exam question through the lapse system:

### Question: "When was the German reunification?"

```
Day 1 (NEW):
├─ You see this question for the first time
├─ Answer: "1990" ✓ (rating: GOOD)
├─ lapse_count: 0
└─ State: NEW → LEARNING

Day 3 (LEARNING):  
├─ Question appears again
├─ Answer: "1990" ✓ (rating: EASY)
├─ lapse_count: 0
└─ State: LEARNING → REVIEW

Day 15 (REVIEW):
├─ Question appears after 12-day interval
├─ Answer: "1989" ✗ (rating: AGAIN)
├─ lapse_count: 0 → 1 ← LAPSE RECORDED!
└─ State: REVIEW → RELEARNING

Day 16 (RELEARNING):
├─ Question appears next day (short interval after lapse)
├─ Answer: "1990" ✓ (rating: GOOD)
├─ lapse_count: remains 1 (no new lapse)
└─ State: RELEARNING → REVIEW

Day 25 (REVIEW):
├─ Question appears after shorter 9-day interval (due to previous lapse)
├─ Answer: "1990" ✓ (rating: EASY)  
├─ lapse_count: remains 1
└─ State: stays REVIEW (but future intervals will be longer)
```

## Identifying Your Problem Areas

### High-Lapse Questions
Questions with `lapse_count ≥ 3` indicate:
- Concepts you struggle to remember long-term
- Topics that need different study approaches
- Areas where additional context/mnemonics might help

### Categories to Watch
Check which exam categories have the most lapses:
- "History and Responsibility" 
- "Human and Society"
- "Rule of Law"

This helps focus your study time on genuinely weak areas.

## Common Misconceptions

### ❌ "I got a HARD rating, so that's a failure"
**Wrong!** HARD (rating 2) means you answered correctly but found it difficult. No lapse is recorded.

### ❌ "All wrong answers create lapses"
**Wrong!** Only wrong answers on REVIEW or RELEARNING cards create lapses. Wrong answers during initial learning (NEW/LEARNING states) are normal and expected.

### ❌ "Lapses are bad and should be avoided"
**Wrong!** Lapses are natural and actually help the algorithm learn your memory patterns. They identify what needs more attention.

## Technical Implementation in Integran

### Database Schema
```sql
-- FSRS Cards table
CREATE TABLE fsrs_cards (
    card_id INTEGER PRIMARY KEY,
    question_id INTEGER,
    lapse_count INTEGER DEFAULT 0,  -- Tracks total lapses
    state INTEGER,                  -- Current FSRS state
    -- ... other FSRS parameters
);
```

### Query for Failed Questions
```sql
-- Questions that appear in "Review Failed Questions" menu
SELECT * FROM questions q
JOIN fsrs_cards f ON q.id = f.question_id  
WHERE f.lapse_count > 0           -- Has been forgotten before
   OR f.state = 3                 -- Currently in RELEARNING state
ORDER BY f.lapse_count DESC;      -- Most problematic first
```

### Code Flow
1. User answers question incorrectly (selects wrong option)
2. System assigns rating 1 (AGAIN)
3. `schedule_card` service checks: is card in REVIEW state?
4. If yes: increment lapse_count and move to RELEARNING
5. Question becomes available in "Failed Questions" menu

## Best Practices

### For Users
1. **Don't fear lapses** - they're part of effective learning
2. **Review failed questions regularly** - use the dedicated menu
3. **Pay attention to high-lapse questions** - they need extra study time
4. **Track progress** - watch lapse rates decrease over time

### For Developers  
1. **Preserve lapse history** - don't reset lapse_counts casually
2. **Use lapse data for analytics** - identify difficult question categories
3. **Consider lapse patterns** - for personalized study recommendations
4. **Monitor system health** - unusual lapse patterns might indicate bugs

## Debugging Lapse Issues

### No Failed Questions Appearing?
Check these common causes:

```bash
# 1. Verify users are actually failing questions (getting wrong answers)
sqlite3 data/trainer.db "SELECT rating, COUNT(*) FROM review_history GROUP BY rating;"

# 2. Check current lapse counts
sqlite3 data/trainer.db "SELECT COUNT(*) FROM fsrs_cards WHERE lapse_count > 0;"

# 3. Verify state transitions
sqlite3 data/trainer.db "SELECT state, COUNT(*) FROM fsrs_cards GROUP BY state;"
```

### Expected Results for Active Learning
- Some ratings should be 1 (AGAIN) if users are genuinely learning
- Some cards should have lapse_count > 0
- Some cards should be in RELEARNING state (state = 3)

If all ratings are 2-4 and all lapse_counts are 0, users haven't failed any questions yet - the "No failed questions" message is correct.

---

*This document explains the FSRS lapse system as implemented in Integran v1.0. For technical implementation details, see `src/domain/learning/services/schedule_card.py`.*