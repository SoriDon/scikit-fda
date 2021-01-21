from __future__ import annotations

import enum
from typing import Callable, Generic, Optional, TypeVar, Union

import joblib
import numpy as np
import sklearn.cluster
from sklearn.base import BaseEstimator, ClusterMixin
from typing_extensions import Literal

from ...misc.metrics import PRECOMPUTED, Metric, PairwiseMetric, l2_distance
from ...misc.metrics._typing import _parse_metric, _PrecomputedTypes
from ...representation import FData

kk = ["ward", "average", "complete"]

MetricElementType = TypeVar(
    "MetricElementType",
    contravariant=True,
    bound=FData,
)


class LinkageCriterion(enum.Enum):
    # WARD = "ward" Not until
    # https://github.com/scikit-learn/scikit-learn/issues/15287 is solved
    COMPLETE = "complete"
    AVERAGE = "average"
    SINGLE = "single"


LinkageCriterionLike = Union[
    LinkageCriterion,
    Literal["ward", "complete", "average", "single"]
]


class AgglomerativeClustering(
        ClusterMixin,  # type: ignore
        BaseEstimator,  # type: ignore
        Generic[MetricElementType],
):
    """
    Agglomerative Clustering

    Recursively merges the pair of clusters that minimally increases
    a given linkage distance.

    Notes:
        This class is an extension of
        :class:`sklearn.cluster.AgglomerativeClustering` that accepts
        functional data objects and metrics. Please check also the
        documentation of the original class.

    Parameters:
        n_clusters:
            The number of clusters to find. It must be ``None`` if
            ``distance_threshold`` is not ``None``.
        metric:
            Metric used to compute the linkage.
            If it is ``skfda.misc.metrics.PRECOMPUTED`` or the string
            ``"precomputed"``, a distance matrix (instead of a similarity
            matrix) is needed as input for the fit method.
        memory:
            Used to cache the output of the computation of the tree.
            By default, no caching is done. If a string is given, it is the
            path to the caching directory.
        connectivity:
            Connectivity matrix. Defines for each sample the neighboring
            samples following a given structure of the data.
            This can be a connectivity matrix itself or a callable that
            transforms the data into a connectivity matrix, such as derived
            from kneighbors_graph. Default is None, i.e, the
            hierarchical clustering algorithm is unstructured.
        compute_full_tree:
            Stop early the construction of the tree at n_clusters. This is
            useful to decrease computation time if the number of clusters
            is not small compared to the number of samples. This option is
            useful only when specifying a connectivity matrix. Note also
            that when varying the number of clusters and using caching, it
            may be advantageous to compute the full tree. It must be ``True``
            if ``distance_threshold`` is not ``None``. By default
            `compute_full_tree` is "auto", which is equivalent to `True` when
            `distance_threshold` is not `None` or that `n_clusters` is
            inferior to the maximum between 100 or `0.02 * n_samples`.
            Otherwise, "auto" is equivalent to `False`.
        linkage:
            Which linkage criterion to use. The linkage criterion determines
            which distance to use between sets of observation. The algorithm
            will merge the pairs of cluster that minimize this criterion.
            - average uses the average of the distances of each observation of
              the two sets.
            - complete or maximum linkage uses the maximum distances between
              all observations of the two sets.
            - single uses the minimum of the distances between all observations
              of the two sets.
        distance_threshold:
            The linkage distance threshold above which, clusters will not be
            merged. If not ``None``, ``n_clusters`` must be ``None`` and
            ``compute_full_tree`` must be ``True``.

    Attributes:
        n_clusters_:
            The number of clusters found by the algorithm. If
            ``distance_threshold=None``, it will be equal to the given
            ``n_clusters``.
        labels_:
            cluster labels for each point
        n_leaves_:
            Number of leaves in the hierarchical tree.
        n_connected_components_:
            The estimated number of connected components in the graph.
        children_ :
            The children of each non-leaf node. Values less than `n_samples`
            correspond to leaves of the tree which are the original samples.
            A node `i` greater than or equal to `n_samples` is a non-leaf
            node and has children `children_[i - n_samples]`. Alternatively
            at the i-th iteration, children[i][0] and children[i][1]
            are merged to form node `n_samples + i`

    Examples:

        >>> from skfda import FDataGrid
        >>> from skfda.ml.clustering import AgglomerativeClustering
        >>> import numpy as np
        >>> data_matrix = np.array([[1, 2], [1, 4], [1, 0],
        ...                        [4, 2], [4, 4], [4, 0]])
        >>> X = FDataGrid(data_matrix)
        >>> clustering = AgglomerativeClustering(
        ...     linkage=AgglomerativeClustering.LinkageCriterion.COMPLETE,
        ... )
        >>> clustering.fit(X)
        AgglomerativeClustering(...)
        >>> clustering.labels_
        array([0, 0, 1, 0, 0, 1], dtype=int64)
    """

    LinkageCriterion = LinkageCriterion

    def __init__(
        self,
        n_clusters: Optional[int] = 2,
        *,
        metric: Union[
            Metric[MetricElementType],
            _PrecomputedTypes,
        ] = l2_distance,
        memory: Union[str, joblib.Memory, None] = None,
        connectivity: Union[
            np.ndarray,
            Callable[[MetricElementType], np.ndarray],
            None,
        ] = None,
        compute_full_tree: Union[Literal['auto'], bool] = 'auto',
        linkage: LinkageCriterionLike,
        distance_threshold: Optional[float] = None,
    ) -> None:
        self.n_clusters = n_clusters
        self.metric = metric
        self.memory = memory
        self.connectivity = connectivity
        self.compute_full_tree = compute_full_tree
        self.linkage = linkage
        self.distance_threshold = distance_threshold

    def _init_estimator(self) -> None:
        linkage = LinkageCriterion(self.linkage)

        self._estimator = sklearn.cluster.AgglomerativeClustering(
            n_clusters=self.n_clusters,
            affinity='precomputed',
            memory=self.memory,
            connectivity=self.connectivity,
            compute_full_tree=self.compute_full_tree,
            linkage=linkage.value,
            distance_threshold=self.distance_threshold,
        )

    def fit(self, X: MetricElementType, y: None = None) -> AgglomerativeClustering:

        self._init_estimator()

        metric = _parse_metric(self.metric)

        if metric is not PRECOMPUTED:
            data = PairwiseMetric(metric)(X)

        self._estimator.fit(data, y)
        return self

    def fit_predict(self, X: MetricElementType, y: None = None) -> np.ndarray:

        self._init_estimator()

        metric = _parse_metric(self.metric)

        if metric is not PRECOMPUTED:
            data = PairwiseMetric(metric)(X)

        return self._estimator.fit_predict(data, y)

    def __getattr__(self, attr):
        return getattr(self._estimator, attr)
