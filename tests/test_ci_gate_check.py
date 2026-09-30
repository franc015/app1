import unittest


class CiGateCheck(unittest.TestCase):
    def test_intentional_failure(self):
        # Temporary test to verify that failing checks block merging into main.
        self.fail("intentional failure to verify the required status checks rule")
