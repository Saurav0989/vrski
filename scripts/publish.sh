#!/bin/bash
# Publish Vrski to PyPI. This is the ONE step that needs your PyPI account.
#
# One-time:
#   1. Create a PyPI account + an API token at https://pypi.org/manage/account/token/
#   2. Put it in ~/.pypirc, or export it:
#        export TWINE_USERNAME=__token__
#        export TWINE_PASSWORD=pypi-AgE...your-token...
#
# Then run:  bash scripts/publish.sh
#
# After it succeeds, `pip install vrski` works for everyone.
set -euo pipefail

python3 -m pip install --upgrade build twine
rm -rf dist
python3 -m build
python3 -m twine check dist/*

echo ""
echo "Built: $(ls dist/)"
echo "About to upload vrski to PyPI. Ctrl+C now to abort."
read -r -p "Press Enter to upload... " _
python3 -m twine upload dist/*
echo "Done. Try:  pip install vrski"
