from dataclasses import fields, is_dataclass
from functools import wraps
from typing import Any, Optional, Type, TypeVar

from .globals import _active
from .loader import ConfigLoader
from .utils import getter_dict

_T = TypeVar("_T")


def _is_pydantic_model(clazz: type) -> bool:
    """是否为 pydantic 模型（未安装 pydantic 时始终返回 False）"""
    try:
        from pydantic import BaseModel
    except ImportError:
        return False
    return issubclass(clazz, BaseModel)


def _is_model(clazz: type) -> bool:
    """是否通过构造参数注入（pydantic 模型 / dataclass）"""
    return _is_pydantic_model(clazz) or is_dataclass(clazz)


def _model_kwargs(clazz: type, config_dict: dict) -> dict:
    """dataclass 只保留自身声明的字段，避免传入未知关键字参数"""
    if is_dataclass(clazz):
        names = {field.name for field in fields(clazz)}
        return {key: value for key, value in config_dict.items() if key in names}
    return dict(config_dict)


def _as_dict(config_dict: Any, prefix: Optional[str]) -> dict:
    """按前缀取出配置子树，并保证返回字典"""
    prefix = prefix.strip('.') if prefix else None
    if prefix:
        config_dict = getter_dict(config_dict, prefix, {})
    if config_dict is None:
        return {}
    if not isinstance(config_dict, dict):
        raise TypeError(
            f"配置前缀 '{prefix}' 对应的值必须是字典，实际为 {type(config_dict).__name__}"
            if prefix else
            f'配置必须是字典，实际为 {type(config_dict).__name__}'
        )
    return config_dict


def configuration(clazz: Type[_T]) -> Type[_T]:
    """标记一个类为配置类（当前仅做标记，返回原类以便链式使用）"""
    setattr(clazz, '__configuration__', True)
    return clazz


def configuration_source(
    path: str,
    encoding: Optional[str] = 'utf-8',
    prefix: Optional[str] = None,
    config_key: Optional[str] = None,
):
    """从指定配置文件（或 URL）注入配置"""

    def wrapper(cls):
        configuration(cls)
        original_init = cls.__init__

        @wraps(original_init)
        def __init__(self, *args, **kwargs):
            config_loader = _active.instance or ConfigLoader()
            config_dict = _as_dict(config_loader.load_config(path, encoding).get_dict(), prefix)

            if config_key:
                setattr(self, config_key, config_dict)

            if _is_model(cls):
                kwargs = {**_model_kwargs(cls, config_dict), **kwargs}
            else:
                _apply_attributes(self, cls, config_dict)

            original_init(self, *args, **kwargs)

        cls.__init__ = __init__
        return cls

    return wrapper


def configuration_values(cls=None, prefix: Optional[str] = None, config_key: Optional[str] = None):
    """从当前激活的配置加载器注入配置"""

    def wrapper(clazz):
        configuration(clazz)
        original_init = clazz.__init__

        @wraps(original_init)
        def __init__(self, *args, **kwargs):
            config_loader = _active.instance
            config_dict = _as_dict(config_loader.config_dict if config_loader else {}, prefix)

            if config_key:
                setattr(self, config_key, config_dict)

            if _is_model(clazz):
                kwargs = {**_model_kwargs(clazz, config_dict), **kwargs}
            else:
                _apply_attributes(self, clazz, config_dict)

            original_init(self, *args, **kwargs)

        clazz.__init__ = __init__
        return clazz

    if cls is None:
        return wrapper
    if isinstance(cls, str):
        return configuration_values(prefix=cls)
    return wrapper(cls)


def _apply_attributes(instance: Any, clazz: type, config_dict: dict) -> None:
    """仅注入类上已声明的属性，避免污染实例命名空间"""
    annotations = getattr(clazz, '__annotations__', {})
    for key, value in config_dict.items():
        if key in annotations or hasattr(instance, key):
            setattr(instance, key, value)
