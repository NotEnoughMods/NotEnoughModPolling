import unittest
import simplejson

from NEMP import NEMP_Class

# From http://stackoverflow.com/a/14902564/134960
def dict_raise_on_duplicates(ordered_pairs):
    """Reject duplicate keys."""
    d = {}
    for k, v in ordered_pairs:
        if k in d:
           raise ValueError("duplicate key: %r" % (k,))
        else:
           d[k] = v
    return d

class TestModsJson(unittest.TestCase):
    def setUp(self):
        self.NEM = NEMP_Class.NotEnoughClasses

        with open('NEMP/mods.json', 'r') as f:
            self.mods = simplejson.load(f, object_pairs_hook=dict_raise_on_duplicates)

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

    def test_forgejson_parser(self):
        for mod, mod_info in self.mods.iteritems():
            parser = mod_info['function']

            if parser != 'CheckForgeJson':
                continue

            msg = 'Mod {!r} has missing ForgeJson parser information'.format(mod)

            self.assertIn('forgejson', mod_info, msg=msg)
            self.assertIn('url', mod_info['forgejson'], msg=msg)
            self.assertIn('mcversion', mod_info['forgejson'], msg=msg)
