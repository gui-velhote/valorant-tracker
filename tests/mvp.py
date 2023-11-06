import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import run
from src.Val import valApiAccess

if __name__ == "__main__":
    val = valApiAccess()

    valMatch = val.get_match_details(val.get_match_history()[0])
    mvp = run.get_mvp(val, valMatch)

    # for match in val.get_match_history():
    #     valMatch = val.get_match_details(match)
    #     mvp = run.get_mvp(val, valMatch)
    print(mvp)
