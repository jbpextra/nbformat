"""Shared JSON codec mechanics for notebook formats."""
from __future__ import annotations

import json


class BytesEncoder(json.JSONEncoder):
    """A JSON encoder that accepts b64 (and other *ascii*) bytestrings."""

    def default(self, obj):
        """Encode ASCII bytes as strings."""
        if isinstance(obj, bytes):
            return obj.decode("ascii")
        return super().default(obj)


def dumps(obj, **kwargs):
    """Serialize an object with the shared notebook JSON encoder."""
    kwargs.setdefault("cls", BytesEncoder)
    return json.dumps(obj, **kwargs)


def loads(s, **kwargs):
    """Parse JSON text."""
    return json.loads(s, **kwargs)
