from functools import lru_cache
import os
from pathlib import Path
import sys

import pandas as pd

_api_dir = Path(__file__).resolve().parent.parent
_train_roots = [
    Path(os.environ.get("TRAIN_DIR", "")),
    _api_dir.parent / "train",
    _api_dir / "train",
]
for _root in _train_roots:
    _predict_dir = Path(_root) / "reassort"
    if (_predict_dir / "predict.py").is_file():
        sys.path.insert(0, str(_predict_dir))
        break

from predict import run_reassort, get_category_list  # noqa: E402


@lru_cache(maxsize=1)
def get_reassort_df() -> pd.DataFrame:
    return run_reassort(
        data_dir=os.environ.get("DATA_DIR", "data"),
        model_path=os.environ.get("MODEL_REASSORT", "models/xgboost_30d_final.pkl"),
    )


@lru_cache(maxsize=1)
def get_categories() -> list:
    return get_category_list(data_dir=os.environ.get("DATA_DIR", "data"))


def reload_reassort():
    get_reassort_df.cache_clear()
    get_categories.cache_clear()
