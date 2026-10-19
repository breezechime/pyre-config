"""最小可用示例：加载配置目录中的文件，并转成带校验的 Pydantic 模型。

在仓库根目录执行：``python examples/basic.py``
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel  # noqa: E402

from pyre_config import ConfigLoader  # noqa: E402

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')

# 为保证示例输出可复现，先清掉宿主机上的 SERVER_*/PYRE_* 变量。
# 实际项目中这些环境变量会参与覆盖（见 examples/priority.py）。
for _key in [key for key in os.environ if key.startswith(('SERVER_', 'PYRE_'))]:
    del os.environ[_key]


class AppSection(BaseModel):
    name: str
    debug: bool = False


class LoggingSection(BaseModel):
    level: str = 'INFO'
    format: str = '%(message)s'


class AppConfig(BaseModel):
    app: AppSection
    logging: LoggingSection


def main():
    loader = ConfigLoader()

    # 用 pyre.config.location 指向示例配置目录，避免依赖当前工作目录
    config_dict, config_files = loader.init_app({'pyre.config.location': CONFIG_DIR})

    print('--- 配置字典 ---')
    print(config_dict)

    print('\n--- 已加载的配置文件 ---')
    for path in config_files:
        print(' ', os.path.basename(path))

    print('\n--- 类型化配置模型 ---')
    app_config = loader.init_config(AppConfig)
    print('app.name     =', app_config.app.name)
    print('app.debug    =', app_config.app.debug)
    print('logging.level=', app_config.logging.level)


if __name__ == '__main__':
    main()
