import unittest

from NEMP import NEMP_Class


class NotEnoughClassesMock(NEMP_Class.NotEnoughClasses):
    def __init__(self):
        self.mods = {
            "testmod": {
                "forgejson": {
                    "url": "testurl",
                    "mcversion": "1.8.9"
                }
            }
        }
        self.urls_data = {}

    def fetch_json(self, url):
        if url not in self.urls_data:
            raise RuntimeError("Invalid url")
        return self.urls_data[url]

    def set_url_json(self, url, data):
        self.urls_data[url] = data


class TestModsJson(unittest.TestCase):
    def setUp(self):
        self.nec = NotEnoughClassesMock()

    def test_forgejson_normal_version(self):
        self.nec.set_url_json("testurl", {
            "promos": {
                "1.8.9-recommended": "1.0.0"
            },
            "1.8.9": {
                "1.0.0": "test changelog"
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals("1.8.9", result["mc"])
        self.assertEquals("1.0.0", result["version"])
        self.assertNotIn("dev", result)
        self.assertEquals("test changelog", result["change"])

    def test_forgejson_dev_version(self):
        self.nec.set_url_json("testurl", {
            "promos": {
                "1.8.9-latest": "1.0.0"
            },
            "1.8.9": {
                "1.0.0": "test changelog"
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals("1.8.9", result["mc"])
        self.assertNotIn("version", result)
        self.assertEquals("1.0.0", result["dev"])
        self.assertEquals("test changelog", result["change"])

    def test_forgejson_both_versions_equal(self):
        self.nec.set_url_json("testurl", {
            "promos": {
                "1.8.9-latest": "1.0.0",
                "1.8.9-recommended": "1.0.0"
            },
            "1.8.9": {
                "1.0.0": "test changelog"
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals("1.8.9", result["mc"])
        self.assertEquals("1.0.0", result["version"])
        self.assertNotIn("dev", result)
        self.assertEquals("test changelog", result["change"])

    def test_forgejson_both_versions_different(self):
        self.nec.set_url_json("testurl", {
            "promos": {
                "1.8.9-latest": "1.0.1",
                "1.8.9-recommended": "1.0.0"
            },
            "1.8.9": {
                "1.0.0": "test changelog",
                "1.0.1": "other changelog"
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals("1.8.9", result["mc"])
        self.assertNotIn("version", result)
        self.assertEquals("1.0.1", result["dev"])
        self.assertEquals("other changelog", result["change"])

    def test_forgejson_no_changelog(self):
        self.nec.set_url_json("testurl", {
            "promos": {
                "1.8.9-recommended": "1.0.0"
            },
            "1.8.9": {
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals("1.8.9", result["mc"])
        self.assertEquals("1.0.0", result["version"])
        self.assertNotIn("dev", result)
        self.assertNotIn("change", result)

    def test_forgejson_no_mcversion_data(self):
        self.nec.set_url_json("testurl", {
            "promos": {
                "1.8.9-recommended": "1.0.0"
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals("1.8.9", result["mc"])
        self.assertEquals("1.0.0", result["version"])
        self.assertNotIn("dev", result)
        self.assertNotIn("change", result)

    def test_forgejson_no_promo_for_mcversion(self):
        self.nec.set_url_json("testurl", {
            "promos": {
                "1.8.8-recommended": "1.0.0"
            },
            "1.8.8": {
                "1.0.0": "test changelog"
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals({}, result)

    def test_forgejson_no_promos(self):
        self.nec.set_url_json("testurl", {
            "1.8.9": {
                "1.0.0": "test changelog"
            }
        })

        result = self.nec.CheckForgeJson("testmod")

        self.assertEquals({}, result)
