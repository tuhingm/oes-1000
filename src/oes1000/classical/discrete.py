"""Binary-response and count-data maximum-likelihood estimators."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, gammaln, log_ndtr, ndtr
from scipy.stats import norm

from oes1000.registry import register_estimator


def _inputs(y, X, add_constant=True):
    y=np.asarray(y,dtype=float).reshape(-1)
    X=np.asarray(X,dtype=float)
    if X.ndim==1: X=X[:,None]
    if X.ndim!=2 or X.shape[0]!=y.size: raise ValueError("X must be n×k and y must have n observations")
    if not np.isfinite(y).all() or not np.isfinite(X).all(): raise ValueError("Inputs must be finite")
    if add_constant: X=np.column_stack((np.ones(y.size),X))
    if y.size<=X.shape[1]: raise ValueError("Insufficient observations: require n > k")
    if np.linalg.matrix_rank(X)<X.shape[1]: raise ValueError("Design matrix is rank deficient")
    return y,X


def _fit(y,X,loglike,score_hessian,model,extra=None):
    start=np.zeros(X.shape[1])
    fit=minimize(lambda b:-loglike(b),start,jac=lambda b:-score_hessian(b)[0],method="BFGS",
                 options={"gtol":1e-8,"maxiter":2000})
    if not fit.success and np.linalg.norm(fit.jac)>1e-5:
        raise RuntimeError(f"{model} maximum likelihood failed: {fit.message}")
    beta=fit.x
    score,hess=score_hessian(beta)
    information=-hess
    if np.linalg.matrix_rank(information)<information.shape[0]:
        raise RuntimeError(f"{model} observed information matrix is singular")
    cov=np.linalg.inv(information)
    se=np.sqrt(np.maximum(np.diag(cov),0))
    stat=beta/np.where(se>0,se,np.nan)
    p=2*norm.sf(np.abs(stat))
    fitted=None
    out={"model":model,"nobs":int(y.size),"params":beta,"covariance":cov,
         "std_errors":se,"test_statistics":stat,"p_values":p,
         "log_likelihood":float(loglike(beta)),"converged":bool(fit.success or np.linalg.norm(fit.jac)<=1e-5),
         "iterations":int(fit.nit),"optimizer_message":str(fit.message)}
    if extra: out.update(extra(beta))
    return out


def _binary(y,X,link):
    if not np.isin(y,[0,1]).all(): raise ValueError("Binary response y must contain only 0 and 1")
    if np.unique(y).size!=2: raise ValueError("Binary response must contain both outcome classes")
    def terms(b):
        eta=X@b
        if link=="logit":
            p=np.clip(expit(eta),1e-12,1-1e-12)
            ll=np.sum(y*np.log(p)+(1-y)*np.log1p(-p))
            score=X.T@(y-p); hess=-(X.T@((p*(1-p))[:,None]*X))
        elif link=="probit":
            # Exact probit score and expected Fisher information.
            lp=log_ndtr(eta); lq=log_ndtr(-eta)
            p=np.clip(ndtr(eta),1e-12,1-1e-12); q=1-p
            dens=np.exp(-0.5*eta**2-0.5*np.log(2*np.pi))
            ll=np.sum(y*lp+(1-y)*lq)
            score_eta=dens*(y/p-(1-y)/q)
            information_eta=(dens**2)/(p*q)
            score=X.T@score_eta
            hess=-(X.T@(np.maximum(information_eta,1e-12)[:,None]*X))
        else:
            # Complementary log-log: p=1-exp(-z), z=exp(eta).
            # Bernoulli expected information: (dp/deta)^2/[p(1-p)] = z^2 exp(-z)/p.
            z=np.exp(np.clip(eta,-30,30)); q=np.exp(-z)
            p=np.clip(-np.expm1(-z),1e-12,1-1e-12)
            ll=np.sum(y*np.log(p)+(1-y)*(-z))
            dlogp=z*q/p
            score=X.T@(y*dlogp-(1-y)*z)
            information_eta=(z*z*q)/p
            hess=-(X.T@(np.maximum(information_eta,1e-12)[:,None]*X))
        return float(ll),score,hess
    def loglike(b): return terms(b)[0]
    def sh(b):
        _,s,h=terms(b); return s,h
    return _fit(y,X,loglike,sh,link,extra=lambda b:{"fitted_probabilities":expit(X@b) if link=="logit" else (ndtr(X@b) if link=="probit" else 1-np.exp(-np.exp(np.clip(X@b,-30,30))))})


@register_estimator("logit")
def estimate_logit(y,X,*,add_constant=True):
    y,X=_inputs(y,X,add_constant); return _binary(y,X,"logit")


@register_estimator("probit")
def estimate_probit(y,X,*,add_constant=True):
    y,X=_inputs(y,X,add_constant); return _binary(y,X,"probit")


@register_estimator("cloglog")
def estimate_cloglog(y,X,*,add_constant=True):
    y,X=_inputs(y,X,add_constant); return _binary(y,X,"cloglog")


@register_estimator("poisson")
def estimate_poisson(y,X,*,add_constant=True):
    y,X=_inputs(y,X,add_constant)
    if np.any(y<0) or not np.allclose(y,np.round(y)): raise ValueError("Poisson y must be non-negative integer counts")
    def ll(b):
        eta=np.clip(X@b,-30,30); mu=np.exp(eta)
        return float(np.sum(y*eta-mu-gammaln(y+1)))
    def sh(b):
        mu=np.exp(np.clip(X@b,-30,30))
        return X.T@(y-mu),-(X.T@(mu[:,None]*X))
    return _fit(y,X,ll,sh,"poisson",extra=lambda b:{"fitted_mean":np.exp(np.clip(X@b,-30,30))})


@register_estimator("negative_binomial")
def estimate_negative_binomial(y,X,*,add_constant=True):
    y,X=_inputs(y,X,add_constant)
    if np.any(y<0) or not np.allclose(y,np.round(y)): raise ValueError("Negative-binomial y must be non-negative integer counts")
    n,k=X.shape
    # Joint NB2 likelihood with log(alpha) as the final parameter.
    def ll(theta):
        b=theta[:k]; alpha=np.exp(np.clip(theta[k],-12,8)); mu=np.exp(np.clip(X@b,-30,30)); r=1/alpha
        return float(np.sum(gammaln(y+r)-gammaln(r)-gammaln(y+1)+r*np.log(r/(r+mu))+y*np.log(mu/(r+mu))))
    fit=minimize(lambda th:-ll(th),np.r_[np.zeros(k),np.log(0.2)],method="L-BFGS-B",
                 bounds=[(None,None)]*k+[(-12,8)],
                 options={"ftol":1e-12,"gtol":1e-7,"maxiter":10000,"maxls":50})
    if not fit.success and np.linalg.norm(fit.jac)>1e-3:
        raise RuntimeError("Negative-binomial MLE failed: "+str(fit.message))
    theta=fit.x
    # Numerical observed Hessian for joint parameter covariance.
    eps=1e-4; d=k+1; H=np.zeros((d,d)); f0=-ll(theta)
    for i in range(d):
        ei=np.zeros(d); ei[i]=eps
        H[i,i]=(-ll(theta+ei)-2*f0-ll(theta-ei))/(eps**2)
        for j in range(i):
            ej=np.zeros(d); ej[j]=eps
            H[i,j]=H[j,i]=(-ll(theta+ei+ej)+ll(theta+ei-ej)+ll(theta-ei+ej)-ll(theta-ei-ej))/(4*eps**2)
    cov=np.linalg.pinv(H)
    beta=theta[:k]; se=np.sqrt(np.maximum(np.diag(cov)[:k],0)); stat=beta/np.where(se>0,se,np.nan)
    mu=np.exp(np.clip(X@beta,-30,30)); alpha=float(np.exp(theta[k]))
    return {"model":"negative_binomial","nobs":int(n),"params":beta,"covariance":cov[:k,:k],"std_errors":se,
            "test_statistics":stat,"p_values":2*norm.sf(np.abs(stat)),"log_likelihood":ll(theta),
            "dispersion_alpha":alpha,"fitted_mean":mu,"converged":bool(fit.success or np.linalg.norm(fit.jac)<=1e-5),
            "iterations":int(fit.nit),"joint_parameters":theta,"joint_covariance":cov}
