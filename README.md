# pyre-config

<p>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/format-YAML%20%7C%20TOML%20%7C%20JSON-8a2be2" alt="Formats">
</p>

轻量级 Python 配置管理库：多配置源、多环境、优先级覆盖与类型化访问。
**核心零依赖**（仅标准库），YAML / TOML / Pydantic / URL 按需接入。

## ✨ 特点

- 🚀 **轻量** — 核心只用标准库，安装即用，不把整个解析生态拖进项目。
- 🎯 **多配置源** — 本地文件与 URL（`http://` / `https://`）统一抽象，同一套 API 读取。
- 🗂 **多格式** — YAML、TOML、JSON，按扩展名自动匹配解析器。
- 🌍 **多环境** — `application-dev.yaml` 这类环境文件，支持逗号分隔多环境与链式加载。
- 🔀 **优先级覆盖** — 默认值 → 基础配置 → 环境配置 → 环境变量 → 命令行参数，逐层合并。
- 🌱 **环境变量映射** — `PYRE_` / `SERVER_` 前缀自动展开成配置键路径。
- ⌨️ **命令行覆盖** — 支持 `--key value` 与 `--key=value` 两种写法。
- 🧬 **类型化配置** — 一行 `init_config(BaseModel)` 得到带校验的配置对象。
- 💉 **注入装饰器** — `configuration_values` / `configuration_source` 把配置直接注入类实例。
- 📦 **零必需依赖** — YAML、TOML、requests、Pydantic 全部可选，不装也能跑。

## 📦 安装

```bash
pip install pyre-config
```

按需安装可选依赖：

```bash
pip install "pyre-config[yaml]"       # pyyaml
pip install "pyre-config[toml]"       # Python < 3.11 才需要（3.11+ 用标准库 tomllib）
pip install "pyre-config[url]"        # requests
pip install "pyre-config[pydantic]"   # pydantic>=2
pip install "pyre-config[all]"
```

## 💡 一个简单的例子

```python
from pyre_config import ConfigLoader

loader = ConfigLoader()

# 扫描 ./config、./resource 下的 application.yaml / application.toml
config, files = loader.init_app({'pyre.config.env': 'dev'})

print(config['server']['host'])   # 0.0.0.0
print(config['server']['port'])   # 8006
print(files)                      # 实际加载的文件列表
```

## 👩‍💻 目录结构

```text
pyre-config
├── pyre_config
│   ├── __init__.py      # 对外导出
│   ├── config.py        # 配置源：FileConfig / UrlConfig
│   ├── parse.py         # 格式匹配与解析器
│   ├── scanner.py       # 目录扫描与文件名匹配
│   ├── loader.py        # 加载器：合并、优先级、环境链
│   ├── environment.py   # 环境描述对象
│   ├── decorators.py    # 注入装饰器
│   ├── globals.py       # 激活实例
│   └── utils.py         # 点号路径读写
├── examples/            # 可运行示例
├── tests/               # 单元测试
└── setup.py
```

## 🚀 快速开始

### 目录约定

```
project/
├── config/
│   ├── application.yaml       # 基础配置
│   └── application-dev.yaml   # 环境配置
└── main.py
```

```yaml
# config/application.yaml
server:
  host: 0.0.0.0
  port: 8006

pyre:
  config:
    env: dev
```

```python
from pyre_config import ConfigLoader

loader = ConfigLoader()
config, files = loader.init_app()

print(config['server']['host'])   # 0.0.0.0
print(config['pyre']['config']['envs'])   # dev（实际生效的环境链）
print(files)   # ['.../config/application.yaml', '.../config/application-dev.yaml']
```

### 类型化配置模型

```python
from pydantic import BaseModel
from pyre_config import ConfigLoader


class ServerConfig(BaseModel):
    host: str = '127.0.0.1'
    port: int = 8080


class AppConfig(BaseModel):
    server: ServerConfig


loader = ConfigLoader()
loader.init_app()

app_config = loader.init_config(AppConfig)
app_config.server.port   # 8006，且已完成类型校验
```

## 🗂 配置源

### 文件

```python
from pyre_config import FileConfig

FileConfig('./config/application.yaml').get_dict()   # 解析为 dict
FileConfig('./config/application.toml', encoding='utf-8').get_text()
```

### URL

```python
from pyre_config import UrlConfig

UrlConfig('https://example.com/application.yaml').get_dict()
```

响应 `Content-Type` 含 `json` 时直接按 JSON 解析，否则按 URL 扩展名匹配解析器。

### 支持格式

| 扩展名 | 解析器 | 依赖 |
| --- | --- | --- |
| `.yaml` / `.yml` | YAML | `pyyaml` |
| `.toml` | TOML | Python ≥ 3.11 内置 `tomllib`，低版本需 `toml` |
| `.json` | JSON | 标准库 |

其它扩展名不会被扫描，直接解析会抛 `ConfigParseNotSupported`。

## 🔀 优先级

从低到高依次覆盖：

| 顺序 | 来源 | 说明 |
| --- | --- | --- |
| 1 | 调用方默认值 | `init_app(config_dict)` 传入的字典 |
| 2 | 基础配置文件 | `{config_name}.{ext}` |
| 3 | 环境配置文件 | `{config_name}-{env}.{ext}` |
| 4 | 环境变量 | `PYRE_*` / `SERVER_*` |
| 5 | 命令行参数 | `--key value` |

字典类型递归合并，其余类型直接覆盖：

```python
loader.safe_merge_config_dict({'a': {'y': 3, 'z': 4}}, {'a': {'x': 1, 'y': 2}})
# {'a': {'x': 1, 'y': 3, 'z': 4}}   —— 不修改入参
```

## 📁 配置文件约定

`ConfigScanner` 在 `config_locations` 中查找**文件名包含 `config_name`** 的文件：

- 默认扫描目录：`./config`、`./resource`、`/config`、`/resource`
- 默认配置名：`application`
- 扫描结果按文件名排序，保证加载顺序稳定
- 同名文件（不同目录）以**位置靠前**的目录为准
- 目录会跳过；不存在的目录会跳过；扩展名不支持的会跳过

```python
from pyre_config import ConfigScanner

scanner = ConfigScanner(config_locations=['./conf'], config_name='myapp')
scanner.scanner()   # {'myapp.yaml': './conf/myapp.yaml', ...}
```

## 🌱 环境变量

前缀 `PYRE_` / `SERVER_` 会被保留为键路径的第一段，下划线 `_` 视为层级分隔符：

| 环境变量 | 结果 |
| --- | --- |
| `SERVER_HOST=0.0.0.0` | `server.host` |
| `PYRE_DATASOURCE_URL=...` | `pyre.datasource.url` |
| `PYRE_DATASOURCE_POOL_SIZE=20` | `pyre.datasource.pool.size` |

> **注意**：既然 `_` 是层级分隔符，键名本身不能包含下划线。
> `pool_size`、`secret_key` 这类键请写在配置文件里，或用带别名的配置模型承接。
> 连续下划线（如 `SERVER__HOST`）会被折叠，不会产生空键。

前缀本身会成为键的第一段，因此默认前缀天然对应两套命名空间：

```yaml
server:
  port: 8006        # 由 SERVER_PORT 覆盖
pyre:
  datasource:
    url: ...        # 由 PYRE_DATASOURCE_URL 覆盖
```

修改前缀：

```python
ConfigLoader.ENV_VAR_PREFIXS = ['MYAPP_']   # 之后 MYAPP_SERVER_PORT -> myapp.server.port
```

## ⌨️ 命令行参数

```bash
python main.py --pyre.config.env=dev
python main.py --server.port 9000 --server.host 0.0.0.0
```

```python
from pyre_config import ConfigLoader

ConfigLoader.parse_cmd_args(['--server.port', '9000'])      # {'server': {'port': '9000'}}
ConfigLoader.parse_cmd_args(['--server.port=9000'])         # {'server': {'port': '9000'}}
ConfigLoader.parse_cmd_args(['--debug'])                    # {'debug': None}
```

无值写法（`--debug`）得到 `None`；紧跟另一个 `--` 开头的参数时不会误吃为值。

## 🎛 控制项

| 配置键 | 说明 |
| --- | --- |
| `pyre.config.location` | 配置文件或目录，逗号分隔；目录会替换扫描位置，文件会被直接加载 |
| `pyre.config.name` | 配置文件名（不含扩展名），默认 `application` |
| `pyre.config.additional` | 为真时把 `location` 目录**追加**到默认扫描位置，而不是替换 |
| `pyre.config.env` | 环境名，逗号分隔多个，如 `dev,test` |
| `pyre.config.envs` | 由库写入，记录最终生效的环境链 |

这四个键可以来自调用方字典、环境变量或命令行参数，会在扫描前解析：

```python
loader = ConfigLoader()
loader.init_app({
    'pyre.config.location': './conf',
    'pyre.config.name': 'myapp',
    'pyre.config.env': 'dev,test',
})
```

### 环境文件链式加载

环境文件里可以继续声明 `pyre.config.env`，实现叠加加载：

```yaml
# application.yaml
pyre:
  config:
    env: base
```

```yaml
# application-base.yaml
pyre:
  config:
    env: extra   # 声明后继续加载 application-extra.yaml
server:
  host: base
```

加载顺序为 `application` → `application-base` → `application-extra`，环境名会去重后写入 `pyre.config.envs`。

## 🧬 配置模型与装饰器

### init_config

```python
app_config = loader.init_config(AppConfig)   # 等价于 AppConfig(**loader.config_dict)
```

### configuration_values

把当前**已激活**的配置加载器中的值注入类实例：

```python
from pyre_config import configuration_values


@configuration_values(prefix='server', config_key='raw')
class ServerService:
    host: str          # 以类注解声明要注入的属性

    def __init__(self):
        print(self.host)   # 0.0.0.0
        print(self.raw)    # {'host': '0.0.0.0', 'port': 8006}
```

- `prefix`：只取配置中的某个子树。
- `config_key`：额外把原始子树挂到指定属性上。
- Pydantic 模型 / dataclass 走构造参数注入（因此会触发校验），普通类只注入**已声明**的属性。
- 未激活加载器时静默不注入；`prefix` 指向非字典值会抛 `TypeError`。

### configuration_source

直接从指定文件（或 URL）注入，不依赖加载器：

```python
from pyre_config import configuration_source


@configuration_source('./config/db.yaml', prefix='database')
class DatabaseService:
    url: str
```

### configuration

在类上打标记，便于自己扩展：

```python
from pyre_config import configuration

@configuration
class AppConfig:
    ...
```

## 🧰 工具函数

点号路径访问嵌套字典，支持列表下标：

```python
from pyre_config import getter_dict, setter_dict

data = {'items': [{'name': 'Item 1'}]}
getter_dict(data, 'items.0.name')          # 'Item 1'
getter_dict(data, 'items.9.name', 'none')  # 'none'

setter_dict(data, 'items.0.price', 9.9)
# {'items': [{'name': 'Item 1', 'price': 9.9}]}
```

- `getter_dict` 查找失败返回 `default`；`raise_error=True` 时抛出原始异常。
- `getter_dict` 兼容扁平的 `"a.b.c"` 键写法。
- `setter_dict` 会自动创建中间字典与列表，路径非法时抛 `ValueError` / `TypeError`。

顶层的扁平键也可以交给 loader 自动展开：

```python
from pyre_config.utils import expand_dotted_keys

expand_dotted_keys({'pyre.config.env': 'dev'})
# {'pyre': {'config': {'env': 'dev'}}}
```

## 🧭 运行环境

`Environment` 描述当前生效的环境链，常由框架或应用自行构造后注入容器：

```python
from pyre_config import Environment

environment = Environment('dev,test', 'dev', config_dict, app_config)
environment.is_dev()          # True
environment.is_prod()         # False
environment.get_env_strings() # ['dev', 'test']
```

## 🔌 与 Web 框架集成

`pyre-config` 不依赖任何 Web 框架。在框架侧只需三步：

1. 构造 `ConfigLoader`（可选自定义 `ConfigScanner`）；
2. 调用 `init_app(config_dict)`，拿到 `(config_dict, config_file_paths)`；
3. 用 `init_config(AppConfig)` 得到类型化配置，用 `Environment(...)` 得到环境对象。

`init_app()` 会顺带把当前加载器登记为「激活实例」，此后 `configuration_values` 装饰器即可直接取用。

## 📖 API 参考

| 名称 | 说明 |
| --- | --- |
| `ConfigLoader` | 加载器。`init_app` / `init_config` / `load_config` / `merge_config_dict` / `safe_merge_config_dict` / `parse_cmd_args` / `parse_environment_variables` / `apply_location` / `active` |
| `ConfigScanner` | 扫描器。`scanner()` / `exists()` / `match_name()` |
| `Config` / `FileConfig` / `UrlConfig` | 配置源。`get_text()` / `get_content()` / `get_dict()` |
| `ConfigParseMatch` | `match()` / `get_parser()` / `get_extension()` |
| `ConfigParseError` / `ConfigParseNotSupported` | 解析异常 |
| `Environment` | 环境描述 |
| `getter_dict` / `setter_dict` / `expand_dotted_keys` | 字典路径工具 |
| `configuration` / `configuration_values` / `configuration_source` | 注入装饰器 |
| `get_active_loader` | 取当前激活的加载器 |

## 🛠 开发

```bash
pip install -e ".[all]" pytest
pytest tests -q
```

## 📄 许可

本项目基于 [MIT](LICENSE) 许可开源。
