import os

import pytest

from pyre_config import ConfigLoader, ConfigScanner, FileConfig, UrlConfig


def make_loader(directory, name='application'):
    return ConfigLoader(scanner=ConfigScanner(config_locations=[str(directory)], config_name=name))


def write(directory, name, content):
    (directory / name).write_text(content, encoding='utf-8')


class TestLoadConfig:
    def test_local_file(self):
        assert isinstance(ConfigLoader.load_config('./a.yaml'), FileConfig)

    @pytest.mark.parametrize('url', ['http://example.com/a.yaml', 'https://example.com/a.yaml'])
    def test_url(self, url):
        assert isinstance(ConfigLoader.load_config(url), UrlConfig)

    def test_path_containing_http_is_not_url(self):
        assert isinstance(ConfigLoader.load_config('./my-http-dir/a.yaml'), FileConfig)


class TestParseCmdArgs:
    def test_space_form(self):
        assert ConfigLoader.parse_cmd_args(['--server.port', '8080']) == {'server': {'port': '8080'}}

    def test_equals_form(self):
        """README 记录的 --key=value 写法必须可用。"""
        assert ConfigLoader.parse_cmd_args(['--pyre.config.env=dev']) == {
            'pyre': {'config': {'env': 'dev'}}
        }

    def test_mixed_forms(self):
        args = ['--pyre.config.env=dev', '--server.port', '8080']
        assert ConfigLoader.parse_cmd_args(args) == {
            'pyre': {'config': {'env': 'dev'}},
            'server': {'port': '8080'},
        }

    def test_flag_without_value(self):
        assert ConfigLoader.parse_cmd_args(['--debug']) == {'debug': None}

    def test_flag_followed_by_flag(self):
        assert ConfigLoader.parse_cmd_args(['--a', '--b', '1']) == {'a': None, 'b': '1'}

    def test_ignores_positional_args(self):
        assert ConfigLoader.parse_cmd_args(['runserver', '--port', '1']) == {'port': '1'}

    def test_empty(self):
        assert ConfigLoader.parse_cmd_args([]) == {}


class TestParseEnvironmentVariables:
    def test_default_prefixes(self, monkeypatch):
        monkeypatch.setattr(
            os,
            'environ',
            {'PYRE_DATASOURCE_URL': 'mysql://x', 'SERVER_HOST': '0.0.0.0', 'PATH': '/bin'},
        )
        assert ConfigLoader().parse_environment_variables() == {
            'pyre': {'datasource': {'url': 'mysql://x'}},
            'server': {'host': '0.0.0.0'},
        }

    def test_consecutive_underscores_do_not_create_empty_keys(self, monkeypatch):
        monkeypatch.setattr(os, 'environ', {'SERVER__HOST': '1.2.3.4'})
        assert ConfigLoader().parse_environment_variables() == {'server': {'host': '1.2.3.4'}}

    def test_underscore_is_a_level_separator(self, monkeypatch):
        """单下划线被视作层级分隔符，这是本库的既定约定。"""
        monkeypatch.setattr(os, 'environ', {'PYRE_DATASOURCE_POOL_SIZE': '20'})
        assert ConfigLoader().parse_environment_variables() == {
            'pyre': {'datasource': {'pool': {'size': '20'}}}
        }

    def test_custom_prefixes(self, monkeypatch, isolated_env):
        monkeypatch.setattr(os, 'environ', {'PRYECFG_SERVER_PORT': '1', 'SERVER_PORT': '2'})
        # 前缀本身会作为键路径保留，与默认前缀行为一致
        assert ConfigLoader().parse_environment_variables() == {'pryecfg': {'server': {'port': '1'}}}

    def test_ignores_unrelated_variables(self, monkeypatch):
        monkeypatch.setattr(os, 'environ', {'OTHER_KEY': '1'})
        assert ConfigLoader().parse_environment_variables() == {}


class TestSafeMerge:
    def test_recursive_merge(self):
        loader = ConfigLoader()
        target = {'a': {'x': 1, 'y': 2}, 'b': 1}
        result = loader.safe_merge_config_dict({'a': {'y': 3, 'z': 4}}, target)
        assert result == {'a': {'x': 1, 'y': 3, 'z': 4}, 'b': 1}

    def test_does_not_mutate_inputs(self):
        loader = ConfigLoader()
        source = {'a': {'y': 3}}
        target = {'a': {'x': 1}}
        loader.safe_merge_config_dict(source, target)
        assert source == {'a': {'y': 3}}
        assert target == {'a': {'x': 1}}

    def test_scalar_overrides_dict(self):
        loader = ConfigLoader()
        assert loader.safe_merge_config_dict({'a': 1}, {'a': {'x': 1}}) == {'a': 1}


class TestInitApp:
    def test_base_and_env_files(self, config_dir, isolated_env):
        config, files = make_loader(config_dir).init_app({'pyre.config.env': 'dev'})

        assert config['server'] == {'host': 'file-host', 'port': 8081}
        assert {os.path.basename(f) for f in files} == {'application.yaml', 'application-dev.yaml'}

    def test_without_env_only_base_file(self, config_dir, isolated_env):
        config, files = make_loader(config_dir).init_app()

        assert config['server'] == {'host': 'file-host', 'port': 8080}
        assert {os.path.basename(f) for f in files} == {'application.yaml'}

    def test_priority_defaults_file_env_file_env_var_cmd(self, monkeypatch, config_dir):
        monkeypatch.setattr(os, 'environ', {'SERVER_PORT': '9000'})
        monkeypatch.setattr(
            ConfigLoader,
            'parse_cmd_args',
            staticmethod(lambda args=None: {'server': {'port': '9001'}}),
        )
        config, _ = make_loader(config_dir).init_app(
            {'server': {'timeout': 5}, 'pyre.config.env': 'dev'}
        )

        assert config['server']['timeout'] == 5  # 调用方默认值保留
        assert config['server']['host'] == 'file-host'  # 基础配置文件
        assert config['server']['port'] == '9001'  # 命令行参数优先级最高

    def test_env_file_overrides_base_file(self, config_dir, isolated_env):
        config, _ = make_loader(config_dir).init_app({'pyre.config.env': 'dev'})
        assert config['server']['port'] == 8081

    def test_env_variable_beats_env_file(self, monkeypatch, config_dir):
        monkeypatch.setattr(os, 'environ', {'SERVER_PORT': '9000'})
        config, _ = make_loader(config_dir).init_app({'pyre.config.env': 'dev'})
        assert config['server']['port'] == '9000'

    def test_defaults_survive_from_caller_dict(self, config_dir, isolated_env):
        config, _ = make_loader(config_dir).init_app({'server': {'timeout': 5}})
        assert config['server']['timeout'] == 5
        assert config['server']['port'] == 8080

    def test_does_not_mutate_caller_dict(self, config_dir, isolated_env):
        caller = {'pyre.config.env': 'dev'}
        make_loader(config_dir).init_app(caller)
        assert caller == {'pyre.config.env': 'dev'}

    def test_records_loaded_envs(self, config_dir, isolated_env):
        config, _ = make_loader(config_dir).init_app({'pyre.config.env': 'dev'})
        assert config['pyre']['config']['envs'] == 'dev'

    def test_chained_env_loading(self, tmp_path, isolated_env):
        directory = tmp_path / 'config'
        directory.mkdir()
        write(directory, 'application.yaml', 'pyre.config.env: base\n')
        write(directory, 'application-base.yaml', 'pyre.config.env: extra\nserver:\n  host: base\n')
        write(directory, 'application-extra.yaml', 'server:\n  port: 9999\n')

        config, files = make_loader(directory).init_app()

        assert config['server'] == {'host': 'base', 'port': 9999}
        assert {os.path.basename(f) for f in files} == {
            'application.yaml',
            'application-base.yaml',
            'application-extra.yaml',
        }

    def test_multiple_envs(self, tmp_path, isolated_env):
        directory = tmp_path / 'config'
        directory.mkdir()
        write(directory, 'application.yaml', 'a: 1\n')
        write(directory, 'application-dev.yaml', 'dev: true\n')
        write(directory, 'application-test.yaml', 'test: true\n')

        config, _ = make_loader(directory).init_app({'pyre.config.env': 'dev,test'})

        assert config['dev'] is True
        assert config['test'] is True

    def test_config_name_from_caller_dict(self, tmp_path, isolated_env):
        directory = tmp_path / 'config'
        directory.mkdir()
        write(directory, 'myapp.yaml', 'server:\n  port: 1\n')

        config, _ = make_loader(directory, name='other').init_app({'pyre.config.name': 'myapp'})
        assert config['server']['port'] == 1

    def test_location_option_replaces_locations(self, tmp_path, isolated_env):
        directory = tmp_path / 'elsewhere'
        directory.mkdir()
        write(directory, 'application.yaml', 'server:\n  port: 123\n')

        loader = ConfigLoader(scanner=ConfigScanner(config_locations=[], config_name='application'))
        config, files = loader.init_app({'pyre.config.location': str(directory)})

        assert config['server']['port'] == 123
        assert len(files) == 1

    def test_additional_option_extends_locations(self, tmp_path, isolated_env):
        first = tmp_path / 'a'
        second = tmp_path / 'b'
        first.mkdir()
        second.mkdir()

        loader = ConfigLoader(scanner=ConfigScanner(config_locations=[str(first)], config_name='application'))
        loader.init_app({'pyre.config.location': str(second), 'pyre.config.additional': True})

        assert loader.scanner.config_locations == [str(first), str(second)]

    def test_additional_option_disabled_replaces_locations(self, tmp_path, isolated_env):
        first = tmp_path / 'a'
        second = tmp_path / 'b'
        first.mkdir()
        second.mkdir()

        loader = ConfigLoader(scanner=ConfigScanner(config_locations=[str(first)], config_name='application'))
        loader.init_app({'pyre.config.location': str(second)})

        assert loader.scanner.config_locations == [str(second)]

    def test_location_pointing_to_file(self, tmp_path, isolated_env):
        directory = tmp_path / 'config'
        directory.mkdir()
        write(directory, 'application.yaml', 'server:\n  port: 7\n')

        loader = ConfigLoader(scanner=ConfigScanner(config_locations=[], config_name='application'))
        config, _ = loader.init_app({'pyre.config.location': str(directory / 'application.yaml')})

        assert config['server']['port'] == 7

    def test_empty_config_file_is_tolerated(self, tmp_path, isolated_env):
        directory = tmp_path / 'config'
        directory.mkdir()
        write(directory, 'application.yaml', '')

        config, _ = make_loader(directory).init_app()
        assert config == {}

    def test_unparsable_file_in_directory_is_skipped(self, tmp_path, isolated_env):
        directory = tmp_path / 'config'
        directory.mkdir()
        write(directory, 'application.yaml', 'a: 1\n')
        write(directory, 'application.txt', 'plain\n')

        config, _ = make_loader(directory).init_app()
        assert config == {'a': 1}

    def test_missing_directory_is_tolerated(self, tmp_path, isolated_env):
        loader = ConfigLoader(
            scanner=ConfigScanner(config_locations=[str(tmp_path / 'nope')], config_name='application')
        )
        config, files = loader.init_app()
        assert config == {} and files == []

    def test_returns_tuple(self, config_dir, isolated_env):
        result = make_loader(config_dir).init_app()
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], dict) and isinstance(result[1], list)

    def test_activates_loader(self, config_dir, isolated_env):
        from pyre_config import get_active_loader

        loader = make_loader(config_dir)
        loader.init_app()
        assert get_active_loader() is loader


class TestInitConfig:
    def test_build_model(self, config_dir, isolated_env):
        from pydantic import BaseModel

        class ServerConfig(BaseModel):
            host: str
            port: int

        class AppConfig(BaseModel):
            server: ServerConfig

        loader = make_loader(config_dir)
        loader.init_app()
        app_config = loader.init_config(AppConfig)

        assert app_config.server.host == 'file-host'
        assert app_config.server.port == 8080
