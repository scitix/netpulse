import urllib.request
from enum import Enum

import requests


class BaseTemplateRenderer:
    """
    Base class of template renderer (kv -> text)

    NOTE: Use `from_rendering_request` instead of __init__.
    """

    template_name: str = "base"

    @classmethod
    def from_rendering_request(cls, req) -> "BaseTemplateRenderer":
        raise NotImplementedError

    def __init__(self):
        raise NotImplementedError

    def render(self, context: dict) -> str:
        raise NotImplementedError


class BaseTemplateParser:
    """
    Base class of template parser (text -> kv)

    NOTE: Use `from_parsing_request` instead of __init__.
    """

    template_name: str = "base"

    @classmethod
    def from_parsing_request(cls, req) -> "BaseTemplateParser":
        raise NotImplementedError

    def __init__(self):
        raise NotImplementedError

    def parse(self, context) -> dict:
        raise NotImplementedError


class TemplateSource:
    """
    Template could from string, file or remote.
    """

    class SourceType(str, Enum):
        STRING = "string"
        FILE = "file"
        HTTP = "http"
        FTP = "ftp"

    def __init__(self, source: str):
        self.source = source
        self.protocol = self._resolve(source)

    def __str__(self):
        return self.source

    def _resolve(self, source: str) -> "TemplateSource.SourceType":
        """
        Resolve the protocol of the source
        """
        s_lower = source.lower()
        if s_lower.startswith("http://") or s_lower.startswith("https://"):
            return self.SourceType.HTTP
        elif s_lower.startswith("ftp://"):
            return self.SourceType.FTP
        elif s_lower.startswith("file://"):
            return self.SourceType.FILE
        else:
            return self.SourceType.STRING

    def load(self) -> str:
        """
        Load the template from source
        """
        if self.protocol == self.SourceType.STRING:
            return self.source

        elif self.protocol == self.SourceType.FILE:
            path = self.source[7:]
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        elif self.protocol == self.SourceType.HTTP:
            response = requests.get(self.source)
            response.raise_for_status()
            return response.text

        elif self.protocol == self.SourceType.FTP:
            with urllib.request.urlopen(self.source) as fp:
                return fp.read().decode("utf-8")

        else:
            raise ValueError(f"Unsupported source protocol: {self.protocol}")
