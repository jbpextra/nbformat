"""Shared mechanics for reading and writing notebook JSON."""
from __future__ import annotations

import copy
import json


class BytesEncoder(json.JSONEncoder):
    """A JSON encoder that accepts ASCII bytestrings."""

    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode("ascii")
        return super().default(obj)


def reads(reader, s, **kwargs):
    """Decode JSON and pass the result through a configured reader."""
    return reader.to_notebook(json.loads(s, **kwargs), **kwargs)


def writes(nb, *, split, strip, defaults, **kwargs):
    """Serialize a notebook with configurable format-specific transforms."""
    kwargs["cls"] = BytesEncoder
    kwargs["indent"] = 1
    kwargs["sort_keys"] = True
    for key, value in defaults.items():
        kwargs.setdefault(key, value)
    nb = copy.deepcopy(nb)
    if kwargs.pop("split_lines", True):
        nb = split(nb)
    if strip is not None:
        nb = strip(nb)
    return json.dumps(nb, **kwargs)
