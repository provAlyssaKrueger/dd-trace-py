from typing import List  # noqa:F401
from typing import Mapping  # noqa:F401
from typing import Optional  # noqa:F401
from typing import Union  # noqa:F401

import six

from ..internal.logger import get_logger
from ..internal.utils.cache import cachedmethod
from ..internal.utils.http import normalize_header_name


log = get_logger(__name__)


class HttpConfig(object):
    """
    Configuration object that expose an API to set and retrieve both global and integration specific settings
    related to the http context.
    """

    def __init__(self, header_tags=None):
        # type: (Optional[Mapping[str, str]]) -> None
        self._header_tags = {normalize_header_name(k): v for k, v in header_tags.items()} if header_tags else {}
        self.trace_query_string = None

    def _reset(self):
        self._header_tags = {}
        self._header_tag_name.invalidate()

    @cachedmethod()
    def _header_tag_name(self, header_name):
        # type: (str) -> Optional[str]
        if not self._header_tags:
            return None

        normalized_header_name = normalize_header_name(header_name)
        log.debug(
            "Checking header '%s' tracing in whitelist %s", normalized_header_name, six.viewkeys(self._header_tags)
        )
        return self._header_tags.get(normalized_header_name)

    @property
    def is_header_tracing_configured(self):
        # type: () -> bool
        return len(self._header_tags) > 0

    def trace_headers(self, whitelist):
        # type: (Union[List[str], str]) -> Optional[HttpConfig]
        """
        Registers a set of headers to be traced at global level or integration level.
        :param whitelist: the case-insensitive list of traced headers
        :type whitelist: list of str or str
        :return: self
        :rtype: HttpConfig
        """
        if not whitelist:
            return None

        whitelist = [whitelist] if isinstance(whitelist, str) else whitelist
        for whitelist_entry in whitelist:
            normalized_header_name = normalize_header_name(whitelist_entry)
            if not normalized_header_name:
                continue
            # Empty tag is replaced by the default tag for this header:
            #  Host on the request defaults to http.request.headers.host
            self._header_tags.setdefault(normalized_header_name, "")

        # Mypy can't catch cached method's invalidate()
        self._header_tag_name.invalidate()  # type: ignore[attr-defined]

        return self

    def header_is_traced(self, header_name):
        # type: (str) -> bool
        """
        Returns whether or not the current header should be traced.
        :param header_name: the header name
        :type header_name: str
        :rtype: bool
        """
        return self._header_tag_name(header_name) is not None

    def __repr__(self):
        return "<{} traced_headers={} trace_query_string={}>".format(
            self.__class__.__name__, self._header_tags.keys(), self.trace_query_string
        )
