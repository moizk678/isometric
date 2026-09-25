import unittest

from isometric_api import __version__


class ApiSmokeTest(unittest.TestCase):
    def test_import(self):
        self.assertEqual(__version__, "0.0.0")
