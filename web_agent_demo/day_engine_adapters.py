from __future__ import annotations

import importlib.util
from dataclasses import dataclass


DAY_ENGINE_ADAPTER_DEFAULT_ID = "native-local"
DAY_ENGINE_ADAPTER_STATUS_ACTIVE = "active"
DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_INSTALLED = "optional-installed"
DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_MISSING = "optional-not-installed"


@dataclass(frozen=True)
class DayEngineAdapterCapability:
    id: str
    label: str
    provider: str
    category: str
    status: str
    selected: bool
    default: bool
    dependency_module: str
    install_hint: str
    integration_stage: str
    capability_summary: str
    source_url: str


_OPTIONAL_ADAPTERS = (
    {
        "id": "uxsim",
        "label": "UXsim traffic-flow effects",
        "provider": "UXsim",
        "category": "lightweight-python-traffic-flow",
        "dependency_module": "uxsim",
        "install_hint": "pip install uxsim",
        "integration_stage": "metadata-only-adapter-seam",
        "capability_summary": "Optional Python traffic-flow layer for congestion and speed effects; native replay remains authoritative when missing.",
        "source_url": "https://github.com/toruseo/UXsim",
    },
    {
        "id": "sumo-traci",
        "label": "SUMO TraCI mobility bridge",
        "provider": "Eclipse SUMO",
        "category": "microscopic-traffic-simulation",
        "dependency_module": "traci",
        "install_hint": "Install Eclipse SUMO and the TraCI Python bindings",
        "integration_stage": "metadata-only-adapter-seam",
        "capability_summary": "Optional high-fidelity traffic simulator bridge for later road-network travel-time feeds.",
        "source_url": "https://eclipse.dev/sumo/",
    },
    {
        "id": "cityflow",
        "label": "CityFlow high-throughput simulator",
        "provider": "CityFlow",
        "category": "large-scale-traffic-simulation",
        "dependency_module": "cityflow",
        "install_hint": "Install CityFlow only for offline traffic-scenario experiments",
        "integration_stage": "metadata-only-adapter-seam",
        "capability_summary": "Optional large-scale traffic-state source; not required for the delivery replay demo.",
        "source_url": "https://cityflow-project.github.io/",
    },
    {
        "id": "mesa-abm",
        "label": "Mesa agent-based courier model",
        "provider": "Mesa",
        "category": "agent-based-modeling",
        "dependency_module": "mesa",
        "install_hint": "pip install mesa",
        "integration_stage": "metadata-only-adapter-seam",
        "capability_summary": "Optional agent-based modeling layer for future courier behavior experiments.",
        "source_url": "https://mesa.readthedocs.io/",
    },
)


def _dependency_status(module_name: str) -> str:
    return (
        DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_INSTALLED
        if importlib.util.find_spec(module_name) is not None
        else DAY_ENGINE_ADAPTER_STATUS_OPTIONAL_MISSING
    )


def normalize_day_engine_adapter(adapter_id: str | None) -> str:
    known_ids = {DAY_ENGINE_ADAPTER_DEFAULT_ID, *(str(item["id"]) for item in _OPTIONAL_ADAPTERS)}
    return str(adapter_id or DAY_ENGINE_ADAPTER_DEFAULT_ID) if str(adapter_id or "") in known_ids else DAY_ENGINE_ADAPTER_DEFAULT_ID


def day_engine_adapter_capabilities(selected_adapter: str | None = None) -> tuple[DayEngineAdapterCapability, ...]:
    selected = normalize_day_engine_adapter(selected_adapter)
    capabilities = [
        DayEngineAdapterCapability(
            id=DAY_ENGINE_ADAPTER_DEFAULT_ID,
            label="Native local discrete-event replay",
            provider="AutoSolver local engine",
            category="native-discrete-event",
            status=DAY_ENGINE_ADAPTER_STATUS_ACTIVE,
            selected=selected == DAY_ENGINE_ADAPTER_DEFAULT_ID,
            default=True,
            dependency_module="",
            install_hint="none",
            integration_stage="active-default",
            capability_summary="Deterministic full-day delivery replay with local road graph, courier movement, shocks and same-stream algorithm comparison.",
            source_url="local:web_agent_demo.day_simulation",
        )
    ]
    for item in _OPTIONAL_ADAPTERS:
        capabilities.append(
            DayEngineAdapterCapability(
                id=str(item["id"]),
                label=str(item["label"]),
                provider=str(item["provider"]),
                category=str(item["category"]),
                status=_dependency_status(str(item["dependency_module"])),
                selected=selected == item["id"],
                default=False,
                dependency_module=str(item["dependency_module"]),
                install_hint=str(item["install_hint"]),
                integration_stage=str(item["integration_stage"]),
                capability_summary=str(item["capability_summary"]),
                source_url=str(item["source_url"]),
            )
        )
    return tuple(capabilities)


def selected_day_engine_payload(selected_adapter: str | None = None) -> dict[str, object]:
    normalized = normalize_day_engine_adapter(selected_adapter)
    capabilities = day_engine_adapter_capabilities(normalized)
    active = next(item for item in capabilities if item.id == normalized)
    if active.status != DAY_ENGINE_ADAPTER_STATUS_ACTIVE:
        normalized = DAY_ENGINE_ADAPTER_DEFAULT_ID
        capabilities = day_engine_adapter_capabilities(normalized)
        active = capabilities[0]
    return {
        "version": "native-discrete-event-v1",
        "routing_provider": "local-road-graph",
        "default_adapter_id": DAY_ENGINE_ADAPTER_DEFAULT_ID,
        "selected_adapter_id": normalized,
        "active_adapter": active,
        "adapter_capabilities": capabilities,
        "optional_dependency_policy": "metadata-only; never import or require optional traffic engines during local demo runs",
    }
