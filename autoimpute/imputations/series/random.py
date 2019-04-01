"""This module implements random imputation via the RandomImputer.

The RandomImputer imputes missing data using a random draw with replacement
from the observed data. Right now, this imputer supports imputation on Series
only. Use SingleImputer(strategy="random") to broadcast the imputation
strategy across multiple columns of a DataFrame.
"""

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.utils.validation import check_is_fitted
from autoimpute.imputations import method_names
methods = method_names
# pylint:disable=attribute-defined-outside-init
# pylint:disable=unnecessary-pass

class RandomImputer(BaseEstimator):
    """Impute missing data using random draws from observed data.

    The RandomImputer samples with replacement from observed data. The imputer
    can be used directly, but such behavior is discouraged because the imputer
    supports Series only. RandomImputer does not have the flexibility or
    robustness of more complex imputers, nor is its behavior identical.
    Instead, use SingleImputer(strategy="random").
    """
    # class variables
    strategy = methods.RANDOM

    def __init__(self):
        """Create an instance of the RandomImputer class."""
        pass

    def fit(self, X):
        """Fit the Imputer to the dataset and get unique observed to sample.

        Args:
            X (pd.Series): Dataset to fit the imputer.

        Returns:
            self. Instance of the class.
        """

        # determine set of observed values to sample from
        random = list(set(X[~X.isnull()]))
        self.statistics_ = {"param": random, "strategy": self.strategy}
        return self

    def impute(self, X):
        """Perform imputations using the statistics generated from fit.

        The transform method handles the actual imputation. Each missing value
        in a given dataset is replaced with a random draw from unique set of
        observed values determined during the fit stage.

        Args:
            X (pd.Series): Dataset to impute missing data from fit.

        Returns:
            np.array -- imputed dataset
        """
        # check if fitted and identify location of missingness
        check_is_fitted(self, "statistics_")
        ind = X[X.isnull()].index

        # get the observed values and sample from them
        param = self.statistics_["param"]
        imp = np.random.choice(param, len(ind))
        return imp

    def fit_impute(self, X):
        """Convenience method to perform fit and imputation in one go."""
        return self.fit(X).impute(X)
