import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from wikipediaapi import WikipediaClient, WikipediaPage, Language, SearchType, SearchSortOrder, PageNotFoundError

class TestWikipediaClient(unittest.TestCase):

    def setUp(self):
        self.client = WikipediaClient(user_agent="TestApp/1.0", language=Language.EN)
        
        
    @patch.object(WikipediaClient, 'get_page_by_title')
    def test_get_pages_by_titles(self, mock_get_page_by_title):
        def side_effect(title, **kwargs):
            if title == "Page1":
                page = MagicMock()
                page.title = "Page1"
                return page
            else:
                raise Exception(f"Page {title} not found")

        mock_get_page_by_title.side_effect = side_effect

        failed_titles, pages = self.client.get_pages_by_titles(["Page1", "Page2"], max_threads=4)

        self.assertIn("Page1", pages)
        self.assertEqual(pages["Page1"].title, "Page1")

        self.assertIn("Page2", failed_titles)
        
        failed_titles, pages = self.client.get_pages_by_titles(["Page1", "Page2"])

        self.assertIn("Page1", pages)
        self.assertEqual(pages["Page1"].title, "Page1")

        self.assertIn("Page2", failed_titles)
        
    @patch.object(WikipediaClient, 'get_page_by_id')
    def test_get_multiple_pages(self, mock_get_page_by_id):
        def side_effect(page_id, **kwargs):
            if page_id == 1:
                page = MagicMock(spec=WikipediaPage)
                page.pageid = 1
                page.title = "Page 1"
                return page
            else:
                raise PageNotFoundError(f"Page with ID {page_id} not found.")

        mock_get_page_by_id.side_effect = side_effect

        failed_ids, pages = self.client.get_pages_by_ids([1, 2, 3], max_threads=4)

        self.assertIn(1, pages)
        self.assertEqual(pages[1].title, "Page 1")

        self.assertIn(2, failed_ids)
        self.assertIn(3, failed_ids)
        
        failed_ids, pages = self.client.get_pages_by_ids([1, 2, 3])

        self.assertIn(1, pages)
        self.assertEqual(pages[1].title, "Page 1")

        self.assertIn(2, failed_ids)
        self.assertIn(3, failed_ids)

if __name__ == '__main__':
    unittest.main()
