from dataclasses import dataclass
from typing import Optional

import pytest
from pydantic import BaseModel

from pyre_config import ConfigLoader, ConfigScanner, configuration, configuration_source, configuration_values
from pyre_config.globals import _active


@pytest.fixture(autouse=True)
def restore_active(monkeypatch):
    monkeypatch.setattr(_active, 'instance', None, raising=False)


@pytest.fixture
def active_loader(isolated_env):
    loader = ConfigLoader(scanner=ConfigScanner(config_locations=[], config_name='application'))
    loader.config_dict = {
        'server': {'host': 'config-host', 'port': 8080},
        'secret_key': 's3cr3t',
        'other': {'unused': 1},
    }
    loader.active()
    return loader


class TestConfiguration:
    def test_returns_same_class(self):
        class Foo:
            pass

        assert configuration(Foo) is Foo

    def test_usable_as_decorator(self):
        @configuration
        class Foo:
            pass

        assert Foo is not None
        assert Foo.__configuration__ is True


class TestConfigurationValuesPlainClass:
    def test_injects_declared_attributes(self, active_loader):
        @configuration_values
        class Service:
            server: dict
            secret_key: str

        service = Service()
        assert service.server == {'host': 'config-host', 'port': 8080}
        assert service.secret_key == 's3cr3t'

    def test_skips_undeclared_attributes(self, active_loader):
        @configuration_values
        class Service:
            secret_key: str

        service = Service()
        assert not hasattr(service, 'server')

    def test_original_init_still_runs(self, active_loader):
        @configuration_values
        class Service:
            secret_key: str

            def __init__(self, tag='default'):
                self.tag = tag
                self.ran = True

        service = Service(tag='custom')
        assert service.ran is True
        assert service.tag == 'custom'
        assert service.secret_key == 's3cr3t'

    def test_explicit_argument_wins(self, active_loader):
        @configuration_values
        class Service:
            secret_key: str = 'placeholder'

            def __init__(self, secret_key=None):
                if secret_key is not None:
                    self.secret_key = secret_key

        assert Service(secret_key='explicit').secret_key == 'explicit'

    def test_prefix(self, active_loader):
        @configuration_values(prefix='server')
        class Service:
            host: str

        assert Service().host == 'config-host'

    def test_prefix_with_trailing_dot(self, active_loader):
        @configuration_values(prefix='server.')
        class Service:
            port: int

        assert Service().port == 8080

    def test_prefix_as_string_decorator(self, active_loader):
        @configuration_values('server')
        class Service:
            port: int

        assert Service().port == 8080

    def test_missing_prefix_injects_nothing(self, active_loader):
        @configuration_values(prefix='not.exist')
        class Service:
            port: int = 1

        assert Service().port == 1

    def test_prefix_pointing_to_scalar_raises(self, active_loader):
        @configuration_values(prefix='secret_key')
        class Service:
            pass

        with pytest.raises(TypeError):
            Service()

    def test_config_key_stashes_raw_dict(self, active_loader):
        @configuration_values(prefix='server', config_key='raw')
        class Service:
            host: str

        service = Service()
        assert service.raw == {'host': 'config-host', 'port': 8080}
        assert service.host == 'config-host'

    def test_no_active_loader_injects_nothing(self):
        @configuration_values
        class Service:
            port: int = 1

        assert Service().port == 1


class TestConfigurationValuesModel:
    def test_pydantic_model(self, active_loader):
        @configuration_values(prefix='server')
        class ServerConfig(BaseModel):
            host: str
            port: int

        config = ServerConfig()
        assert config.host == 'config-host'
        assert config.port == 8080

    def test_pydantic_explicit_kwargs_win(self, active_loader):
        @configuration_values(prefix='server')
        class ServerConfig(BaseModel):
            host: str
            port: int

        assert ServerConfig(port=9999).port == 9999

    def test_pydantic_type_validation(self, active_loader):
        @configuration_values(prefix='server')
        class ServerConfig(BaseModel):
            host: str
            port: int

        with pytest.raises(Exception):
            ServerConfig(port='not-a-number')

    def test_dataclass_filters_unknown_fields(self, active_loader):
        @configuration_values
        class AppConfig:
            secret_key: str
            server: dict = None

        config = AppConfig()
        assert config.secret_key == 's3cr3t'
        assert config.server == {'host': 'config-host', 'port': 8080}

    def test_dataclass_with_required_field(self, active_loader):
        @configuration_values(prefix='server')
        @dataclass
        class ServerConfig:
            host: Optional[str] = None
            port: Optional[int] = None

        config = ServerConfig()
        assert config.host == 'config-host'
        assert config.port == 8080


class TestConfigurationSource:
    def test_load_from_file(self, tmp_path, isolated_env):
        path = tmp_path / 'custom.yaml'
        path.write_text('secret_key: from-file\n', encoding='utf-8')

        @configuration_source(str(path))
        class Service:
            secret_key: str

        assert Service().secret_key == 'from-file'

    def test_prefix_and_config_key(self, tmp_path, isolated_env):
        path = tmp_path / 'custom.yaml'
        path.write_text('server:\n  host: file-host\n  port: 1\n', encoding='utf-8')

        @configuration_source(str(path), prefix='server', config_key='raw')
        class Service:
            host: str

        service = Service()
        assert service.host == 'file-host'
        assert service.raw == {'host': 'file-host', 'port': 1}

    def test_pydantic_model(self, tmp_path, isolated_env):
        path = tmp_path / 'custom.yaml'
        path.write_text('server:\n  host: file-host\n  port: 1\n', encoding='utf-8')

        @configuration_source(str(path), prefix='server')
        class ServerConfig(BaseModel):
            host: str
            port: int

        assert ServerConfig().host == 'file-host'

    def test_original_init_runs(self, tmp_path, isolated_env):
        path = tmp_path / 'custom.yaml'
        path.write_text('secret_key: from-file\n', encoding='utf-8')

        @configuration_source(str(path))
        class Service:
            secret_key: str

            def __init__(self):
                self.built = True

        service = Service()
        assert service.built is True

    def test_uses_active_loader(self, tmp_path, isolated_env):
        path = tmp_path / 'custom.yaml'
        path.write_text('a: 1\n', encoding='utf-8')

        from pyre_config import get_active_loader

        loader = ConfigLoader(scanner=ConfigScanner(config_locations=[], config_name='application'))
        loader.active()

        @configuration_source(str(path))
        class Service:
            a: int

        assert Service().a == 1
        assert get_active_loader() is loader
