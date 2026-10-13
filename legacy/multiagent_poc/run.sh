#!/bin/bash

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "WARNING: No ANTHROPIC_API_KEY found."
    echo "The experiment will run with mock responses."
    echo "To use Claude, set your API key:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    echo ""
fi

# Run the experiment
python experiment.py
