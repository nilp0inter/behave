"""
Provides the ``@param`` decorator for declaring step parameters
that are configured externally via YAML configuration files.

This enables a "configuration phase" between test definition and execution,
where QA engineers can supply concrete values for degrees-of-freedom
declared by step decorators.

Usage example::

    from behave import given, param

    @param("temperature", type=float, min=0.0, max=2.0)
    @param("max_tokens", type=int, min=1, max=4096)
    @given("the LLM is configured")
    def step_impl(context):
        temp = context.params.temperature
        tokens = context.params.max_tokens
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


class ParamValidationError(ValueError):
    """Raised when a parameter value fails validation."""
    pass


@dataclass
class ParamDef:
    """Stores metadata for a single step parameter declaration."""
    name: str
    type: Callable = float
    min: Optional[Any] = None
    max: Optional[Any] = None
    choices: Optional[list] = None


def param(name, type=float, min=None, max=None, choices=None):
    """Decorator that declares a configurable parameter on a step function.

    Multiple ``@param`` decorators can be stacked on the same function.
    Must be placed **above** the ``@given``/``@when``/``@then`` decorator.

    :param name:    Parameter name (used as key in YAML config and context.params).
    :param type:    Callable for type conversion (default: float).
    :param min:     Optional minimum value (inclusive).
    :param max:     Optional maximum value (inclusive).
    :param choices: Optional list of allowed values.
    """
    param_def = ParamDef(name=name, type=type, min=min, max=max, choices=choices)

    def decorator(func):
        if not hasattr(func, "_behave_params"):
            func._behave_params = []
        func._behave_params.append(param_def)
        return func
    return decorator


def validate_value(param_def, value):
    """Validate and convert a value according to a ParamDef's constraints.

    :param param_def:  The ParamDef describing the parameter.
    :param value:      The raw value to validate.
    :returns: The converted value.
    :raises ParamValidationError: If conversion or constraint check fails.
    """
    try:
        converted = param_def.type(value)
    except (ValueError, TypeError) as e:
        raise ParamValidationError(
            "Parameter '{name}': cannot convert {value!r} to {type_name}: {error}".format(
                name=param_def.name,
                value=value,
                type_name=param_def.type.__name__,
                error=e,
            )
        ) from e

    if param_def.min is not None and converted < param_def.min:
        raise ParamValidationError(
            "Parameter '{name}': value {value!r} is below minimum {min}".format(
                name=param_def.name,
                value=converted,
                min=param_def.min,
            )
        )
    if param_def.max is not None and converted > param_def.max:
        raise ParamValidationError(
            "Parameter '{name}': value {value!r} is above maximum {max}".format(
                name=param_def.name,
                value=converted,
                max=param_def.max,
            )
        )
    if param_def.choices is not None and converted not in param_def.choices:
        raise ParamValidationError(
            "Parameter '{name}': value {value!r} not in choices {choices}".format(
                name=param_def.name,
                value=converted,
                choices=param_def.choices,
            )
        )
    return converted


def get_step_params(func):
    """Return the list of ParamDef objects declared on a step function.

    :param func:  The step function (possibly decorated with @param).
    :returns: List of ParamDef objects, or empty list if none declared.
    """
    return getattr(func, "_behave_params", [])
