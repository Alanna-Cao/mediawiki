"""
Wikipedia-API is easy to use wrapper for extracting information from Wikipedia through the Media-Wiki API.

It supports extracting texts, sections, links, categories, translations, etc.
from Wikipedia. Documentation provides code snippets for common use cases.


"""

__version__ = (0, 7, 1)

import logging
import re

from collections import defaultdict
from enum import IntEnum, Enum
from typing import Any, Optional, Union
from urllib import parse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, TimeoutError
from typing import List, Dict, Union, Tuple
import threading

import requests

USER_AGENT = (
    "Wikipedia-API/"
    + ".".join(str(s) for s in __version__)
    + "; https://github.com/martin-majlis/Wikipedia-API/"
)

log = logging.getLogger(__name__)


# https://www.mediawiki.org/wiki/API:Main_page
PagesDict = dict[str, "WikipediaPage"]


class ExtractFormat(IntEnum):
    """
    Represents the available formats for extracting data from Wikipedia pages. 
    This enum allows you to specify how the data should be extracted, currently 
    can be either as raw text or HTML.

    Example usage::

        from wikipediaapi import ExtractFormat
        format = ExtractFormat.WIKI
    """

    WIKI = 1
    """
    Extracts the content in a raw Wiki-style format, allowing subsections to be recognized.
    Example usage: https://goo.gl/PScNVV
    """

    HTML = 2
    """
    Extracts the page content as HTML, including any HTML tags.
    Example usage: https://goo.gl/1Jwwpr
    """

    # Plain: https://goo.gl/MAv2qz
    # Doesn't allow to recognize subsections
    # PLAIN = 3


class Namespace(IntEnum):
    """
    Represents the different namespaces used within Wikipedia. Each namespace 
    refers to a specific category or type of Wikipedia page, such as the main content, 
    user pages, or talk pages. This class helps you identify which part of Wikipedia 
    you are working with.

    You can get list of possible namespaces here:

    * https://en.wikipedia.org/wiki/Wikipedia:Namespace
    * https://en.wikipedia.org/wiki/Wikipedia:Namespace#Programming

    Example usage::
        from wikipediaapi import Namespace
        namespace = Namespace.MAIN

    Currently, the following namespaces are supported:
    """

    MAIN = 0
    TALK = 1
    USER = 2
    USER_TALK = 3
    WIKIPEDIA = 4
    WIKIPEDIA_TALK = 5
    FILE = 6
    FILE_TALK = 7
    MEDIAWIKI = 8
    MEDIAWIKI_TALK = 9
    TEMPLATE = 10
    TEMPLATE_TALK = 11
    HELP = 12
    HELP_TALK = 13
    CATEGORY = 14
    CATEGORY_TALK = 15
    PORTAL = 100
    PORTAL_TALK = 101
    PROJECT = 102
    PROJECT_TALK = 103
    REFERENCE = 104
    REFERENCE_TALK = 105
    BOOK = 108
    BOOK_TALK = 109
    DRAFT = 118
    DRAFT_TALK = 119
    EDUCATION_PROGRAM = 446
    EDUCATION_PROGRAM_TALK = 447
    TIMED_TEXT = 710
    TIMED_TEXT_TALK = 711
    MODULE = 828
    MODULE_TALK = 829
    GADGET = 2300
    GADGET_TALK = 2301
    GADGET_DEFINITION = 2302
    GADGET_DEFINITION_TALK = 2303


WikiNamespace = Union[Namespace, int]


def namespace2int(namespace: WikiNamespace) -> int:
    """Converts namespace into integer"""
    if isinstance(namespace, Namespace):
        return namespace.value

    return namespace


RE_SECTION = {
    ExtractFormat.WIKI: re.compile(r"\n\n *(==+) (.*?) (==+) *\n"),
    ExtractFormat.HTML: re.compile(
        r"\n? *<h([1-9])[^>]*?>(<span[^>]*></span>)? *"
        + "(<span[^>]*>)? *(<span[^>]*></span>)? *(.*?) *"
        + "(</span>)?(<span>Edit</span>)?</h[1-9]>\n?"
        #                  ^^^^
        # Example page with 'Edit' erroneous links: https://bit.ly/2ui4FWs
    ),
    # ExtractFormat.PLAIN.value: re.compile(r'\n\n *(===*) (.*?) (===*) *\n'),
}

class WikipediaAPIError(Exception):
    """Base class for all Wikipedia API errors."""
    pass

class PageNotFoundError(WikipediaAPIError):
    """Raised when a specific Wikipedia page cannot be found."""
    pass


class StaticLanguage(Enum):
    """
    A predefined enum class for a static set of supported languages.

    This class provides a fixed list of commonly used languages in MediaWiki API.
    """

    EN = "en"
    ES = "es"
    DE = "de"
    FR = "fr"
    IT = "it"

class LanguageManager:
    """
    Handles the creation and management of dynamically supported languages.

    **Responsibilities:**
    - Fetch supported languages dynamically from the MediaWiki API.
    - Create an Enum class dynamically based on fetched language data.

    **Intended Usage:**
    1. **Fetch Supported Languages:**
       Use `fetch_supported_languages()` to retrieve a dictionary of language codes and their corresponding names.
       ```
       supported_languages = LanguageManager.fetch_supported_languages()
       print(supported_languages)
       # Output: {'EN': 'English', 'ES': 'Spanish', 'DE': 'German', ...}
       ```

    2. **Dynamic Language Enum Creation:**
       Use `create_language_enum()` to dynamically create an Enum class from fetched language data.
       ```
       language_data = {'EN': 'English', 'ES': 'Spanish'}
       dynamic_enum = LanguageManager.create_language_enum("DynamicLanguageEnum", language_data)
       print(dynamic_enum.EN)  # Output: 'English'
       ```

    **Important Notes:**
    - This class abstracts the logic for dynamic language creation and fetching supported languages.
    """
    Language = None

    @staticmethod
    def fetch_supported_languages() -> dict[str, str]:
        """
        Fetches the supported language codes and their descriptions from the MediaWiki API.

        This method makes a request to the MediaWiki API and retrieves a list of supported language codes
        and their corresponding names. The data is returned as a dictionary with the language codes as keys 
        and the full language names as values.

        :return: A dictionary mapping language codes (str) to their full names (str).
        :raises ConnectionError: If there is an issue with fetching the language data from the API.
        :raises requests.RequestException: For other request-related issues such as timeouts or invalid responses.
        
        Example usage::
            languages = LanguageManager.fetch_supported_languages()
            print(languages)
            # Output: {'EN': 'English', 'ES': 'Spanish', 'DE': 'German', ...}
        """
        url = "https://www.mediawiki.org/w/api.php"
        params = {
            "action": "query",
            "meta": "siteinfo",
            "siprop": "languages",
            "format": "json",
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {lang["code"].upper(): lang["*"] for lang in data["query"]["languages"]}
        except requests.RequestException as e:
            raise ConnectionError("Failed to fetch supported languages") from e

    @staticmethod
    def create_language_enum(name: str, language_data: dict[str, str]) -> Enum:
        """
        Dynamically creates an Enum class for supported languages.

        Given a dictionary of language codes and their names, this method creates and returns a new Enum class.
        The generated Enum class will have each language code as an attribute, and the corresponding language name 
        as the value of that attribute.

        :param name: The name of the Enum class to be created.
        :param language_data: A dictionary of language codes (str) as keys and their names (str) as values.
        :return: A dynamically created Enum class representing the supported languages.
        
        Example usage::
            language_data = {'EN': 'English', 'ES': 'Spanish'}
            language_enum = LanguageManager.create_language_enum("LanguageEnum", language_data)
            print(language_enum.EN)  # Output: 'English'
            print(language_enum.ES)  # Output: 'Spanish'
        """
        return Enum(name, {key: key.lower() for key in language_data})


    @classmethod
    def initialize(cls):
        """
        Initializes the Language enum dynamically and assigns it to the class.
        """
        try:
            language_data = cls.fetch_supported_languages()
            cls.Language = cls.create_language_enum("Language", language_data)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Language enum: {e}")

    @classmethod
    def get_language_enum(cls):
        """
        Returns the dynamically created Language enum.
        """
        if cls.Language is None:
            cls.initialize()
        return cls.Language


# Initialize the LanguageManager
LanguageManager.initialize()
Language = LanguageManager.Language

class SearchType(Enum):
    KEYWORD = "keyword"
    TEXT = "text"
    LOCATION = "location"
    LANGUAGE = "language"
    PREFIX = "prefix"

class SearchSortOrder(Enum):
    RELEVANCE = "relevance"
    CREATE_TIMESTAMP_ASC = "create_timestamp_asc"
    CREATE_TIMESTAMP_DESC = "create_timestamp_desc"
    INCOMING_LINKS_ASC = "incoming_links_asc"
    INCOMING_LINKS_DESC = "incoming_links_desc"
    JUST_MATCH = "just_match"
    LAST_EDIT_ASC = "last_edit_asc"
    LAST_EDIT_DESC = "last_edit_desc"
    NONE = "none"
    RANDOM = "random"
    USER_RANDOM = "user_random"
    DISTANCE = "distance"

class WikipediaClient:
    """
    Unified interface for Wikipedia search and extraction functionalities.
    This class provides methods for querying pages by their title or ID, and for performing 
    flexible keyword-based searches.
    
    Rate Limiting:
    For all search functions, if the request rate is too high, the API will return "Too Many Requests" error.
    The rate limit is 200 request/sec for a client. See https://www.mediawiki.org/wiki/Wikimedia_REST_API

    Example usage::

        wiki_client = WikipediaClient(
            user_agent="MyApp/1.0",
            language=Language.EN,
            extract_format=ExtractFormat.WIKI,
            headers={"Custom-Header": "Value"},
            timeout=15.0,
        )
    """

    def __init__(
        self,
        user_agent: str,
        language: Language = Language.EN,
        extract_format: ExtractFormat = ExtractFormat.WIKI,
        headers: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """
        Constructs WikipediaClient object for searching for Wikipedia pages and extracting information from them. A single restful API request
        timeout is set to be 10 seconds by default, to change it, see param kwargs.

        :param user_agent: HTTP User-Agent used in requests.
                            It should adhere to Wikipedia's User-Agent policy:
                            https://meta.wikimedia.org/wiki/User-Agent_policy
        :param language: The language edition of Wikipedia to query. Default is English (Language.EN).
                         A valid `Language` enum value is required. See: 
                         http://meta.wikimedia.org/wiki/List_of_Wikipedias, and the :class: `Language` object.
        :param extract_format: The format for page extraction, defined by the `ExtractFormat` enum. 
                               Default is `ExtractFormat.WIKI`.
                                :class:`ExtractFormat` object.
        :param headers: Optional dictionary of HTTP headers to send with the request. 
                        If not provided, default headers will be used.
        :param kwargs: Additional optional parameters such as headers to be passed to the HTTP requests.
                       For more details, refer to:
                       https://docs.python-requests.org/en/master/api/#requests.request

        :raises AssertionError: If an invalid or empty user agent or language is provided.

        """
        kwargs.setdefault("timeout", 10.0)

        # Set default headers and validate User-Agent
        default_headers = {} if headers is None else headers
        if user_agent:
            default_headers.setdefault(
                "User-Agent",
                user_agent,
            )
        used_user_agent = default_headers.get("User-Agent")
        if not (used_user_agent and len(used_user_agent) > 5):
            raise AssertionError(
                "Please, be nice to Wikipedia and specify user agent - "
                + "https://meta.wikimedia.org/wiki/User-Agent_policy. Current user_agent: '"
                + str(used_user_agent)
                + "' is not sufficient."
            )
        default_headers["User-Agent"] += " (" + USER_AGENT + ")"

        self.__language = language.value
        self.__extract_format = extract_format

        log.info(
            "Wikipedia: language=%s, user_agent: %s, extract_format=%s",
            self.__language,
            default_headers["User-Agent"],
            self.__extract_format,
        )

        # Initialize the shared session
        self.__session = requests.Session()
        self.__session.headers.update(default_headers)
        self.__request_kwargs = kwargs

    def get_language(self) -> Language:
        return self.__language

    def get_extract_format(self):
        return self.__extract_format
    
    def get_session(self):
        return self.__session
    
    def get_request_kwargs(self):
        return self.__request_kwargs
    
    
    def get_page_by_id(self, page_id: int, **kwargs) -> "WikipediaPage":
        """
        Retrieves a Wikipedia page using its page_id.

        :param page_id: The unique identifier for the Wikipedia page.
        :param kwargs: Additional arguments for the original `query` RESTful API endpoint. These arguments are optional 
               and can be provided by the user if needed.
        :return: object representing :class:`WikipediaPage`
        :raises ValueError: If the page ID is invalid.
        :raises PageNotFoundError: If the page does not exist.
        """
        if not isinstance(page_id, int) or page_id <= 0:
            raise ValueError("Page ID must be a positive integer.")
        params = {
            "action": "query",
            "prop": "info|extracts",
            "pageids": page_id,
            "format": "json"
        }
        additional_params = kwargs
        params.update(additional_params)

        raw = self.__query(params)  # No specific page context required for this query
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))
        pages = raw.get("query", {}).get("pages", {})

        # Check if the page exists
        if str(page_id) in pages:
            page_data = pages[str(page_id)]
            # print(page_data)
            namespace = page_data.get("ns")
            if not "title" in page_data:
                raise PageNotFoundError(f"Page with ID {page_id} does not exist.")
            return WikipediaPage(
                wiki=self,
                title=page_data["title"],
                ns=namespace,
                language=self.__language,
                page_id=page_data["pageid"],
            )
        else:
            raise PageNotFoundError(f"Page with ID {page_id} does not exist.")
    

    def get_page_by_title(self, title: str, namespace: WikiNamespace = Namespace.MAIN, fallback_search: bool = True, **kwargs) -> "WikipediaPage":
        """
        Retrieves a Wikipedia page by its title. Attempts an exact match first, 
        then falls back to a flexible, broader search if enabled.

        Example::

            wiki = wikipediaapi.Wikipedia(user_agent="MyApp/1.0", language=Language.EN)

            # Exact match only
            page = wiki.get_page("Python (programming language)", fallback_search=False)

            # Exact match with fallback to search
            page = wiki.get_page("Python programming")

        :param title: The title of the page to retrieve.
        :param namespace: The namespace of the page (default: Namespace.MAIN).
        :param fallback_search: Whether to perform a broader search if the exact title is not found (default: True).
        :param kwargs: Additional arguments for the original `query` RESTful API endpoint. These arguments are optional 
               and can be provided by the user if needed.
        :raises ValueError: If the title is empty.
        :raises PageNotFoundError: If the page does not exist and no fallback results are available.
        """
        if not title.strip():
            raise ValueError("The title must be a non-empty string.")
        
        params = {
            "action": "query",
            "prop": "info|extracts",
            "titles": title,
            "format": "json",
        }
        additional_params = kwargs
        params.update(additional_params)

        raw = self.__query(params)
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))
        pages = raw.get("query", {}).get("pages", {})

        for page_id, page_data in pages.items():
            if page_id != "-1": 
                return WikipediaPage(
                    wiki=self,
                    title=page_data["title"],
                    ns=page_data.get("ns", namespace2int(namespace)),
                    language=self.__language,
                    page_id=page_data.get("pageid"),
                )

        if fallback_search:
            results = self.search_pages(search_type=SearchType.KEYWORD, keyword=title, limit=1, namespace=namespace, sort_by=SearchSortOrder.RELEVANCE)
            if results:
                return results[0]

        raise PageNotFoundError(f"Page with title '{title}' does not exist.")

    def get_pages_by_ids(self, page_ids: List[int], max_threads: int = 0, **kwargs) -> Tuple[Dict[int, str], Dict[int, "WikipediaPage"]]:
        """
        Retrieves multiple Wikipedia pages using their page IDs, either sequentially or using multi-threading based on the max_threads parameter.

        Parameters:
        - page_ids (List[int]): List of page IDs to retrieve.
        - max_threads (int): Number of threads to use for fetching pages. If 0, fetches sequentially. Default is 0.
        - kwargs: Additional arguments for the original `query` RESTful API endpoint. These arguments are optional 
               and can be provided by the user if needed.

        Returns:
        - Tuple[Dict[int, str], Dict[int, "WikipediaPage"]]:
            - A dictionary of failed page IDs and their corresponding error messages.
            - A dictionary of successfully fetched page IDs and their corresponding WikipediaPage objects.

        """
        failed_ids = {}
        pages = {}

        def fetch_page_by_id(page_id: int):
            try:
                return page_id, self.get_page_by_id(page_id, **kwargs), None
            except Exception as e:
                return page_id, None, str(e)

        if max_threads == 0:
            # Sequential execution
            for page_id in page_ids:
                try:
                    result_id, result_page, error = fetch_page_by_id(page_id)
                    if result_page:
                        pages[result_id] = result_page
                    else:
                        failed_ids[result_id] = error
                except Exception as e:
                    failed_ids[page_id] = str(e)
        else:
            # Multi-threaded execution
            with ThreadPoolExecutor(max_threads) as executor:
                futures = {executor.submit(fetch_page_by_id, page_id): page_id for page_id in page_ids}

                for future in as_completed(futures):
                    page_id = futures[future]
                    try:
                        result_id, result_page, error = future.result()
                        if result_page:
                            pages[result_id] = result_page
                        else:
                            failed_ids[result_id] = error
                    except Exception as e:
                        failed_ids[page_id] = str(e)

        return failed_ids, pages

    def get_pages_by_titles(self, titles: List[str], namespace: WikiNamespace = Namespace.MAIN, fallback_search: bool = True, max_threads: int = 0, **kwargs) -> Tuple[Dict[str, str], Dict[str, "WikipediaPage"]]:
        """
        Fetches pages by their titles, either sequentially or using multi-threading based on the max_threads parameter.

        Parameters:
        - titles (List[str]): List of titles to fetch.
        - namespace (WikiNamespace): Namespace to search in. Default is Namespace.MAIN.
        - fallback_search (bool): Whether to perform a fallback search if the exact title is not found. Default is True.
        - max_threads (int): Number of threads to use for fetching pages. If 0, fetches sequentially. Default is 0.
        - kwargs: Additional arguments for the original `query` RESTful API endpoint. These arguments are optional 
               and can be provided by the user if needed.

        Returns:
        - Tuple[Dict[str, str], Dict[str, "WikipediaPage"]]:
            - A dictionary of failed titles and their corresponding error messages.
            - A dictionary of successfully fetched titles and their corresponding WikipediaPage objects.

        """
        failed_titles = {}
        pages = {}

        def fetch_page_by_title(title: str):
            try:
                return title, self.get_page_by_title(title=title, namespace=namespace, fallback_search=fallback_search, **kwargs), None
            except Exception as e:
                return title, None, str(e)

        if max_threads == 0:
            # Sequential execution
            for title in titles:
                try:
                    result_title, result_page, error = fetch_page_by_title(title)
                    if result_page:
                        pages[result_title] = result_page
                    else:
                        failed_titles[result_title] = error
                except Exception as e:
                    failed_titles[title] = str(e)
        elif max_threads>0:
            # Multi-threaded execution
            with ThreadPoolExecutor(max_threads) as executor:
                futures = {executor.submit(fetch_page_by_title, title): title for title in titles}

                for future in as_completed(futures):
                    title = futures[future]
                    try:
                        result_title, result_page, error = future.result()
                        if result_page:
                            pages[result_title] = result_page
                        else:
                            failed_titles[result_title] = error
                    except Exception as e:
                        failed_titles[title] = str(e)
        else:
            raise ValueError("max_threads argument must be a non-negative number")
        
        return failed_titles, pages


    def search_pages(self, search_type: SearchType, limit: int = 10, sort_by: SearchSortOrder = SearchSortOrder.RELEVANCE, namespace: WikiNamespace = Namespace.MAIN, **kwargs) -> List["WikipediaPage"]:
        """
        Unified search function for Wikipedia pages.

        :param search_type: The type of search to perform, specified by the SearchType enum.
        :param limit: The maximum number of results to return (default: 10).
        :param sort_by: The sort order for the results. Must be a valid enum value (default depends on search type).
        :param namespace: The namespace to restrict the search (default: 0 for MAIN namespace).
        :param kwargs: Additional arguments specific to the search type. Raises ValueError if missing required parameter or if the parameter is not of specified type.
            - For `SearchType.KEYWORD`:
                - `keyword` (str): The keyword to search for.
            - For `SearchType.TEXT`:
                - `text` (str): The text to search for. 
            - For `SearchType.LOCATION`:
                - `latitude` (float): The latitude of the location. 
                - `longitude` (float): The longitude of the location.
                - `radius` (int): The search radius in meters (optional, default: 1000).
            - For `SearchType.LANGUAGE`:
                - `language` (Language): The language to search for.
            - For `SearchType.PREFIX`:
                - `prefix` (str): The prefix to search for.
        :return: A list of `WikipediaPage` objects for the search results. List will return empty if there are no wikipedia pages found after search.
        :raises ValueError: If required parameters for the specified search type are missing.
        """
        if search_type == SearchType.KEYWORD:
            return self.__search_by_keyword(limit, sort_by, namespace, **kwargs)
        elif search_type == SearchType.TEXT:
            return self.__search_by_keyword(limit, sort_by, namespace, keyword=f"text:{kwargs.get('text')}")
        elif search_type == SearchType.LOCATION:
            return self.__search_by_location(limit, sort_by, **kwargs)
        elif search_type == SearchType.LANGUAGE:
            language = kwargs.get('language')
            if not isinstance(language, Language):
                raise ValueError("'language' must be of type Language enum for LANGUAGE searches.")
            return self.__search_by_keyword(limit, sort_by, namespace, keyword=f"language:{kwargs.get('language').value}")
        elif search_type == SearchType.PREFIX:
            return self.__search_by_prefix(limit, namespace, **kwargs)
        else:
            raise ValueError(f"Unsupported search type: {search_type}")

    def __search_by_keyword(self, limit: int, sort_by: SearchSortOrder, namespace: WikiNamespace = Namespace.MAIN, **kwargs) -> List["WikipediaPage"]:
        keyword = kwargs.get("keyword")
        if not keyword:
            raise ValueError("'keyword' is required for KEYWORD or TEXT searches.")
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "srlimit": limit,
            "srnamespace": namespace2int(namespace),
            "srsort": sort_by.value,
            "format": "json",
        }
        return self.__execute_search(params)

    def __search_by_location(self, limit: int, sort_by: SearchSortOrder, **kwargs) -> List["WikipediaPage"]:
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")
        if latitude is None or longitude is None:
            raise ValueError("'latitude' and 'longitude' are required for LOCATION searches.")
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90.")
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180.")
        params = {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{latitude}|{longitude}",
            "gsradius": kwargs.get("radius", 1000),
            "gslimit": limit,
            "gssort": sort_by.value,
            "format": "json",
        }
        return self.__execute_search(params)

    def __search_by_prefix(self, limit: int, namespace: WikiNamespace = Namespace.MAIN, **kwargs) -> List["WikipediaPage"]:
        prefix = kwargs.get("prefix")
        if not prefix:
            raise ValueError("'prefix' is required for PREFIX searches.")
        params = {
            "action": "query",
            "list": "prefixsearch",
            "pssearch": prefix,
            "pslimit": limit,
            "psnamespace": namespace2int(namespace),
            "format": "json",
        }
        return self.__execute_search(params)

    def __execute_search(self, params: Dict[str, Any]) -> List["WikipediaPage"]:
        """
        Executes a search query against the Wikipedia API and returns the results.

        :param params: Query parameters for the Wikipedia API.
        :return: A list of `WikipediaPage` objects for the search results.
        """
        raw_data = self.__query(params)
        if "prefixsearch" in params.get("list", ""):
            search_results = raw_data.get("query", {}).get("prefixsearch", [])
        else:
            search_results = raw_data.get("query", {}).get("search", []) or raw_data.get("query", {}).get("geosearch", [])

        if not search_results:
            raise RuntimeError(f"No results found for query: {params}")

        return [
            WikipediaPage(
                wiki=self,
                title=result["title"],
                ns=result.get("ns"),
                language=self.__language,
                page_id=result.get("pageid"),
            )
            for result in search_results
        ]
    
    def __query(self, params: dict) -> dict:
        """Internal method to make an API call."""
        base_url = f"https://{self.__language}.wikipedia.org/w/api.php"
        params["format"] = "json"
        try:
            response = self.__session.get(base_url, params=params, **self.__request_kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Request failed: {e}")

    def __del__(self) -> None:
        """Closes session."""
        if hasattr(self, "__session") and self.__session:
            self.__session.close()

class MediaType(Enum):
    """
    Represents the type of a media object.

    This enum is used to categorize media objects into predefined types
    for better organization and processing. The types are inferred based
    on the MIME type of the media file.

    Attributes:
        IMAGE (str): Represents media of type image (e.g., JPEG, PNG, SVG).
        VIDEO (str): Represents media of type video (e.g., MP4, AVI, WebM).
        AUDIO (str): Represents media of type audio (e.g., MP3, WAV, OGG).
        OTHER (str): Represents media that does not fall into the above categories.

    Example Usage::

        media_type = MediaType.IMAGE
        print(media_type.name)  # Output: IMAGE
        print(media_type.value)  # Output: Image
    """
    IMAGE = "Image"
    VIDEO = "Video"
    AUDIO = "Audio"
    OTHER = "Other"


class MediaObject:
    """
    Represents a media object (e.g., image, video, audio) in a Wikipedia page section.

    This class encapsulates the metadata of a media file associated with a Wikipedia section. It includes properties 
    such as the file's title, URL, MIME type, size, caption, and inferred media type. The `MediaType` enum is used 
    to categorize the type of media.

    Example usage::

        media = MediaObject(
            title="Example Image",
            url="https://example.com/image.jpg",
            mime="image/jpeg",
            size=1024,
            caption="An example image for demonstration purposes.",
        )
        print(f"Title: {media.title}, URL: {media.url}, Type: {media.media_type}")

    """

    def __init__(self, title: str, url: str, mime: str, size: int, caption: Optional[str] = None):
        """
        Constructs a MediaObject instance representing a media file.

        :param title: The title of the media file (e.g., the name of the file in the Wikimedia repository).
        :param url: The URL pointing to the media file.
        :param mime: The MIME type of the media file (e.g., 'image/jpeg', 'video/mp4').
        :param size: The size of the media file in bytes.
        :param caption: An optional caption or description of the media file, if available.

        Example:

            media = MediaObject(
                title="Paris Image",
                url="https://example.com/paris.jpg",
                mime="image/jpeg",
                size=2048,
                caption="An aerial view of Paris."
            )
            print(media.title)  # Output: Paris Image
        """
        self.title = title
        self.url = url
        self.mime = mime
        self.size = size
        self.caption = caption
        self.media_type = self.determine_media_type(mime)

    def determine_media_type(self, mime: str) -> MediaType:
        """
        Determines the media type based on the MIME type.

        Args:
            mime (str): The MIME type of the media file.

        Returns:
            MediaType: The determined media type.
        """
        if mime.startswith("image/"):
            return MediaType.IMAGE
        elif mime.startswith("video/"):
            return MediaType.VIDEO
        elif mime.startswith("audio/"):
            return MediaType.AUDIO
        else:
            return MediaType.OTHER

    def __repr__(self):
        return (f"MediaObject(title={self.title}, url={self.url}, mime={self.mime}, "
                f"size={self.size}, caption={self.caption}, media_type={self.media_type.value})")


class WikipediaPageSection:
    """
    WikipediaPageSection represents section in the page.

    This class provides functionality for accessing and interacting with individual sections 
    of a Wikipedia page, including their title, text, subsections, and associated media.
    """

    def __init__(
        self, wiki: WikipediaClient, title: str, level: int = 0, text: str = ""
    ) -> None:
        """Constructs WikipediaPageSection."""
        self._wiki = wiki
        self._title = title
        self._level = level
        self._text = text
        self._section = []  # type: list['WikipediaPageSection']
        self._media = [] 

    @property
    def title(self) -> str:
        """
        Returns title of the current section.

        :return: title of the current section
        """
        return self._title

    @property
    def level(self) -> int:
        """
        Returns indentation level of the current section.

        :return: indentation level of the current section
        """
        return self._level

    @property
    def text(self) -> str:
        """
        Returns text of the current section.

        :return: text of the current section
        """
        return self._text

    @property
    def sections(self) -> list["WikipediaPageSection"]:
        """
        Returns subsections of the current section.

        :return: subsections of the current section
        """
        return self._section
    
    @property
    def media(self) -> list[MediaObject]:
        """
        Returns the media objects associated with this section.

        This function returns media objects (of type MediaType: images, videos, audio, other) 
        related to the current section of the Wikipedia page. Media objects are retrieved 
        from the Wikipedia API and has metadata URL, MIME type, size, 
        and optional captions. The data is represented as a list of `MediaObject` instances.
        Media files are fetched only if the section contains associated media.

        :return: List of MediaObject instances.
        """
        if not self._media:
            self._media = self._fetch_media()
        return self._media

    def _fetch_media(self) -> list["MediaObject"]:
        """
        Fetches media objects associated with this section.

        :return: A list of MediaObject instances.
        """
        params = {
            "action": "query",
            "prop": "images",
            "titles": self.title,
            "format": "json",
        }

        raw_data = self._wiki._WikipediaPage__query(params)

        media_files = []
        pages = raw_data.get("query", {}).get("pages", {})
        for page_data in pages.values():
            images = page_data.get("images", [])
            for image in images:
                media_files.append({"title": image["title"]})

        enriched_media_files = self._enrich_media_info(media_files)
        return enriched_media_files

    def _enrich_media_info(self, media_files: list[dict]) -> list["MediaObject"]:
        """
        Enriches media files with detailed information like URL, MIME type, and size.

        :param media_files: A list of dictionaries containing media file titles.
        :return: A list of enriched MediaObject instances.
        """
        if not media_files:
            return []

        titles = "|".join([media["title"] for media in media_files])
        params = {
            "action": "query",
            "prop": "imageinfo",
            "titles": titles,
            "iiprop": "url|mime|size",
            "format": "json",
        }

        raw_data = self._wiki._WikipediaPage__query(params)

        enriched_media_files = []
        pages = raw_data.get("query", {}).get("pages", {})
        for page_data in pages.values():
            if "imageinfo" in page_data:
                image_info = page_data["imageinfo"][0]
                enriched_media_files.append(
                    MediaObject(
                        title=page_data.get("title", ""),
                        url=image_info.get("url", ""),
                        mime=image_info.get("mime", ""),
                        size=image_info.get("size", 0),
                        caption=image_info.get("descriptionurl", None),  
                    )
                )

        return enriched_media_files

    def get_subsection_by_title(self, title: str) -> Optional["WikipediaPageSection"]:
        """
        Returns subsections of the current section with given title.

        :param title: title of the subsection
        :return: subsection if it exists
        """
        sections = [s for s in self._section if s.title == title]
        if sections:
            return sections[-1]
        return None

    def get_full_text(self, level: int = 1) -> str:
        """
        Returns text of the current section as well as all its subsections.

        :param level: indentation level
        :return: text of the current section as well as all its subsections
        """
        res = ""
        if self._wiki.get_extract_format() == ExtractFormat.WIKI:
            res += self.title
        elif self._wiki.get_extract_format() == ExtractFormat.HTML:
            res += f"<h{level}>{self.title}</h{level}>"
        else:
            raise NotImplementedError("Unknown ExtractFormat type")

        res += "\n"
        res += self._text
        if len(self._text) > 0:
            res += "\n\n"
        for sec in self.sections:
            res += sec.full_text(level + 1)
        return res

    def __repr__(self):
        return "Section: {} ({}):\n{}\nSubsections ({}):\n{}".format(
            self._title,
            self._level,
            self._text,
            len(self._section),
            len(self._media),
            "\n".join(map(repr, self._section)),
        )

class WikipediaPage:
    """
    Represents a Wikipedia page.

    This class allows access to Wikipedia page properties and data about a given
    Wikipedia page. Some properties are retrieved from the Wikimedia API
    and cached within the object to optimize subsequent access.
    
    Thread-safety:
    - The `WikipediaPage` class is designed to be thread-safe. Locks are used to
      ensure the integrity of the class's internal state during concurrent page field access.
    - All property methods that modify or access shared state are synchronized
      using thread locks.

    Note:
    - Page fields fetched via API calls (e.g., `pageid`, `links`, `categories`)
      are cached and only fetched once per instance. Subsequent accesses to these
      fields will retrieve data from the cache, avoiding repeated API calls.
    - Access to these fields may trigger API calls upon the first access if
      they are not already cached.
    """


    def __init__(
        self,
        wiki: WikipediaClient,
        title: str,
        ns: WikiNamespace = Namespace.MAIN,
        language: Language = Language.EN,
        url: Optional[str] = None,
        page_id: Optional[int] = None,
    ) -> None:
        """
        Initializes a WikipediaPage object.

        :param wiki: The Wikipedia API wrapper instance.
        :param title: The title of the page.
        :param ns: The namespace of the page.
        :param language: The language of the page, as a Language enum.
        :param url: Optional full URL of the page.
        :param page_id: Optional unique identifier for the page.
        """
        # locks to protect the following fields when methods are concurrently called
        self.__extract_builder_lock = threading.Lock() # protects the following
        self._wiki = wiki
        self._summary = ""  # type: str
        self._section = []  # type: list[WikipediaPageSection]
        self._section_mapping = {}  # type: dict[str, list[WikipediaPageSection]]
        
        self.__langlinks_lock = threading.Lock()
        self._langlinks = {}  # type: PagesDict
        
        self.__links_lock = threading.Lock()
        self._links = {}  # type: PagesDict
        
        self.__backlinks_lock = threading.Lock()
        self._backlinks = {}  # type: PagesDict
        
        self.__categories_lock = threading.Lock()
        self._categories = []  # type: list[str]
        
        self.__called_functions_lock = threading.Lock() # protects the following field
        self.__called_functions = set()

        self._attributes = {
            "title": title,
            "ns": namespace2int(ns),
            "language": language,
            "image_url": "",
        }  # type: dict[str, Any]

        if url is not None:
            self._attributes["fullurl"] = url

        if page_id is not None:
            self._attributes["pageid"] = page_id
            
        self.ATTRIBUTES_MAPPING = {
        "language": [],
        "pageid": [self.__info, self.extracts, self.__langlinks_func],
        "ns": [self.__info, self.extracts, self.__langlinks_func],
        "title": [self.__info, self.extracts, self.__langlinks_func],
        "contentmodel": [self.__info],
        "pagelanguage": [self.__info],
        "pagelanguagehtmlcode": [self.__info],
        "pagelanguagedir": [self.__info],
        "touched": [self.__info],
        "lastrevid": [self.__info],
        "length": [self.__info],
        "protection": [self.__info],
        "watched": [self.__info],
        "restrictiontypes": [self.__info],
        "watchers": [self.__info],
        "visitingwatchers": [self.__info],
        "notificationtimestamp": [self.__info],
        "subjectid": [self.__info],
        "associatedpage": [self.__info],
        "talkid": [self.__info],
        "fullurl": [self.__info],
        "editurl": [self.__info],
        "canonicalurl": [self.__info],
        "readable": [self.__info],
        "redirect": [self.__info],
        "preload": [self.__info],
        "displaytitle": [self.__info],
        "image_url": [self.__info],
        "preloadcontent": [self.__info],
        "editintro": [self.__info],
        "varianttitles": [self.__info],
        "linkclasses": [self.__info],
        "summary": ["extracts"],
    }
            
    def extracts(self, **kwargs) -> str:
        """
        Retrieve plain-text or limited HTML extracts of specified pages. 

        API Calls for parameters:

        - https://www.mediawiki.org/w/api.php?action=help&modules=query%2Bextracts
        - https://www.mediawiki.org/wiki/Extension:TextExtracts#API

        :param kwargs: parameters used in API call
        :return: plain-text or HTML of the page

        """
        params = {
            "action": "query",
            "prop": "extracts",
            "titles": self.title,
        }  # type: dict[str, Any]

        if self._wiki.get_extract_format() == ExtractFormat.HTML:
            # we do nothing, when format is HTML
            pass
        elif self._wiki.get_extract_format() == ExtractFormat.WIKI:
            params["explaintext"] = 1
            params["exsectionformat"] = "wiki"

        used_params = kwargs
        used_params.update(params)

        raw = self.__query(used_params)
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))
        self.__common_attributes(raw["query"])
        pages = raw["query"]["pages"]
        for k, v in pages.items():
            if k == "-1":
                self._attributes["pageid"] = -1
                return ""
            with self.__extract_builder_lock:
                self.__build_extracts(v)
            return v["extract"]
        return ""
    
    def __is_in_called_functions(self, func):
        with self.__called_functions_lock:
            return func in self.__called_functions

    def __called_functions_add(self, func):
        with self.__called_functions_lock:
            self.__called_functions.add(func)
        
    def __info(self):
        """
        https://www.mediawiki.org/w/api.php?action=help&modules=query%2Binfo
        https://www.mediawiki.org/wiki/API:Info
        """
        params = {
            "action": "query",
            "prop": "info",
            "titles": self.title,
            "inprop": "|".join(
                [
                    "protection",
                    "talkid",
                    "watched",
                    "watchers",
                    "visitingwatchers",
                    "notificationtimestamp",
                    "subjectid",
                    "associatedpage",
                    "url",
                    "preloadcontent",
                    "editintro",
                    "displaytitle",
                    "varianttitles",
                    "linkclasses",
                    "restrictiontypes",
                ]
            ),
        }
        raw = self.__query(params)
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))
        self.__common_attributes(raw["query"])
        pages = raw["query"]["pages"]
        for k, v in pages.items():
            if k == "-1":
                self._attributes["pageid"] = -1
                return self
            return self.__build_info(v)

    def __langlinks_func(self, **kwargs) -> PagesDict:
        """
        Returns langlinks of the page with respect to parameters

        API Calls for parameters:

        - https://www.mediawiki.org/w/api.php?action=help&modules=query%2Blanglinks
        - https://www.mediawiki.org/wiki/API:Langlinks

        :param page: :class:`WikipediaPage`
        :param kwargs: parameters used in API call
        :return: links to pages in other languages

        """
        params = {
            "action": "query",
            "prop": "langlinks",
            "titles": self.title,
            "lllimit": 500,
            "llprop": "url",
        }

        used_params = kwargs
        used_params.update(params)

        raw = self.__query(used_params)
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))
        self.__common_attributes(raw["query"])
        pages = raw["query"]["pages"]
        for k, v in pages.items():
            if k == "-1":
                self._attributes["pageid"] = -1
                return {}
            with self.__langlinks_lock:
                return self.__build_langlinks(v)
        return {}

    def __links_func(self, **kwargs) -> PagesDict:
        """
        Returns links to other pages with respect to parameters

        API Calls for parameters:

        - https://www.mediawiki.org/w/api.php?action=help&modules=query%2Blinks
        - https://www.mediawiki.org/wiki/API:Links

        :param page: :class:`WikipediaPage`
        :param kwargs: parameters used in API call
        :return: links to linked pages

        """
        params = {
            "action": "query",
            "prop": "links",
            "titles": self.title,
            "pllimit": 500,
        }

        used_params = kwargs
        used_params.update(params)

        raw = self.__query(used_params)
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))
        self.__common_attributes(raw["query"])
        pages = raw["query"]["pages"]
        for k, v in pages.items():
            if k == "-1":
                self._attributes["pageid"] = -1
                return {}

            while "continue" in raw:
                params["plcontinue"] = raw["continue"]["plcontinue"]
                raw = self.__query(params)
                v["links"] += raw["query"]["pages"][k]["links"]
            with self.__links_lock:
                return self.__build_links(v)
        return {}

    def __backlinks_func(self, **kwargs) -> PagesDict:
        """
        Returns backlinks from other pages with respect to parameters

        API Calls for parameters:

        - https://www.mediawiki.org/w/api.php?action=help&modules=query%2Bbacklinks
        - https://www.mediawiki.org/wiki/API:Backlinks

        :param page: :class:`WikipediaPage`
        :param kwargs: parameters used in API call
        :return: backlinks from other pages

        """
        params = {
            "action": "query",
            "list": "backlinks",
            "bltitle": self.title,
            "bllimit": 500,
        }

        used_params = kwargs
        used_params.update(params)

        raw = self.__query(used_params)
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))

        self.__common_attributes(raw["query"])
        v = raw["query"]
        while "continue" in raw:
            params["blcontinue"] = raw["continue"]["blcontinue"]
            raw = self.__query(params)
            v["backlinks"] += raw["query"]["backlinks"]
        with self.__backlinks_lock:
            return self.__build_backlinks(v)

    def __categories_func(self, **kwargs) -> PagesDict:
        """
        Returns categories for page with respect to parameters

        API Calls for parameters:

        - https://www.mediawiki.org/w/api.php?action=help&modules=query%2Bcategories
        - https://www.mediawiki.org/wiki/API:Categories

        :param page: :class:`WikipediaPage`
        :param kwargs: parameters used in API call
        :return: categories for page
        """
        params = {
            "action": "query",
            "prop": "categories",
            "titles": self.title,
            "cllimit": 500,
        }

        used_params = kwargs
        used_params.update(params)

        raw = self.__query(used_params)
        if 'warnings' in raw:
            log.warning("WARNING "+str(raw['warnings']))
        self.__common_attributes(raw["query"])
        pages = raw["query"]["pages"]
        for k, v in pages.items():
            if k == "-1":
                self._attributes["pageid"] = -1
                return {}
            with self.__categories_lock:
                return self.__build_categories(v)
        return {}

    def __query(self,  params: dict[str, Any]):
        """Queries Wikimedia API to fetch content."""
        # base_url = "https://" + page.language + ".wikipedia.org/w/api.php"
        language = self.language

        base_url = f"https://{language}.wikipedia.org/w/api.php"
        log.info(
            "Request URL: %s",
            base_url + "?" + "&".join([k + "=" + str(v) for k, v in params.items()]),
        )
        params["format"] = "json"
        params["redirects"] = 1
        
        try:
            r = self._wiki.get_session().get(base_url, params=params, **self._wiki.get_request_kwargs())
            r.raise_for_status()  # Raise an error for HTTP errors
            data = r.json()  # Parse JSON response

            # Check for errors in the API response
            if 'error' in data:
                raise ValueError(f"Error fetching data: {data['error']['info']}")

            return data
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Request failed: {e}")
        except ValueError as e:
            raise RuntimeError(f"API returned an error: {e}")


    def __build_extracts(self, extract):
        """Constructs summary of given page."""
        self._summary = ""
        self._section_mapping = defaultdict(list)

        self.__common_attributes(extract)

        section_stack = [self]
        section = None
        prev_pos = 0

        for match in re.finditer(RE_SECTION[self._wiki.get_extract_format()], extract["extract"]):
            if len(self._section_mapping) == 0:
                self._summary = extract["extract"][0 : match.start()].strip()
            elif section is not None:
                section._text = (extract["extract"][prev_pos : match.start()]).strip()

            section = self.__build_section(match)
            sec_level = section.level + 1

            if sec_level > len(section_stack):
                section_stack.append(section)
            elif sec_level == len(section_stack):
                section_stack.pop()
                section_stack.append(section)
            else:
                for _ in range(len(section_stack) - sec_level + 1):
                    section_stack.pop()
                section_stack.append(section)

            section_stack[len(section_stack) - 2]._section.append(section)
            # section_stack[sec_level - 1]._section.append(section)

            prev_pos = match.end()
            self._section_mapping[section.title].append(section)

        # pages without sections have only summary
        if self._summary == "":
            self._summary = extract["extract"].strip()

        if prev_pos > 0 and section is not None:
            section._text = extract["extract"][prev_pos:]


    def __build_section(self, match):
        """Creates section."""
        sec_title = ""
        sec_level = 2
        if self._wiki.get_extract_format() == ExtractFormat.WIKI:
            sec_title = match.group(2).strip()
            sec_level = len(match.group(1))
        elif self._wiki.get_extract_format() == ExtractFormat.HTML:
            sec_title = match.group(5).strip()
            sec_level = int(match.group(1).strip())

        section = WikipediaPageSection(self, sec_title, sec_level - 1)
        section._media = section._fetch_media()
        return section

    def __build_info(self, extract) -> "WikipediaPage":
        """Builds page from API call info."""
        self.__common_attributes(extract)
        for k, v in extract.items():
            self._attributes[k] = v

        return self

    def __build_langlinks(self, extract) -> PagesDict:
        """Builds page from API call langlinks."""
        self._langlinks = {}

        self.__common_attributes(extract)

        for langlink in extract.get("langlinks", []):
            lang_code = langlink['lang'].lower()
            try:
                language_enum = Language[lang_code.upper()]
            except KeyError:
                print(f"Invalid language code '{langlink['lang']}', defaulting to EN.")
                language_enum = Language.EN  
            p = WikipediaPage(
                wiki=self._wiki,
                title=langlink["*"],
                ns=Namespace.MAIN,
                language=language_enum,
                url=langlink["url"],
            )
            self._langlinks[language_enum.value] = p

        return self._langlinks

    def __build_links(self, extract) -> PagesDict:
        """Builds page from API call links."""
        self._links = {}

        self.__common_attributes(extract)

        for link in extract.get("links", []):
            lang_code = self.language.lower()
            try:
                language_enum = Language[lang_code.upper()]
            except ValueError:
                print("Invalid language code detected in links. Defaulting to EN.")
                language_enum = Language.EN  # Fallback to EN if the language code is invalid

            self._links[link["title"]] = WikipediaPage(
                wiki=self._wiki,
                title=link["title"],
                ns=int(link["ns"]),
                language=language_enum,
            )

        return self._links

    def __build_backlinks(self, extract) -> PagesDict:
        """Builds page from API call backlinks."""
        self._backlinks = {}

        self.__common_attributes(extract)

        for backlink in extract.get("backlinks", []):
            language_code = self.language.lower()

            try:
                language_enum = Language[language_code.upper()]
            except KeyError:
                print(f"Invalid language code '{language_code}' detected. Using EN as a fallback.")
                language_enum = Language.EN  # Fallback to EN if the language code is invalid

            self._backlinks[backlink["title"]] = WikipediaPage(
                wiki=self._wiki,
                title=backlink["title"],
                ns=int(backlink["ns"]),
                language=language_enum,
            )

        return self._backlinks

    def __build_categories(self, extract) -> PagesDict:
        """Builds page from API call categories."""
        self._categories = []

        self.__common_attributes(extract)

        for category in extract.get("categories", []):
            self._categories.append(category["title"])
        return self._categories

    def __common_attributes(self, extract):
        """Fills in common attributes for page."""
        common_attributes = ["title", "pageid", "ns", "redirects"]

        for attr in common_attributes:
            if attr in extract:
                self._attributes[attr] = extract[attr]

    # get an attribution. The attribution must be defined in ATTRIBUTES_MAPPING as key
    def __load_attribution(self, name):
        if name not in self.ATTRIBUTES_MAPPING:
            return self.__getattribute__(name)

        if name in self._attributes:
            return self._attributes[name]

        for function in self.ATTRIBUTES_MAPPING[name]:
            if not self.__is_in_called_functions(function):
                function()
                self.__called_functions_add(function)
                return self._attributes[name]

    @property
    def language(self) -> str:
        """
        Returns language of the current page.

        :return: language
        """
        return str(self._attributes["language"])

    @property
    def pageid(self) -> int:
        """Retrive the page id of a wikipedia page

        Returns:
            int: the page id
        """
        return self.__load_attribution("pageid")
    
    @property
    def protection(self) -> list:
        """List the protection level of each page.

        Returns:
            list: The protection level of the page.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("protection")

    @property
    def restrictiontypes(self) -> list:
        """Retrieve the restriction types that apply to a page.

        Returns:
            list: A list of strings representing the types of restrictions applied to the page.
                Common values include 'edit' and 'move'.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("restrictiontypes")

    
    @property
    def talkid(self) -> int:
        """Retrieve the page ID of the talk page for each non-talk page.

        Returns:
            int: The talk id.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("talkid")

    @property
    def watched(self) -> list:
        """List the watched status of each page.

        Returns:
            list: List of watched status of the page.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("watched")

    @property
    def watchers(self) -> int:
        """The number of watchers, if allowed.

        Returns:
            int: The number of watchers.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("watchers")

    @property
    def visitingwatchers(self) -> int:
        """The number of watchers of each page who have visited recent edits to that page, if allowed.

        Returns:
            int: The number of visiting watchers.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("visitingwatchers")

    @property
    def notificationtimestamp(self) -> str:
        """The watchlist notification timestamp of each page.

        Returns:
            str: The notification timestamp.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("notificationtimestamp")

    @property
    def subjectid(self) -> int:
        """The page ID of the parent page for each talk page.

        Returns:
            int: The subject id.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("subjectid")

    @property
    def associatedpage(self) -> str:
        """The prefixed title of the associated subject or talk page.

        Returns:
            str: The associated page title.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("associatedpage")



    @property
    def preloadcontent(self) -> str:
        """Gives the content to be shown in the editor when the page does not exist or while adding a new section.

        Returns:
            str: Preload content.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("preloadcontent")

    @property
    def editintro(self) -> str:
        """Gives the intro messages that should be shown to the user while editing this page or revision, as HTML.

        Returns:
            str: The edit intro message.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("editintro")

    @property
    def displaytitle(self) -> str:
        """Gives the manner in which the page title is actually displayed.

        Returns:
            str: The display title of the page.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("displaytitle")

    @property
    def varianttitles(self) -> dict:
        """Gives the display title in all variants of the site content language.

        Returns:
            list: The variant titles.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("varianttitles")

    @property
    def linkclasses(self) -> list:
        """Gives the additional CSS classes (e.g., link colors) used for links to this page if they were to appear on the page named by inlinkcontext.

        Returns:
            list: The link classes.
            `None`: if this field does not exist.
        """
        return self.__load_attribution("linkclasses")

            
    @property
    def title(self) -> str:
        """
        Returns title of the current page.

        :return: title
        """
        return str(self._attributes["title"])

    @property
    def namespace(self) -> int:
        """
        Returns namespace of the current page.

        :return: namespace
        """
        return int(self._attributes["ns"])

    def exists(self) -> bool:
        """
        Returns `True` if the current page exists, otherwise `False`.

        :return: if current page existst or not
        """
        return bool(self.pageid != -1)

    @property
    def summary(self) -> str:
        """
        Returns summary of the current page.

        :return: summary
        """
        if not self.__is_in_called_functions(self.extracts):
            self.extracts()
            self.__called_functions_add(self.extracts)
        return self._summary

    @property
    def sections(self) -> list[WikipediaPageSection]:
        """
        Returns all sections of the current page.

        :return: List of :class:`WikipediaPageSection`
        """
        if not self.__is_in_called_functions(self.extracts):
            self.extracts()
            self.__called_functions_add(self.extracts)
        return self._section

    def get_sections_by_title(
        self,
        title: str,
    ) -> list[WikipediaPageSection]:
        """
        Returns all section of the current page with given `title`.

        :param title: section title
        :return: :class:`WikipediaPageSection`
        """
        if not self.__is_in_called_functions(self.extracts):
            self.extracts()
            self.__called_functions_add(self.extracts)
        sections = self._section_mapping.get(title)
        if sections is None:
            return []
        return sections

    def get_section_by_id(self, section_id: int) -> WikipediaPageSection:
        """
        Returns the section of the current page with the given `section_id`.

        :param section_id: The ID of the section
        :return: :class:`WikipediaPageSection` if found, otherwise None
        """
        if not self.__is_in_called_functions(self.extracts):
            self.extracts()
            self.__called_functions_add(self.extracts)
        
        for section in self._section:
            if section.id == section_id:
                return section
        
        return None

    @property
    def text(self) -> str:
        """
        Returns text of the current page.

        :return: text of the current page
        """
        txt = self.summary
        if len(txt) > 0:
            txt += "\n\n"
        for sec in self.sections:
            txt += sec.full_text(level=2)
        return txt.strip()

    @property
    def langlinks(self) -> PagesDict:
        """
        Returns all language links to pages in other languages.

        This is wrapper for:

        * https://www.mediawiki.org/w/api.php?action=help&modules=query%2Blanglinks
        * https://www.mediawiki.org/wiki/API:Langlinks

        :return: :class:`PagesDict`
        """
        if not self.__is_in_called_functions(self.__langlinks_func ):
            self.__langlinks_func()
            self.__called_functions_add(self.__langlinks_func)
        with self.__langlinks_lock:
            return self._langlinks

    @property
    def links(self) -> PagesDict:
        """
        Returns all pages linked from the current page.

        This is wrapper for:

        * https://www.mediawiki.org/w/api.php?action=help&modules=query%2Blinks
        * https://www.mediawiki.org/wiki/API:Links

        :return: :class:`PagesDict`
        """
        if not self.__is_in_called_functions(self.__links_func):
            self.__links_func()
            self.__called_functions_add(self.__links_func)
        with self.__links_lock:
            return self._links

    @property
    def backlinks(self) -> PagesDict:
        """
        Returns all pages linking to the current page.

        This is wrapper for:

        * https://www.mediawiki.org/w/api.php?action=help&modules=query%2Bbacklinks
        * https://www.mediawiki.org/wiki/API:Backlinks

        :return: :class:`PagesDict`
        """
        if not self.__is_in_called_functions(self.__backlinks_func):
            self.__backlinks_func()
            self.__called_functions_add(self.__backlinks_func)
        with self.__backlinks_lock:
            return self._backlinks

    @property
    def categories(self) -> PagesDict:
        """
        Returns categories associated with the current page.

        This is wrapper for:

        * https://www.mediawiki.org/w/api.php?action=help&modules=query%2Bcategories
        * https://www.mediawiki.org/wiki/API:Categories

        :return: :class:`PagesDict`
        """
        if not self.__is_in_called_functions(self.__categories_func):
            self.__categories_func()
            self.__called_functions_add(self.__categories_func)
        with self.__categories_lock:
            return self._categories

    def __repr__(self):
        with self.__called_functions_lock:
            if len(self.__called_functions)!=0:
                return f"{self.title} (ns: {self.namespace})"
            return f"{self.title} (ns: {self.namespace})"
    
    @property
    def last_edited(self) -> str:
        """
        Returns the last edited timestamp of the page.

        :return: ISO8601 timestamp of the last edit.
        """
        return self.__load_attribution("touched")

    @property
    def redirect(self) -> bool:
        """
        Returns whether the page is a redirect.

        :return: True if the page is a redirect, False otherwise.
        """
        if "redirect" not in self._attributes:
            # Fetch via ATTRIBUTES_MAPPING if not already loaded
            self.__load_attribution("redirect")
        return self._attributes.get("redirect", False)
    
    @property
    def length(self) -> int:
        """
        Returns the size of the page content in bytes.

        :return: Length of the page content.
        """
        return self.__load_attribution("length")

    @property
    def templates(self) -> list[str]:
        """
        Returns a list of templates used in the page.

        This is a wrapper for:
        * https://www.mediawiki.org/wiki/API:Templates

        :return: List of template names.
        """
        params = {
            "action": "query",
            "prop": "templates",
            "titles": self.title,
            "tllimit": 500,
        }
        raw_data = self.__query(params)
        templates = []
        for page in raw_data.get("query", {}).get("pages", {}).values():
            templates.extend(t["title"] for t in page.get("templates", []))
        return templates

    @property
    def external_links(self) -> list[str]:
        """
        Returns external links from the page.

        This is a wrapper for:
        * https://www.mediawiki.org/wiki/API:Extlinks

        :return: List of external URLs.
        """
        params = {
            "action": "query",
            "prop": "extlinks",
            "titles": self.title,
            "ellimit": 500,
        }
        raw_data = self.__query(params)
        links = []
        for page in raw_data.get("query", {}).get("pages", {}).values():
            links.extend(el["*"] for el in page.get("extlinks", []))
        return links

    @property
    def geo_coordinates(self) -> dict:
        """
        Returns geographic coordinates (latitude, longitude) if available.

        This is a wrapper for:
        * https://www.mediawiki.org/wiki/API:Coordinates

        :return: Dictionary with 'lat' and 'lon' keys, or empty dict if unavailable.
        """
        params = {
            "action": "query",
            "prop": "coordinates",
            "titles": self.title,
            "colimit": 1,
        }
        raw_data = self.__query(params)
        for page in raw_data.get("query", {}).get("pages", {}).values():
            coords = page.get("coordinates", [{}])[0]
            return {"lat": coords.get("lat"), "lon": coords.get("lon")}
        return {}

    @property
    def infobox(self) -> str:
        """
        Retrieves the raw infobox wikitext of the page if present.

        The infobox is returned as raw wikitext, allowing the client to parse
        it as needed. This approach provides flexibility for handling the infobox
        in a custom manner based on the application's requirements.

        The raw wikitext includes: Infobox fields and values, Nested templates (if present), Any additional formatting or metadata as defined in the page content
            
        Example response::

            {{Infobox French commune
            |name                   = Paris
            |commune status         = [[Capital city]], [[Communes of France|commune]], and [[Departments of France|department]]
            |image                  = {{multiple image
            |border            = infobox
            |perrow            = 1/3/2/1
            |total_width       = 290
            |caption_align = center

        Example Usage::

            page = wiki_client.get_page_by_title("Python (programming language)")
            raw_infobox = page.infobox
            lines = raw_infobox.split("\n")
            fields = {}
            for line in lines:
                if "=" in line and not line.strip().startswith("|}"):
                    key, value = line.split("=", 1)
                    fields[key.strip()] = value.strip()
            print(fields)

        Note: If the page does not contain an infobox, an empty string is returned. Parsing and extracting specific fields or values should be done by the client.

        :return: The raw wikitext of the infobox, or an empty string if not present.
        """
        params = {
            "action": "parse",
            "page": self.title,
            "prop": "wikitext",
        }
        raw_data = self.__query(params)
        wikitext = raw_data.get("parse", {}).get("wikitext", {}).get("*", "")

        if "{{Infobox" in wikitext:
            infobox_start = wikitext.split("{{Infobox", 1)[1]
            infobox_content = []
            brace_stack = ["{{"]

            for i, char in enumerate(infobox_start):
                infobox_content.append(char)

                if char == '{' and i + 1 < len(infobox_start) and infobox_start[i + 1] == '{':
                    brace_stack.append('{{')
                elif char == '}' and i + 1 < len(infobox_start) and infobox_start[i + 1] == '}':
                    brace_stack.pop()
                    if not brace_stack:
                        infobox_content.append('}')
                        break
            print("{{Infobox" + ''.join(infobox_content))
            return "{{Infobox" + ''.join(infobox_content)

        return ""

    
    @property
    def image_url(self) -> str:
        """
        Returns the primary image URL of the page if available.

        :return: URL of the primary image or an empty string if not available.
        """
        if "image_url" in self._attributes and self._attributes["image_url"]:
            return self._attributes["image_url"]

        params = {
            "action": "query",
            "prop": "pageimages",
            "titles": self.title,
            "pithumbsize": 500,  # Thumbnail size in pixels
        }
        raw_data = self.__query(params)
        self.__common_attributes(raw_data.get("query", {}))
        pages = raw_data.get("query", {}).get("pages", {})

        for _, page_data in pages.items():
            self._attributes["image_url"] = page_data.get("thumbnail", {}).get("source", "")
            return self._attributes["image_url"]

        self._attributes["image_url"] = ""
        return ""
        

    VALID_PROPERTIES = {
        "ids", "flags", "timestamp", "user", "userid", "size", "slotsize", "sha1",
        "slotsha1", "contentmodel", "comment", "parsedcomment", "content",
        "tags", "roles"
    }
    """
    Defines valid properties (`rvprop`) for querying revision metadata in the MediaWiki API.

    Purpose:
    - Specifies which metadata fields to include in the response when fetching revisions.

    Examples:
    - To fetch only revision IDs, users, and timestamps:
    rvprop = ["ids", "user", "timestamp"]

    - To fetch detailed content-related fields:
    rvprop = ["content", "contentmodel"]

    Warnings:
    - Including `content` caps `rvlimit` at 50 for performance reasons.

    Attributes:
    - `ids`: Revision ID.
    - `flags`: Flags associated with the revision (e.g., `minor` for minor edits).
    - `timestamp`: Timestamp of the revision in ISO 8601 format.
    - `user`: Username of the revision author.
    - `comment`: Edit summary provided by the author, if available.
    """

    DEPRECATED_PROPERTIES = {
        "parsetree", "rvexpandtemplates", "rvgeneratexml", "rvparse", "rvdiffto", "rvdifftotext"
    }
    """
    Specifies deprecated properties for querying revisions.

    Purpose:
    - Retains backward compatibility with older versions of the MediaWiki API.

    Warnings:
    - Deprecated properties will raise warnings when used. Replace them with the recommended alternatives.

    Examples:
    - `rvexpandtemplates` → Use `action=expandtemplates`.
    - `rvdiffto` → Use `action=compare`.
    """

    def validate_revisions_params(self, **kwargs) -> dict:
        """
        Validates and constructs parameters for querying revisions using the MediaWiki API.
        Ensures that parameters provided for fetching revisions conform to the MediaWiki API specifications.
        Detects invalid or deprecated properties and raises warnings.

        :param kwargs: Query parameters for revisions.
            - **rvlimit** (int): Number of revisions to fetch. Must be between 1 and 500.
            - **rvprop** (list[str]): List of properties to include in the response. Must be valid properties from `VALID_PROPERTIES`.
            - **rvdir** (str): Direction to list revisions. Can be "newer" (oldest first) or "older" (default).
            - **rvstart** (str): ISO timestamp to start fetching revisions from.
            - **rvend** (str): ISO timestamp to stop fetching revisions at.
        :return: A dictionary of validated query parameters for the MediaWiki API.
        :raises ValueError: If an invalid parameter or value is provided, DeprecationWarning for deprecated properties.

        .. note::
            - Parameters are validated against `VALID_PROPERTIES` and `DEPRECATED_PROPERTIES`.
            - Any deprecated properties used will raise a warning.

        **Example Usage**::

            validated_params = my_wrapper.validate_revisions_params(
                rvlimit=10,
                rvprop=["ids", "user", "timestamp", "comment"],
                rvdir="older",
                rvstart="2024-01-01T00:00:00Z"
            )
        """
        params = {
            "action": "query",
            "prop": "revisions",
            "titles": self.title,
            "format": "json",
        }

        if "rvlimit" in kwargs:
            if not 1 <= kwargs["rvlimit"] <= 500:
                raise ValueError("rvlimit must be between 1 and 500")
            params["rvlimit"] = kwargs["rvlimit"]

        if "rvprop" in kwargs:
            invalid_props = set(kwargs["rvprop"]) - self.VALID_PROPERTIES - self.DEPRECATED_PROPERTIES
            if invalid_props:
                raise ValueError(f"Invalid rvprop values: {invalid_props}")
            deprecated_props = set(kwargs["rvprop"]) & self.DEPRECATED_PROPERTIES
            if deprecated_props:
                warnings.warn(
                    f"Deprecated rvprop values: {deprecated_props}. Use alternatives where possible.",
                    DeprecationWarning
                )
            params["rvprop"] = "|".join(kwargs["rvprop"])

        if "rvdir" in kwargs:
            if kwargs["rvdir"] not in {"newer", "older"}:
                raise ValueError("rvdir must be either 'newer' or 'older'")
            params["rvdir"] = kwargs["rvdir"]

        if "rvstart" in kwargs:
            params["rvstart"] = kwargs["rvstart"]

        if "rvend" in kwargs:
            params["rvend"] = kwargs["rvend"]

        return params


    def get_revisions(self, filter_substantive: bool = True, **kwargs) -> Optional[list[dict]]:
        """
        Fetches revisions for the current page using specified query parameters.
        Provides detailed metadata about the revisions of a Wikipedia page and optionally filters out minor edits.

        :param filter_substantive: 
            If True, excludes minor edits (marked with the "minor" flag in `flags`).
            Minor edits typically involve formatting or other non-content changes.
        :param kwargs: Additional parameters validated by `validate_revisions_params`.
        :return: A list of revision dictionaries, each containing:
        - **revid**: Revision ID.
        - **flags**: Flags for the revision (e.g., `minor`).
        - **timestamp**: Timestamp of the revision.
        - **user**: Username of the editor.
        - **comment**: Edit summary, if available.
        :raises ValueError: If an invalid parameter or value is provided. RuntimeError if the API request fails.

        **Example Usage**::
            
                revisions = my_wrapper.get_revisions(rvlimit=5, rvprop=["ids", "user", "timestamp", "comment"])
                for rev in revisions:
                    print(f"Revision ID: {rev['revid']}, User: {rev['user']}, Timestamp: {rev['timestamp']}")
                    print(f"Comment: {rev['comment']}")
        """
        log_message = "Filtering out non-substantive edits (flagged as 'minor')." if filter_substantive else "Including all edits, including minor changes."
        log.info(log_message)

        params = self.validate_revisions_params(**kwargs)
        raw_data = self.__query(params)
        pages = raw_data.get("query", {}).get("pages", {})
        if not pages:
            return []

        page_data = next(iter(pages.values()), {})
        revisions = page_data.get("revisions", [])

        if filter_substantive:
            revisions = [rev for rev in revisions if "minor" not in rev.get("flags", [])]

        return revisions


    def summarize_recent_revisions(self, rvlimit: int = 5) -> list[dict]:
        """
        Summarizes recent revisions for the current page.

        :param rvlimit: Number of recent revisions to summarize (default: 5).
        :return: A list of dictionaries with revision summaries (user, timestamp, comment).
        """
        revisions = self.get_revisions(rvlimit=rvlimit, rvprop=["ids", "user", "timestamp", "comment"])
        return [
            {
                "revid": rev.get("revid"),
                "user": rev.get("user"),
                "timestamp": rev.get("timestamp"),
                "comment": rev.get("comment"),
            }
            for rev in revisions
        ]

    def fetch_revision_diff(self, old_revid: int, new_revid: int) -> str:
        """
        Fetches the difference between two revisions.

        :param old_revid: Revision ID of the older revision.
        :param new_revid: Revision ID of the newer revision.
        :return: The diff as a string.
        """
        params = {
            "action": "compare",
            "fromrev": old_revid,
            "torev": new_revid,
            "format": "json",
        }
        raw_data = self.__query(params)
        return raw_data.get("compare", {}).get("*", "")

    def fetch_latest_revisions_diff(self, filter_substantive: bool = True) -> Optional[dict]:
        """
        Fetches the difference between the latest two revisions.
        Provides a quick comparison between the latest two revisions, enabling users to track recent changes
        
        :param filter_substantive: If True, filters non-substantive changes.
        :return: A dictionary containing:
        - `fromrev`: Older revision ID.
        - `torev`: Newer revision ID.
        - `diff`: Highlighted differences.
        or None if there are not enough revisions to compare.
        :raises RuntimeError: If the API request fails.

        **Example Usage**::
            
                diff = my_wrapper.fetch_latest_revisions_diff(filter_substantive=True)
                if diff:
                    print(f"Changes from revision {diff['fromrev']} to {diff['torev']}:")
                    print(diff['diff'])
        """
        revisions = self.get_revisions(rvprop=["ids", "flags"], rvlimit=2)

        if filter_substantive:
            revisions = [rev for rev in revisions if "minor" not in rev.get("flags", [])]

        if len(revisions) < 2:
            return None

        old_revid = revisions[1]["revid"]
        new_revid = revisions[0]["revid"]
        diff = self.fetch_revision_diff(old_revid, new_revid)

        return {
            "fromrev": old_revid,
            "torev": new_revid,
            "diff": diff,
        }

    def fetch_diffs_in_timeframe(self, start_time: str, end_time: str = None) -> list[dict]:
        """
        Fetches differences between all revisions within a specified timeframe. Allows detailed tracking of changes over a specific period.

        :param start_time: Start timestamp in ISO format.
        :param end_time: Optional end timestamp. Defaults to the current time.
        :return: A list of dictionaries with revision differences. Each dictionary contains:
        - `fromrev`: Older revision ID.
        - `torev`: Newer revision ID.
        - `timestamp`: Timestamp of the newer revision.
        - `user`: Username of the editor.
        - `comment`: Edit summary, if available.
        - `diff`: Highlighted differences between revisions.
        :raises RuntimeError: If the API request fails. ValueError if there are not enough revisions to compare.
        
        **Example Usage**::

            changes = my_wrapper.fetch_diffs_in_timeframe("2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z")
            for change in changes:
                print(f"Changes from revision {change['fromrev']} to {change['torev']} by {change['user']} at {change['timestamp']}")
                print(f"Edit summary: {change['comment']}")
                print(change['diff'])
        """
        revisions = self.get_revisions(rvstart=start_time, rvend=end_time, rvprop=["ids", "user", "timestamp", "comment"])

        if len(revisions) < 2:
            return [{"message": "Not enough revisions to calculate diffs in the specified timeframe."}]

        if len(revisions) > 50:
            warnings.warn("Fetching diffs for a large number of revisions may be slow.", UserWarning)

        changes = []
        for i in range(len(revisions) - 1):
            old_revid = revisions[i + 1]["revid"]
            new_revid = revisions[i]["revid"]
            diff = self.fetch_revision_diff(old_revid, new_revid)

            changes.append({
                "fromrev": old_revid,
                "torev": new_revid,
                "timestamp": revisions[i]["timestamp"],
                "user": revisions[i]["user"],
                "comment": revisions[i].get("comment", ""),
                "diff": diff,
            })

        return changes
