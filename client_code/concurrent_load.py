# setup path to import wikipediaapi
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wikipediaapi import WikipediaClient, Language

if __name__ == "__main__":
    # generate 1k page ids
    page_ids = list(range(1, 1000))
        
    client = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)
    
    failed_ids, id_pages = client.get_pages_by_ids(page_ids, max_threads=16)
    # success pageid
    for page_id, page in id_pages.items():
        print(f"Page ID: {page_id}, Title: {page.title}")
        
    # failed pageid
    for page_id, error in failed_ids.items():
        print(f"Page ID: {page_id}, Error: {error}")