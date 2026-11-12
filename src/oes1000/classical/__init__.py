"""Classical regression estimators."""
from . import linear as _linear  # register linear and robust regression estimators

from . import discrete as _discrete  # register binary-response and count estimators

from . import glm_extra as _glm_extra  # register additional GLM and count estimators

from . import advanced_discrete as _advanced_discrete  # register beta, multinomial, and hurdle models

from . import ordinal_censored as _ordinal_censored  # register ordered and censored-response models

from . import truncated as _truncated  # register left-truncated Gaussian regression

from . import penalized as _penalized  # register L2-penalized binary GLMs
