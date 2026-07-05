"""Runtime wiring: register the per-tick consequences on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .breath import BreathConsequence
from .currents import CurrentConsequence, HazardConsequence
from .marinelife import MarineThreatConsequence


def install_aquasim(actor: WorldActor) -> None:
    """Register the per-tick consequences (a ``service_factories`` entry).

    Covers the v1 breath/current/hazard drains plus the v2 marine-life threat, which reuses
    the core :class:`~bunnyland.core.HealthComponent` to bite divers sharing a predator's room.
    """
    actor.register_consequence(BreathConsequence())
    actor.register_consequence(CurrentConsequence())
    actor.register_consequence(HazardConsequence())
    actor.register_consequence(MarineThreatConsequence())


__all__ = ["install_aquasim"]
