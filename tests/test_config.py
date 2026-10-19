import sys

import pytest

from pyre_config import FileConfig, UrlConfig


class FakeResponse:
    def __init__(self, text, content_type='text/plain', payload=None):
        self.text = text
        self.content = text.encode('utf-8')
        self.encoding = None
        self.headers = {} if content_type is None else {'Content-Type': content_type}
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeRequests:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append({'url': url, 'timeout': timeout})
        return self.response


@pytest.fixture
def fake_requests(monkeypatch):
    def install(response):
        module = FakeRequests(response)
        monkeypatch.setitem(sys.modules, 'requests', module)
        return module

    return install


class TestFileConfig:
    def test_get_dict(self, tmp_path):
        path = tmp_path / 'application.yaml'
        path.write_text('server:\n  port: 8080\n', encoding='utf-8')
        assert FileConfig(str(path)).get_dict() == {'server': {'port': 8080}}

    def test_get_text_is_idempotent(self, tmp_path):
        path = tmp_path / 'application.yaml'
        path.write_text('server:\n  port: 8080\n', encoding='utf-8')
        config = FileConfig(str(path))
        assert config.get_text() == config.get_text()

    def test_get_dict_twice(self, tmp_path):
        path = tmp_path / 'application.toml'
        path.write_text('[server]\nport = 8080\n', encoding='utf-8')
        config = FileConfig(str(path))
        assert config.get_dict() == config.get_dict() == {'server': {'port': 8080}}

    def test_get_content(self, tmp_path):
        path = tmp_path / 'application.yaml'
        path.write_bytes(b'a: 1\n')
        assert FileConfig(str(path)).get_content() == b'a: 1\n'

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            FileConfig(str(tmp_path / 'nope.yaml')).get_text()

    def test_unsupported_extension_raises(self, tmp_path):
        from pyre_config import ConfigParseNotSupported

        path = tmp_path / 'application.ini'
        path.write_text('a=1\n', encoding='utf-8')
        with pytest.raises(ConfigParseNotSupported):
            FileConfig(str(path)).get_dict()


class TestUrlConfig:
    def test_get_text(self, fake_requests):
        fake_requests(FakeResponse('server:\n  port: 8080\n'))
        assert UrlConfig('https://example.com/application.yaml').get_text() == 'server:\n  port: 8080\n'

    def test_get_content(self, fake_requests):
        fake_requests(FakeResponse('a: 1\n'))
        assert UrlConfig('https://example.com/application.yaml').get_content() == b'a: 1\n'

    def test_get_dict_json_content_type(self, fake_requests):
        fake_requests(FakeResponse('{}', content_type='application/json; charset=utf-8', payload={'a': 1}))
        assert UrlConfig('https://example.com/api').get_dict() == {'a': 1}

    def test_get_dict_missing_content_type(self, fake_requests):
        """Content-Type 缺失时不能抛 TypeError，应回退到按扩展名解析。"""
        fake_requests(FakeResponse('server:\n  port: 8080\n', content_type=None))
        assert UrlConfig('https://example.com/application.yaml').get_dict() == {'server': {'port': 8080}}

    def test_timeout_is_forwarded(self, fake_requests):
        module = fake_requests(FakeResponse('a: 1\n'))
        UrlConfig('https://example.com/application.yaml', timeout=3).get_text()
        assert module.calls[0]['timeout'] == 3

    def test_is_open_is_false(self):
        assert UrlConfig('https://example.com/application.yaml').is_open is False
