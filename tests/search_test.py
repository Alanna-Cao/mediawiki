import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import unittest
from unittest.mock import patch
from wikipediaapi import WikipediaClient, SearchType, SearchSortOrder, Language, Namespace

class TestWikipediaSearch(unittest.TestCase):
    def setUp(self):
        self.wiki = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)

    @patch('wikipediaapi.WikipediaClient._WikipediaClient__query')
    def test_keyword_search(self, mock_query):
        mock_query.return_value = {
            "query": {
                "search": [
                    {"title": "Python (programming language)", "pageid": 23862, "ns": 0},
                    {"title": "History of Python", "pageid": 21356332, "ns": 0},
                    {"title": "Python", "pageid": 46332325, "ns": 0},
                ]
            }
        }

        results = self.wiki.search_pages(
            search_type=SearchType.KEYWORD,
            keyword="Python programming",
            limit=3,
            sort_by=SearchSortOrder.RELEVANCE
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].title, "Python (programming language)")
        self.assertEqual(results[0].pageid, 23862)

    @patch('wikipediaapi.WikipediaClient._WikipediaClient__query')
    def test_text_search(self, mock_query):
        mock_query.return_value = {
            "query": {
                "search": [
                    {"title": "High-level programming language", "pageid": 21427346, "ns": 0},
                    {"title": "Programming language", "pageid": 1985783, "ns": 0},
                ]
            }
        }

        results = self.wiki.search_pages(
            search_type=SearchType.TEXT,
            text="high-level programming language",
            limit=2,
            sort_by=SearchSortOrder.RANDOM
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "High-level programming language")
        self.assertEqual(results[0].pageid, 21427346)

    @patch('wikipediaapi.WikipediaClient._WikipediaClient__query')
    def test_location_search(self, mock_query):
        mock_query.return_value = {
            "query": {
                "geosearch": [
                    {"title": "Fillmore West", "pageid": 2239406, "ns": 0},
                    {"title": "Van Ness station", "pageid": 1511602, "ns": 0},
                ]
            }
        }

        results = self.wiki.search_pages(
            search_type=SearchType.LOCATION,
            latitude=37.7749,
            longitude=-122.4194,
            radius=2000,
            limit=2,
            sort_by=SearchSortOrder.DISTANCE
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Fillmore West")
        self.assertEqual(results[0].pageid, 2239406)

    @patch('wikipediaapi.WikipediaClient._WikipediaClient__query')
    def test_language_search(self, mock_query):
        mock_query.return_value = {
            "query": {
                "search": [
                    {"title": "Spanish language", "pageid": 26825, "ns": 0},
                    {"title": "Lexus ES", "pageid": 1310341, "ns": 0},
                ]
            }
        }

        results = self.wiki.search_pages(
            search_type=SearchType.LANGUAGE,
            language=Language.ES,
            limit=2,
            sort_by=SearchSortOrder.RELEVANCE
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Spanish language")
        self.assertEqual(results[0].pageid, 26825)

    @patch('wikipediaapi.WikipediaClient._WikipediaClient__query')
    def test_prefix_search(self, mock_query):
        mock_query.return_value = {
            "query": {
                "prefixsearch": [
                    {"title": "Python", "pageid": 46332325, "ns": 0},
                    {"title": "Python (programming language)", "pageid": 23862, "ns": 0},
                ]
            }
        }

        results = self.wiki.search_pages(
            search_type=SearchType.PREFIX,
            prefix="Python",
            limit=2,
            namespace=Namespace.MAIN
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Python")
        self.assertEqual(results[0].pageid, 46332325)


if __name__ == "__main__":
    unittest.main()
