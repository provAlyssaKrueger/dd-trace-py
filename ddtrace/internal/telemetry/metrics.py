# -*- coding: utf-8 -*-
import abc
import time
from typing import Dict  # noqa:F401
from typing import List  # noqa:F401
from typing import Optional  # noqa:F401
from typing import Tuple  # noqa:F401

import six


MetricTagType = Optional[Tuple[Tuple[str, str], ...]]


class Metric(six.with_metaclass(abc.ABCMeta)):
    """
    Telemetry Metrics are stored in DD dashboards, check the metrics in datadoghq.com/metric/explorer
    """

    metric_type = ""
    __slots__ = ["namespace", "name", "_tags", "is_common_to_all_tracers", "interval", "_points", "_count"]

    def __init__(self, namespace, name, tags, common, interval=None):
        # type: (str, str, MetricTagType, bool, Optional[float]) -> None
        """
        namespace: the scope of the metric: tracer, appsec, etc.
        name: string
        tags: extra information attached to a metric
        common: set to True if a metric is common to all tracers, false if it is python specific
        interval: field set for gauge and rate metrics, any field set is ignored for count metrics (in secs)
        """
        self.name = name.lower()
        self.is_common_to_all_tracers = common
        self.interval = interval
        self.namespace = namespace
        self._tags = tags
        self._count = 0.0
        self._points = []  # type: List

    @classmethod
    def get_id(cls, name, namespace, tags, metric_type):
        # type: (str, str, MetricTagType, str) -> int
        """
        https://www.datadoghq.com/blog/the-power-of-tagged-metrics/#whats-a-metric-tag
        """
        return hash((name, namespace, tags, metric_type))

    def __hash__(self):
        return self.get_id(self.name, self.namespace, self._tags, self.metric_type)

    @abc.abstractmethod
    def add_point(self, value=1.0):
        # type: (float) -> None
        """adds timestamped data point associated with a metric"""
        pass

    def to_dict(self):
        # type: () -> Dict
        """returns a dictionary containing the metrics fields expected by the telemetry intake service"""
        data = {
            "metric": self.name,
            "type": self.metric_type,
            "common": self.is_common_to_all_tracers,
            "points": self._points,
            "tags": ["{}:{}".format(k, v).lower() for k, v in self._tags] if self._tags else [],
        }
        if self.interval is not None:
            data["interval"] = int(self.interval)
        return data


class CountMetric(Metric):
    """
    A count type adds up all the submitted values in a time interval. This would be suitable for a
    metric tracking the number of website hits, for instance.
    """

    metric_type = "count"

    def add_point(self, value=1.0):
        # type: (float) -> None
        """adds timestamped data point associated with a metric"""
        if self._points:
            self._points[0][1] += value
        else:
            self._points = [[time.time(), value]]


class GaugeMetric(Metric):
    """
    A gauge type takes the last value reported during the interval. This type would make sense for tracking RAM or
    CPU usage, where taking the last value provides a representative picture of the host’s behavior during the time
    interval. In this case, using a different type such as count would probably lead to inaccurate and extreme values.
    Choosing the correct metric type ensures accurate data.
    """

    metric_type = "gauge"

    def add_point(self, value=1.0):
        # type: (float) -> None
        """adds timestamped data point associated with a metric"""
        self._points = [(time.time(), value)]


class RateMetric(Metric):
    """
    The rate type takes the count and divides it by the length of the time interval. This is useful if you’re
    interested in the number of hits per second.
    """

    metric_type = "rate"

    def add_point(self, value=1.0):
        # type: (float) -> None
        """Example:
        https://github.com/DataDog/datadogpy/blob/ee5ac16744407dcbd7a3640ee7b4456536460065/datadog/threadstats/metrics.py#L181
        """
        self._count += value
        rate = (self._count / self.interval) if self.interval else 0.0
        self._points = [(time.time(), rate)]


class DistributionMetric(Metric):
    """
    The rate type takes the count and divides it by the length of the time interval. This is useful if you’re
    interested in the number of hits per second.
    """

    metric_type = "distributions"

    def add_point(self, value=1.0):
        # type: (float) -> None
        """Example:
        https://github.com/DataDog/datadogpy/blob/ee5ac16744407dcbd7a3640ee7b4456536460065/datadog/threadstats/metrics.py#L181
        """
        self._points.append(value)

    def to_dict(self):
        # type: () -> Dict
        """returns a dictionary containing the metrics fields expected by the telemetry intake service"""
        data = {
            "metric": self.name,
            "points": self._points,
            "tags": ["{}:{}".format(k, v).lower() for k, v in self._tags] if self._tags else [],
        }
        return data
