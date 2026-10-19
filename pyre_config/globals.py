from typing import Any, Optional, TypeVar

from .loader import ConfigLoader

_T = TypeVar("_T")

#: 模块级名称，用于声明当前激活的加载器（兼容旧写法）
_active: 'ConfigLoaderProxy'


class ConfigLoaderProxy:
    """持有当前激活的 ``ConfigLoader``，并转发属性访问到该实例。"""

    def __init__(self):
        self.instance: Optional[ConfigLoader] = None

    def set_instance(self, instance: ConfigLoader) -> None:
        self.instance = instance

    def __getattr__(self, item: str) -> Any:
        instance = self.__dict__.get('instance')
        if instance is None:
            raise RuntimeError('配置加载器尚未初始化，请先调用 ConfigLoader().init_app()')
        return getattr(instance, item)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(instance={self.instance!r})'


_active = ConfigLoaderProxy()


def get_active_loader() -> Optional[ConfigLoader]:
    """返回当前激活的配置加载器，未激活时返回 ``None``"""
    return _active.instance
