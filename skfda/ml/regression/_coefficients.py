from __future__ import annotations

import abc
from functools import singledispatch
from typing import Any, Generic, TypeVar

import numpy as np

from ...misc._math import inner_product
from ...representation.basis import Basis, FDataBasis

CovariateType = TypeVar("CovariateType")


class CoefficientInfo(abc.ABC, Generic[CovariateType]):
    """
    Information about an estimated coefficient.

    Parameters:
        basis: Basis of the coefficient.

    """

    def __init__(
        self,
        basis: CovariateType,
    ) -> None:
        self.basis = basis

    @abc.abstractmethod
    def regression_matrix(
        self,
        X: CovariateType,
        y: np.ndarray,
    ) -> np.ndarray:
        """
        Return the constant coefficients matrix for regression.

        Parameters:
            X: covariate data for regression.
            y: target data for regression.

        Returns:
            Coefficients matrix.

        """
        pass

    @abc.abstractmethod
    def convert_from_constant_coefs(
        self,
        coefs: np.ndarray,
    ) -> CovariateType:
        """
        Return the coefficients object from the constant coefs.

        Parameters:
            coefs: estimated constant coefficients.

        Returns:
            Coefficient.

        """
        pass

    @abc.abstractmethod
    def inner_product(
        self,
        coefs: CovariateType,
        X: CovariateType,
    ) -> np.ndarray:
        """
        Inner product.

        Compute the inner product between the coefficient and
        the covariate.

        """
        pass


class CoefficientInfoNdarray(CoefficientInfo[np.ndarray]):

    def regression_matrix(  # noqa: D102
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> np.ndarray:

        return np.atleast_2d(X)

    def convert_from_constant_coefs(  # noqa: D102
        self,
        coefs: np.ndarray,
    ) -> np.ndarray:

        return coefs

    def inner_product(  # noqa: D102
        self,
        coefs: np.ndarray,
        X: np.ndarray,
    ) -> np.ndarray:

        return inner_product(coefs, X)


class CoefficientInfoFDataBasis(CoefficientInfo[FDataBasis]):
    """
    Information about a FDataBasis coefficient.

    Parameters:
        basis: Basis of the coefficient.

    """

    def regression_matrix(  # noqa: D102
        self,
        X: FDataBasis,
        y: np.ndarray,
    ) -> np.ndarray:
        # The matrix is the matrix of coefficients multiplied by
        # the matrix of inner products.

        xcoef = X.coefficients
        self.inner_basis = X.basis.inner_product_matrix(self.basis)
        return xcoef @ self.inner_basis

    def convert_from_constant_coefs(  # noqa: D102
        self,
        coefs: np.ndarray,
    ) -> FDataBasis:
        return FDataBasis(self.basis.basis, coefs.T)

    def inner_product(  # noqa: D102
        self,
        coefs: FDataBasis,
        X: FDataBasis,
    ) -> np.ndarray:
        # Efficient implementation of the inner product using the
        # inner product matrix previously computed
        return inner_product(coefs, X, inner_product_matrix=self.inner_basis.T)


@singledispatch
def coefficient_info_from_covariate(
    X: CovariateType,
    y: np.ndarray,
    **_: Any,
) -> CoefficientInfo[CovariateType]:
    """Make a coefficient info object from a covariate."""
    raise ValueError(f"Invalid type of covariate = {type(X)}.")


@coefficient_info_from_covariate.register(np.ndarray)
def _coefficient_info_from_covariate_ndarray(
    X: np.ndarray,
    y: np.ndarray,
    **_: Any,
) -> CoefficientInfo[np.ndarray]:
    return CoefficientInfoNdarray(basis=np.identity(X.shape[1], dtype=X.dtype))


@coefficient_info_from_covariate.register(FDataBasis)
def _coefficient_info_from_covariate_fdatabasis(
    X: FDataBasis,
    y: np.ndarray,
    *,
    basis: Basis,
    **_: Any,
) -> CoefficientInfoFDataBasis:

    if basis is None:
        basis = X.basis

    if not isinstance(basis, Basis):
        raise TypeError(f"basis must be a Basis object, not {type(basis)}")

    return CoefficientInfoFDataBasis(basis=basis.to_basis())
