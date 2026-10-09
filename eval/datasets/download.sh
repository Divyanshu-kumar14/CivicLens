#!/bin/bash
# Fetch the RDD2020 benchmark set for detector evaluation.
# RDD2020 is hosted by the CRDDC (https://github.com/sekilab/RoadDamageDetector);
# links rotate, so this script takes the current mirror as an argument.
# Usage: ./eval/datasets/download.sh [MIRROR_URL]
set -euo pipefail
MIRROR="${1:-https://github.com/sekilab/RoadDamageDetector}"
DEST="eval/datasets/rdd2020"

mkdir -p "$DEST"
echo "RDD2020 mirror: $MIRROR"
echo "The CRDDC distributes RDD2020 as per-country zips behind a form."
echo "1. Request access at $MIRROR"
echo "2. Unzip the India split into $DEST/ (expect */train/images/*.jpg + *.txt labels)"
echo "3. Run: ls $DEST/*/train/images | head  (sanity check)"
echo "NOTE: detector smoke test (vision/tests/test_detector.py) auto-skips until samples exist."
