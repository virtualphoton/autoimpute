"""This module implements median imputation via the MedianImputer.

The MedianImputer imputes missing data with the median of observed data.
Right now, this imputer supports imputation on Series only. Use
SingleImputer(strategy="median") to broadcast the imputation strategy across
multiple columns of a DataFrame.
"""

from sklearn.base import BaseEstimator
from sklearn.utils.validation import check_is_fitted
from autoimpute.imputations import method_names
from autoimpute.imputations.errors import _not_num_series
methods = method_names
# pylint:disable=attribute-defined-outside-init
# pylint:disable=unnecessary-pass

class MedianImputer(BaseEstimator):
    """Impute missing values with the median of the observed data.

    This imputer imputes missing values with the median of observed data.
    The imputer can be used directly, but such behavior is discouraged because
    the imputer supports Series only. MedianImputer does not have the
    flexibility or robustness of more complex imputers, nor is its behavior
    identical. Instead, use SingleImputer(strategy="median").
    """
    # class variables
    strategy = methods.MEDIAN

    def __init__(self):
        """Create an instance of the MedianImputer class."""
        pass

    def fit(self, X):
        """Fit the Imputer to the dataset and calculate the median.

        Args:
            X (pd.Series): Dataset to fit the imputer.

        Returns:
            self. Instance of the class.
        """
        _not_num_series(self.strategy, X)
        median = X.median()
        self.statistics_ = {"param": median, "strategy": self.strategy}
        return self

    def impute(self, X):
        """Perform imputations using the statistics generated from fit.

        The impute method handles the actual imputation. Missing values
        in a given dataset are replaced with the respective median from fit.

        Args:
            X (pd.Series): Dataset to impute missing data from fit.

        Returns:
            float -- imputed dataset.
        """
        # check is fitted then impute with median
        check_is_fitted(self, "statistics_")
        _not_num_series(self.strategy, X)
        imp = self.statistics_["param"]
        return imp

    def fit_impute(self, X):
        """Convenience method to perform fit and imputation in one go."""
        return self.fit(X).impute(X)
