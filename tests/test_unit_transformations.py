from types import SimpleNamespace
from unittest.mock import patch

from src_new.extractors.unit_extractor import UnitExtractor
from src_new.extraction.state_extractor import StateExtractor


TYPE_NAMES = {
    1: "Zergling",
    2: "BanelingCocoon",
    3: "Drone",
    4: "HighTemplar",
}


class MockUnit:
    def __init__(
        self,
        tag,
        unit_type,
        owner=1,
        x=10.0,
        y=10.0,
        z=8.0,
        build_progress=1.0,
    ):
        self.tag = tag
        self.unit_type = unit_type
        self.owner = owner
        self.pos = SimpleNamespace(x=x, y=y, z=z)
        self.health = 35.0
        self.health_max = 35.0
        self.shield = 0.0
        self.shield_max = 0.0
        self.energy = 0.0
        self.energy_max = 0.0
        self.facing = 0.0
        self.radius = 0.375
        self.build_progress = build_progress
        self.is_flying = False
        self.is_burrowed = False
        self.is_hallucination = False
        self.weapon_cooldown = 0.0
        self.attack_upgrade_level = 0
        self.armor_upgrade_level = 0
        self.shield_upgrade_level = 0
        self.cargo_space_taken = 0
        self.cargo_space_max = 0
        self.orders = []
        self.buff_ids = []
        self.buff_duration_remain = 0
        self.buff_duration_max = 0
        self.engaged_target_tag = 0
        self.detect_range = 0.0
        self.radar_range = 0.0
        self.is_active = True
        self.cloak = 3
        self.display_type = 1


def make_obs(units, dead_units=None, game_loop=1):
    raw_data = SimpleNamespace(
        units=units,
        event=SimpleNamespace(dead_units=dead_units or []),
    )
    return SimpleNamespace(
        observation=SimpleNamespace(raw_data=raw_data, game_loop=game_loop),
        chat=[],
    )


def fake_type_name(unit_type_id):
    return TYPE_NAMES[unit_type_id]


@patch("src_new.extractors.unit_extractor.is_building", return_value=False)
@patch("src_new.extractors.unit_extractor.get_unit_type_name", side_effect=fake_type_name)
def test_same_tag_morph_closes_source_and_assigns_target_id(_name, _building):
    extractor = UnitExtractor(player_id=1)

    first = extractor.extract(make_obs([MockUnit(10, 1)], game_loop=1))
    assert first["p1_zergling_001"]["_lifecycle"] == "completed"

    second = extractor.extract(
        make_obs([MockUnit(10, 2, build_progress=0.0)], game_loop=2)
    )

    assert second["p1_zergling_001"]["_lifecycle"] == "morphed"
    assert second["p1_banelingcocoon_001"]["_lifecycle"] == "unit_started"
    assert extractor.tag_to_readable_id[10] == "p1_banelingcocoon_001"

    TYPE_NAMES[5] = "Baneling"
    third = extractor.extract(make_obs([MockUnit(10, 5)], game_loop=3))
    assert third["p1_banelingcocoon_001"]["_lifecycle"] == "morphed"
    assert third["p1_baneling_001"]["_lifecycle"] == "completed"
    assert extractor.tag_to_readable_id[10] == "p1_baneling_001"


@patch("src_new.extractors.unit_extractor.is_building", return_value=False)
@patch("src_new.extractors.unit_extractor.get_unit_type_name", side_effect=fake_type_name)
def test_hidden_drone_near_new_zerg_building_is_morphed(_name, _building):
    extractor = UnitExtractor(player_id=1)
    extractor.extract(make_obs([MockUnit(20, 3, x=11.0, y=12.0)], game_loop=1))
    extractor.extract(make_obs([], game_loop=2))

    resolved = extractor.resolve_hidden_units(
        buildings_data={},
        transformation_candidates=[
            {
                "tag": 99,
                "unit_type_name": "extractor",
                "position": (12.0, 12.0, 8.0),
                "pos_string": "(12.0, 12.0, 8.0)",
                "entity_kind": "building",
            }
        ],
    )

    assert resolved["p1_drone_001"]["_lifecycle"] == "morphed"
    assert 20 not in extractor.tag_to_readable_id


@patch("src_new.extractors.unit_extractor.is_building", return_value=False)
@patch("src_new.extractors.unit_extractor.get_unit_type_name", side_effect=fake_type_name)
def test_hidden_templar_near_archon_cocoon_is_merged(_name, _building):
    extractor = UnitExtractor(player_id=1)
    extractor.extract(make_obs([MockUnit(30, 4, x=40.0, y=41.0)], game_loop=1))
    extractor.extract(make_obs([], game_loop=2))

    resolved = extractor.resolve_hidden_units(
        buildings_data={},
        transformation_candidates=[
            {
                "tag": 100,
                "unit_type_name": "archoncocoon",
                "position": (40.5, 41.0, 8.0),
                "pos_string": "(40.5, 41.0, 8.0)",
                "entity_kind": "unit",
            }
        ],
    )

    assert resolved["p1_hightemplar_001"]["_lifecycle"] == "merged"
    assert 30 not in extractor.tag_to_readable_id


def test_state_extractor_indexes_type_change_hints_by_loop_and_tag():
    extractor = StateExtractor()
    extractor.set_unit_type_change_events({
        123: [
            {"game_loop": 123, "tag": 42, "unit_type_name": "BanelingCocoon"}
        ]
    })

    assert extractor.unit_type_change_events[123][42]["unit_type_name"] == (
        "BanelingCocoon"
    )
