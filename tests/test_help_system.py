import pytest

from help_system import HelpEntity, HelpModule


class TestHelpEntity:
    def test_add_description(self):
        entity = HelpEntity("test")
        entity.add_description("A test command")
        assert entity.description == ["A test command"]

    def test_add_description_wrong_type(self):
        entity = HelpEntity("test")
        with pytest.raises(TypeError):
            entity.add_description(123)

    def test_add_argument(self):
        entity = HelpEntity("test")
        entity.add_argument("name", "The name to use")
        assert entity.arguments == [("name", "The name to use", False)]

    def test_add_argument_optional(self):
        entity = HelpEntity("test")
        entity.add_argument("flag", "An optional flag", optional=True)
        assert entity.arguments == [("flag", "An optional flag", True)]

    def test_add_argument_no_description(self):
        entity = HelpEntity("test")
        entity.add_argument("name")
        assert entity.arguments == [("name", None, False)]

    def test_add_argument_wrong_type(self):
        entity = HelpEntity("test")
        with pytest.raises(TypeError):
            entity.add_argument(123)

    def test_add_argument_wrong_description_type(self):
        entity = HelpEntity("test")
        with pytest.raises(TypeError):
            entity.add_argument("name", 42)

    def test_set_custom_handler(self):
        entity = HelpEntity("test")

        def handler(self, *args):
            pass

        entity.set_custom_handler(handler)
        assert entity.custom_handler is handler

    def test_set_custom_handler_not_callable(self):
        entity = HelpEntity("test")
        with pytest.raises(TypeError):
            entity.set_custom_handler("not a function")


class TestHelpModule:
    def test_new_help(self):
        module = HelpModule()
        entity = module.new_help("test")
        assert isinstance(entity, HelpEntity)
        assert entity.cmdname == "test"

    def test_register_help(self):
        module = HelpModule()
        entity = module.new_help("test")
        module.register_help(entity)
        assert module.get_command_help("test") is entity

    def test_register_help_duplicate_raises(self):
        module = HelpModule()
        entity = module.new_help("test")
        module.register_help(entity)
        with pytest.raises(RuntimeError):
            module.register_help(entity)

    def test_register_help_overwrite(self):
        module = HelpModule()
        entity1 = module.new_help("test")
        entity1.add_description("first")
        module.register_help(entity1)

        entity2 = module.new_help("test")
        entity2.add_description("second")
        module.register_help(entity2, overwrite=True)

        assert module.get_command_help("test").description == ["second"]

    def test_register_help_wrong_type(self):
        module = HelpModule()
        with pytest.raises(TypeError):
            module.register_help("not an entity")

    def test_unregister_help(self):
        module = HelpModule()
        entity = module.new_help("test")
        module.register_help(entity)
        module.unregister_help("test")
        with pytest.raises(KeyError):
            module.get_command_help("test")

    def test_get_command_help_missing(self):
        module = HelpModule()
        with pytest.raises(KeyError):
            module.get_command_help("nonexistent")
