"""演示配置优先级：默认值 < 基础配置文件 < 环境配置文件 < 环境变量 < 命令行参数。

在仓库根目录执行：``python examples/priority.py``
再叠加命令行参数验证最高优先级：``python examples/priority.py --server.port 9001``
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyre_config import ConfigLoader, ConfigScanner  # noqa: E402

# 清掉宿主机上已有的 SERVER_*/PYRE_* 变量，保证示例输出稳定可复现
for _key in [key for key in os.environ if key.startswith(('SERVER_', 'PYRE_'))]:
    del os.environ[_key]

# 第 4 优先级：环境变量（SERVER_PORT -> server.port）
os.environ['SERVER_PORT'] = '9000'

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'priority_config')

if __name__ == '__main__':
    print('输入：')
    print('  调用方默认值          server.timeout=5')
    print('  application.yaml      server.host=file-host  server.port=8080')
    print('  application-dev.yaml  server.port=8081')
    print('  环境变量              SERVER_PORT=9000')
    print('  命令行参数            ', sys.argv[1:] or '（无）')
    print()

    loader = ConfigLoader(scanner=ConfigScanner(config_locations=[CONFIG_DIR], config_name='application'))
    config_dict, files = loader.init_app({
        'server': {'timeout': 5},
        'pyre.config.env': 'dev',
    })

    print('生效结果：')
    print('  server.host    =', config_dict['server']['host'], '（来自基础配置）')
    print('  server.port    =', repr(config_dict['server']['port']), '（环境变量 / 命令行）')
    print('  server.timeout =', config_dict['server']['timeout'], '（调用方默认值）')
    print('  pyre.config.envs =', config_dict['pyre']['config']['envs'])
    print()
    print('加载文件：', [os.path.basename(path) for path in files])
