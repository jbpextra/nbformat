"""Read and write notebooks in JSON format."""
from __future__ import annotations

from nbformat import _nbjson
from nbformat.notebooknode import from_dict

from .rwbase import NotebookReader, NotebookWriter, rejoin_lines, split_lines, strip_transient


class BytesEncoder(_nbjson.BytesEncoder):
    """A JSON encoder that accepts b64 (and other *ascii*) bytestrings."""


class JSONReader(NotebookReader):
    """A JSON notebook reader."""

    def reads(self, s, **kwargs):
        return _nbjson.reads(self, s, **kwargs)

    def to_notebook(self, d, **kwargs):
        return strip_transient(rejoin_lines(from_dict(d)))


class JSONWriter(NotebookWriter):
    """A JSON notebook writer."""

    def writes(self, nb, **kwargs):
        # v4 strips transient fields and uses UTF-8 output by default.
        kwargs["cls"] = BytesEncoder
        kwargs["indent"] = 1
        kwargs["sort_keys"] = True
        kwargs["separators"] = (",", ": ")
        kwargs.setdefault("ensure_ascii", False)
        nb = __import__("copy").deepcopy(nb)
        if kwargs.pop("split_lines", True):
            nb = split_lines(nb)
        nb = strip_transient(nb)
        import json

        return json.dumps(nb, **kwargs)


_reader = JSONReader()
_writer = JSONWriter()

reads = _reader.reads
read = _reader.read
to_notebook = _reader.to_notebook
write = _writer.write
writes = _writer.writes
