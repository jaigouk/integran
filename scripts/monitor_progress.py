#!/usr/bin/env python3
"""
Monitor Step 3 Progress
Simple script to check current progress without interrupting the main processing.
"""

import json
import time
from pathlib import Path

def monitor_progress():
    """Monitor the progress of Step 3 processing."""
    progress_file = Path("data/step3_explanations_progress.json")
    
    if not progress_file.exists():
        print("❌ Progress file not found. Processing may not have started.")
        return
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        progress = metadata.get('progress', 'Unknown')
        last_processed = metadata.get('last_processed', 'Unknown')
        processed_questions = metadata.get('processed_questions', [])
        
        # Calculate progress percentage
        if len(processed_questions) > 0:
            percentage = (len(processed_questions) / 459) * 100
        else:
            percentage = 0
        
        print("=" * 60)
        print("STEP 3 PROGRESS MONITOR")
        print("=" * 60)
        print(f"📊 Progress: {progress}")
        print(f"📈 Percentage: {percentage:.1f}%")
        print(f"🕒 Last processed: {last_processed}")
        print(f"✅ Questions completed: {len(processed_questions)}")
        print(f"⏳ Remaining: {459 - len(processed_questions)}")
        
        if len(processed_questions) >= 5:
            print(f"🎯 Recent questions: {processed_questions[-5:]}")
        else:
            print(f"🎯 Processed questions: {processed_questions}")
        
        # Estimate completion time based on recent progress
        if len(processed_questions) > 0:
            # Assume average 30 seconds per question (conservative estimate)
            remaining = 459 - len(processed_questions)
            estimated_minutes = (remaining * 30) / 60
            print(f"⏰ Estimated time remaining: {estimated_minutes:.0f} minutes")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error reading progress file: {e}")

if __name__ == "__main__":
    monitor_progress()