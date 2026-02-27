"""Tests for behave.param_config module."""

import os
import tempfile
import textwrap

import pytest
import yaml

from behave.param_config import StepParams, ParamConfig, ParamConfigError
from behave.param_decorator import param, ParamDef


# ---------------------------------------------------------------------------
# TEST: StepParams
# ---------------------------------------------------------------------------
class TestStepParams:
    def test_attribute_access(self):
        sp = StepParams({"temperature": 0.7, "max_tokens": 1024})
        assert sp.temperature == 0.7
        assert sp.max_tokens == 1024

    def test_missing_attribute_raises(self):
        sp = StepParams({"temperature": 0.7})
        with pytest.raises(AttributeError, match="no parameter 'missing'"):
            _ = sp.missing

    def test_empty_params(self):
        sp = StepParams()
        with pytest.raises(AttributeError):
            _ = sp.anything

    def test_set(self):
        sp = StepParams()
        sp._set("temperature", 0.7)
        assert sp.temperature == 0.7

    def test_clear(self):
        sp = StepParams({"x": 1})
        sp._clear()
        with pytest.raises(AttributeError):
            _ = sp.x

    def test_as_dict(self):
        data = {"a": 1, "b": 2}
        sp = StepParams(data)
        result = sp._as_dict()
        assert result == data
        assert result is not data  # should be a copy

    def test_bool_false_when_empty(self):
        sp = StepParams()
        assert not sp

    def test_bool_true_when_populated(self):
        sp = StepParams({"x": 1})
        assert sp

    def test_repr(self):
        sp = StepParams({"x": 1})
        assert "StepParams" in repr(sp)
        assert "x" in repr(sp)

    def test_read_only(self):
        sp = StepParams({"x": 1})
        with pytest.raises(AttributeError, match="read-only"):
            sp.x = 2


# ---------------------------------------------------------------------------
# HELPERS for ParamConfig tests
# ---------------------------------------------------------------------------
class MockStep:
    """Minimal step mock for testing."""
    def __init__(self, name, step_type="given"):
        self.name = name
        self.step_type = step_type


class MockMatch:
    """Minimal match mock for testing."""
    def __init__(self, func):
        self.func = func


class MockStepRegistry:
    """Step registry mock that maps step names to match objects."""
    def __init__(self, step_map=None):
        self.step_map = step_map or {}

    def find_match(self, step):
        if step.name in self.step_map:
            return MockMatch(self.step_map[step.name])
        return None


class MockBackground:
    def __init__(self, steps=None):
        self.steps = steps or []
        self.all_steps = self.steps


class MockScenario:
    def __init__(self, name, steps=None, background=None):
        self.name = name
        self.steps = steps or []
        self.background = background


class MockFeature:
    def __init__(self, filename, name, scenarios=None, background=None, rules=None):
        self.filename = filename
        self.name = name
        self.scenarios = scenarios or []
        self.background = background
        self.rules = rules or []


class MockRule:
    def __init__(self, name, scenarios=None, background=None):
        self.name = name
        self.scenarios = scenarios or []
        self.background = background


# ---------------------------------------------------------------------------
# TEST: ParamConfig
# ---------------------------------------------------------------------------
class TestParamConfig:
    def test_no_yaml_no_params_is_ok(self):
        """Feature with no @param steps and no YAML file is fine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("a plain step")])]
            )
            registry = MockStepRegistry({
                "a plain step": lambda ctx: None
            })
            # Should not raise
            pc.load_and_validate([feature], registry)

    def test_missing_yaml_for_params_raises(self):
        """Feature with @param steps but no YAML raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pc = ParamConfig(tmpdir)

            @param("temperature", type=float, min=0.0, max=2.0)
            def step_func(context):
                pass

            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("configure LLM")])]
            )
            registry = MockStepRegistry({"configure LLM": step_func})

            with pytest.raises(ParamConfigError, match="no YAML config file"):
                pc.load_and_validate([feature], registry)

    def test_valid_yaml_loads_params(self):
        """Valid YAML config is loaded and params are accessible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("temperature", type=float, min=0.0, max=2.0)
            def step_func(context):
                pass

            yaml_content = {
                "feature": "Test",
                "scenarios": [{
                    "scenario": "sc1",
                    "steps": [{
                        "step": "configure LLM",
                        "params": {"temperature": 0.7}
                    }]
                }]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("configure LLM")])]
            )
            registry = MockStepRegistry({"configure LLM": step_func})
            pc.load_and_validate([feature], registry)

            sp = pc.get_step_params("test.feature", "sc1", 0)
            assert sp.temperature == 0.7

    def test_missing_param_in_yaml_raises(self):
        """YAML that omits a required param raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("temperature", type=float)
            @param("max_tokens", type=int)
            def step_func(context):
                pass

            yaml_content = {
                "feature": "Test",
                "scenarios": [{
                    "scenario": "sc1",
                    "steps": [{
                        "step": "configure LLM",
                        "params": {"temperature": 0.7}
                        # max_tokens is missing
                    }]
                }]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("configure LLM")])]
            )
            registry = MockStepRegistry({"configure LLM": step_func})

            with pytest.raises(ParamConfigError, match="missing parameter 'max_tokens'"):
                pc.load_and_validate([feature], registry)

    def test_out_of_range_value_raises(self):
        """YAML with out-of-range value raises validation error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("temperature", type=float, min=0.0, max=2.0)
            def step_func(context):
                pass

            yaml_content = {
                "feature": "Test",
                "scenarios": [{
                    "scenario": "sc1",
                    "steps": [{
                        "step": "configure LLM",
                        "params": {"temperature": 5.0}
                    }]
                }]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("configure LLM")])]
            )
            registry = MockStepRegistry({"configure LLM": step_func})

            with pytest.raises(ParamConfigError, match="above maximum"):
                pc.load_and_validate([feature], registry)

    def test_wrong_type_value_raises(self):
        """YAML with wrong type raises validation error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("count", type=int)
            def step_func(context):
                pass

            yaml_content = {
                "feature": "Test",
                "scenarios": [{
                    "scenario": "sc1",
                    "steps": [{
                        "step": "do something",
                        "params": {"count": "not_a_number"}
                    }]
                }]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("do something")])]
            )
            registry = MockStepRegistry({"do something": step_func})

            with pytest.raises(ParamConfigError, match="cannot convert"):
                pc.load_and_validate([feature], registry)

    def test_step_count_mismatch_raises(self):
        """YAML with wrong number of steps raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("x", type=float)
            def step_func(context):
                pass

            yaml_content = {
                "feature": "Test",
                "scenarios": [{
                    "scenario": "sc1",
                    "steps": [
                        {"step": "step one", "params": {"x": 1.0}},
                        {"step": "step two"},
                    ]
                }]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("step one")])]
            )
            registry = MockStepRegistry({"step one": step_func})

            with pytest.raises(ParamConfigError, match="YAML has 2 steps"):
                pc.load_and_validate([feature], registry)

    def test_get_step_params_returns_empty_for_unknown(self):
        """get_step_params returns empty StepParams for unregistered keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pc = ParamConfig(tmpdir)
            sp = pc.get_step_params("nonexistent.feature", "sc", 0)
            assert not sp

    def test_multiple_scenarios(self):
        """Params are correctly keyed per scenario."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("x", type=float)
            def step_a(context):
                pass

            @param("y", type=int)
            def step_b(context):
                pass

            yaml_content = {
                "feature": "Test",
                "scenarios": [
                    {
                        "scenario": "first",
                        "steps": [{"step": "do A", "params": {"x": 1.0}}]
                    },
                    {
                        "scenario": "second",
                        "steps": [{"step": "do B", "params": {"y": 42}}]
                    },
                ]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[
                    MockScenario("first", [MockStep("do A")]),
                    MockScenario("second", [MockStep("do B")]),
                ]
            )
            registry = MockStepRegistry({"do A": step_a, "do B": step_b})
            pc.load_and_validate([feature], registry)

            sp1 = pc.get_step_params("test.feature", "first", 0)
            assert sp1.x == 1.0

            sp2 = pc.get_step_params("test.feature", "second", 0)
            assert sp2.y == 42

    def test_steps_without_params_ok(self):
        """Steps without @param in YAML don't need params key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("x", type=float)
            def step_with_param(context):
                pass

            def step_plain(context):
                pass

            yaml_content = {
                "feature": "Test",
                "scenarios": [{
                    "scenario": "sc1",
                    "steps": [
                        {"step": "plain step"},
                        {"step": "param step", "params": {"x": 1.0}},
                    ]
                }]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [
                    MockStep("plain step"),
                    MockStep("param step"),
                ])]
            )
            registry = MockStepRegistry({
                "plain step": step_plain,
                "param step": step_with_param,
            })
            pc.load_and_validate([feature], registry)

            sp = pc.get_step_params("test.feature", "sc1", 1)
            assert sp.x == 1.0

    def test_background_steps_with_params(self):
        """Background steps with params are validated and stored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("level", type=str)
            def bg_step(context):
                pass

            def scenario_step(context):
                pass

            yaml_content = {
                "feature": "Test",
                "background": {
                    "steps": [
                        {"step": "init system", "params": {"level": "debug"}}
                    ]
                },
                "scenarios": [{
                    "scenario": "sc1",
                    "steps": [
                        {"step": "do something"},
                    ]
                }]
            }
            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f)

            bg = MockBackground([MockStep("init system")])
            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("do something")])],
                background=bg,
            )
            registry = MockStepRegistry({
                "init system": bg_step,
                "do something": scenario_step,
            })
            pc.load_and_validate([feature], registry)

            sp = pc.get_step_params("test.feature", "sc1", 0)
            assert sp.level == "debug"

    def test_empty_yaml_with_params_raises(self):
        """Empty YAML file when feature has param steps raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            @param("x", type=float)
            def step_func(context):
                pass

            yaml_path = os.path.join(tmpdir, "test.yml")
            with open(yaml_path, "w") as f:
                f.write("")  # empty file

            pc = ParamConfig(tmpdir)
            feature = MockFeature(
                filename="test.feature",
                name="Test",
                scenarios=[MockScenario("sc1", [MockStep("do it")])]
            )
            registry = MockStepRegistry({"do it": step_func})

            with pytest.raises(ParamConfigError, match="empty"):
                pc.load_and_validate([feature], registry)
