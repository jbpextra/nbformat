"""API for converting notebooks between versions."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from . import versions
from ._utils import get_version
from .validator import ValidationError


def convert(nb, to_version):
    """Convert a notebook node object to a specific version."""
    version, _version_minor = get_version(nb)
    if version == to_version:
        return nb
    if to_version in versions:
        if to_version > version:
            step_version = version + 1
            convert_function = versions[step_version].upgrade
        else:
            step_version = version - 1
            convert_function = versions[version].downgrade
        try:
            converted = convert_function(nb)
            if converted.get("nbformat", 1) == version:
                raise ValueError("Failed to convert notebook from v%d to v%d." % (version, step_version))
        except AttributeError as e:
            raise ValidationError(f"Notebook could not be converted from version {version} to version {step_version} because it's missing a key: {e}") from None
        return convert(converted, to_version)
    raise ValueError("Cannot convert notebook to v%d because that version doesn't exist" % to_version)
