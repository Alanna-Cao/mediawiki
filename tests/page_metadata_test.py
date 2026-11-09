import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import unittest
from unittest.mock import MagicMock
from wikipediaapi import WikipediaClient, Language, MediaObject, MediaType

class TestWikipediaClient(unittest.TestCase):

    def setUp(self):
        self.mock_client = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)

    def test_page_metadata(self):
        mock_page = MagicMock()
        mock_page.pageid = 12345
        mock_page.title = "Demographics of Guadeloupe"
        mock_page.summary = "Guadeloupe has a population of 375,693 (2021)."
        mock_page.restrictiontypes = ["edit", "move"]
        mock_page.protection = []
        mock_page.talkid = 41853206
        mock_page.watched = None
        mock_page.watchers = None
        mock_page.visitingwatchers = None
        mock_page.notificationtimestamp = ""
        mock_page.subjectid = None
        mock_page.associatedpage = "Talk:Demographics of Guadeloupe"
        mock_page.preloadcontent = None
        self.mock_client.get_page_by_id = MagicMock(return_value=mock_page)

        page = self.mock_client.get_page_by_id(12345)

        self.assertEqual(page.pageid, 12345)
        self.assertEqual(page.title, "Demographics of Guadeloupe")
        self.assertEqual(page.summary, "Guadeloupe has a population of 375,693 (2021).")
        self.assertEqual(page.restrictiontypes, ["edit", "move"])
        self.assertEqual(page.protection, [])
        self.assertEqual(page.talkid, 41853206)
        self.assertIsNone(page.watched)
        self.assertIsNone(page.watchers)
        self.assertIsNone(page.visitingwatchers)
        self.assertEqual(page.notificationtimestamp, "")
        self.assertIsNone(page.subjectid)
        self.assertEqual(page.associatedpage, "Talk:Demographics of Guadeloupe")
        self.assertIsNone(page.preloadcontent)

    def test_page_edit_intro(self):
        mock_page = MagicMock()
        mock_page.editintro = {
            'editnotice-notext': "Page notice",
            'anoneditwarning': "You are not logged in.",
            'editpage-head-copy-warn': "Content that violates copyrights will be deleted."
        }
        mock_page.displaytitle = "Demographics of Guadeloupe"
        mock_page.varianttitles = {"en": "Demographics of Guadeloupe"}
        self.mock_client.get_page_by_id = MagicMock(return_value=mock_page)

        page = self.mock_client.get_page_by_id(12345)

        self.assertEqual(page.editintro['editnotice-notext'], "Page notice")
        self.assertEqual(page.displaytitle, "Demographics of Guadeloupe")
        self.assertEqual(page.varianttitles, {"en": "Demographics of Guadeloupe"})

    def test_page_links_and_categories(self):
        mock_page = MagicMock()
        mock_page.linkclasses = []
        mock_page.categories = [
            "Category:Articles with short description",
            "Category:Demographics of Guadeloupe"
        ]
        mock_page.backlinks = {
            "Demographics of Antigua and Barbuda": "Demographics of Antigua and Barbuda (ns: 0)"
        }
        mock_page.links = {
            "Antillean Creole French": "Antillean Creole French (ns: 0)"
        }
        mock_page.langlinks = {"fr": "Démographie de la Guadeloupe (ns: 0)"}

        self.mock_client.get_page_by_id = MagicMock(return_value=mock_page)

        page = self.mock_client.get_page_by_id(12345)

        self.assertEqual(page.categories, ["Category:Articles with short description", "Category:Demographics of Guadeloupe"])
        self.assertIn("Demographics of Antigua and Barbuda", page.backlinks)
        self.assertIn("Antillean Creole French", page.links)
        self.assertIn("fr", page.langlinks)

    def test_infobox_parsing(self):
        mock_page = MagicMock()
        mock_page.infobox = """
            | logo = Python-logo-notext.svg
            | paradigm = Multi-paradigm
        """

        self.mock_client.get_page_by_title = MagicMock(return_value=mock_page)

        page = self.mock_client.get_page_by_title("Python (programming language)")

        self.assertEqual(page.infobox, """
            | logo = Python-logo-notext.svg
            | paradigm = Multi-paradigm
        """)

        fields = {}
        for line in page.infobox.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                fields[key.strip()] = value.strip()

        expected_fields = {
            "| logo": "Python-logo-notext.svg",
            "| paradigm": "Multi-paradigm"
        }
        self.assertEqual(fields, expected_fields)

    def test_page_media(self):
        mock_media = [
            MediaObject(
                title="Example Image",
                url="https://example.com/image.jpg",
                mime="image/jpeg",
                size=1024,
                caption="An example image for demonstration purposes."
            ),
            MediaObject(
                title="Sample Video",
                url="https://example.com/video.mp4",
                mime="video/mp4",
                size=2048,
                caption="A sample video for testing purposes."
            )
        ]

        mock_page = MagicMock()
        mock_page.media = mock_media
        self.mock_client.get_page_by_id = MagicMock(return_value=mock_page)

        page = self.mock_client.get_page_by_id(12345)

        media_objects = page.media

        self.assertEqual(len(media_objects), 2)
        self.assertEqual(media_objects[0].title, "Example Image")
        self.assertEqual(media_objects[0].url, "https://example.com/image.jpg")
        self.assertEqual(media_objects[0].mime, "image/jpeg")
        self.assertEqual(media_objects[0].size, 1024)
        self.assertEqual(media_objects[0].caption, "An example image for demonstration purposes.")
        self.assertEqual(media_objects[0].media_type, MediaType.IMAGE)

        self.assertEqual(media_objects[1].title, "Sample Video")
        self.assertEqual(media_objects[1].url, "https://example.com/video.mp4")
        self.assertEqual(media_objects[1].mime, "video/mp4")
        self.assertEqual(media_objects[1].size, 2048)
        self.assertEqual(media_objects[1].caption, "A sample video for testing purposes.")
        self.assertEqual(media_objects[1].media_type, MediaType.VIDEO)

if __name__ == "__main__":
    unittest.main()