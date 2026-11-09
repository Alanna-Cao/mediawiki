# setup path to import wikipediaapi
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wikipediaapi import WikipediaClient, Language, WikipediaPage

load_dotenv()

class LLMHelper:
    """
    Helper class for determining whether differences exist/influence the semantics of different language translations
    of the same Wikipedia page. This is done using an LLM to compare the translations and provide insights.
    """
    def __init__(self):
        self.__client = OpenAI()
        
    def chat(self, prompt:str):
        """
        Interacts with an LLM to generate a response based on the provided prompt.
        """
        completion = self.__client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return completion.choices[0].message.content
    
        
    def compare_language_difference(self, title, lang1, lang2):
        """
        Compares the translations of a Wikipedia page in two different languages and determines if there are any differences.
        """
        lang1_client = WikipediaClient(user_agent="MyApp/1.0", language=lang1)
        lang2_client = WikipediaClient(user_agent="MyApp/1.0", language=lang2)
        try:
            page_lang1 = lang1_client.get_page_by_title(title)
            page_lang2 = lang2_client.get_page_by_title(title)
            
            lang1_raw_text = page_lang1.extracts()
            lang2_raw_text = page_lang2.extracts()
            prompt = (
                f"Compare the following translations in different languages and explain the differences:\n\n"
                f"Translation 1: {lang1_raw_text}\n"
                f"Translation 2: {lang2_raw_text}\n\n"
                f"Output format:\n"
                f"- If they have the same meaning, output: 'Same meaning'.\n"
                f"- If they are different, output: 'Difference: <detailed explanation>'.\n"
            )
            return self.chat(prompt)
        except ValueError as e:
            print(f"Error: {e}\n")

if __name__=="__main__":
    llm_helper = LLMHelper()
    difference = llm_helper.compare_language_difference("Python Software Foundation", 
                                           lang1=Language.EN,
                                           lang2=Language.ES
                                        )
    print(difference)