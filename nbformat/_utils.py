"""Shared low-level utilities for nbformat."""

from __future__ import annotations


def get_version(nb):
    """Get the version of a notebook.

    Parameters
    ----------
    nb : dict
        NotebookNode or dict containing notebook data.

    Returns
    -------
    tuple[int, int]
        Major and minor version numbers.
    """
    major = nb.get("nbformat", 1)
    minor = nb.get("nbformat_minor", 0)
    return (major, minor)
