import numpy as np
import pandas as pd

from oes1000.api import estimate_frame


def test_ordered_models_and_tobit_dispatch_through_dataframe_api():
    rng=np.random.default_rng(501)
    n=700
    x=rng.normal(size=n)
    latent=0.5*x+rng.logistic(size=n)
    ordinal=np.digitize(latent,[-0.5,0.6])
    frame=pd.DataFrame({"y_ord":ordinal,"x":x})
    ordered=estimate_frame(frame,"ordered_logit",{"dependent":"y_ord","regressors":["x"]})
    assert ordered["model"]=="ordered_logit"
    assert len(ordered["cutpoints"])==2
    latent_y=0.7+0.8*x+rng.normal(size=n)
    censored=np.maximum(latent_y,0)
    tobit_frame=pd.DataFrame({"y":censored,"x":x})
    tobit=estimate_frame(tobit_frame,"tobit",{"dependent":"y","regressors":["x"],"lower":0,"upper":None})
    assert tobit["model"]=="tobit"
    assert tobit["n_censored_lower"]>0
    assert np.isfinite(tobit["sigma"])
    truncated_y=latent_y[latent_y>0]
    truncated_frame=pd.DataFrame({"y":truncated_y,"x":x[latent_y>0]})
    truncated=estimate_frame(truncated_frame,"truncated_regression",{"dependent":"y","regressors":["x"],"lower":0})
    assert truncated["model"]=="truncated_regression"
    assert truncated["nobs"]==len(truncated_y)
