#!/usr/bin/env python3
"""Quick test to check final dataset structure."""

import json

# Load the final dataset
with open("data/final_dataset.json", encoding="utf-8") as f:
    data = json.load(f)

# Get the questions data
if isinstance(data, dict) and "questions" in data:
    questions_data = list(data["questions"].values())
else:
    questions_data = data

print(f"Total questions: {len(questions_data)}")

# Check first question structure
first_question = questions_data[0]
print("\nFirst question structure:")
for key, value in first_question.items():
    print(f"  {key}: {type(value)} = {str(value)[:100]}...")

# Check for any list values that should be strings
print("\nChecking for problematic fields:")
for key, value in first_question.items():
    if isinstance(value, list):
        print(f"  WARNING: {key} is a list: {value}")
