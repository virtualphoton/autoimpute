"""Module for BaseImputer - a base class for classifiers/predictive imputers.

This module contains the `BaseImputer`, which is used to abstract away
functionality in both missingness classifiers and predictive imputers.
"""

import warnings
import itertools
import numpy as np
import pandas as pd
from sklearn.base import clone
# pylint:disable=attribute-defined-outside-init
# pylint:disable=too-many-arguments
# pylint:disable=too-many-instance-attributes
# pylint:disable=inconsistent-return-statements


class BaseImputer:
    """Building blocks for more advanced imputers and missingness classifiers.

    The `BaseImputer` is not a stand-alone class and thus serves no purpose
    other than as a Parent to Imputers and MissingnessClassifiers. Therefore,
    the BaseImputer should not be used directly unless creating an Imputer.
    """

    def __init__(self, imp_kwgs, scaler, verbose):
        """Initialize the BaseImputer.

        Args:
            imp_kwgs (dict, optional): keyword arguments for each imputer.
                Default is None, which means default imputer created to match
                specific strategy. imp_kwgs keys can be either columns or
                strategies. If strategies, each column given that strategy is
                instantiated with same arguments.
            scaler (sklearn scaler, optional): A scaler supported by sklearn.
                Default to None. Otherwise, must be sklearn-compliant scaler.
            verbose (bool, optional): Print information to the console.
                Defaults to False.
        """
        self.imp_kwgs = imp_kwgs
        self.scaler = scaler
        self.verbose = verbose

    @property
    def scaler(self):
        """Property getter to return the value of the scaler property."""
        return self._scaler

    @scaler.setter
    def scaler(self, s):
        """Validate the scaler property and set default parameters.

        Args:
            s (scaler): if None, implement the xgboost classifier

        Raises:
            ValueError: classifier does not implement `fit_transform`
        """
        if s is None:
            self._scaler = s
        else:
            m = "fit_transform"
            if not hasattr(s, m):
                raise ValueError(f"Scaler must implement {m} method.")
            self._scaler = s

    @property
    def imp_kwgs(self):
        """Property getter to return the value of imp_kwgs."""
        return self._imp_kwgs

    @imp_kwgs.setter
    def imp_kwgs(self, kwgs):
        """Validate the imp_kwgs and set default properties."""
        if not isinstance(kwgs, (type(None), dict)):
            err = "imp_kwgs must be dict of args used to instantiate Imputer."
            raise ValueError(err)
        self._imp_kwgs = kwgs

    def _scaler_fit(self):
        """Private method to scale data based on scaler provided."""
        # scale numerical data and dummy data if it exists
        if self._len_num > 0:
            sc = clone(self.scaler)
            self._scaled_num = sc.fit(self._data_num.values)
        else:
            self._scaled_num = None
        if self._len_dum > 0:
            sc = clone(self.scaler)
            self._scaled_dum = sc.fit(self._data_dum.values)
        else:
            self._scaled_dum = None

    def _scaler_transform(self):
        """Private method to transform data using scaled fit."""
        if self._scaled_num:
            sn = self._scaled_num.transform(self._data_num.values)
            self._data_num = pd.DataFrame(sn, columns=self._cols_num)
        if self._scaled_dum:
            sd = self._scaled_dum.transform(self._data_dum.values)
            self._data_dum = pd.DataFrame(sd, columns=self._cols_dum)

    def _scaler_fit_transform(self):
        """Private method to perform fit and transform of scaler"""
        self._scaler_fit()
        self._scaler_transform()

    def check_strategy_allowed(self, strat_names, s):
        """Logic to determine if the strategy passed for imputation is valid.

        Imputer Classes in this library have a very flexible strategy argument.
        The arg can be a string, an iterator, or a dictionary. In each case,
        the method(s) passed are checked against method(s) allowed, which are
        generally stored in a class variable of the given Imputer.

        Args:
            strat_names (iterator): strategies allowed by the Imputer class
            strategy (any): strategies passed as arguments

        Returns:
            strategy (any): if string, iterator, or dictionary

        Raises:
            ValueError: Strategies not valid (not in allowed strategies).
            TypeError: Strategy must be a string, tuple, list, or dict.
        """
        err_op = f"Strategies must be one of {list(strat_names)}."
        if isinstance(s, str):
            if s not in strat_names:
                err = f"Strategy {s} not a valid imputation method.\n"
                raise ValueError(f"{err} {err_op}")
        elif isinstance(s, (list, tuple, dict)):
            if isinstance(s, dict):
                ss = set(s.values())
            else:
                ss = set(s)
            sdiff = ss.difference(strat_names)
            if sdiff:
                err = f"Strategies {sdiff} in {s} not valid imputation.\n"
                raise ValueError(f"{err} {err_op}")
        else:
            raise TypeError("Strategy must be string, tuple, list, or dict.")
        return s

    def check_strategy_fit(self, s, cols):
        """Check whether strategies of imputer make sense given data passed.

        An Imputer takes strategies to use for imputation. Those strategies
        are validated when an instance is created. When fitting actual data,
        strategies must be validated again to verify they make sense given
        the columns in the dataset passed. For example, "mean" is fine
        when instance created, but "mean" will not work for a categorical
        column. This check validates strategy used for given column each
        strategy assigned to.

        Args:
            strategy (str, iter, dict): strategies passed for columns.
                String = 1 strategy, broadcast to all columns.
                Iter = multiple strategies, must match col index and length.
                Dict = multiple strategies, must match col name, but not all
                columns are mandatory. Will simply impute based on name.
            cols: columns in dataset for which strategies checked.

        Raises:
            ValueError (iter): length of columns and strategies must be equal.
            ValueError (dict): keys of strategies and columns must match.
        """
        c_l = len(cols)
        # if strategy is string, extend strategy to all cols
        if isinstance(s, str):
            return {c:s for c in cols}

        # if list or tuple, ensure same number of cols in X as strategies
        # note that list/tuple must have strategy specified for every column
        if isinstance(s, (list, tuple)):
            s_l = len(s)
            if s_l != c_l:
                err = "Length of columns not equal to number of strategies.\n"
                err_c = f"Length of columns: {c_l}\n"
                err_s = f"Length of strategies: {s_l}"
                raise ValueError(f"{err}{err_c}{err_s}")
            return {c[0]:c[1] for c in zip(cols, s)}

        # if strategy is dict, ensure keys in strategy match cols in X
        # note that dict is preferred way to impute SOME columns and not all
        if isinstance(s, dict):
            diff_s = set(s.keys()).difference(cols)
            if diff_s:
                err = "Keys of strategies and column names must match.\n"
                err_k = f"Ill-specified keys: {diff_s}"
                raise ValueError(f"{err}{err_k}")
            return s

    def _fit_init_params(self, column, method, kwgs):
        """Private method to supply imputation model fit params if any."""
        # first, handle easy case when no kwargs given
        if kwgs is None:
            final_params = kwgs

        # next, check if any kwargs for a given Imputer method type
        # then, override those parameters if specific column kwargs supplied
        if isinstance(kwgs, dict):
            initial_params = kwgs.get(method, None)
            final_params = kwgs.get(column, initial_params)

        # final params must be None or a dictionary of kwargs
        # this additional validation step is crucial to dictionary unpacking
        if not isinstance(final_params, (type(None), dict)):
            err = "Additional params must be dict of args used to init model."
            raise ValueError(err)
        return final_params

    def check_predictors_fit(self, predictors, cols):
        """Checked predictors used for fitting each column.

        Args:
            predictors (str, iter, dict): predictors passed for columns.
                String = "all" or raises error
                Iter = multiple strategies, must match col index and length.
                Dict = multiple strategies, must match col name, but not all
                columns are mandatory. Will simply impute based on name.
            cols: columns in dataset for which predictors checked.

        Returns:
            predictors

        Raises:
            ValueError (str): string not equal to all.
            ValueError (iter): items in `predictors` not in columns of X.
            ValueError (dict, keys): keys of response must be columns in X.
            ValueError (dict, vals): vals of responses must be columns in X.
        """
        # if string, value must be `all`, or else raise an error
        if isinstance(predictors, str):
            if predictors != "all" and predictors not in cols:
                err = f"String {predictors} must be valid column in X.\n"
                err_all = "To use all columns, set predictors='all'."
                raise ValueError(f"{err}{err_all}")
            return {c:predictors for c in cols}

        # if list or tuple, remove nan cols and check col names
        if isinstance(predictors, (list, tuple)):
            bad_preds = [p for p in predictors if p not in cols]
            if bad_preds:
                err = f"{bad_preds} in predictors not a valid column in X."
                raise ValueError(err)
            return {c:predictors for c in cols}

        # if dictionary, remove nan cols and check col names
        if isinstance(predictors, dict):
            diff_s = set(predictors.keys()).difference(cols)
            if diff_s:
                err = "Keys of strategies and column names must match.\n"
                err_k = f"Ill-specified keys: {diff_s}"
                raise ValueError(f"{err}{err_k}")
            # then check the values of each key
            for k, preds in predictors.items():
                if isinstance(preds, str):
                    if preds != "all" and preds not in cols:
                        err = f"Invalid column as only predictor for {k}."
                        raise ValueError(err)
                elif isinstance(preds, (tuple, list)):
                    bad_preds = [p for p in preds if p not in cols]
                    if bad_preds:
                        err = f"{bad_preds} for {k} not a valid column in X."
                        raise ValueError(err)
                else:
                    err = "Values in predictor must be str, list, or tuple."
                    raise ValueError(err)
            # finally, create predictors dict
            for c in cols:
                if c not in predictors:
                    predictors[c] = "all"
            return predictors

    def _check_if_single_dummy(self, col, X):
        """Private method to check if encoding results in single cat."""
        cats = X.columns.tolist()
        if len(cats) == 1:
            c = cats[0]
            msg = f"{c} only category for feature {col}."
            cons = f"Consider removing {col} from dataset."
            warnings.warn(f"{msg} {cons}")

    def _prep_fit_dataframe(self, X):
        """Private method to process numeric & categorical data for fit."""
        self._X_idx = X.index
        self.data_mi = pd.isnull(X)*1
        if self.verbose:
            prep = "PREPPING DATAFRAME FOR IMPUTATION ANALYSIS..."
            print(f"{prep}\n{'-'*len(prep)}")

        # numerical columns first
        self._data_num = X.select_dtypes(include=(np.number,))
        self._cols_num = self._data_num.columns.tolist()
        self._len_num = len(self._cols_num)

        # datetime columns next
        self._data_time = X.select_dtypes(include=(np.datetime64,))
        self._cols_time = self._data_time.columns.tolist()
        self._len_time = len(self._cols_time)

        # check categorical columns last
        # right now, only support for one-hot encoding
        orig_dum = X.select_dtypes(include=(np.object,))
        self._orig_dum = orig_dum.columns.tolist()
        if not orig_dum.columns.tolist():
            self._dum_dict = {}
            self._data_dum = pd.DataFrame()
        else:
            dummies = []
            self._dum_dict = {}
            self._data_dum = pd.DataFrame()
            for col in orig_dum:
                col_dum = pd.get_dummies(orig_dum[col], prefix=col)
                self._dum_dict[col] = col_dum.columns.tolist()
                self._check_if_single_dummy(col, col_dum)
                dummies.append(col_dum)
            ld = len(dummies)
            if ld == 1:
                self._data_dum = dummies[0]
            else:
                self._data_dum = pd.concat(dummies, axis=1)
        self._cols_dum = self._data_dum.columns.tolist()
        self._len_dum = len(self._cols_dum)

        # print categorical and numeric columns if verbose true
        if self.verbose:
            nm = "Number of numeric columns in X: "
            cm = "Number of categorical columns after one-hot encoding: "
            print(f"{nm}{self._len_num}")
            print(f"{cm}{self._len_dum}")

    def _use_all_cols(self, c):
        """Private method to pedict using all columns."""
        # set numerical columns first
        if c in self._cols_num:
            num_cols = self._data_num.drop(c, axis=1)
        else:
            num_cols = self._data_num

        # set categorical columns second
        if c in self._orig_dum:
            d_c = [v for k, v in self._dum_dict.items() if k != c]
            d_fc = list(itertools.chain.from_iterable(d_c))
            d = [k for k in self._data_dum.columns if k in d_fc]
            dum_cols = self._data_dum[d]
        else:
            dum_cols = self._data_dum

        # return all predictors and target for predictor
        return num_cols, dum_cols, self._data_time

    def _use_iter_cols(self, c, preds):
        """Private method to predict using some columns."""
        # set numerical columns first
        if c in self._cols_num:
            cn = self._data_num.drop(c, axis=1)
        else:
            cn = self._data_num
        cols = list(set(preds).intersection(cn.columns.tolist()))
        num_cols = cn[cols]

        # set categorical columns second
        if c in self._orig_dum:
            d_c = [v for k, v in self._dum_dict.items()
                   if k != c and k in preds]
        else:
            d_c = [v for k, v in self._dum_dict.items()
                   if k in preds]
        d_fc = list(itertools.chain.from_iterable(d_c))
        d = [k for k in self._data_dum.columns
             if k in d_fc]
        dum_cols = self._data_dum[d]

        # set the time columns last
        ct = list(set(preds).intersection(self._data_time.columns.tolist()))
        time_cols = self._data_time[ct]

        return num_cols, dum_cols, time_cols

    def _prep_predictor_cols(self, c, predictors):
        """Private method to prep cols for prediction."""
        preds = predictors[c]
        if isinstance(preds, str):
            if preds == "all":
                if self.verbose:
                    print(f"No predictors given for {c}, using all columns.")
                num, dum, time = self._use_all_cols(c)
            else:
                if self.verbose:
                    print(f"Using single column {preds} to predict {c}.")
                num, dum, time = self._use_iter_cols(c, [preds])
        if isinstance(preds, (list, tuple)):
            if self.verbose:
                print(f"Using {preds} as covariates for {c}.")
            num, dum, time = self._use_iter_cols(c, preds)

        # error handling and printing to console
        predictors = [num, dum, time]
        predictor_str = list(map(lambda df: df.columns.tolist(), predictors))
        if not any(predictor_str):
            err = f"Need at least one predictor column to fit {c}."
            raise ValueError(err)
        if self.verbose:
            print(f"Columns used for {c}:")
            print(f"Numeric: {predictor_str[0]}")
            print(f"Categorical: {predictor_str[1]}")
            print(f"Datetime: {predictor_str[2]}")

        # final columns to return for x and y
        predictors = [p for p in predictors if p.size > 0]
        x = pd.concat(predictors, axis=1)
        y = self.data_mi[c]
        return x, y
