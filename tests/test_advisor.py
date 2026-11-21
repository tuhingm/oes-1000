import pandas as pd
from engine.advisor import recommend


def test_numeric_outcome_recommends_ols():
    frame = pd.DataFrame({"y": [1., 2., 3., 4.], "x": [2., 3., 4., 5.]})
    recs = recommend(frame, {"outcome": "y"})
    assert recs[0]["id"] == "ols_hc3"
    assert recs[0]["implemented"] is True


def test_binary_outcome_recommends_logit():
    frame = pd.DataFrame({"y": [0, 1, 0, 1, 1], "x": [2., 3., 4., 5., 6.]})
    recs = recommend(frame, {"outcome": "y"})
    assert recs[0]["id"] == "logit"


def test_entity_role_recommends_fixed_effects_first():
    frame = pd.DataFrame({"y": [1., 2., 3., 4.], "x": [2., 3., 4., 5.], "id": [1, 1, 2, 2]})
    recs = recommend(frame, {"outcome": "y", "entity": "id"})
    assert recs[0]["id"] == "entity_fe"
