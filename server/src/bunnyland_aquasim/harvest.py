"""Harvesting pearls, coral, and fish (v2 support mechanic + connectors).

A :class:`HarvestNodeComponent` sits on a pearl bed, coral head, or fish shoal resting in a
water room. The ``harvest`` verb pulls one yield from it, chosen **deterministically** from
the node's desirability-ordered ``table`` (a hash of the node id and epoch), biased upward by
the harvester's luck when a fortune pack is loaded. Each yield feeds several sinks at once:

- edible yields carry Foundation Consumables' ``FoodComponent``, so
  fish always feeds **lifesim hunger** with no other pack required; and, when a hearth pack
  is loaded, an ``IngredientComponent`` so it can be cooked;
- pearls and treasures carry a museum ``CollectibleComponent`` when a museum pack is loaded;
- a :class:`HarvestedEvent` is published for any interested pack.

Validation order follows the project convention: invalid id -> missing entity -> wrong
state -> wrong kind -> apply. Deterministic throughout.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    contents,
    spawn_entity,
)
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_entity,
)
from bunnyland.foundation.consumables.components import FoodComponent
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .breath import BreathComponent, breath_band
from .spatial import room_of
from .submersion import is_water_room
from .swim import improve_swim
from .synergy import publish_collectible, publish_ingredient, read_luck

#: Luck units that shift the chosen loot one step up the desirability-ordered table.
LUCK_PER_STEP = 5.0


@dataclass(frozen=True)
class HarvestNodeComponent(Component):
    """A harvestable pearl bed, coral head, or fish shoal in a water room.

    ``table`` is ordered plainest-first; luck shifts the pick upward. ``remaining`` yields
    are left; ``edible`` yields feed hunger and carry ``food_tags`` for cooking; ``category``
    and ``rarity`` classify a museum collectible.
    """

    resource: str = "pearl"
    table: tuple[str, ...] = ("a small pearl",)
    remaining: int = 1
    edible: bool = False
    food_tags: tuple[str, ...] = ()
    nutrition: float = 0.0
    satiety: float = 0.0
    collectible: bool = False
    category: str = "curio"
    rarity: str = "common"

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if self.remaining <= 0:
            return ()
        return (f"There is {self.resource} here to harvest.",)


class HarvestedEvent(DomainEvent):
    """A diver harvested a yield from a marine node (a connector surface for hearth/museum)."""

    node_id: str
    resource: str
    yield_id: str
    yield_name: str
    category: str


def luck_biased_index(seed_key: str, epoch: int, size: int, luck: float = 0.0) -> int:
    """Deterministically pick an index in ``[0, size)``, shifted upward by ``luck``."""
    digest = hashlib.sha256(f"{seed_key}:{epoch}".encode()).hexdigest()
    base = int(digest, 16) % size
    shift = int(luck // LUCK_PER_STEP)
    return max(0, min(size - 1, base + shift))


def luck_biased_loot(seed_key: str, epoch: int, table: tuple[str, ...], luck: float = 0.0) -> str:
    """Pick one yield from a desirability-ordered ``table``, biased upward by ``luck``."""
    return table[luck_biased_index(seed_key, epoch, len(table), luck)]


def _first_node_in_room(world: World, room: Entity) -> Entity | None:
    nodes: list[Entity] = []
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if entity.has_component(HarvestNodeComponent) and (
            entity.get_component(HarvestNodeComponent).remaining > 0
        ):
            nodes.append(entity)
    nodes.sort(key=lambda entity: str(entity.id))
    return nodes[0] if nodes else None


class HarvestHandler:
    """Pull a single yield from a marine harvest node in the diver's water room."""

    command_type = "harvest"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if not is_water_room(room):
            return rejected("you are not in the water")
        if character.has_component(BreathComponent) and (
            breath_band(character.get_component(BreathComponent)) == "crisis"
        ):
            return rejected("you have no breath left to harvest")

        node, rejection = self._resolve_node(ctx, room, command)
        if rejection is not None:
            return rejection

        events: list[DomainEvent] = [self._harvest(ctx, character, node)]
        skill_event = improve_swim(character, epoch=ctx.epoch)
        if skill_event is not None:
            events.append(skill_event)
        return ok(*events)

    def _resolve_node(self, ctx: HandlerContext, room: Entity, command: SubmittedCommand):
        raw_node = command.payload.get("node_id")
        if raw_node is not None:
            node_id, node, rejection = require_entity(
                ctx,
                raw_node,
                invalid_reason="invalid node id",
                missing_reason="that node does not exist",
            )
            if rejection is not None:
                return None, rejection
            node_room = room_of(ctx.world, node_id)
            if node_room is None or node_room.id != room.id:
                return None, rejected("that node is not here")
            if not node.has_component(HarvestNodeComponent):
                return None, rejected("that is not a harvest node")
            if node.get_component(HarvestNodeComponent).remaining <= 0:
                return None, rejected("that node is exhausted")
            return node, None
        node = _first_node_in_room(ctx.world, room)
        if node is None:
            return None, rejected("there is nothing here to harvest")
        return node, None

    def _harvest(self, ctx: HandlerContext, character: Entity, node: Entity) -> DomainEvent:
        component = node.get_component(HarvestNodeComponent)
        luck = read_luck(character)
        yield_name = luck_biased_loot(str(node.id), ctx.epoch, component.table, luck)
        item = self._spawn_yield(ctx.world, component, yield_name)
        character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)
        replace_component(node, replace(component, remaining=component.remaining - 1))
        room = room_of(ctx.world, character.id)
        return HarvestedEvent(
            **ctx.event_base(
                visibility=EventVisibility.ROOM,
                actor_id=str(character.id),
                room_id=str(room.id) if room is not None else None,
                target_ids=(str(node.id),),
                node_id=str(node.id),
                resource=component.resource,
                yield_id=str(item.id),
                yield_name=yield_name,
                category=component.category,
            )
        )

    def _spawn_yield(
        self, world: World, component: HarvestNodeComponent, yield_name: str
    ) -> Entity:
        item = spawn_entity(
            world,
            [
                IdentityComponent(
                    name=yield_name,
                    kind="item",
                    tags=("aquasim", "harvest", component.resource),
                ),
                PortableComponent(),
                HoldableComponent(slot="hand"),
            ],
        )
        if component.edible:
            # Core FoodComponent feeds lifesim hunger with no partner pack required.
            item.add_component(
                FoodComponent(nutrition=component.nutrition, satiety=component.satiety, raw=True)
            )
            publish_ingredient(item, tags=component.food_tags)
        if component.collectible:
            publish_collectible(item, category=component.category, rarity=component.rarity)
        return item


def harvest_fragments(world: World, character: Entity) -> list[str]:
    """List the harvestable nodes in the character's current water room."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if not is_water_room(room):
        return []
    lines: list[str] = []
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if not entity.has_component(HarvestNodeComponent):
            continue
        ctx = ComponentPromptContext.for_entity(world, entity)
        lines.extend(entity.get_component(HarvestNodeComponent).prompt_fragments(ctx))
    return sorted(lines)


HARVEST_DEF = ActionDefinition(
    command_type="harvest",
    title="Harvest",
    description="Harvest pearls, coral, or fish from a marine node in the water room you are in.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "node_id": ActionArgument(
            title="Node",
            description="The harvest node to work; omit to take the first one here.",
            kind="entity",
        ),
    },
)

HARVEST_ACTION_DEFINITIONS = (HARVEST_DEF,)
HARVEST_ACTION_HANDLERS = (HarvestHandler,)


__all__ = [
    "HARVEST_ACTION_DEFINITIONS",
    "HARVEST_ACTION_HANDLERS",
    "HARVEST_DEF",
    "LUCK_PER_STEP",
    "HarvestHandler",
    "HarvestNodeComponent",
    "HarvestedEvent",
    "harvest_fragments",
    "luck_biased_index",
    "luck_biased_loot",
]
