"""Tests for the /api/palette endpoint and palette.py parsing logic."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SAMPLE_POKEMON = [
    {
        "dex": 143,
        "name_en": "Snorlax",
        "name_ko": "잠만보",
        "form": "Base",
        "type1": "Normal",
        "type2": "",
        "hp": 160,
        "atk": 110,
        "def": 65,
        "spa": 65,
        "spd": 110,
        "spe": 30,
        "total": 540,
        "abilities": ["Immunity", "Thick Fat"],
        "ability_hidden": "Gluttony",
        "champions_legal": True,
    },
    {
        "dex": 445,
        "name_en": "Garchomp",
        "name_ko": "한카리아스",
        "form": "Base",
        "type1": "Dragon",
        "type2": "Ground",
        "hp": 108,
        "atk": 130,
        "def": 95,
        "spa": 80,
        "spd": 85,
        "spe": 102,
        "total": 600,
        "abilities": ["Sand Veil", "Rough Skin"],
        "ability_hidden": "Rough Skin",
        "champions_legal": True,
    },
    {
        # Mega form — dex stays at 6 (base Charizard)
        "dex": 6,
        "name_en": "Mega Charizard X",
        "name_ko": "메가 리자몽 X",
        "form": "Mega",
        "type1": "Fire",
        "type2": "Dragon",
        "hp": 78,
        "atk": 130,
        "def": 111,
        "spa": 130,
        "spd": 85,
        "spe": 100,
        "total": 634,
        "abilities": ["Tough Claws"],
        "ability_hidden": None,
        "champions_legal": True,
    },
]


@pytest.fixture(autouse=True)
def reset_palette_cache():
    """Ensure palette module cache is cleared before and after each test."""
    from pokemon_dashboard.palette import clear_palette_cache
    clear_palette_cache()
    yield
    clear_palette_cache()


@pytest.fixture()
def db_root(tmp_path: Path) -> Path:
    """Create a fake pokemon-champions-db directory with a small pokemon.json."""
    db = tmp_path / "pokemon-champions-db"
    data_dir = db / "data" / "json"
    data_dir.mkdir(parents=True)
    (data_dir / "pokemon.json").write_text(
        json.dumps(SAMPLE_POKEMON), encoding="utf-8"
    )
    return db


@pytest.fixture()
def client(db_root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("POKEMON_CHAMPIONS_DB", str(db_root))
    monkeypatch.setenv("POKEMON_RUNS_ROOT", str(db_root / "runs"))
    from pokemon_dashboard.server import app
    return TestClient(app)


def test_palette_returns_200(client: TestClient) -> None:
    r = client.get("/api/palette")
    assert r.status_code == 200


def test_palette_shape(client: TestClient) -> None:
    data = client.get("/api/palette").json()
    assert "species" in data
    assert isinstance(data["species"], dict)


def test_palette_normalized_ids(client: TestClient) -> None:
    species = client.get("/api/palette").json()["species"]
    # Base species use simple lowercase names
    assert "snorlax" in species
    assert "garchomp" in species
    # Mega form: "Mega Charizard X" → "mega_charizard_x"
    assert "mega_charizard_x" in species


def test_palette_snorlax_entry(client: TestClient) -> None:
    species = client.get("/api/palette").json()["species"]
    snorlax = species["snorlax"]
    assert snorlax["dex"] == 143
    assert snorlax["types"] == ["normal"]
    assert snorlax["display"] == "Snorlax"


def test_palette_garchomp_dual_type(client: TestClient) -> None:
    species = client.get("/api/palette").json()["species"]
    garchomp = species["garchomp"]
    assert garchomp["dex"] == 445
    assert set(garchomp["types"]) == {"dragon", "ground"}


def test_palette_mega_uses_base_dex(client: TestClient) -> None:
    """Mega Charizard X must use base dex 6 (PokéAPI sprite limitation)."""
    species = client.get("/api/palette").json()["species"]
    mega = species["mega_charizard_x"]
    assert mega["dex"] == 6
    assert set(mega["types"]) == {"fire", "dragon"}
    assert mega["display"] == "Mega Charizard X"


def test_palette_count(client: TestClient) -> None:
    species = client.get("/api/palette").json()["species"]
    assert len(species) == len(SAMPLE_POKEMON)


def test_palette_missing_json_returns_503(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When pokemon.json is absent, /api/palette must return 503."""
    empty_db = tmp_path / "empty-db"
    empty_db.mkdir()
    monkeypatch.setenv("POKEMON_CHAMPIONS_DB", str(empty_db))
    monkeypatch.setenv("POKEMON_RUNS_ROOT", str(empty_db / "runs"))
    from pokemon_dashboard.server import app
    c = TestClient(app)
    r = c.get("/api/palette")
    assert r.status_code == 503
    body = r.json()
    assert "error" in body
