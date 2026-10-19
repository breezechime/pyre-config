"""核心功能不应依赖 yaml / toml / pydantic / requests 等可选依赖。"""
import os
import subprocess
import sys
import textwrap

PACKAGE_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLOCK_AND_RUN = textwrap.dedent(
    """
    import sys

    BLOCKED = {'yaml', 'toml', 'tomllib', 'pydantic', 'requests'}

    class Blocker:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in BLOCKED:
                raise ImportError('blocked optional dependency: ' + fullname)
            return None

    sys.meta_path.insert(0, Blocker())
    sys.path.insert(0, __PATH__)

    import pyre_config
    from pyre_config import ConfigLoader, ConfigScanner, getter_dict, setter_dict

    assert setter_dict({}, 'a.b', 1) == {'a': {'b': 1}}
    assert getter_dict({'a': {'b': 1}}, 'a.b') == 1

    scanner = ConfigScanner(config_locations=[], config_name='application')
    config, files = ConfigLoader(scanner=scanner).init_app({'server': {'port': 1}})
    assert config == {'server': {'port': 1}}, config
    assert files == []

    print('OK')
    """
).replace('__PATH__', repr(PACKAGE_PARENT))


def test_core_works_without_optional_dependencies():
    # 剔除宿主机上可能存在的 SERVER_*/PYRE_* 变量，避免污染断言
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(('SERVER_', 'PYRE_', 'PRYECFG_'))
    }
    env['PYTHONPATH'] = PACKAGE_PARENT

    result = subprocess.run(
        [sys.executable, '-c', BLOCK_AND_RUN],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert 'OK' in result.stdout
