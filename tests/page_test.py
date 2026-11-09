import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import unittest
from unittest.mock import patch, MagicMock
from wikipediaapi import WikipediaClient, WikipediaPage, Language, SearchType, SearchSortOrder, PageNotFoundError

class TestWikipediaClient(unittest.TestCase):

    def setUp(self):
        self.client = WikipediaClient(user_agent="TestApp/1.0", language=Language.EN)

    @patch('wikipediaapi.requests.Session.get')
    def test_get_page_by_title_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "Python (programming language)",
                        "extract": "Python is a programming language."
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        page = self.client.get_page_by_title("Python (programming language)")
        self.assertEqual(page.pageid, 12345)
        self.assertEqual(page.title, "Python (programming language)")
        self.assertIn("Python is a programming language.", page.summary)

    @patch('wikipediaapi.requests.Session.get')
    def test_get_page_by_id_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "Python (programming language)",
                        "extract": "Python is a programming language."
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        page = self.client.get_page_by_id(12345)
        self.assertEqual(page.pageid, 12345)
        self.assertEqual(page.title, "Python (programming language)")
        self.assertIn("Python is a programming language.", page.summary)

    @patch('wikipediaapi.requests.Session.get')
    def test_get_page_by_id_invalid_id(self, mock_get):
        with self.assertRaises(ValueError):
            self.client.get_page_by_id(-1)

    @patch('wikipediaapi.requests.Session.get')
    def test_search_pages_keyword(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "search": [
                    {"pageid": 12345, "title": "Python (programming language)"},
                    {"pageid": 54321, "title": "Python (snake)"}
                ]
            }
        }
        mock_get.return_value = mock_response

        results = self.client.search_pages(
            search_type=SearchType.KEYWORD,
            keyword="Python",
            limit=2,
            sort_by=SearchSortOrder.RELEVANCE
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Python (programming language)")
        self.assertEqual(results[1].title, "Python (snake)")

if __name__ == '__main__':
    unittest.main()
