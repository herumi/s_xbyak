#!/bin/sh
# usage: ./update.sh <path to Intel SDM vol.2 pdf> [-debug]
# Update the MemRegTbl/RegMemTbl in ../s_xbyak.py from the SDM pdf.
set -e
dir="$(dirname "$0")"
if [ $# -lt 1 ]; then
  echo "usage: $0 <path to Intel SDM vol.2 pdf> [-debug]"
  exit 1
fi
pdf="$1"
shift
pdftotext "$pdf" "$dir/sdm-all.txt"
python3 "$dir/update.py" "$dir/sdm-all.txt" "$@"
