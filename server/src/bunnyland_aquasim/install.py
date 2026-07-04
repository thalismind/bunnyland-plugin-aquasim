"""Runtime wiring: register the per-tick consequences on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .breath import BreathConsequence
from .currents import CurrentConsequence, HazardConsequence


def install_aquasim(actor: WorldActor) -> None:
    """Register the breath, current, and hazard consequences (a ``service_factories`` entry)."""
    actor.register_consequence(BreathConsequence())
    actor.register_consequence(CurrentConsequence())
    actor.register_consequence(HazardConsequence())


__all__ = ["install_aquasim"]
