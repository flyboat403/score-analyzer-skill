#!/bin/bash
set -e
echo "=== Score Analyzer Environment Check ==="
python3 --version || { echo "ERROR: Python 3 required"; exit 1; }
echo "Installing dependencies..."
pip install pandas matplotlib seaborn openpyxl python-docx numpy scipy
if fc-list :lang=zh >/dev/null 2>&1; then
    echo "Chinese font: OK"
else
    echo "WARNING: No Chinese font. Install: apt install fonts-noto-cjk"
fi
python3 -c "import pandas, matplotlib, seaborn, openpyxl, docx; print('All packages: OK')"
echo "Environment ready!"