"""演示三种注入装饰器。

在仓库根目录执行：``python examples/decorators.py``
"""

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_config import (  # noqa: E402
    ConfigLoader,
    ConfigScanner,
    configuration,
    configuration_source,
    configuration_values,
)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'priority_config')

# 清掉宿主机上已有的 SERVER_*/PYRE_* 变量，保证示例输出稳定可复现
for _key in [key for key in os.environ if key.startswith(('SERVER_', 'PYRE_'))]:
    del os.environ[_key]


@configuration_values(prefix='server')
@dataclass
class ServerConfig:
    """dataclass / Pydantic 模型走构造参数注入，因此会触发类型校验。"""

    host: str = 'localhost'
    port: int = 80


@configuration_values(prefix='server', config_key='raw')
class ServerService:
    """普通类只注入「已声明」的属性，未声明的键不会污染实例。"""

    host: str

    def __init__(self):
        self.started = True


@configuration_source(os.path.join(CONFIG_DIR, 'application.yaml'), prefix='server')
class StandaloneService:
    """不依赖加载器，直接从指定文件读取。"""

    host: str


@configuration
class Marker:
    """configuration 只是打标记，便于自行扩展。"""


if __name__ == '__main__':
    # 激活加载器后，configuration_values 才能取到配置
    loader = ConfigLoader(scanner=ConfigScanner(config_locations=[CONFIG_DIR], config_name='application'))
    loader.init_app({'pyre.config.env': 'dev'})

    server_config = ServerConfig()
    print('--- configuration_values + dataclass ---')
    print('  host =', server_config.host, ' port =', server_config.port)

    service = ServerService()
    print('--- configuration_values + 普通类 ---')
    print('  host =', service.host)
    print('  raw  =', service.raw)
    print('  started =', service.started)

    standalone = StandaloneService()
    print('--- configuration_source ---')
    print('  host =', standalone.host)
    print('  Marker 已标记 =', getattr(Marker, '__configuration__', False))