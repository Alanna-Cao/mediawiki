# setup path to import wikipediaapi
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wikipediaapi import WikipediaClient, WikipediaPageSection, Language
from fpdf import FPDF
import textwrap
import requests
from PIL import Image
from io import BytesIO


def summarize_section(section: "WikipediaPageSection", max_sentences=1) -> str:
    """
    Summarizes the text of a section to the specified number of sentences.
    """
    sentences = section.text.split(". ")
    summary = ". ".join(sentences[:max_sentences]).strip()
    if len(sentences) > max_sentences:
        summary += "..."
    return summary


def format_sections(section: "WikipediaPageSection", level=0) -> str:
    """
    Formats the sections and subsections with summaries.
    """
    indent = "    " * level
    summary = summarize_section(section)
    formatted_text = f"{indent}- {section.title}\n"
    if summary:
        wrapped_summary = textwrap.fill(
            f"Summary: {summary}", width=80, subsequent_indent=" " * (level * 4 + 2)
        )
        formatted_text += f"{indent}  {wrapped_summary}\n\n"
    for subsection in section.sections:
        formatted_text += format_sections(subsection, level + 1)
    return formatted_text


def clean_text(text: str) -> str:
    """
    Removes or replaces characters not supported by the 'latin-1' codec.
    """
    return text.encode("latin-1", errors="replace").decode("latin-1")


def fetch_and_save_sections(page_title: str, file_name: str = "output.pdf"):
    """
    Fetches a Wikipedia page, extracts sections, and saves them to a PDF file.
    """
    wiki_client = WikipediaClient(
        user_agent="SectionFormatter/1.0", language=Language.EN
    )
    page = wiki_client.get_page_by_title(page_title)

    metadata = {
        "Title": page.title,
        "Page ID": page.pageid,
        "Language": page.language,
        "Image URL": page.image_url,
        "Namespace": page.namespace,
        "Last Edited": page.last_edited,
        "Redirect": page.redirect, # new
        "Page Length": page.length,
        "Protection": page.protection,
        "Talk Page ID": page.talkid,
        "Watchers": page.watchers,
        "Visiting Watchers": page.visitingwatchers,
        "Notification Timestamp": page.notificationtimestamp,
        "Associated Page": page.associatedpage, # new
        "Display Title": page.displaytitle,
        "Preload Content": page.preloadcontent,
        "Variant Titles": page.varianttitles, # new
        "Link Classes": page.linkclasses, # new
        "Geo Coordinates": page.geo_coordinates # new
    }

    # Prepare text output for sections and metadata
    page_summary = page.summary.strip()
    formatted_sections = f"--- Sections and Subsections for '{page_title}' ---\n\n"
    for section in page.sections:
        formatted_sections += format_sections(section)

    # Create the PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add metadata
    pdf.multi_cell(0, 10, clean_text("--- Page Metadata ---"))
    for key, value in metadata.items():
        pdf.multi_cell(0, 10, clean_text(f"{key}: {value}"))

    # Add image if available
    if metadata["Image URL"]:
        try:
            # response = requests.get(metadata["Image URL"])
            response = requests.get(metadata["Image URL"], headers={"User-Agent": "YourAppName/1.0 (your.email@example.com)"})
        
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            if image.mode != "RGB":
                image = image.convert("RGB")

            
            temp_image_path = "temp_image.jpg"
            image.save(temp_image_path, format="JPEG")

            pdf.image(temp_image_path, x=10, y=pdf.get_y() + 10, w=100)
            pdf.ln(60)  # Adjust spacing for the image
        except Exception as e:
            print(f"Could not add image: {e}")

    # Add page summary
    pdf.ln()
    pdf.multi_cell(0, 10, clean_text(f"--- Summary for '{page_title}' ---"))
    pdf.multi_cell(0, 10, clean_text(page_summary))

    # Add sections and subsections
    pdf.ln()
    pdf.multi_cell(0, 10, clean_text(formatted_sections))

    # Save the PDF
    pdf.output(file_name)
    print(f"PDF report saved to {file_name}")


if __name__ == "__main__":
    page_title = input("Enter the title of the Wikipedia page: ")
    fetch_and_save_sections(page_title)
