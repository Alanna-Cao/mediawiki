import unittest
from unittest.mock import patch
from wikipediaapi import LanguageManager

class TestWikipediaLanguages(unittest.TestCase):

    def test_language_enum_fetch(self):
        with patch("wikipediaapi.LanguageManager.fetch_supported_languages") as mock_fetch:
            mock_fetch.return_value = {'EN': 'English', 'ES': 'Spanish'}
            languages = LanguageManager.fetch_supported_languages()
            self.assertEqual(languages, {'EN': 'English', 'ES': 'Spanish'})

    def test_dynamic_language_enum_creation(self):
        language_data = {'EN': 'English', 'ES': 'Spanish'}
        dynamic_enum = LanguageManager.create_language_enum("DynamicLanguageEnum", language_data)
        self.assertEqual(dynamic_enum.EN.value, 'en')
        self.assertEqual(dynamic_enum.ES.value, 'es')

if __name__ == '__main__':
    unittest.main()
