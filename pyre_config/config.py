from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TextIO

from .parse import ConfigParseMatch


class Config(ABC):
    """
    Abstract base class for configuration sources.
    配置源的抽象基类。
    """

    @abstractmethod
    def get_content(self) -> bytes:
        """
        Get the raw content as bytes.
        获取原始内容（字节格式）。
        :return: Raw content in bytes 字节格式的原始内容
        """
        pass

    @abstractmethod
    def get_text(self) -> str:
        """
        Get the content as text string.
        获取文本格式的内容。
        :return: Content as text string 文本格式的内容
        """
        pass

    @abstractmethod
    def get_dict(self) -> Dict[str, Any]:
        """
        Parse and get the content as dictionary.
        解析并获取字典格式的内容。
        :return: Parsed content as dictionary 解析后的字典格式内容
        """
        pass

    def close(self) -> None:
        """Release any resource held by this source. 释放配置源占用的资源。"""


class FileConfig(Config):
    """
    File-based configuration source implementation.
    基于文件的配置源实现。
    """

    path: str
    file: Optional[TextIO]

    def __init__(self, path: str, encoding: str = 'utf-8'):
        """
        Initialize file configuration.
        初始化文件配置。
        :param path: File path 文件路径
        :param encoding: File encoding 文件编码
        """
        self.path = path
        self.encoding = encoding
        self.file: Optional[TextIO] = None

    @property
    def is_open(self) -> bool:
        """
        Check if the file is currently open.
        检查文件是否已打开。
        :return: True if file is open, False otherwise 文件已打开返回True，否则返回False
        """
        if not self.file:
            return False
        return not self.file.closed

    def get_text(self) -> str:
        """
        Read and return the file content as text.
        读取并返回文件的文本内容。
        :return: File content as text 文件的文本内容
        """
        with open(self.path, 'r', encoding=self.encoding) as file:
            return file.read()

    def get_content(self) -> bytes:
        """
        Get the file content as bytes.
        获取文件的字节内容。
        :return: File content as bytes 文件的字节内容
        """
        with open(self.path, 'rb') as file:
            return file.read()

    def get_dict(self) -> Dict[str, Any]:
        """
        Parse the file content and return as dictionary.
        解析文件内容并返回字典格式。
        :return: Parsed file content as dictionary 解析后的文件内容字典
        """
        return ConfigParseMatch.match(self.path).parse(self.get_text())

    def close(self) -> None:
        """Close the underlying file handle if it is open. 关闭底层文件句柄。"""
        if self.is_open:
            self.file.close()  # type: ignore[union-attr]
        self.file = None


class UrlConfig(Config):
    """
    URL-based configuration source implementation.
    基于URL的配置源实现。
    """

    url: str

    def __init__(self, url: str, timeout: Optional[float] = 10.0, encoding: str = 'utf-8'):
        """
        Initialize URL configuration.
        初始化URL配置。
        :param url: Configuration URL 配置URL地址
        :param timeout: Request timeout in seconds 请求超时时间（秒）
        :param encoding: Fallback encoding when the response declares none 响应未声明编码时的回退编码
        """
        self.url = url
        self.timeout = timeout
        self.encoding = encoding

    @property
    def is_open(self) -> bool:
        """
        URL-based configs are never considered "open" in the traditional sense.
        基于URL的配置在传统意义上从不被认为是"打开"的。
        :return: Always False 总是返回False
        """
        return False

    @property
    def _response(self):
        """
        Fetch the URL once per call.
        拉取URL响应。
        """
        try:
            import requests
        except ImportError as e:
            raise ImportError('使用 URL 配置源需要安装 requests: pip install requests') from e

        response = requests.get(self.url, timeout=self.timeout)
        response.raise_for_status()
        return response

    def get_text(self) -> str:
        """
        Fetch and return the URL content as text.
        获取并返回URL内容的文本格式。
        :return: URL response text URL响应的文本内容
        """
        response = self._response
        if response.encoding is None:
            response.encoding = self.encoding
        return response.text

    def get_content(self) -> bytes:
        """
        Fetch and return the URL content as bytes.
        获取并返回URL内容的字节格式。
        :return: URL response content as bytes URL响应的字节内容
        """
        return self._response.content

    def get_dict(self) -> Dict[str, Any]:
        """
        Fetch the URL content and parse it as dictionary.
        获取URL内容并解析为字典格式。
        :return: Parsed URL content as dictionary 解析后的URL内容字典
        """
        response = self._response
        content_type = response.headers.get('Content-Type') or ''
        # 如果响应是JSON格式，直接解析 (If response is JSON format, parse directly)
        if 'json' in content_type:
            return response.json()
        # 否则使用配置解析器解析 (Otherwise use config parser to parse)
        if response.encoding is None:
            response.encoding = self.encoding
        return ConfigParseMatch.match(self.url).parse(response.text)
