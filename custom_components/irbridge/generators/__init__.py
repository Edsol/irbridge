from __future__ import annotations

from .base import ClimateCapabilities, ClimateGenerator
from .midea_climate import MideaClimateGenerator
from .electra_climate import ElectraClimateGenerator

_REGISTRY: dict[str, type[ClimateGenerator]] = {
    "midea": MideaClimateGenerator,
    "electra": ElectraClimateGenerator,
}


def get_generator(protocol: str) -> ClimateGenerator:
    """Return a ClimateGenerator instance for the given protocol key.

    Raises KeyError if the protocol is not registered.
    """
    cls = _REGISTRY[protocol]
    return cls()


def available_protocols() -> list[str]:
    return list(_REGISTRY.keys())
