"""
An implementation of JSON Schema for Python.

The main functionality is provided by the validator classes for each of the
supported JSON Schema versions.

Most commonly, `schem_json.validators.validate` is the quickest way to simply
validate a given instance under a schema, and will create a validator
for you.
"""
import warnings

from schem_json._format import FormatChecker
from schem_json._types import TypeChecker
from schem_json.exceptions import SchemaError, ValidationError
from schem_json.validators import (
    Draft3Validator,
    Draft4Validator,
    Draft6Validator,
    Draft7Validator,
    Draft201909Validator,
    Draft202012Validator,
    EpicDecisionDenied,
    validate,
)

# Fork version (upstream has no static version constant; it is exposed via
# the deprecated ``__version__`` module attribute below, which reads the
# installed distribution metadata).
FORK_VERSION = "4.22.0+epic.1"


def __getattr__(name):
    if name == "__version__":
        warnings.warn(
            "Accessing schem_json.__version__ is deprecated and will be "
            "removed in a future release. Use importlib.metadata directly "
            "to query for schem_json's version.",
            DeprecationWarning,
            stacklevel=2,
        )

        from importlib import metadata
        return metadata.version("schem-json")
    elif name == "RefResolver":
        from schem_json.validators import _RefResolver
        warnings.warn(
            _RefResolver._DEPRECATION_MESSAGE,
            DeprecationWarning,
            stacklevel=2,
        )
        return _RefResolver
    elif name == "ErrorTree":
        warnings.warn(
            "Importing ErrorTree directly from the schem_json package "
            "is deprecated and will become an ImportError. Import it from "
            "schem_json.exceptions instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from schem_json.exceptions import ErrorTree
        return ErrorTree
    elif name == "FormatError":
        warnings.warn(
            "Importing FormatError directly from the schem_json package "
            "is deprecated and will become an ImportError. Import it from "
            "schem_json.exceptions instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from schem_json.exceptions import FormatError
        return FormatError
    elif name == "Validator":
        warnings.warn(
            "Importing Validator directly from the schem_json package "
            "is deprecated and will become an ImportError. Import it from "
            "schem_json.protocols instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from schem_json.protocols import Validator
        return Validator
    elif name == "RefResolutionError":
        from schem_json.exceptions import _RefResolutionError
        warnings.warn(
            _RefResolutionError._DEPRECATION_MESSAGE,
            DeprecationWarning,
            stacklevel=2,
        )
        return _RefResolutionError

    format_checkers = {
        "draft3_format_checker": Draft3Validator,
        "draft4_format_checker": Draft4Validator,
        "draft6_format_checker": Draft6Validator,
        "draft7_format_checker": Draft7Validator,
        "draft201909_format_checker": Draft201909Validator,
        "draft202012_format_checker": Draft202012Validator,
    }
    ValidatorForFormat = format_checkers.get(name)
    if ValidatorForFormat is not None:
        warnings.warn(
            f"Accessing schem_json.{name} is deprecated and will be "
            "removed in a future release. Instead, use the FORMAT_CHECKER "
            "attribute on the corresponding Validator.",
            DeprecationWarning,
            stacklevel=2,
        )
        return ValidatorForFormat.FORMAT_CHECKER

    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "Draft201909Validator",
    "Draft202012Validator",
    "Draft3Validator",
    "Draft4Validator",
    "Draft6Validator",
    "Draft7Validator",
    "FormatChecker",
    "SchemaError",
    "TypeChecker",
    "ValidationError",
    "validate",
]
