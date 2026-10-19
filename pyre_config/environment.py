from typing import Any, List, Optional


class Environment:
    """运行环境描述：当前激活环境与其加载链"""

    def __init__(self, envs: Optional[str] = None, env: Optional[str] = None, config_dict: Optional[dict] = None, app_config: Any = None):
        self.envs: str = envs or ''
        self.env: str = env or ''
        self.config_dict: dict = config_dict if config_dict is not None else {}
        self.app_config = app_config

    def get_env_strings(self) -> List[str]:
        """返回所有已激活的环境名（含链式加载出的环境）"""
        return [item.strip() for item in self.envs.split(',') if item.strip()]

    def is_dev(self) -> bool:
        return 'dev' in self.get_env_strings()

    def is_prod(self) -> bool:
        return 'prod' in self.get_env_strings()

    def is_test(self) -> bool:
        return 'test' in self.get_env_strings()

    def is_env(self, env: str) -> bool:
        """判断某个环境是否已激活"""
        return env in self.get_env_strings()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(env={self.env!r}, envs={self.envs!r})'
