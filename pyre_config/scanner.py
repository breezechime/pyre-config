import os
from typing import Dict, List, Optional

from .parse import ConfigParseMatch


class ConfigScanner:
    """配置扫描器，用于扫描配置文件"""

    """默认扫描路径"""
    DEFAULT_CONFIG_LOCATIONS = ['./config', './resource', '/config', '/resource']

    """默认配置名称"""
    DEFAULT_CONFIG_NAME = 'application'

    def __init__(self, config_locations: List[str] = None, config_name: str = None):
        self.config_locations = config_locations or list(self.DEFAULT_CONFIG_LOCATIONS)
        self.config_name = config_name or self.DEFAULT_CONFIG_NAME

    def scanner(self) -> Dict[str, str]:
        """扫描配置文件，返回 文件名 -> 文件路径 的映射。

        目录按 ``config_locations`` 的顺序扫描，同名文件以**先出现的目录**为准，
        即位置在前的目录优先级更高。
        """
        file_paths: Dict[str, str] = {}
        for config_location in self.config_locations:
            if not os.path.isdir(config_location):
                continue
            for file_name in sorted(os.listdir(config_location)):
                if file_name in file_paths or self.config_name not in file_name:
                    continue
                file_path = os.path.join(config_location, file_name)
                if not os.path.isfile(file_path):
                    continue
                if ConfigParseMatch.get_parser(file_path) is None:
                    continue
                file_paths[file_name] = file_path
        return file_paths

    def exists(self, file_path: str) -> bool:
        """判断给定路径是否是可被本库解析的配置文件"""
        return os.path.isfile(file_path) and ConfigParseMatch.get_parser(file_path) is not None

    def match_name(self, file_name: str, env: Optional[str] = None) -> bool:
        """判断文件名是否匹配当前配置名（可指定环境后缀）"""
        stem = os.path.splitext(file_name)[0]
        if env is None:
            return stem == self.config_name
        return stem == f'{self.config_name}-{env}'
