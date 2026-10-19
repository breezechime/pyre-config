import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_config import ConfigLoader  # noqa: E402


@pytest.fixture
def isolated_env(monkeypatch):
    """隔离环境变量，避免宿主机上的 SERVER_* / PYRE_* 干扰断言。"""
    monkeypatch.setattr(ConfigLoader, 'ENV_VAR_PREFIXS', ['PRYECFG_'])
    return monkeypatch


@pytest.fixture
def config_dir(tmp_path):
    """构造一个包含基础配置与环境配置的目录。"""
    directory = tmp_path / 'config'
    directory.mkdir()
    (directory / 'application.yaml').write_text(
        'server:\n  host: file-host\n  port: 8080\n', encoding='utf-8'
    )
    (directory / 'application-dev.yaml').write_text('server:\n  port: 8081\n', encoding='utf-8')
    return directory
