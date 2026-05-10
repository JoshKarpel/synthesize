from __future__ import annotations

import pytest
from click.exceptions import Exit
from rich.console import Console

from synthesize.cli import _select_flow
from synthesize.config import Config, Flow, ResolvedConfig, ResolvedFlow, Settings

FLOW_A = ResolvedFlow(nodes={})
FLOW_B = ResolvedFlow(nodes={})
FLOW_DEFAULT = ResolvedFlow(nodes={})


def make_resolved(flows: dict[str, ResolvedFlow], default_flow_name: str, **settings_kwargs: object) -> ResolvedConfig:
    return ResolvedConfig(flows=flows, default_flow_name=default_flow_name, settings=Settings(**settings_kwargs))


def make_config(flow_names: list[str], **settings_kwargs: object) -> Config:
    return Config(flows={name: Flow() for name in flow_names}, settings=Settings(**settings_kwargs))


def test_resolve_uses_default_flow_setting() -> None:
    resolved = make_config(["a", "b"], default_flow="b").resolve()
    assert resolved.default_flow_name == "b"


def test_resolve_raises_when_default_flow_setting_names_missing_flow() -> None:
    with pytest.raises(ValueError, match="nonexistent"):
        make_config(["a"], default_flow="nonexistent").resolve()


def test_resolve_falls_back_to_flow_named_default() -> None:
    resolved = make_config(["a", "default"]).resolve()
    assert resolved.default_flow_name == "default"


def test_resolve_falls_back_to_first_defined_flow() -> None:
    resolved = make_config(["a", "b"]).resolve()
    assert resolved.default_flow_name == "a"


def test_resolve_applies_setting_overrides() -> None:
    resolved = make_config(["a"]).resolve(["timestamps.sub_second_digits=3"])
    assert resolved.settings.timestamps.sub_second_digits == 3


def test_select_flow_returns_named_flow() -> None:
    resolved = make_resolved({"a": FLOW_A, "b": FLOW_B}, default_flow_name="a")
    assert _select_flow(resolved, "b", Console()) is FLOW_B


def test_select_flow_errors_on_missing_named_flow() -> None:
    resolved = make_resolved({"a": FLOW_A}, default_flow_name="a")
    with pytest.raises(Exit):
        _select_flow(resolved, "nonexistent", Console())


def test_select_flow_uses_default_flow_name_when_flow_is_none() -> None:
    resolved = make_resolved({"a": FLOW_A, "default": FLOW_DEFAULT}, default_flow_name="default")
    assert _select_flow(resolved, None, Console()) is FLOW_DEFAULT
