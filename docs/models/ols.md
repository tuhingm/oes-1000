# Ordinary least squares (OLS)

## Specification

For (y\in\mathbb R^n) and a full-column-rank design matrix (X\in\mathbb R^{n\times k}),

\[
y=X\beta+u,\qquad \widehat\beta=(X'X)^{-1}X'y.
\]

An intercept is prepended by default. The implementation rejects non-finite inputs, (n\leq k), and rank-deficient designs.

## Covariance estimators

Let (\widehat u_i) denote OLS residuals, (h_{ii}) the diagonal elements of the hat matrix, and (B=(X'X)^{-1}). The sandwich estimator is

\[
\widehat V(\widehat\beta)=B\left(\sum_{i=1}^n x_ix_i'\widehat\omega_i\right)B.
\]

The supported HC weights are:
- HC0: (\widehat\omega_i=\widehat u_i^2)
- HC1: (\widehat\omega_i=\frac{n}{n-k}\widehat u_i^2)
- HC2: (\widehat\omega_i=\frac{\widehat u_i^2}{1-h_{ii}})
- HC3: (\widehat\omega_i=\frac{\widehat u_i^2}{(1-h_{ii})^2})

The conventional covariance uses (\widehat\sigma^2=\widehat u'\widehat u/(n-k)) and (\widehat V=\widehat\sigma^2(X'X)^{-1}).

## Inference

The current implementation reports t statistics and two-sided Student-t p-values with (n-k) residual degrees of freedom. For HC covariance estimators, this is a conventional finite-sample reference distribution; asymptotic normal inference can be added as an explicit option rather than silently substituted.

## Validation

Unit tests check exact coefficient recovery in a noiseless design, finite HC1 standard errors under a seeded simulation, and rejection of rank-deficient designs.
