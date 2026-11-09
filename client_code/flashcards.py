# setup path to import wikipediaapi
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame
import random
import re
from wikipediaapi import WikipediaClient, Language

def extract_infobox_fields(raw_infobox: str) -> dict:
    """
    Extracts key-value pairs from the raw infobox wikitext.

    Args:
        raw_infobox (str): Raw wikitext of the infobox.

    Returns:
        dict: Extracted key-value pairs as a dictionary.
    """
    fields = {}
    lines = raw_infobox.split("\n")
    for line in lines:
        if "=" in line and not line.strip().startswith("|}"):
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    return fields

def clean_infobox_value(value: str) -> str:
    """
    Cleans infobox values by removing wiki markup, HTML tags, and extraneous text.

    Args:
        value (str): Raw value from the infobox.

    Returns:
        str: Cleaned value.
    """
    value = re.sub(r"\[\[|\]\]", "", value)
    value = re.sub(r"\{\{.*?\}\}", "", value)
    value = re.sub(r"<.*?>", "", value)
    value = re.sub(r"&nbsp;", " ", value)
    value = re.sub(r"\|.*", "", value)
    return value.strip()

def flashcard_maker(destination_name: str):
    """
    Creates flashcards from the infobox of a Wikipedia page.

    Args:
        destination_name (str): The title of the Wikipedia page.

    Returns:
        list: List of flashcards as tuples (question, answer).
    """
    wiki_client = WikipediaClient(user_agent="FlashcardMaker/1.0", language=Language.EN)
    page = wiki_client.get_page_by_title(destination_name)

    raw_infobox = page.infobox
    if not raw_infobox:
        print(f"No infobox found for '{destination_name}'. Limited details available.")
        return []

    infobox_fields = extract_infobox_fields(raw_infobox)
    flashcards = []
    for key, value in infobox_fields.items():
        if any(exclude in key for exclude in ["image", "caption", "alt", "data", "blank"]):
            continue
        cleaned_value = clean_infobox_value(value)
        if cleaned_value:
            cleaned_key = key.lstrip("|").replace("_", " ").capitalize()
            question = f"What is the {cleaned_key} of {destination_name}?"
            flashcards.append((question, cleaned_value))

    return flashcards

def run_flashcards(destination_name: str):
    """
    Runs a flashcard quiz based on the Wikipedia page's infobox.

    Args:
        destination_name (str): The title of the Wikipedia page.
    """
    flashcards = flashcard_maker(destination_name)
    if not flashcards:
        print("No flashcards available. Exiting.")
        return

    random.shuffle(flashcards)
    pygame.init()
    screen_width, screen_height = 800, 600
    background_color = (245, 245, 245)
    text_color = (0, 0, 0)
    button_color = (200, 200, 200)
    button_hover_color = (180, 180, 180)
    font = pygame.font.Font(None, 36)
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption(f"Flashcards for {destination_name}")
    current_index = 0
    show_answer = False
    button_width, button_height = 120, 50
    next_button_rect = pygame.Rect(
        (screen_width - button_width) // 2,
        screen_height - 100,
        button_width,
        button_height,
    )

    def draw_flashcard():
        screen.fill(background_color)
        if current_index < len(flashcards):
            question, answer = flashcards[current_index]
            text = question if not show_answer else f"Answer: {answer}"
        else:
            text = "No more flashcards."
        rendered_text = font.render(text, True, text_color)
        text_rect = rendered_text.get_rect(center=(screen_width // 2, screen_height // 2))
        screen.blit(rendered_text, text_rect)
        pygame.draw.rect(
            screen,
            button_hover_color if next_button_rect.collidepoint(pygame.mouse.get_pos()) else button_color,
            next_button_rect,
        )
        button_text = font.render("Next", True, text_color)
        button_text_rect = button_text.get_rect(center=next_button_rect.center)
        screen.blit(button_text, button_text_rect)
        pygame.display.flip()

    running = True
    while running:
        draw_flashcard()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                show_answer = not show_answer
            elif event.type == pygame.MOUSEBUTTONDOWN and next_button_rect.collidepoint(event.pos):
                show_answer = False
                current_index = (current_index + 1) % len(flashcards)

    pygame.quit()

if __name__ == "__main__":
    destination_name = input("Enter the name of the destination: ")
    run_flashcards(destination_name)

