"""Classical regression estimators."""
from . import linear as _linear  # register linear and robust regression estimators

from . import discrete as _discrete  # register binary-response and count estimators

from . import glm_extra as _glm_extra  # register additional GLM and count estimators

from . import advanced_discrete as _advanced_discrete  # register beta, multinomial, and hurdle models
