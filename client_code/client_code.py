import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wikipediaapi import WikipediaClient, Language, SearchType, SearchSortOrder

def attributes():
    """
    Initialize a Wikipedia client with a default language (English) and retrieve information about a Wikipedia page.
    """
    wiki_client = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)

    # Search for page(s)
    print("Searching for 'Python programming'...")
    try:
        page = wiki_client.get_page_by_title("Python programming")
        print("Page - Id: %s" % page.pageid)
        print("Page - Title: %s" % page.title)
        print("Page - Summary: %s" % page.summary)
        print("Page - restrictiontypes: %s" % page.restrictiontypes)
        print("Page - Protection Level: %s" % page.protection)
        print("Page - Talk Id: %s" % page.talkid)
        print("Page - Watched Status: %s" % page.watched)
        print("Page - Number of Watchers: %s" % page.watchers)
        print("Page - Number of Visiting Watchers: %s" % page.visitingwatchers)
        print("Page - Notification Timestamp: %s" % page.notificationtimestamp)
        print("Page - Subject Id: %s" % page.subjectid)
        print("Page - Associated Page: %s" % page.associatedpage)
        print("Page - Preload Content: %s" % page.preloadcontent)
        print("Page - Edit Intro: %s" % page.editintro)
        print("Page - Display Title: %s" % page.displaytitle)
        print("Page - Variant Titles: %s" % page.varianttitles)
        print("Page - Link Classes: %s" % page.linkclasses)
        print("Page - categories: %s" % page.categories)
        print("Page - backlinks: %s" % page.backlinks)
        print("Page - links: %s" % page.links)
        print("Page - langlinks: %s" % page.langlinks)
    except ValueError as e:
        print(f"Error: {e}\n")

    # Extract information from a page
    page = wiki_client.get_page_by_id(12345)
    print("Page - Id: %s" % page.pageid)
    print("Page - Title: %s" % page.title)
    print("Page - Summary: %s" % page.summary)
    print("Page - restrictiontypes: %s" % page.restrictiontypes)
    print("Page - Protection Level: %s" % page.protection)
    print("Page - Talk Id: %s" % page.talkid)
    print("Page - Watched Status: %s" % page.watched)
    print("Page - Number of Watchers: %s" % page.watchers)
    print("Page - Number of Visiting Watchers: %s" % page.visitingwatchers)
    print("Page - Notification Timestamp: %s" % page.notificationtimestamp)
    print("Page - Subject Id: %s" % page.subjectid)
    print("Page - Associated Page: %s" % page.associatedpage)
    print("Page - Preload Content: %s" % page.preloadcontent)
    print("Page - Edit Intro: %s" % page.editintro)
    print("Page - Display Title: %s" % page.displaytitle)
    print("Page - Variant Titles: %s" % page.varianttitles)
    print("Page - Link Classes: %s" % page.linkclasses)
    print("Page - categories: %s" % page.categories)
    print("Page - backlinks: %s" % page.backlinks)
    print("Page - links: %s" % page.links)
    print("Page - langlinks: %s" % page.langlinks)

    # Initialize a Wikipedia client with a custom user agent and English language setting
    wiki_client = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)

    # Retrieve the Wikipedia page for the exact title "Python (programming language)"
    page = wiki_client.get_page_by_title("Python (programming language)")

    # Extract the raw infobox content from the page
    raw_infobox = page.infobox

    # Split the raw infobox into individual lines for processing
    lines = raw_infobox.split("\n")

    # Initialize a dictionary to store parsed key-value pairs from the infobox
    fields = {}

    # Process each line to extract key-value pairs
    for line in lines:
        if "=" in line and not line.strip().startswith("|}"):
            key, value = line.split("=", 1)  
            fields[key.strip()] = value.strip() 

    print(fields)

def search():
    """
    Search for Wikipedia pages using different search types and parameters.
    """
    wiki_client = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)

    # Test KEYWORD search
    print("Testing KEYWORD search...")
    results = wiki_client.search_pages(
        search_type=SearchType.KEYWORD,
        keyword="Python programming",
        limit=3,
        sort_by=SearchSortOrder.RELEVANCE
    )
    for idx, page in enumerate(results, start=1):
        print(f"{idx}. {page.title} (ID: {page.pageid})")

    # Test TEXT search
    print("\nTesting TEXT search...")
    results = wiki_client.search_pages(
        search_type=SearchType.TEXT,
        text="high-level programming language",
        limit=2,
        sort_by=SearchSortOrder.RANDOM
    )
    for idx, page in enumerate(results, start=1):
        print(f"{idx}. {page.title} (ID: {page.pageid})")

    # Test LOCATION search
    print("\nTesting LOCATION search...")
    results = wiki_client.search_pages(
        search_type=SearchType.LOCATION,
        latitude=37.7749,
        longitude=-122.4194,
        radius=2000,
        limit=5,
        sort_by=SearchSortOrder.DISTANCE
    )
    for idx, page in enumerate(results, start=1):
        print(f"{idx}. {page.title} (ID: {page.pageid})")

    # Test LANGUAGE search
    print("\nTesting LANGUAGE search...")
    results = wiki_client.search_pages(
        search_type=SearchType.LANGUAGE,
        language=Language.ES,  # Language code for Spanish
        limit=5,
        sort_by=SearchSortOrder.RELEVANCE
    )
    for idx, page in enumerate(results, start=1):
        print(f"{idx}. {page.title} (ID: {page.pageid})")

    # Test PREFIX search
    print("\nTesting PREFIX search...")
    results = wiki_client.search_pages(
        search_type=SearchType.PREFIX,
        prefix="Python",
        limit=3
    )
    print(results)
    for idx, page in enumerate(results, start=1):
        print(f"{idx}. {page.title} (ID: {page.pageid})")



if __name__ == "__main__":
    attributes()
    search()