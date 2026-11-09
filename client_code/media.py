# setup path to import wikipediaapi
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wikipediaapi import WikipediaClient, Language

wiki_client = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)
page = wiki_client.get_page_by_title("Paris")

for section in page.sections:
    print(f"Section: {section.title}")
    for media in section.media:
        print(f"  Media: {media.title}, URL: {media.url}, Caption: {media.caption}, Type: {media.media_type}")
