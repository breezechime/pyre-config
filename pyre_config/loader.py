import os
import sys
from typing import Any, List, Optional, Sequence, Tuple

from .config import Config, FileConfig, UrlConfig
from .scanner import ConfigScanner
from .utils import expand_dotted_keys, getter_dict, setter_dict


class ConfigLoader:
    """配置加载器，支持多种配置源和优先级"""

    """配置文件路径"""
    LOCATION_KEY = 'pyre.config.location'

    """配置文件名称"""
    CONFIG_NAME_KEY = 'pyre.config.name'

    """同时扫描指定配置目录和默认目录"""
    ADDITIONAL_KEY = 'pyre.config.additional'

    """环境键"""
    ENV_KEY = 'pyre.config.env'

    """环境变量前缀"""
    ENV_VAR_PREFIXS = ['PYRE_', 'SERVER_']

    def __init__(self, scanner: Optional[ConfigScanner] = None):
        self.scanner = scanner or ConfigScanner()
        self.config_dict: dict[str, Any] = {}

    @staticmethod
    def load_config(path: str, encoding: str = 'utf-8') -> Config:
        """加载指定路径的配置源"""
        if path.startswith(('http://', 'https://')):
            return UrlConfig(path)
        return FileConfig(path, encoding)

    def init_app(self, config_dict: dict = None) -> Tuple[dict, List[str]]:
        """初始化配置模块，按优先级应用配置源，返回 (配置字典, 已加载的配置文件路径列表)

        优先级由低到高：调用方默认值 → 基础配置文件 → 环境配置文件 → 环境变量 → 命令行参数。
        """
        config_dict = dict(config_dict) if config_dict else dict(self.config_dict)
        config_dict = expand_dotted_keys(config_dict)

        cmd_args = self.parse_cmd_args()
        env_variables = self.parse_environment_variables()

        # 先并入环境变量与命令行参数，使其中的控制项（location / name）参与扫描范围决策
        config_dict = self.merge_config_dict(env_variables, config_dict)
        config_dict = self.merge_config_dict(cmd_args, config_dict)
        config_dict = self.apply_location(config_dict)

        # 设置配置文件名
        config_name = getter_dict(config_dict, self.CONFIG_NAME_KEY)
        if config_name:
            self.scanner.config_name = config_name

        # 扫描配置文件
        file_paths = self.scanner.scanner()

        # 加载基础配置文件
        config_file_paths: List[str] = []
        for file_name, file_path in file_paths.items():
            if not self.scanner.match_name(file_name):
                continue
            config_file_paths.append(file_path)
            config_dict = self.merge_config_dict(self.load_config(file_path).get_dict(), config_dict)

        # 环境变量与命令行参数覆盖配置文件
        config_dict = self.merge_config_dict(env_variables, config_dict)
        config_dict = self.merge_config_dict(cmd_args, config_dict)

        # 加载环境配置文件
        env = getter_dict(config_dict, self.ENV_KEY)
        if env:
            envs, config_dict = self.load_env_config(env, file_paths, config_file_paths, config_dict)
            envs = list(dict.fromkeys(envs))
            # 环境配置文件加载完成后，重新用环境变量与命令行参数覆盖
            config_dict = self.merge_config_dict(env_variables, config_dict)
            config_dict = self.merge_config_dict(cmd_args, config_dict)
            setter_dict(config_dict, f'{self.ENV_KEY}s', ','.join(envs))

        # 激活
        self.config_dict = config_dict
        self.active()
        return self.config_dict, config_file_paths

    def init_config(self, config_model):
        """将配置字典实例化为配置模型"""
        return config_model(**self.config_dict)

    def handle_env_or_cmd_config(self, config_dict: dict, data: dict) -> dict:
        """合并环境变量 / 命令行参数，并处理其中的配置定位项"""
        return self.apply_location(self.merge_config_dict(data, config_dict))

    def apply_location(self, config_dict: dict) -> dict:
        """按 ``pyre.config.location`` 调整扫描位置，并合并其直接指向的配置文件"""
        config_location = getter_dict(config_dict, self.LOCATION_KEY)
        if not config_location:
            return config_dict

        location_dirs: List[str] = []
        for location in str(config_location).split(','):
            location = location.strip()
            if not location:
                continue
            if os.path.isdir(location):
                location_dirs.append(location)
            else:
                config_dict = self.merge_config_dict(self.load_config(location).get_dict(), config_dict)

        if getter_dict(config_dict, self.ADDITIONAL_KEY):
            for location_dir in location_dirs:
                if location_dir not in self.scanner.config_locations:
                    self.scanner.config_locations.append(location_dir)
        else:
            self.scanner.config_locations = location_dirs
        return config_dict

    def load_env_config(
        self, env: str, file_paths: dict, config_file_paths: List[str], config_dict: dict
    ) -> Tuple[List[str], dict]:
        """加载环境配置，支持环境配置文件内继续声明 env 形成链式加载"""
        pending = [item.strip() for item in env.split(',') if item.strip()]
        envs: List[str] = []
        while pending:
            current_env = pending.pop(0)
            if current_env in envs:
                continue
            envs.append(current_env)
            for file_name, file_path in file_paths.items():
                if not self.scanner.match_name(file_name, current_env):
                    continue
                if file_path in config_file_paths:
                    continue
                config_file_paths.append(file_path)
                temp_config = self.load_config(file_path).get_dict()
                temp_env = getter_dict(temp_config, self.ENV_KEY)
                if temp_env:
                    pending.extend(item.strip() for item in temp_env.split(',') if item.strip())
                config_dict = self.merge_config_dict(temp_config, config_dict)
        return envs, config_dict

    def merge_config_dict(self, src: dict, target: dict) -> dict:
        """展开扁平键后安全合并（不修改入参）"""
        return self.safe_merge_config_dict(expand_dotted_keys(src), target)

    def safe_merge_config_dict(self, src: dict, target: dict) -> dict:
        """安全合并配置字典：递归合并子字典，其余类型直接覆盖；不修改入参"""
        result = dict(target)
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self.safe_merge_config_dict(value, result[key])
            else:
                result[key] = value
        return result

    def active(self):
        """激活当前实例"""
        from .globals import _active

        _active.set_instance(self)

    @staticmethod
    def parse_cmd_args(args: Optional[Sequence[str]] = None) -> dict:
        """解析命令行参数，支持 ``--key value`` 与 ``--key=value`` 两种写法"""
        args = list(sys.argv[1:] if args is None else args)
        cmd_args: dict = {}
        for index, arg in enumerate(args):
            if not arg.startswith('--'):
                continue
            body = arg[2:]
            if not body:
                continue
            if '=' in body:
                key, value = body.split('=', 1)
            else:
                key = body
                next_arg = args[index + 1] if index + 1 < len(args) else None
                value = None if next_arg is None or next_arg.startswith('--') else next_arg
            if not key:
                continue
            setter_dict(cmd_args, key, value)
        return cmd_args

    def parse_environment_variables(self) -> dict:
        """获取环境变量配置，下划线视为层级分隔符（连续下划线会被折叠）"""
        environment_variables: dict = {}
        for key, value in os.environ.items():
            if not any(key.startswith(prefix) for prefix in self.ENV_VAR_PREFIXS):
                continue
            # 将环境变量格式 PYRE_DATASOURCE_URL 转换为 pyre.datasource.url
            config_key = '.'.join(part for part in key.replace('_', '.').lower().split('.') if part)
            if not config_key:
                continue
            setter_dict(environment_variables, config_key, value)
        return environment_variables
