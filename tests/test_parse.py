import pytest

from pyre_config.parse import (
    ConfigParseMatch,
    ConfigParseNotSupported,
    JsonConfigParse,
    TomlConfigParse,
    YamlConfigParse,
)


class TestParsers:
    def test_yaml(self):
        assert YamlConfigParse().parse('server:\n  port: 8080\n') == {'server': {'port': 8080}}

    def test_yaml_empty_returns_dict(self):
        assert YamlConfigParse().parse('') == {}
        assert YamlConfigParse().parse('# only a comment\n') == {}

    def test_toml(self):
        parsed = TomlConfigParse().parse('[server]\nport = 8080\nhost = "0.0.0.0"\n')
        assert parsed == {'server': {'port': 8080, 'host': '0.0.0.0'}}

    def test_toml_empty_returns_dict(self):
        assert TomlConfigParse().parse('') == {}

    def test_json(self):
        assert JsonConfigParse().parse('{"server": {"port": 1}}') == {'server': {'port': 1}}


class TestConfigParseMatch:
    @pytest.mark.parametrize(
        'path,expected',
        [
            ('config/application.yaml', 'yaml'),
            ('config/application.yml', 'yml'),
            ('config/application.toml', 'toml'),
            ('config/application.json', 'json'),
            (r'C:\project\config\application.toml', 'toml'),
            ('https://example.com/application.yaml', 'yaml'),
            ('https://example.com/application.yaml?token=abc', 'yaml'),
            ('https://example.com/config/app.v2.yaml', 'yaml'),
            ('config/application', ''),
        ],
    )
    def test_get_extension(self, path, expected):
        assert ConfigParseMatch.get_extension(path) == expected

    def test_match_supported(self):
        assert isinstance(ConfigParseMatch.match('a.yaml'), YamlConfigParse)
        assert isinstance(ConfigParseMatch().match('a.toml'), TomlConfigParse)

    def test_match_unsupported_raises(self):
        with pytest.raises(ConfigParseNotSupported) as excinfo:
            ConfigParseMatch.match('a.ini')
        assert 'ini' in str(excinfo.value)

    def test_get_parser_returns_none(self):
        assert ConfigParseMatch.get_parser('a.ini') is None
        assert ConfigParseMatch.get_parser('no-extension') is None

    def test_config_parse_not_supported_is_config_parse_error(self):
        # 便于调用方统一按一种基类捕获
        from pyre_config.parse import ConfigParseError

        assert issubclass(ConfigParseNotSupported, ConfigParseError)
        with pytest.raises(ConfigParseError):
            ConfigParseMatch.match('a.ini')
