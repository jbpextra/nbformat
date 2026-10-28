"""Read and write notebooks in JSON format.

Authors:

* Brian Granger
"""
from __future__ import annotations

from nbformat import _nbjson

from .nbbase import from_dict
from .rwbase import NotebookReader, NotebookWriter, rejoin_lines, restore_bytes, split_lines


class BytesEncoder(_nbjson.BytesEncoder):
    """A JSON encoder that accepts b64 (and other *ascii*) bytestrings."""


class JSONReader(NotebookReader):
    """A JSON notebook reader."""

    def reads(self, s, **kwargs):
        return _nbjson.reads(self, s, **kwargs)

    def to_notebook(self, d, **kwargs):
        return restore_bytes(rejoin_lines(from_dict(d)))


class JSONWriter(NotebookWriter):
    """A JSON notebook writer."""

    def writes(self, nb, **kwargs):
        # Preserve the historical v2 JSON defaults and byte restoration behavior.
        kwargs["cls"] = BytesEncoder
        kwargs["indent"] = 1
        kwargs["sort_keys"] = True
        if kwargs.pop("split_lines", True):
            nb = split_lines(__import__("copy").deepcopy(nb))
        import json

        return json.dumps(nb, **kwargs)


_reader = JSONReader()
_writer = JSONWriter()

reads = _reader.reads
read = _reader.read
to_notebook = _reader.to_notebook
write = _writer.write
writes = _writer.writes
