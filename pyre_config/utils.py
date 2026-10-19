from typing import Any, Union


def getter_dict(data: Union[dict, list], key: str, default: Any = None, raise_error: bool = False) -> Any:
    """
    Access nested dictionary values using dot notation.

    Args:
        data (dict): The dictionary to access
        key (str): Path to the value using dot notation (e.g., "user.address.city" or "items.0.name")
        default: Value to return if the path doesn't exist
        raise_error (bool): Re-raise the original exception instead of returning ``default``

    Returns:
        The value at the specified path or default if not found

    Example:
        data = {"user": {"name": "John", "items": [{"id": 1, "name": "Item 1"}]}}
        getter_dict(data, "user.name")  # Returns "John"
        getter_dict(data, "user.items.0.name")  # Returns "Item 1"
    """
    if not data or not key:
        return default

    current: Any = data
    for name in key.split('.'):
        if isinstance(current, list):
            # 列表只能按下标访问
            if not name.isdigit():
                if raise_error:
                    raise TypeError(f'cannot use {name!r} as a list index while resolving {key!r}')
                return _flat_lookup(data, key, default)
            name = int(name)
        try:
            current = current[name]
        except (KeyError, IndexError, TypeError):
            if raise_error:
                raise
            return _flat_lookup(data, key, default)

    return current


def _flat_lookup(data: Any, key: str, default: Any) -> Any:
    """嵌套查找失败时，兼容 "a.b.c" 形式的扁平键写法。"""
    if isinstance(data, dict) and key in data:
        return data[key]
    return default


def expand_dotted_keys(data: Any) -> Any:
    """
    将顶层的 "a.b.c" 形式扁平键展开为嵌套字典，例如::

        expand_dotted_keys({'pyre.config.env': 'dev'})
        # {'pyre': {'config': {'env': 'dev'}}}

    没有扁平键时原样返回（不复制）。
    """
    if not isinstance(data, dict):
        return data
    if not any(isinstance(key, str) and '.' in key for key in data):
        return data

    result: dict = {}
    for key, value in data.items():
        if isinstance(key, str) and '.' in key:
            setter_dict(result, key, value)
        else:
            result[key] = value
    return result


def setter_dict(data: Union[dict, list], key: str, value: Any) -> Union[dict, list]:
    """
    Set a value in a nested dictionary using dot notation.
    Creates intermediate dictionaries and lists as needed.

    Args:
        data (dict): The dictionary to modify
        key (str): Path where to set the value using dot notation (e.g., "user.address.city")
        value: Value to set

    Returns:
        The modified dictionary

    Example:
        data = {"user": {"name": "John"}}
        setter_dict(data, "user.address.city", "New York")
        # Results in: {"user": {"name": "John", "address": {"city": "New York"}}}

        data = {"items": []}
        setter_dict(data, "items.0.name", "Item 1")
        # Results in: {"items": [{"name": "Item 1"}]}
    """
    if not isinstance(data, (dict, list)):
        raise TypeError(f'data must be a dict or list, got {type(data).__name__}')

    keys = key.split('.')
    if not key or any(part == '' for part in keys):
        raise ValueError(f'invalid key: {key!r}')

    current: Any = data
    for index, name in enumerate(keys[:-1]):
        next_is_index = keys[index + 1].isdigit()

        if isinstance(current, list):
            if not name.isdigit():
                raise TypeError(f'invalid path {key!r}: a list can only be indexed by a number, got {name!r}')
            position = int(name)
            while len(current) <= position:
                current.append(None)
            if not isinstance(current[position], (dict, list)):
                current[position] = [] if next_is_index else {}
            current = current[position]
        else:
            existing = current.get(name)
            if next_is_index:
                if not isinstance(existing, list):
                    existing = []
                    current[name] = existing
            elif not isinstance(existing, dict):
                existing = {}
                current[name] = existing
            current = existing

    last = keys[-1]
    if isinstance(current, list):
        position = int(last)
        while len(current) <= position:
            current.append(None)
        current[position] = value
    else:
        current[last] = value

    return data
