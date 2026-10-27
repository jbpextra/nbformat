"""Shared JSON encoding and serialization helpers for notebook formats."""
from __future__ import annotations

import json


class BytesEncoder(json.JSONEncoder):
    """A JSON encoder that accepts bytes containing ASCII data."""

    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode("ascii")
        return super().default(obj)


def loads(s, **kwargs):
    """Decode a JSON string."""
    return json.loads(s, **kwargs)


def dumps(obj, **kwargs):
    """Encode an object to JSON using the shared bytes encoder."""
    kwargs.setdefault("cls", BytesEncoder)
    return json.dumps(obj, **kwargs)
