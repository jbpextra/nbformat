"""Shared notebook-format utilities."""

from __future__ import annotations


def get_version(nb):
    """Get the version of a notebook.

    Parameters
    ----------
    nb : dict
        NotebookNode or dict containing notebook data.

    Returns
    -------
    Tuple containing major (int) and minor (int) version numbers
    """
    major = nb.get("nbformat", 1)
    minor = nb.get("nbformat_minor", 0)
    return (major, minor)
