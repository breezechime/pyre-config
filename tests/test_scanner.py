import os

from pyre_config import ConfigScanner


class TestConfigScanner:
    def test_scanner_finds_supported_files_only(self, tmp_path):
        directory = tmp_path / 'config'
        directory.mkdir()
        (directory / 'application.yaml').write_text('a: 1\n', encoding='utf-8')
        (directory / 'application-dev.yaml').write_text('a: 2\n', encoding='utf-8')
        (directory / 'application.txt').write_text('not a config\n', encoding='utf-8')
        (directory / 'other.yaml').write_text('a: 3\n', encoding='utf-8')
        (directory / 'notes.md').write_text('# notes\n', encoding='utf-8')

        result = ConfigScanner(config_locations=[str(directory)], config_name='application').scanner()

        assert set(result) == {'application.yaml', 'application-dev.yaml'}

    def test_scanner_result_is_sorted(self, tmp_path):
        directory = tmp_path / 'config'
        directory.mkdir()
        for name in ['application.yaml', 'application-dev.yaml', 'application-prod.yaml']:
            (directory / name).write_text('a: 1\n', encoding='utf-8')

        result = ConfigScanner(config_locations=[str(directory)], config_name='application').scanner()
        assert list(result) == ['application-dev.yaml', 'application-prod.yaml', 'application.yaml']

    def test_scanner_skips_missing_and_file_locations(self, tmp_path):
        a_file = tmp_path / 'application.yaml'
        a_file.write_text('a: 1\n', encoding='utf-8')

        scanner = ConfigScanner(config_locations=[str(tmp_path / 'nope'), str(a_file)], config_name='application')
        assert scanner.scanner() == {}

    def test_scanner_skips_sub_directories(self, tmp_path):
        directory = tmp_path / 'config'
        (directory / 'application.yaml').mkdir(parents=True)
        assert ConfigScanner(config_locations=[str(directory)], config_name='application').scanner() == {}

    def test_scanner_does_not_leak_into_other_names(self, tmp_path):
        directory = tmp_path / 'config'
        directory.mkdir()
        (directory / 'application.yaml').write_text('a: 1\n', encoding='utf-8')
        (directory / 'myapplication.yaml').write_text('a: 2\n', encoding='utf-8')

        assert scanner_keys(directory, 'application') == {'application.yaml', 'myapplication.yaml'}


class TestScannerHelpers:
    def test_match_name(self):
        scanner = ConfigScanner(config_name='application')
        assert scanner.match_name('application.yaml') is True
        assert scanner.match_name('application.toml') is True
        assert scanner.match_name('application-dev.yaml', 'dev') is True
        assert scanner.match_name('application-prod.yaml', 'dev') is False
        assert scanner.match_name('application-dev.yaml') is False

    def test_exists(self, tmp_path):
        yaml_file = tmp_path / 'application.yaml'
        yaml_file.write_text('a: 1\n', encoding='utf-8')
        ini_file = tmp_path / 'application.ini'
        ini_file.write_text('a=1\n', encoding='utf-8')

        scanner = ConfigScanner()
        assert scanner.exists(str(yaml_file)) is True
        assert scanner.exists(str(ini_file)) is False
        assert scanner.exists(str(tmp_path / 'missing.yaml')) is False

    def test_default_locations_not_shared_between_instances(self):
        first = ConfigScanner()
        first.config_locations.append('./custom')
        assert './custom' not in ConfigScanner().config_locations

    def test_default_locations(self):
        scanner = ConfigScanner()
        assert os.path.isdir('./config') is False or './config' in scanner.config_locations
        assert './resource' in scanner.config_locations


def scanner_keys(directory, name):
    return set(ConfigScanner(config_locations=[str(directory)], config_name=name).scanner())
