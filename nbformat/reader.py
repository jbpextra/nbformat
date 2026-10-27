"""API for reading notebooks of different versions"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import json

from ._versioning import get_version
from .validator import ValidationError


class NotJSONError(ValueError):
    """An error raised when an object is not valid JSON."""


def parse_json(s, **kwargs):
    """Parse a JSON string into a dict."""
    try:
        nb_dict = json.loads(s, **kwargs)
    except ValueError as e:
        message = f"Notebook does not appear to be JSON: {s!r}"
        if len(message) > 80:
            message = message[:77] + "..."
        raise NotJSONError(message) from e
    return nb_dict


# High level API


def reads(s, **kwargs):
    """Read a notebook from a json string and return the NotebookNode object."""
    from . import NBFormatError, versions  # noqa: PLC0415

    nb_dict = parse_json(s, **kwargs)
    (major, minor) = get_version(nb_dict)
    if major in versions:
        try:
            return versions[major].to_notebook_json(nb_dict, minor=minor)
        except AttributeError as e:
            msg = f"The notebook is invalid and is missing an expected key: {e}"
            raise ValidationError(msg) from None
    raise NBFormatError("Unsupported nbformat version %s" % major)


def read(fp, **kwargs):
    """Read a notebook from a file and return the NotebookNode object."""
    return reads(fp.read(), **kwargs)
