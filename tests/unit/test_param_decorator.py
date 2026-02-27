"""Tests for behave.param_decorator module."""

import pytest
from behave.param_decorator import (
    ParamDef,
    ParamValidationError,
    param,
    validate_value,
    get_step_params,
)


# ---------------------------------------------------------------------------
# TEST: ParamDef
# ---------------------------------------------------------------------------
class TestParamDef:
    def test_stores_name(self):
        pd = ParamDef(name="temperature")
        assert pd.name == "temperature"

    def test_default_type_is_float(self):
        pd = ParamDef(name="x")
        assert pd.type is float

    def test_stores_custom_type(self):
        pd = ParamDef(name="count", type=int)
        assert pd.type is int

    def test_min_max_defaults_to_none(self):
        pd = ParamDef(name="x")
        assert pd.min is None
        assert pd.max is None

    def test_stores_min_max(self):
        pd = ParamDef(name="temperature", type=float, min=0.0, max=2.0)
        assert pd.min == 0.0
        assert pd.max == 2.0

    def test_stores_all_metadata(self):
        pd = ParamDef(name="tokens", type=int, min=1, max=4096)
        assert pd.name == "tokens"
        assert pd.type is int
        assert pd.min == 1
        assert pd.max == 4096

    def test_choices_defaults_to_none(self):
        pd = ParamDef(name="x")
        assert pd.choices is None

    def test_stores_choices(self):
        pd = ParamDef(name="model", type=str, choices=["gpt-4", "gpt-3.5"])
        assert pd.choices == ["gpt-4", "gpt-3.5"]


# ---------------------------------------------------------------------------
# TEST: @param decorator
# ---------------------------------------------------------------------------
class TestParamDecorator:
    def test_attaches_behave_params_to_function(self):
        @param("temperature", type=float, min=0.0, max=2.0)
        def step_impl(context):
            pass

        assert hasattr(step_impl, "_behave_params")
        assert len(step_impl._behave_params) == 1
        pd = step_impl._behave_params[0]
        assert pd.name == "temperature"
        assert pd.type is float
        assert pd.min == 0.0
        assert pd.max == 2.0

    def test_multiple_params_compose(self):
        @param("temperature", type=float, min=0.0, max=2.0)
        @param("max_tokens", type=int, min=1, max=4096)
        def step_impl(context):
            pass

        assert len(step_impl._behave_params) == 2
        names = [pd.name for pd in step_impl._behave_params]
        assert "max_tokens" in names
        assert "temperature" in names

    def test_returns_original_function(self):
        def my_step(context):
            return "hello"

        decorated = param("x")(my_step)
        assert decorated is my_step
        assert my_step("ctx") == "hello"

    def test_param_with_defaults(self):
        @param("value")
        def step_impl(context):
            pass

        pd = step_impl._behave_params[0]
        assert pd.type is float
        assert pd.min is None
        assert pd.max is None
        assert pd.choices is None

    def test_param_with_choices(self):
        @param("model", type=str, choices=["gpt-4", "gpt-3.5"])
        def step_impl(context):
            pass

        pd = step_impl._behave_params[0]
        assert pd.name == "model"
        assert pd.type is str
        assert pd.choices == ["gpt-4", "gpt-3.5"]

    def test_param_above_step_decorator(self):
        """Simulates @param placed above @given by decorating in correct order."""
        def mock_given(text):
            def decorator(func):
                func._step_text = text
                return func
            return decorator

        @param("temperature", type=float)
        @mock_given("the LLM is configured")
        def step_impl(context):
            pass

        assert hasattr(step_impl, "_behave_params")
        assert hasattr(step_impl, "_step_text")
        assert step_impl._step_text == "the LLM is configured"
        assert step_impl._behave_params[0].name == "temperature"


# ---------------------------------------------------------------------------
# TEST: validate_value
# ---------------------------------------------------------------------------
class TestValidateValue:
    def test_accepts_valid_float(self):
        pd = ParamDef(name="temp", type=float, min=0.0, max=2.0)
        result = validate_value(pd, 0.7)
        assert result == 0.7
        assert isinstance(result, float)

    def test_accepts_valid_int(self):
        pd = ParamDef(name="tokens", type=int, min=1, max=4096)
        result = validate_value(pd, 100)
        assert result == 100
        assert isinstance(result, int)

    def test_converts_string_to_float(self):
        pd = ParamDef(name="temp", type=float)
        result = validate_value(pd, "0.7")
        assert result == 0.7

    def test_converts_string_to_int(self):
        pd = ParamDef(name="count", type=int)
        result = validate_value(pd, "42")
        assert result == 42

    def test_accepts_boundary_min(self):
        pd = ParamDef(name="x", type=float, min=0.0, max=1.0)
        result = validate_value(pd, 0.0)
        assert result == 0.0

    def test_accepts_boundary_max(self):
        pd = ParamDef(name="x", type=float, min=0.0, max=1.0)
        result = validate_value(pd, 1.0)
        assert result == 1.0

    def test_rejects_below_min(self):
        pd = ParamDef(name="temp", type=float, min=0.0, max=2.0)
        with pytest.raises(ParamValidationError, match="below minimum"):
            validate_value(pd, -0.1)

    def test_rejects_above_max(self):
        pd = ParamDef(name="temp", type=float, min=0.0, max=2.0)
        with pytest.raises(ParamValidationError, match="above maximum"):
            validate_value(pd, 2.5)

    def test_rejects_wrong_type(self):
        pd = ParamDef(name="count", type=int)
        with pytest.raises(ParamValidationError, match="cannot convert"):
            validate_value(pd, "not_a_number")

    def test_no_min_constraint(self):
        pd = ParamDef(name="x", type=float, max=10.0)
        result = validate_value(pd, -999.0)
        assert result == -999.0

    def test_no_max_constraint(self):
        pd = ParamDef(name="x", type=float, min=0.0)
        result = validate_value(pd, 999999.0)
        assert result == 999999.0

    def test_string_type(self):
        pd = ParamDef(name="mode", type=str)
        result = validate_value(pd, "verbose")
        assert result == "verbose"

    def test_accepts_value_in_choices(self):
        pd = ParamDef(name="model", type=str, choices=["gpt-4", "gpt-3.5"])
        result = validate_value(pd, "gpt-4")
        assert result == "gpt-4"

    def test_rejects_value_not_in_choices(self):
        pd = ParamDef(name="model", type=str, choices=["gpt-4", "gpt-3.5"])
        with pytest.raises(ParamValidationError, match="not in choices"):
            validate_value(pd, "claude")

    def test_choices_with_numeric_type(self):
        pd = ParamDef(name="size", type=int, choices=[128, 256, 512])
        assert validate_value(pd, 256) == 256
        with pytest.raises(ParamValidationError, match="not in choices"):
            validate_value(pd, 64)


# ---------------------------------------------------------------------------
# TEST: get_step_params
# ---------------------------------------------------------------------------
class TestGetStepParams:
    def test_returns_empty_list_for_undecorated(self):
        def plain_func(context):
            pass

        assert get_step_params(plain_func) == []

    def test_returns_params_for_decorated(self):
        @param("x", type=float)
        @param("y", type=int)
        def step_impl(context):
            pass

        params = get_step_params(step_impl)
        assert len(params) == 2
        assert all(isinstance(p, ParamDef) for p in params)
