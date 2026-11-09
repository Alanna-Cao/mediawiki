import unittest
from unittest.mock import patch, MagicMock
from wikipediaapi import WikipediaClient, WikipediaPage, PageNotFoundError, LanguageManager


class TestErrorHandling(unittest.TestCase):

    def setUp(self):
        self.client = WikipediaClient(user_agent="TestApp/1.0", language=LanguageManager.Language.EN)
        self.page = WikipediaPage(title="Test Page", wiki=self.client)

    @patch("wikipediaapi.LanguageManager.fetch_supported_languages")
    def test_language_fetch_error(self, mock_fetch_languages):
        mock_fetch_languages.side_effect = ConnectionError("Failed to fetch supported languages")
        with self.assertRaises(ConnectionError):
            LanguageManager.fetch_supported_languages()

    @patch("wikipediaapi.WikipediaClient.get_page_by_title")
    def test_page_not_found_error(self, mock_get_page):
        mock_get_page.side_effect = PageNotFoundError("Page not found")
        with self.assertRaises(PageNotFoundError):
            self.client.get_page_by_title("Nonexistent Page")

    @patch("wikipediaapi.WikipediaPage.validate_revisions_params")
    def test_revision_validation_error(self, mock_validate):
        mock_validate.side_effect = ValueError("Invalid parameters")
        with self.assertRaises(ValueError):
            self.page.validate_revisions_params(rvlimit=1000)


if __name__ == "__main__":
    unittest.main()
