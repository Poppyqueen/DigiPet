# books_construct.py

import os
import sys

# --- TEMPORARY FIX FOR DIRECT EXECUTION ---
# This block allows the script to find the 'utils' package
# when run directly from its current location.
# Assuming 'utils' is in the parent directory of this script's location
# This adds the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
# -------------------------------------------

from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json
import time

from ai_managers.ai_utils.ai_loader import AIConfiguration

# --- Structure for the individual book definition ---
class Chapter(BaseModel):
    """Represents a single chapter in a book."""
    title: str = Field(description="The title of the chapter")
    content: str = Field(description="The full content of the chapter")

class ItemDefinition(BaseModel):
    """
    Represents the data required to define a single book for creation.
    Excludes the ID as per requirements.
    """
    name: str = Field(description="A unique string identifier for the book.")
    descriptions: List[str] = Field(description="A list of strings providing descriptions for the book.")
    static: bool = Field(default=False, description="This should always be false for our books")
    type: List[str] = Field(default=["book"], description="This should always be ['book']")
    chapters: List[Chapter] = Field(description="A list of chapters in the book")
    is_locked: bool = Field(default=True, description="This should always be true for our books")

# Pydantic models for the enhanced three-step AI call process
class ChapterOutline(BaseModel):
    title: str = Field(description="The chapter title")
    outline: str = Field(description="Detailed outline/summary of what this chapter should cover, including key points, themes, and how it connects to other chapters")

class InitialBookSetup(BaseModel):
    book_name: str = Field(description="The generated name of the book.")
    descriptions: List[str] = Field(description="A list of 2-3 descriptive strings about the book.")
    chapter_outlines: List[ChapterOutline] = Field(
        description="A list of 3 to 7 chapter outlines, each with title and detailed outline for coherent book structure."
    )

class ChapterContent(BaseModel):
    content: str = Field(
        description="The full content of the chapter. Should be substantial, engaging, and appropriate for the book's theme."
    )

class books_writer:

    def __init__(self, select_model="gemini-flash-latest", select_provider="gemini"):
        self.llm_client = AIConfiguration(provider=select_provider, model=select_model, mode="simple_ai").get_client()

    def _generate_book_outline(self, book_concept: str) -> InitialBookSetup | None:
        """
        First AI call: Generates the book name, descriptions, and detailed chapter outlines.
        """
        system_prompt = """
You are an expert book architect helping to create comprehensive, coherent book structures.

Given a book concept, you need to:

1. Generate a creative and fitting book title
2. Create 2-3 descriptive strings that capture the essence and appeal of the book
3. Design 3-7 chapter outlines that form a logical, coherent progression

For each chapter, provide:
- A compelling chapter title
- A detailed outline that includes:
  * Key points and themes to be covered
  * How this chapter connects to previous and following chapters
  * Specific topics, concepts, or narrative elements to include
  * The chapter's role in the overall book structure

The chapter outlines should be detailed enough that another AI could write the full chapter content based solely on:
- The chapter's outline
- The book's overall theme
- Context from neighboring chapters

Ensure the book flows logically from beginning to end, with each chapter building upon previous ones and setting up future ones.
"""
        user_prompt = f"Develop a comprehensive book structure with detailed chapter outlines based on the concept: '{book_concept}'."

        print(f"  Calling AI (Step 1: Book Structure) for concept: '{book_concept}'")
        response = self.llm_client.structured_output(
            system=system_prompt,
            user=user_prompt,
            structure=InitialBookSetup
        )

        if response:
            print(f"  [AI Response] Book Name: '{response.book_name}', Chapters: {len(response.chapter_outlines)}")
        else:
            print(f"  [AI Response] Failed to generate book outline for '{book_concept}'.")
        return response

    def _generate_chapter_content(self, book_name: str, book_descriptions: List[str], 
                                chapter_outline: ChapterOutline, chapter_index: int, 
                                all_chapter_outlines: List[ChapterOutline]) -> ChapterContent | None:
        """
        Second AI call (repeated for each chapter): Generates content for a specific chapter
        with full context of the book structure.
        """
        system_prompt = """
You are an expert chapter writer creating detailed content for books across various genres and topics.

You will be provided with:
1. The book's title and descriptions
2. The current chapter's title and detailed outline
3. The current chapter's position in the book
4. Outlines of all other chapters for context

Your task is to write engaging content for the current chapter that:
- Follows the provided chapter outline closely
- Maintains consistency with the book's overall theme and tone
- References or builds upon previous chapters when appropriate
- Sets up future chapters naturally
- Feels like part of a cohesive, well-structured book

The content should be:
- Medium in length (multiple paragraphs, typically 500-1000 words)
- Well-written and engaging
- Appropriate for the book's genre and target audience
- Complete and self-contained while fitting the larger narrative

Pay attention to the chapter's position in the book and adjust the writing style accordingly:
- Opening chapters should establish tone and introduce key concepts
- Middle chapters should develop themes and build upon earlier content
- Final chapters should bring resolution and tie themes together
"""
        
        # Build context string with neighboring chapters
        context_parts = []
        
        # Add previous chapter context
        if chapter_index > 0:
            prev_chapter = all_chapter_outlines[chapter_index - 1]
            context_parts.append(f"PREVIOUS CHAPTER: '{prev_chapter.title}' - {prev_chapter.outline}")
        
        # Add current chapter
        context_parts.append(f"CURRENT CHAPTER (to write): '{chapter_outline.title}' - {chapter_outline.outline}")
        
        # Add next chapter context
        if chapter_index < len(all_chapter_outlines) - 1:
            next_chapter = all_chapter_outlines[chapter_index + 1]
            context_parts.append(f"NEXT CHAPTER: '{next_chapter.title}' - {next_chapter.outline}")
        
        # Add overview of all chapters for broader context
        all_chapters_overview = "\n".join([
            f"Chapter {i+1}: '{outline.title}'" 
            for i, outline in enumerate(all_chapter_outlines)
        ])
        
        descriptions_text = " | ".join(book_descriptions)
        user_prompt = f"""
Book: "{book_name}"
Book Descriptions: {descriptions_text}

CHAPTER CONTEXT:
{chr(10).join(context_parts)}

ALL CHAPTERS OVERVIEW:
{all_chapters_overview}

This is chapter {chapter_index + 1} of {len(all_chapter_outlines)} total chapters.

Write the full content for the current chapter following its outline while maintaining coherence with the overall book structure.
"""

        print(f"  Calling AI (Step 2: Chapter Content) for Chapter {chapter_index + 1}: '{chapter_outline.title}'")
        response = self.llm_client.structured_output(
            system=system_prompt,
            user=user_prompt,
            structure=ChapterContent
        )

        if response and hasattr(response, 'content') and response.content:
            print(f"  [AI Response] Generated content for chapter '{chapter_outline.title}' ({len(response.content)} characters).")
        elif response:
            print(f"  [AI Response] Received response for '{chapter_outline.title}', but no valid content found.")
        else:
            print(f"  [AI Response] Failed to generate content for chapter '{chapter_outline.title}'.")
        return response

    def create_full_book(self, book_concept: str) -> ItemDefinition | None:
        """
        Orchestrates the two-step generation process to create a complete book.
        """
        print(f"\n--- Initiating Book Generation for Concept: '{book_concept}' ---")

        # Step 1: Generate book outline (name, descriptions, chapter outlines)
        book_outline = self._generate_book_outline(book_concept)

        # Fixed: Check for chapter_outlines instead of chapter_titles
        if not book_outline or not book_outline.book_name or not book_outline.chapter_outlines:
            print("Critical failure: Could not generate book outline (name or chapter outlines missing). Aborting book creation.")
            return None

        # Step 2: For each chapter outline, generate its content
        chapters = []
        for i, chapter_outline in enumerate(book_outline.chapter_outlines):
            chapter_content_response = self._generate_chapter_content(
                book_outline.book_name, 
                book_outline.descriptions, 
                chapter_outline,  # Pass the full ChapterOutline object
                i,  # Chapter index
                book_outline.chapter_outlines  # All chapter outlines for context
            )

            if chapter_content_response and hasattr(chapter_content_response, 'content') and chapter_content_response.content:
                chapter = Chapter(title=chapter_outline.title, content=chapter_content_response.content)
                chapters.append(chapter)
            else:
                print(f"Warning: No content generated for chapter '{chapter_outline.title}'. Adding with placeholder content.")
                chapter = Chapter(title=chapter_outline.title, content="[Content to be written]")
                chapters.append(chapter)

        # Create the final book definition
        book_definition = ItemDefinition(
            name=book_outline.book_name,
            descriptions=book_outline.descriptions,
            static=False,
            type=["book"],
            chapters=chapters,
            is_locked=True
        )

        print(f"--- Book Generation Complete: '{book_outline.book_name}' with {len(chapters)} chapters ---")
        return book_definition

    def append_book_to_file(self, file_path: str, new_book: ItemDefinition) -> bool:
        """
        Loads existing books from a JSON file, appends a new book,
        and saves the combined data back to the same file.

        Args:
            file_path: The path to the JSON file containing the books.
            new_book: The new book to append.

        Returns:
            True if the append and save operation was successful, False otherwise.
        """
        books_list: List[Dict[str, Any]] = []

        # 1. Load existing data from the file
        try:
            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                    # Handle both list format and single book format
                    if isinstance(data, list):
                        books_list = data
                    elif isinstance(data, dict):
                        # If it's a single book, convert to list
                        books_list = [data]
                    else:
                        print(f"Warning: File '{file_path}' contains unexpected data format. Starting fresh.")
                        books_list = []
                except json.JSONDecodeError:
                    print(f"Warning: File '{file_path}' contains invalid JSON. Starting fresh.")
                    books_list = []
                except Exception as e:
                    print(f"An unexpected error occurred while reading '{file_path}': {e}")
                    books_list = []

        except FileNotFoundError:
            print(f"Info: File '{file_path}' not found. Creating a new file.")
            books_list = []

        # 2. Check if book already exists (by name) and update or append
        book_dict = new_book.model_dump()
        existing_book_index = None
        
        for i, existing_book in enumerate(books_list):
            if existing_book.get('name') == new_book.name:
                existing_book_index = i
                break

        if existing_book_index is not None:
            print(f"Book '{new_book.name}' already exists. Replacing with new version.")
            books_list[existing_book_index] = book_dict
        else:
            print(f"Appending new book: '{new_book.name}'")
            books_list.append(book_dict)

        # 3. Save the combined data back to the file
        try:
            with open(file_path, 'w') as f:
                json.dump(books_list, f, indent=2)
            print(f"Successfully saved books to '{file_path}'.")
            return True
        except Exception as e:
            print(f"Error writing books to file '{file_path}': {e}")
            return False

# Example Usage:
if __name__ == "__main__":
    writer = books_writer()
    books_file = "inventory_items/items_provider/items_data/books/Little_Red_Riding_Hood.json"  # Define the path to your books file

    book_concepts = [
        "A contemporary hypermodern interpretation of the classic tale of 'Little Red Riding Hood' the narrative explores AI technology as a main focus point."
    ]
    
    total_books = len(book_concepts)

    for index, concept in enumerate(book_concepts):
        current_book_number = index + 1

        print(f"\n--- Generating and Saving Book Concept: '{concept}' ({current_book_number} of {total_books}) ---")

        book = writer.create_full_book(concept)

        if book:
            success = writer.append_book_to_file(books_file, book)
            if success:
                print(f"'{book.name}' added to file.")
                if current_book_number < total_books:
                    print(f"Successfully processed concept '{concept}' ({current_book_number} of {total_books}).")
                    print("Sleeping for 10 seconds!")
                    time.sleep(10)
            else:
                print(f"Failed to add '{book.name}' to file.")
        else:
            print(f"Book generation failed for concept '{concept}'.")

    print("\nAll books generated and saved!")