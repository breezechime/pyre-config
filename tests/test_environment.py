from pyre_config import Environment


class TestEnvironment:
    def test_get_env_strings(self):
        assert Environment('dev,test', 'dev').get_env_strings() == ['dev', 'test']

    def test_get_env_strings_ignores_blanks(self):
        assert Environment('dev,, test ,', 'dev').get_env_strings() == ['dev', 'test']

    def test_none_values(self):
        environment = Environment(None, None)
        assert environment.env == ''
        assert environment.envs == ''
        assert environment.get_env_strings() == []
        assert environment.is_dev() is False

    def test_is_dev(self):
        assert Environment('dev', 'dev').is_dev() is True
        assert Environment('prod', 'prod').is_dev() is False

    def test_is_prod(self):
        assert Environment('prod', 'prod').is_prod() is True
        assert Environment('dev', 'dev').is_prod() is False

    def test_is_test(self):
        assert Environment('test', 'test').is_test() is True

    def test_is_env(self):
        assert Environment('dev,test', 'dev').is_env('test') is True
        assert Environment('dev', 'dev').is_env('prod') is False

    def test_config_dict_default(self):
        assert Environment('dev', 'dev').config_dict == {}
        assert Environment('dev', 'dev', {'a': 1}).config_dict == {'a': 1}
        assert Environment('dev', 'dev', None, 'app').app_config == 'app'

    def test_repr(self):
        assert "env='dev'" in repr(Environment('dev', 'dev'))
