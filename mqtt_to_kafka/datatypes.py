from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Identity:
    name: str
    family: str
    archetype: str
    birthday_ts: str
    birthday_epoch: int
    badge_id: str
    rock: bool
    is_active: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "family": self.family,
            "archetype": self.archetype,
            "birthday_epoch": self.birthday_epoch,
            "badge_id": self.badge_id,
            "rock": self.rock,
        }

@dataclass
class State:
    status: int
    wellness: int
    disposition: int
    age: int
    hunger: int
    thirst: int
    weight: int
    happiness: int
    health: int
    life_phase: str = field(default="egg")
    life_phase_change_timestamp: str = field(default="")

    def to_pipe_delimited(self) -> str:
        return "|".join(str(getattr(self, field)) for field in self.__dataclass_fields__)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "wellness": self.wellness,
            "disposition": self.disposition,
            "age": self.age,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "weight": self.weight,
            "happiness": self.happiness,
            "health": self.health,
            "life_phase": self.life_phase,
            "life_phase_change_timestamp": self.life_phase_change_timestamp,
        }


@dataclass
class Modifier:
    multiplier: float


@dataclass
class Modifiers:
    age: Modifier
    hunger: Modifier
    thirst: Modifier
    weight: Modifier
    happiness: Modifier


@dataclass
class RawCyberPartnerStatus:
    identity: Identity
    state: State
    modifiers: Modifiers

    def mqtt_payload(self) -> dict:
        payload = {}
        payload.update(self.identity.to_dict())
        payload.update(self.state.to_dict())
        # Add modifiers with prefix
        for field_name, field_value in vars(self.modifiers).items():
            payload[f"modifier_{field_name}"] = field_value.multiplier

        payload_whitelist = [
            "birthday_epoch",
            "rock",
            "status",
            "hunger",
            "thirst",
            "weight",
            "happiness",
            "health",
            "modifier_age"
        ]
        payload = {k: v for k, v in payload.items() if k in payload_whitelist}
        return payload


def transform_cyberpartner_dict(raw_cyberpartner: Dict) -> RawCyberPartnerStatus | None:
    try:
        identity = Identity(
            name=raw_cyberpartner["cp"].get("name"),
            family=raw_cyberpartner["cp"].get("family"),
            archetype=raw_cyberpartner["cp"].get("archetype"),
            birthday_ts=raw_cyberpartner["cp"].get("birthday_ts"),
            birthday_epoch=raw_cyberpartner["cp"].get("birthday_epoch"),
            badge_id=raw_cyberpartner["cp"].get("badge_id"),
            rock=raw_cyberpartner["cp"].get("rock"),
            is_active=raw_cyberpartner["cp"].get("is_active"),
        )
        state = State(
            status=raw_cyberpartner["state"].get("status"),
            wellness=raw_cyberpartner["state"].get("wellness"),
            disposition=raw_cyberpartner["state"].get("disposition"),
            age=raw_cyberpartner["state"].get("age"),
            hunger=raw_cyberpartner["state"].get("hunger"),
            thirst=raw_cyberpartner["state"].get("thirst"),
            weight=raw_cyberpartner["state"].get("weight"),
            happiness=raw_cyberpartner["state"].get("happiness"),
            health=raw_cyberpartner["state"].get("health"),
            life_phase=raw_cyberpartner["state"].get("life_phase"),
            life_phase_change_timestamp=str(raw_cyberpartner["state"].get("life_phase_change_timestamp")),
        )
        modifiers = Modifiers(**{k: Modifier(**v) for k, v in raw_cyberpartner["cp"].get("stat_modifiers", {}).items()})
        return RawCyberPartnerStatus(
            identity=identity,
            state=state,
            modifiers=modifiers
        )
    except Exception as e:
        return None
