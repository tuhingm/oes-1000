from pathlib import Path

import pandas as pd


def test_synthetic_datasets_have_expected_shapes_and_distinct_schemas():
    root = Path("examples")
    expected = {
        "synthetic_macro_quarterly.csv": (240, {"quarter", "industrial_activity", "producer_price_index", "policy_rate", "credit_spread"}),
        "synthetic_labor_panel.csv": (432, {"firm_id", "year", "worker_skill_index", "capital_stock", "log_hourly_wage", "training_hours"}),
        "synthetic_policy_panel.csv": (576, {"region_id", "year", "adoption_year", "policy_exposure", "baseline_capacity", "employment_index"}),
        "synthetic_building_energy.csv": (420, {"building_obs", "outdoor_temperature_c", "solar_irradiance", "floor_area_scale", "occupants", "electric_load_mwh", "district_peak_load"}),
        "synthetic_bayesian_monthly.csv": (180, {"month_id", "output_gap", "inflation_rate", "term_premium", "survey_expectations"}),
        "synthetic_regime_series.csv": (600, {"period", "latent_regime_for_validation", "synthetic_growth", "volatility_proxy", "spread_signal"}),
    }
    schemas = []
    for filename, (nrows, required) in expected.items():
        frame = pd.read_csv(root / filename)
        assert len(frame) == nrows
        assert required <= set(frame.columns)
        schemas.append(tuple(frame.columns))
    assert len(set(schemas)) == len(schemas)


def test_synthetic_policy_panel_contains_treated_and_never_treated_units():
    frame = pd.read_csv("examples/synthetic_policy_panel.csv")
    assert frame["region_id"].nunique() == 48
    assert (frame["adoption_year"].isna()).any()
    assert (frame["adoption_year"].notna()).any()
    assert set(frame["policy_exposure"].unique()) == {0, 1}


def test_synthetic_regime_fixture_has_two_simulation_states():
    frame = pd.read_csv("examples/synthetic_regime_series.csv")
    assert set(frame["latent_regime_for_validation"].unique()) == {0, 1}
