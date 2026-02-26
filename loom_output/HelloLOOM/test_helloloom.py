import unittest
from helloloom import is_prime
class T(unittest.TestCase):
    def test_p(self):
        self.assertTrue(is_prime(13)); self.assertFalse(is_prime(21))
if __name__=='__main__':unittest.main()
