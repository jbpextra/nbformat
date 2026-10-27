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
from ._utils import get_version
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


def _relax_additional_properties(obj):
    """relax any `additionalProperties`"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            value = True if key == "additionalProperties" else _relax_additional_properties(value)
            obj[key] = value
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            obj[i] = _relax_additional_properties(value)
    return obj


def _allow_undefined(schema):
    schema["definitions"]["cell"]["oneOf"].append({"$ref": "#/definitions/unrecognized_cell"})
    schema["definitions"]["output"]["oneOf"].append({"$ref": "#/definitions/unrecognized_output"})
    return schema


def get_validator(version=None, version_minor=None, relax_add_props=False, name=None):
    """Load the JSON schema into a Validator"""
    if version is None:
        from . import current_nbformat  # noqa:PLC0415

        version = current_nbformat

    v = import_item("nbformat.v%s" % version)
    current_minor = getattr(v, "nbformat_minor", 0)
    if version_minor is None:
        version_minor = current_minor

    current_validator = _validator_for_name(name) if name else get_current_validator()
    version_tuple = (current_validator.name, version, version_minor, relax_add_props)

    if version_tuple not in validators:
        try:
            schema_json = _get_schema_json(v, version=version, version_minor=version_minor)
        except AttributeError:
            return None

        if current_minor < version_minor:
            schema_json = _relax_additional_properties(schema_json)
            schema_json = _allow_undefined(schema_json)

        if relax_add_props:
            schema_json = _relax_additional_properties(schema_json)

        validators[version_tuple] = current_validator(schema_json)

    return validators[version_tuple]


def _get_schema_json(v, version=None, version_minor=None):
    """Gets the json schema from a given imported library and nbformat version."""
    if (version, version_minor) in v.nbformat_schema:
        schema_path = str(Path(v.__file__).parent / v.nbformat_schema[(version, version_minor)])
    elif version_minor > v.nbformat_minor:
        schema_path = str(Path(v.__file__).parent / v.nbformat_schema[(None, None)])
    else:
        raise AttributeError("Cannot find appropriate nbformat schema file.")
    with Path(schema_path).open(encoding="utf8") as f:
        return json.load(f)


def isvalid(nbjson, ref=None, version=None, version_minor=None):
    """Checks whether the given notebook JSON conforms to the current notebook format schema."""
    orig = deepcopy(nbjson)
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=MissingIDFieldWarning)
            _validate(nbjson, ref, version, version_minor, repair_duplicate_cell_ids=False)
    except ValidationError:
        return False
    else:
        return True
    finally:
        if nbjson != orig:
            raise AssertionError


def _format_as_index(indices):
    """Construct indexing operations for indices."""
    if not indices:
        return ""
    return "[%s]" % "][".join(repr(index) for index in indices)


_ITEM_LIMIT = 16
_STR_LIMIT = 64


def _truncate_obj(obj):
    """Truncate objects for use in validation tracebacks."""
    if isinstance(obj, dict):
        truncated_dict = {k: _truncate_obj(v) for k, v in list(obj.items())[:_ITEM_LIMIT]}
        if isinstance(truncated_dict.get("cells"), list):
            truncated_dict["cells"] = ["...%i cells..." % len(obj["cells"])]
        if isinstance(truncated_dict.get("outputs"), list):
            truncated_dict["outputs"] = ["...%i outputs..." % len(obj["outputs"])]
        if len(obj) > _ITEM_LIMIT:
            truncated_dict["..."] = "%i keys truncated" % (len(obj) - _ITEM_LIMIT)
        return truncated_dict
    if isinstance(obj, list):
        truncated_list = [_truncate_obj(item) for item in obj[:_ITEM_LIMIT]]
        if len(obj) > _ITEM_LIMIT:
            truncated_list.append("...%i items truncated..." % (len(obj) - _ITEM_LIMIT))
        return truncated_list
    if isinstance(obj, str):
        truncated_str = obj[:_STR_LIMIT]
        if len(obj) > _STR_LIMIT:
            truncated_str += "..."
        return truncated_str
    return obj


class NotebookValidationError(ValidationError):
    """Schema ValidationError with truncated representation."""

    def __init__(self, original, ref=None):
        self.original = original
        self.ref = getattr(self.original, "ref", ref)
        self.message = self.original.message

    def __getattr__(self, key):
        return getattr(self.original, key)

    def __unicode__(self):
        error = self.original
        instance = _truncate_obj(error.instance)
        return "\n".join(
            [
                error.message,
                "",
                "Failed validating {!r} in {}{}:".format(
                    error.validator,
                    self.ref or "notebook",
                    _format_as_index(list(error.relative_schema_path)[:-1]),
                ),
                "",
                "On instance%s:" % _format_as_index(error.relative_path),
                pprint.pformat(instance, width=78),
            ]
        )

    __str__ = __unicode__


def better_validation_error(error, version, version_minor):
    """Get better ValidationError on oneOf failures."""
    if not len(error.schema_path):
        return error
    key = error.schema_path[-1]
    ref = None
    if key.endswith("Of"):
        if isinstance(error.instance, dict):
            if "cell_type" in error.instance:
                ref = error.instance["cell_type"] + "_cell"
            elif "output_type" in error.instance:
                ref = error.instance["output_type"]
        if ref:
            try:
                validate(error.instance, ref, version=version, version_minor=version_minor)
            except ValidationError as sub_error:
                error.relative_path.extend(sub_error.relative_path)
                sub_error.relative_path = error.relative_path
                better = better_validation_error(sub_error, version, version_minor)
                if better.ref is None:
                    better.ref = ref
                return better
            except Exception:  # noqa: S110, BLE001
                pass
    return NotebookValidationError(error, ref)


def normalize(nbdict: Any, version: int | None = None, version_minor: int | None = None, *, relax_add_props: bool = False, strip_invalid_metadata: bool = False) -> tuple[int, Any]:
    """Normalise a notebook prior to validation."""
    nbdict = deepcopy(nbdict)
    nbdict_version, nbdict_version_minor = get_version(nbdict)
    if version is None:
        version = nbdict_version
    if version_minor is None:
        version_minor = nbdict_version_minor
    return _normalize(nbdict, version, version_minor, True, relax_add_props=relax_add_props, strip_invalid_metadata=strip_invalid_metadata)


def _normalize(nbdict: Any, version: int, version_minor: int, repair_duplicate_cell_ids: bool, relax_add_props: bool, strip_invalid_metadata: bool) -> tuple[int, Any]:
    """Private normalisation routine."""
    changes = 0
    if (version, version_minor) >= (4, 5):
        for cell in nbdict["cells"]:
            if "id" not in cell:
                warnings.warn("Cell is missing an id field, this will become a hard error in future nbformat versions. You may want to use `normalize()` on your notebooks before validations (available since nbformat 5.1.4). Previous versions of nbformat are fixing this issue transparently, and will stop doing so in the future.", MissingIDFieldWarning, stacklevel=3)
                if repair_duplicate_cell_ids:
                    cell["id"] = generate_corpus_id()
                    changes += 1
        seen_ids = set()
        for cell in nbdict["cells"]:
            if "id" not in cell:
                continue
            cell_id = cell["id"]
            if cell_id in seen_ids:
                if repair_duplicate_cell_ids:
                    new_id = generate_corpus_id()
                    cell["id"] = new_id
                    changes += 1
                    warnings.warn(f"Non-unique cell id {cell_id!r} detected. Corrected to {new_id!r}.", DuplicateCellId, stacklevel=3)
                else:
                    raise ValidationError(f"Non-unique cell id '{cell_id}' detected.")
            seen_ids.add(cell_id)
    if strip_invalid_metadata:
        changes += _strip_invalida_metadata(nbdict, version, version_minor, relax_add_props=relax_add_props)
    return changes, nbdict


def validate(nbdict: Any = None, ref: str | None = None, version: int | None = None, version_minor: int | None = None, relax_add_props: bool = False, nbjson: Any = None) -> None:
    """Checks whether the given notebook conforms to its schema."""
    if nbdict is None and nbjson is not None:
        nbdict = nbjson
    elif nbdict is None:
        raise TypeError("validate() missing 1 required argument: 'nbdict'")
    _validate(nbdict, ref, version, version_minor, relax_add_props)


def _validate(nbdict: Any, ref: str | None = None, version: int | None = None, version_minor: int | None = None, relax_add_props: bool = False, *, repair_duplicate_cell_ids: bool = True, strip_invalid_metadata: bool = False) -> None:
    """Validate a notebook, with explicit control over normalization behavior."""
    assert isinstance(ref, str) or ref is None
    if ref is None:
        nbdict_version, nbdict_version_minor = get_version(nbdict)
        if version is None:
            version = nbdict_version
        if version_minor is None:
            version_minor = nbdict_version_minor
    elif version is None:
        version, version_minor = 1, 0
    if ref is None:
        assert isinstance(version, int)
        assert isinstance(version_minor, int)
        _normalize(nbdict, version, version_minor, repair_duplicate_cell_ids, relax_add_props=relax_add_props, strip_invalid_metadata=strip_invalid_metadata)
    for error in iter_validate(nbdict, ref=ref, version=version, version_minor=version_minor, relax_add_props=relax_add_props, strip_invalid_metadata=strip_invalid_metadata):
        raise error


def _get_errors(nbdict: Any, version: int, version_minor: int, relax_add_props: bool, *args: Any) -> Any:
    validator = get_validator(version, version_minor, relax_add_props=relax_add_props)
    if not validator:
        raise ValidationError(f"No schema for validating v{version}.{version_minor} notebooks")
    errors = iter(validator.iter_errors(nbdict, *args))
    first = next(errors, None)
    if first is None:
        return iter(())
    if validator.name != "jsonschema":
        validator = get_validator(version=version, version_minor=version_minor, relax_add_props=relax_add_props, name="jsonschema")
        return validator.iter_errors(nbdict, *args)
    return chain((first,), errors)


def _strip_invalida_metadata(nbdict: Any, version: int, version_minor: int, relax_add_props: bool) -> int:
    """Strip invalid metadata keys."""
    errors = _get_errors(nbdict, version, version_minor, relax_add_props)
    changes = 0
    if next(iter(errors), None) is not None:
        validator = get_validator(version=version, version_minor=version_minor, relax_add_props=relax_add_props, name="jsonschema")
        if not validator:
            raise ValidationError(f"No jsonschema for validating v{version}.{version_minor} notebooks")
        errors = validator.iter_errors(nbdict)
        error_tree = validator.error_tree(errors)
        if "metadata" in error_tree:
            for key in error_tree["metadata"]:
                nbdict["metadata"].pop(key, None)
                changes += 1
        if "cells" in error_tree:
            number_of_cells = len(nbdict.get("cells", 0))
            for cell_idx in range(number_of_cells):
                if "oneOf" in error_tree["cells"][cell_idx].errors:
                    intended_cell_type = nbdict["cells"][cell_idx]["cell_type"]
                    schemas_by_index = [ref["$ref"] for ref in error_tree["cells"][cell_idx].errors["oneOf"].schema["oneOf"]]
                    cell_type_definition_name = f"#/definitions/{intended_cell_type}_cell"
                    if cell_type_definition_name in schemas_by_index:
                        schema_index = schemas_by_index.index(cell_type_definition_name)
                        for error in error_tree["cells"][cell_idx].errors["oneOf"].context:
                            rel_path = error.relative_path
                            error_for_intended_schema = error.schema_path[0] == schema_index
                            is_top_level_metadata_key = len(rel_path) == 2 and rel_path[0] == "metadata"
                            if error_for_intended_schema and is_top_level_metadata_key:
                                nbdict["cells"][cell_idx]["metadata"].pop(rel_path[1], None)
                                changes += 1
    return changes


def iter_validate(nbdict=None, ref=None, version=None, version_minor=None, relax_add_props=False, nbjson=None, strip_invalid_metadata=False):
    """Return a generator of validation errors."""
    if nbdict is None and nbjson is not None:
        nbdict = nbjson
    elif nbdict is None:
        raise TypeError("iter_validate() missing 1 required argument: 'nbdict'")
    if version is None:
        version, version_minor = get_version(nbdict)
    if ref:
        try:
            errors = _get_errors(nbdict, version, version_minor, relax_add_props, {"$ref": "#/definitions/%s" % ref})
        except ValidationError as e:
            yield e
            return
    else:
        if strip_invalid_metadata:
            _strip_invalida_metadata(nbdict, version, version_minor, relax_add_props)
        try:
            errors = _get_errors(nbdict, version, version_minor, relax_add_props)
        except ValidationError as e:
            yield e
            return
    for error in errors:
        yield better_validation_error(error, version, version_minor)
