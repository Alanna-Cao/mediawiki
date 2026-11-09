import unittest
from unittest.mock import patch
from wikipediaapi import WikipediaClient, WikipediaPage, LanguageManager


class TestWikipediaRevisions(unittest.TestCase):

    def setUp(self):
        self.client = WikipediaClient(user_agent="TestApp/1.0", language=LanguageManager.Language.EN)
        self.page = WikipediaPage(title="Example Page", wiki=self.client)

    @patch("wikipediaapi.WikipediaPage._WikipediaPage__query")
    def test_get_revisions(self, mock_query):
        mock_query.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "revisions": [
                            {"revid": 1, "user": "UserA", "timestamp": "2024-01-01T00:00:00Z", "comment": "Initial edit"},
                            {"revid": 2, "user": "UserB", "timestamp": "2024-01-02T00:00:00Z", "flags": ["minor"], "comment": "Minor edit"}
                        ]
                    }
                }
            }
        }

        revisions = self.page.get_revisions(rvlimit=5, filter_substantive=True)
        self.assertEqual(len(revisions), 1)  # Only substantive revision
        self.assertEqual(revisions[0]["user"], "UserA")

    @patch("wikipediaapi.WikipediaPage._WikipediaPage__query")
    def test_fetch_revision_diff(self, mock_query):
        mock_query.return_value = {
            "compare": {
                "*": "Diff content here"
            }
        }
        diff = self.page.fetch_revision_diff(old_revid=1, new_revid=2)
        self.assertEqual(diff, "Diff content here")

    @patch("wikipediaapi.WikipediaPage._WikipediaPage__query")
    def test_summarize_recent_revisions(self, mock_query):
        mock_query.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "revisions": [
                            {"revid": 1, "user": "UserA", "timestamp": "2024-01-01T00:00:00Z", "comment": "Initial edit"},
                            {"revid": 2, "user": "UserB", "timestamp": "2024-01-02T00:00:00Z", "comment": "Added content"}
                        ]
                    }
                }
            }
        }

        summaries = self.page.summarize_recent_revisions(rvlimit=2)
        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0]["user"], "UserA")

    @patch("wikipediaapi.WikipediaPage._WikipediaPage__query")
    def test_fetch_latest_revisions_diff(self, mock_query):
        # Mock data with at least two substantive revisions
        mock_query.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "revisions": [
                            {"revid": 2, "flags": []},  # Substantive edit
                            {"revid": 1, "flags": []},  # Substantive edit
                        ]
                    }
                }
            }
        }

        with patch("wikipediaapi.WikipediaPage.fetch_revision_diff") as mock_diff:
            mock_diff.return_value = "Diff content here"
            diff = self.page.fetch_latest_revisions_diff(filter_substantive=True)
            self.assertIsNotNone(diff, "fetch_latest_revisions_diff returned None unexpectedly.")
            self.assertEqual(diff["diff"], "Diff content here")


if __name__ == "__main__":
    unittest.main()
