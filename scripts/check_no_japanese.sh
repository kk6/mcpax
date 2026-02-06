#!/usr/bin/env bash
# Pre-commit hook: detect Japanese characters in source code.
# All user-facing strings in src/ and tests/ must be English only.
#
# Detects: Hiragana, Katakana, CJK Unified Ideographs
# Uses grep with Unicode character classes for macOS/Linux compatibility.
set -euo pipefail

found=0
for file in "$@"; do
    if grep -Hn '[ぁ-んァ-ヶ一-龥]' "$file" 2>/dev/null; then
        found=1
    fi
done

if [ "$found" -ne 0 ]; then
    echo ""
    echo "ERROR: Japanese characters found in source code."
    echo "All user-facing strings must be in English."
    exit 1
fi
