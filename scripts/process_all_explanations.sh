#!/bin/bash
# Process all questions for Step 3: Generate Multilingual Explanations
# Robust version that handles failures gracefully and retries failed questions

echo "Starting full dataset processing for Step 3..."
echo "This will process all 459 questions with multilingual explanations"
echo "========================================================="

# Get starting time
start_time=$(date +%s)

# Arrays to track results
processed=0
failed_questions=()
total_processed=0

# Function to process a single question
process_question() {
    local question_id=$1
    local attempt=$2
    
    if python scripts/generate_explanations_single.py --question-id $question_id > /dev/null 2>&1; then
        return 0  # Success
    else
        return 1  # Failure
    fi
}

echo "=== FIRST PASS: Processing all questions ==="

# First pass: Process all questions 1-459
for i in {1..459}; do
    echo -n "Processing question $i... "
    
    if process_question $i "first"; then
        echo "✓"
        ((processed++))
    else
        echo "✗ (failed - will retry later)"
        failed_questions+=($i)
    fi
    
    ((total_processed++))
    
    # Show progress every 25 questions
    if [ $((i % 25)) -eq 0 ]; then
        echo "Progress: $i/459 questions processed ($processed successful, ${#failed_questions[@]} failed)"
    fi
    
    # Small delay to avoid rate limiting (reduced for faster processing)
    sleep 0.5
done

echo ""
echo "=== FIRST PASS COMPLETE ==="
echo "Successfully processed: $processed"
echo "Failed questions: ${#failed_questions[@]}"

# Second pass: Retry failed questions
if [ ${#failed_questions[@]} -gt 0 ]; then
    echo ""
    echo "=== SECOND PASS: Retrying failed questions ==="
    
    retry_failed=()
    retry_processed=0
    
    for question_id in "${failed_questions[@]}"; do
        echo -n "Retrying question $question_id... "
        
        if process_question $question_id "retry"; then
            echo "✓ (success on retry)"
            ((processed++))
            ((retry_processed++))
        else
            echo "✗ (failed again)"
            retry_failed+=($question_id)
        fi
        
        # Longer delay for retries to avoid API issues
        sleep 1
    done
    
    echo ""
    echo "=== RETRY RESULTS ==="
    echo "Retry attempts: ${#failed_questions[@]}"
    echo "Retry successes: $retry_processed"
    echo "Still failed: ${#retry_failed[@]}"
    
    # Update failed_questions to only contain permanently failed ones
    failed_questions=("${retry_failed[@]}")
fi

# Calculate elapsed time
end_time=$(date +%s)
elapsed=$((end_time - start_time))
minutes=$((elapsed / 60))
seconds=$((elapsed % 60))

echo ""
echo "========================================================="
echo "PROCESSING COMPLETE!"
echo "========================================================="
echo "Total questions: 459"
echo "Successfully processed: $processed"
echo "Still failed after retry: ${#failed_questions[@]}"
echo "Success rate: $(echo "scale=1; $processed * 100 / 459" | bc -l)%"
echo "Time elapsed: ${minutes}m ${seconds}s"
echo "Output file: data/step3_explanations_progress.json"

# Write failed questions to a file for manual review
if [ ${#failed_questions[@]} -gt 0 ]; then
    echo ""
    echo "=== WRITING FAILED QUESTIONS LOG ==="
    
    failed_log="data/failed_questions_log.txt"
    echo "Failed questions ($(date)):" > "$failed_log"
    echo "These questions failed processing after 2 attempts:" >> "$failed_log"
    echo "" >> "$failed_log"
    
    for question_id in "${failed_questions[@]}"; do
        echo "Question ID: $question_id" >> "$failed_log"
    done
    
    echo "" >> "$failed_log"
    echo "To retry manually, run:" >> "$failed_log"
    for question_id in "${failed_questions[@]}"; do
        echo "python scripts/generate_explanations_single.py --question-id $question_id" >> "$failed_log"
    done
    
    echo "Failed questions written to: $failed_log"
    echo ""
    echo "Failed question IDs: ${failed_questions[*]}"
else
    echo ""
    echo "🎉 ALL QUESTIONS PROCESSED SUCCESSFULLY!"
fi

echo "========================================================="

# Create final dataset if all questions processed successfully
if [ $processed -eq 459 ]; then
    echo "Creating final dataset..."
    cp data/step3_explanations_progress.json data/final_dataset.json
    echo "Final dataset created: data/final_dataset.json"
    echo "✅ Step 3 Complete: Multilingual explanations generated for all 459 questions"
else
    echo "⚠️  $(( 459 - processed )) questions still need manual processing"
    echo "Check data/failed_questions_log.txt for details"
fi