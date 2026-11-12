import json
from pathlib import Path


def test_catalogue_target_allocations_sum_to_1000():
    data = json.loads(Path("catalog/targets.json").read_text())
    assert sum(f["target"] for f in data["families"]) == data["catalogue_target"] == 1000


def test_legacy_catalogue_snapshot_has_44_entries():
    data = json.loads(Path("catalog/legacy-oes-catalog.json").read_text())
    ids = [model["id"] for model in data["models"]]
    assert len(ids) == 44
    assert len(ids) == len(set(ids))


def test_canonical_catalogue_has_unique_ids_and_expected_progress():
    data = json.loads(Path("catalog/models.json").read_text())
    ids = [model["id"] for model in data["models"]]
    assert len(ids) == len(set(ids))
    assert len(ids) == 1000
    assert sum(model.get("legacy_catalogue_id") is not None for model in data["models"]) == 44
    assert sum(model["status"] == "planned" for model in data["models"]) == 944
    assert sum(model["status"] == "implemented" for model in data["models"]) == 12
    assert all(model["status"] in {"planned", "implemented", "tested", "validated"} for model in data["models"])
