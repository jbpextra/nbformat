"""Notebook format validators."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import json
import pprint
import warnings
from copy import deepcopy
from itertools import chain
from pathlib import Path
from typing import Any

from ._imports import import_item
from ._versioning import get_version
from .corpus.words import generate_corpus_id
from .json_compat import ValidationError, _validator_for_name, get_current_validator
from .warnings import DuplicateCellId, MissingIDFieldWarning

validators: dict[tuple[str, int | None, int | None, bool], Any] = {}


__all__ = [
    "NotebookValidationError",
    "ValidationError",
    "better_validation_error",
    "get_validator",
    "isvalid",
    "iter_validate",
    "normalize",
    "validate",
]

