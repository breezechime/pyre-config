from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pyre-config',
    version='1.0.0',
    author='且听风吟、我是指针*、ZDLAY、KYZ',
    author_email='breezechime@163.com',
    description='轻量级 Python 配置管理库：多配置源、多环境、优先级覆盖，核心零依赖',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/breezechime/pyre-config',
    project_urls={
        'Source': 'https://github.com/breezechime/pyre-config',
        'Issues': 'https://github.com/breezechime/pyre-config/issues',
    },
    license='MIT',
    packages=find_packages(exclude=('tests', 'tests.*', 'examples', 'examples.*')),
    package_data={'pyre_config': ['py.typed']},
    include_package_data=True,
    python_requires='>=3.9',
    install_requires=[],
    extras_require={
        'yaml': ['pyyaml'],
        'toml': ['toml; python_version < "3.11"'],
        'json': [],
        'url': ['requests'],
        'pydantic': ['pydantic>=2'],
        'all': ['pyyaml', 'toml; python_version < "3.11"', 'requests', 'pydantic>=2'],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Software Distribution',
    ],
    keywords='config configuration yaml toml json environment-variables dotenv twelve-factor pydantic',
)
