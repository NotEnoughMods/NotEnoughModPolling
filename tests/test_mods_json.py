import unittest
import simplejson

from NEMP import NEMP_Class

class TestModsJson(unittest.TestCase):
    def setUp(self):
        self.NEM = NEMP_Class.NotEnoughClasses

        with open('NEMP/mods.json', 'r') as f:
            self.mods = simplejson.load(f)

    def test_parsers_exist(self):
        for mod, mod_info in self.mods.iteritems():
            parser = mod_info['function']
            self.assertTrue(parser.startswith('Check'), msg="Parser name {!r} for mod {!r} is invalid".format(parser, mod))
            self.assertTrue(hasattr(self.NEM, parser), msg="Parser {!r} for mod {!r} doesn't exist".format(parser, mod))

    def test_curse_parser(self):
        for mod, mod_info in self.mods.iteritems():
            parser = mod_info['function']

            if parser != 'CheckCurse':
                continue

            msg = 'Mod {!r} has missing Curse parser information'.format(mod)

            self.assertIn('curse', mod_info, msg=msg)
            self.assertIn('regex', mod_info['curse'], msg=msg)
