import os
from dotenv import load_dotenv
from openai import OpenAI
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wikipediaapi import WikipediaClient, Language

load_dotenv()

class LLMRevisionsHelper:
    """
    Helper class for interacting with Wikipedia revisions and analyzing changes using an LLM.
    Demonstrates the use of an LLM to summarize, compare, and analyze Wikipedia revisions meaningfully, as
    well as the ease of use of the WikipediaClient for fetching revision data.
    """

    def __init__(self):
        self.__client = OpenAI()
        self.__wiki_client = WikipediaClient(user_agent="RevisionsApp/1.0", language=Language.EN)

    def chat(self, prompt: str) -> str:
        """
        Interacts with an LLM to generate a response based on the provided prompt.
        """
        completion = self.__client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        )
        return completion.choices[0].message.content

    def summarize_revisions(self, title: str, rvlimit: int = 5) -> str:
        """
        Fetches recent revisions for a Wikipedia page and summarizes the changes.

        :param title: The title of the Wikipedia page.
        :param rvlimit: Number of revisions to retrieve (default: 5).
        """
        page = self.__wiki_client.get_page_by_title(title)
        revisions = page.get_revisions(rvprop=["ids", "user", "timestamp", "comment"], rvlimit=rvlimit)

        if not revisions:
            return f"No revisions found for the page '{title}'."

        prompt = f"Summarize the recent revisions of the Wikipedia page '{title}':\n\n"
        for rev in revisions:
            prompt += (
                f"- Revision by {rev['user']} on {rev['timestamp']}:\n"
                f"  Comment: {rev.get('comment', 'No comment provided.')}\n\n"
            )
        prompt += (
            "Analyze the significance of these changes and their potential impact on the page's content."
        )
        return self.chat(prompt)

    def compare_latest_revisions(self, title: str, filter_substantive: bool = True) -> str:
        """
        Compares the two most recent revisions of a Wikipedia page.

        :param title: The title of the Wikipedia page.
        :param filter_substantive: If True, only substantive revisions are compared.
        """
        page = self.__wiki_client.get_page_by_title(title)
        diff = page.fetch_latest_revisions_diff(filter_substantive=filter_substantive)

        if not diff:
            return f"Not enough revisions found for the page '{title}' to compare."

        prompt = (
            f"Compare the following two revisions of the Wikipedia page '{title}':\n\n"
            f"Revision 1 (fromrev: {diff['fromrev']}):\n"
            f"Diff:\n{diff['diff'][:500]}...\n\n"
            f"Revision 2 (torev: {diff['torev']}):\n"
            f"Diff:\n{diff['diff'][:500]}...\n\n"
            f"Analyze the key differences, their impact on content quality, and whether they are substantive."
        )
        return self.chat(prompt)

    def fetch_diffs_in_timeframe(self, title: str, start_time: str, end_time: str = None) -> str:
        """
        Fetches and analyzes differences between revisions within a specified timeframe.

        :param title: The title of the Wikipedia page.
        :param start_time: Start timestamp in ISO format.
        :param end_time: End timestamp in ISO format (optional).
        """
        page = self.__wiki_client.get_page_by_title(title)
        diffs = page.fetch_diffs_in_timeframe(start_time=start_time, end_time=end_time)

        if not diffs or 'message' in diffs[0]:
            return f"No diffs found in the specified timeframe for '{title}'."

        prompt = f"Analyze the following diffs for the Wikipedia page '{title}':\n\n"
        for diff in diffs[:3]:  # Limit to 3 for demonstration
            prompt += (
                f"- From Revision {diff['fromrev']} to {diff['torev']} by {diff['user']} on {diff['timestamp']}:\n"
                f"  Comment: {diff.get('comment', 'No comment provided')}\n"
                f"  Diff:\n{diff['diff'][:500]}...\n\n"
            )
        prompt += "Summarize the trends and potential motivations behind these changes."
        return self.chat(prompt)

    def fetch_and_analyze_latest_revisions(self, title: str):
        """
        Fetches and analyzes the difference between the latest two revisions of a Wikipedia page.

        :param title: The title of the Wikipedia page.
        """
        page = self.__wiki_client.get_page_by_title(title)
        latest_diff = page.fetch_latest_revisions_diff()

        if not latest_diff:
            print(f"No sufficient revisions found for the page '{title}' to analyze.")
            return

        summary = self.chat(
            f"Analyze the following revision differences for '{title}':\n"
            f"From Revision {latest_diff['fromrev']} to {latest_diff['torev']}:\n"
            f"{latest_diff['diff'][:500]}...\n"
            "Summarize the changes and assess their potential impact on the page's content."
        )
        print("\nLatest Revision Analysis:\n", summary)

if __name__ == "__main__":
    llm_revisions_helper = LLMRevisionsHelper()

    # Hardcoded values for demonstration
    page_title = "2024 United States Presidential Election"
    start_time = "2024-12-01T00:00:00Z"
    end_time = None  # Use None for open-ended timeframe

    print("\nWikipedia Revisions Analysis Tool Demo")
    print("Use Cases:")
    print("1 - Summarize recent revisions for a Wikipedia page.")
    print("2 - Compare the two most recent revisions for a Wikipedia page.")
    print("3 - Fetch and analyze differences in revisions within a specified timeframe.")
    print("4 - Fetch and analyze the latest revision differences.\n")

    option = input("Enter the number corresponding to your desired use case (1-4): ")

    if option == "1":
        print("\nRunning Use Case 1: Summarize recent revisions.")
        summary = llm_revisions_helper.summarize_revisions(page_title, rvlimit=5)
        print("\nRevisions Summary:\n", summary)
    elif option == "2":
        print("\nRunning Use Case 2: Compare the two most recent revisions.")
        comparison = llm_revisions_helper.compare_latest_revisions(page_title)
        print("\nRevisions Comparison:\n", comparison)
    elif option == "3":
        print("\nRunning Use Case 3: Fetch diffs in a specified timeframe.")
        timeframe_summary = llm_revisions_helper.fetch_diffs_in_timeframe(
            page_title, start_time=start_time, end_time=end_time
        )
        print("\nTimeframe Diffs Summary:\n", timeframe_summary)
    elif option == "4":
        print("\nRunning Use Case 4: Fetch and analyze the latest revision differences.")
        llm_revisions_helper.fetch_and_analyze_latest_revisions(page_title)
    else:
        print("\nInvalid selection. Please choose a number between 1 and 4.")
