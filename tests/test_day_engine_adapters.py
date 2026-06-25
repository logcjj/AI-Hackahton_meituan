from __future__ import annotations

import sys

from web_agent_demo.day_engine_adapters import (
    DAY_ENGINE_ADAPTER_DEFAULT_ID,
    DAY_ENGINE_ADAPTER_STATUS_ACTIVE,
    DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_INSTALLED,
    DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_MISSING,
    day_engine_adapter_capabilities,
    normalize_day_engine_adapter,
    selected_day_engine_payload,
)
from web_agent_demo.simulation_engine import simulation_to_dict


def test_day_engine_adapters_keep_native_default_without_optional_imports():
    before = {name for name in ("uxsim", "traci", "cityflow", "mesa") if name in sys.modules}
    payload = simulation_to_dict(selected_day_engine_payload())
    after = {name for name in ("uxsim", "traci", "cityflow", "mesa") if name in sys.modules}
    capabilities = payload["adapter_capabilities"]
    by_id = {item["id"]: item for item in capabilities}

    assert before == after
    assert payload["default_adapter_id"] == DAY_ENGINE_ADAPTER_DEFAULT_ID
    assert payload["selected_adapter_id"] == DAY_ENGINE_ADAPTER_DEFAULT_ID
    assert payload["active_adapter"]["id"] == DAY_ENGINE_ADAPTER_DEFAULT_ID
    assert payload["active_adapter"]["status"] == DAY_ENGINE_ADAPTER_STATUS_ACTIVE
    assert by_id[DAY_ENGINE_ADAPTER_DEFAULT_ID]["default"] is True
    assert by_id[DAY_ENGINE_ADAPTER_DEFAULT_ID]["selected"] is True
    assert {"uxsim", "sumo-traci", "cityflow", "mesa-abm"}.issubset(by_id)
    assert all(
        by_id[adapter_id]["status"] in {DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_INSTALLED, DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_MISSING}
        for adapter_id in ("uxsim", "sumo-traci", "cityflow", "mesa-abm")
    )
    assert by_id[DAY_ENGINE_ADAPTER_DEFAULT_ID]["integration_stage"] == "active-runtime-simulator"
    assert payload["version"] == "courier-agent-sim-v1"
    assert all(by_id[adapter_id]["integration_stage"] == "optional-runtime-adapter" for adapter_id in ("uxsim", "sumo-traci", "cityflow", "mesa-abm"))
    assert "active CourierSim runtime is always used" in payload["optional_dependency_policy"]


def test_optional_or_unknown_day_engine_adapter_requests_fall_back_to_native():
    assert normalize_day_engine_adapter("unknown-engine") == DAY_ENGINE_ADAPTER_DEFAULT_ID
    payload = simulation_to_dict(selected_day_engine_payload("sumo-traci"))
    selected_flags = {item["id"]: item["selected"] for item in payload["adapter_capabilities"]}

    assert payload["selected_adapter_id"] == DAY_ENGINE_ADAPTER_DEFAULT_ID
    assert payload["active_adapter"]["id"] == DAY_ENGINE_ADAPTER_DEFAULT_ID
    assert selected_flags[DAY_ENGINE_ADAPTER_DEFAULT_ID] is True
    assert selected_flags["sumo-traci"] is False


def test_day_engine_capabilities_carry_source_and_install_metadata():
    capabilities = day_engine_adapter_capabilities()

    assert all(item.source_url for item in capabilities)
    assert all(item.install_hint for item in capabilities)
    assert next(item for item in capabilities if item.id == "uxsim").source_url == "https://github.com/toruseo/UXsim"
    assert next(item for item in capabilities if item.id == "sumo-traci").source_url == "https://eclipse.dev/sumo/"
