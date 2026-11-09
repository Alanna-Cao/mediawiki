17480/780 Final Project: Wikipedia API
======================================

`Wikipedia-API` is an easy-to-use Python wrapper for Wikipedia's API. It supports extracting texts, sections, links, categories, and more from Wikipedia.

Key Features
------------
- Retrieve and cache Wikipedia page summaries, sections, links, categories, and other metadata.
- Perform full-text, keyword, or location-based searches.
- Access pages in multiple languages and compare language differences.
- Generate flashcards or reports from Wikipedia content.
- Analyze page revisions using LLMs for difference.

Documentation
-------------
Detailed documentation is available on the `GitHub Page <https://cmu-api-design.github.io/team3-f24/wikipediaapi.html>`_.


Quick Start
-----------
Below are examples showcasing common use cases of the `Wikipedia-API`.

Importing the Library
~~~~~~~~~~~~~~~~~~~~~
To begin using the library, import the necessary classes and create a client:

.. code-block:: python

   from wikipediaapi import WikipediaClient, Language
   wiki_client = WikipediaClient(user_agent="MyApp/1.0", language=Language.EN)

Perform a Full-Text Search
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Search Wikipedia for pages using the full-text search:

.. code-block:: python

   results = wiki_client.search_pages(search_type=SearchType.TEXT, text="high-level programming language", limit=2)
   for idx, page in enumerate(results, start=1):
       print(f"{idx}. {page.title} (ID: {page.pageid})")

Fetch Pages by ID Concurrently
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Retrieve multiple pages by their IDs using multithreading for better performance:

.. code-block:: python

   page_ids = list(range(1, 1000))
   # if max_threads is not specified, it fetch pages sequentially
   failed_ids, id_pages = wiki_client.get_pages_by_ids(page_ids, max_threads=16)

   # Display successful page fetches
   for page_id, page in id_pages.items():
       print(f"Page ID: {page_id}, Title: {page.title}")

   # Display failed page fetches
   for page_id, error in failed_ids.items():
       print(f"Page ID: {page_id}, Error: {error}")

Compare Page Content in Different Languages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Compare the content of a page in two different languages using LLM analysis:

.. code-block:: python

   from LLM_client_code import LLMHelper

   llm_helper = LLMHelper()
   difference = llm_helper.compare_language_difference("Python Software Foundation", lang1=Language.EN, lang2=Language.ES)
   print(difference)

Generate Flashcards from Infobox
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Create flashcards from the infobox of a Wikipedia page:

.. code-block:: python

   from flashcards import run_flashcards

   run_flashcards("Python (programming language)")

Analyze Revisions with LLM
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Summarize or compare Wikipedia page revisions using an LLM:

.. code-block:: python

   from LLM_revisions_client_code import LLMRevisionsHelper

   helper = LLMRevisionsHelper()
   summary = helper.summarize_revisions("Python (programming language)", rvlimit=5)
   print(summary)

Generate a PDF Report
~~~~~~~~~~~~~~~~~~~~~
Generate a structured PDF report containing sections, metadata, and summaries from a Wikipedia page:

.. code-block:: python

   from report import fetch_and_save_sections

   fetch_and_save_sections("Python (programming language)", file_name="output.pdf")

Acknowledgments
---------------
This project is forked and adapted from https://github.com/martin-majlis/Wikipedia-API
