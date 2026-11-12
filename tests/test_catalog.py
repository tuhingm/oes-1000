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
