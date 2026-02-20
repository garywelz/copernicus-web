#!/bin/bash
# Test script to generate citations for one process

echo "Testing LLM citation generation..."
echo "This will process one example process to verify the script works."
echo ""

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY not set."
    echo "   The script will generate template citations instead."
    echo "   Set it with: export GEMINI_API_KEY='your-key-here'"
    echo ""
fi

# Run in test mode
python3 /home/gdubs/copernicus-web-public/huggingface-space/scripts/add_llm_sources.py --test

echo ""
echo "✅ Test complete!"
echo ""
echo "To run on all processes:"
echo "  python3 scripts/add_llm_sources.py"
echo ""
echo "To see what would be updated without making changes:"
echo "  python3 scripts/add_llm_sources.py --dry-run"
