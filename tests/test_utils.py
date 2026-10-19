import pytest

from pyre_config.utils import getter_dict, setter_dict


class TestGetterDict:
    def test_nested_dict(self):
        data = {'server': {'host': 'localhost', 'port': 8080}}
        assert getter_dict(data, 'server.port') == 8080
        assert getter_dict(data, 'server') == {'host': 'localhost', 'port': 8080}

    def test_list_index(self):
        data = {'items': [{'id': 1, 'name': 'Item 1'}, {'id': 2, 'name': 'Item 2'}]}
        assert getter_dict(data, 'items.0.name') == 'Item 1'
        assert getter_dict(data, 'items.1.id') == 2

    def test_missing_returns_default(self):
        data = {'server': {'port': 8080}}
        assert getter_dict(data, 'server.host', 'fallback') == 'fallback'
        assert getter_dict(data, 'nope.deep.deep', None) is None
        assert getter_dict(data, 'server.port.deeper', 'x') == 'x'

    def test_list_with_non_digit_key_returns_default(self):
        data = {'items': [{'name': 'a'}]}
        assert getter_dict(data, 'items.name', 'fallback') == 'fallback'

    def test_raise_error(self):
        with pytest.raises(KeyError):
            getter_dict({'a': 1}, 'b', raise_error=True)
        with pytest.raises(TypeError):
            getter_dict({'a': [1]}, 'a.b', raise_error=True)

    def test_empty_inputs(self):
        assert getter_dict({}, 'a', 'default') == 'default'
        assert getter_dict({'a': 1}, '', 'default') == 'default'
        assert getter_dict(None, 'a', 'default') == 'default'


class TestSetterDict:
    def test_create_intermediate_dict(self):
        data = {'user': {'name': 'John'}}
        setter_dict(data, 'user.address.city', 'New York')
        assert data == {'user': {'name': 'John', 'address': {'city': 'New York'}}}

    def test_create_from_empty(self):
        data = {}
        setter_dict(data, 'server.port', 8080)
        assert data == {'server': {'port': 8080}}

    def test_list_index_with_existing_list(self):
        data = {'items': []}
        setter_dict(data, 'items.0.name', 'Item 1')
        assert data == {'items': [{'name': 'Item 1'}]}

    def test_list_index_from_scratch(self):
        data = {}
        setter_dict(data, 'servers.1.host', 'b')
        assert data == {'servers': [None, {'host': 'b'}]}

    def test_deep_mixed_path(self):
        data = {}
        setter_dict(data, 'a.0.b.1.c', 1)
        assert data == {'a': [{'b': [None, {'c': 1}]}]}

    def test_overwrite_existing_scalar_with_dict(self):
        data = {'server': 1}
        setter_dict(data, 'server.port', 80)
        assert data == {'server': {'port': 80}}

    def test_returns_same_object(self):
        data = {}
        assert setter_dict(data, 'a.b', 1) is data

    def test_invalid_key(self):
        with pytest.raises(ValueError):
            setter_dict({}, 'a..b', 1)

    def test_non_container_data(self):
        with pytest.raises(TypeError):
            setter_dict('not-a-dict', 'a.b', 1)

    def test_list_requires_numeric_index(self):
        with pytest.raises(TypeError):
            setter_dict([], 'name.value', 1)

    def test_roundtrip_with_getter(self):
        data = {}
        setter_dict(data, 'pyre.datasource.pool_size', 20)
        assert getter_dict(data, 'pyre.datasource.pool_size') == 20
