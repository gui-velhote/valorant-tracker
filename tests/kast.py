import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import run
from src.Val import valApiAccess

if __name__ == "__main__":
    val = valApiAccess()
    valMatch = val.get_match_details(val.get_match_history()[0])
    # matchStats = run.get_match_stats(val, valMatch)
    run.get_kast(val, valMatch)