import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ConfigParseError(Exception):
    """配置解析失败。"""


class ConfigParseNotSupported(ConfigParseError):
    """没有匹配到可用的配置解析器。"""


class ConfigParse(ABC):
    """配置解析"""

    @property
    @abstractmethod
    def extension(self) -> str:
        """解析器对应的文件扩展名"""

    @abstractmethod
    def parse(self, text: str) -> Dict[str, Any]:
        """将文本解析为字典"""
        pass


class YamlConfigParse(ConfigParse):

    extension = 'yaml'

    def parse(self, text: str) -> Dict[str, Any]:
        try:
            import yaml
        except ImportError as e:  # pragma: no cover
            raise ConfigParseError('解析 YAML 需要安装 pyyaml: pip install pyyaml') from e
        return yaml.safe_load(text) or {}


class TomlConfigParse(ConfigParse):

    extension = 'toml'

    def parse(self, text: str) -> Dict[str, Any]:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import toml

                return toml.loads(text) or {}
            except ImportError as e:  # pragma: no cover
                raise ConfigParseError('解析 TOML 需要 Python 3.11+ 或安装 toml: pip install toml') from e
        return tomllib.loads(text) or {}


class JsonConfigParse(ConfigParse):

    extension = 'json'

    def parse(self, text: str) -> Dict[str, Any]:
        return json.loads(text) or {}


class ConfigParseMatch:
    """按文件扩展名匹配配置解析器"""

    matching = {
        'yaml': YamlConfigParse,
        'yml': YamlConfigParse,
        'toml': TomlConfigParse,
        'json': JsonConfigParse,
    }

    @classmethod
    def get_extension(cls, path: str) -> str:
        """从路径中提取扩展名（忽略查询串与目录名中的点）"""
        pure_path = path.split('?')[0].split('#')[0].rstrip('/')
        file_name = pure_path.replace('\\', '/').split('/')[-1]
        if '.' not in file_name:
            return ''
        return file_name.rsplit('.', 1)[-1].lower()

    @classmethod
    def get_parser(cls, path: str) -> Optional[ConfigParse]:
        """返回匹配到的解析器实例，未匹配到返回 ``None``"""
        parser_class = cls.matching.get(cls.get_extension(path))
        return parser_class() if parser_class else None

    @classmethod
    def match(cls, path: str) -> ConfigParse:
        """返回匹配到的解析器实例，未匹配到抛出 ``ConfigParseNotSupported``"""
        parser = cls.get_parser(path)
        if parser is None:
            extension = cls.get_extension(path) or '<无扩展名>'
            raise ConfigParseNotSupported(
                f'配置文件解析器匹配失败, key: {extension}, path: {path}'
            )
        return parser
