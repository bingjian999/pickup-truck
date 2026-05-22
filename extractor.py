import fitz
import json
import os
from dataclasses import dataclass
from typing import Optional
from tqdm import tqdm


@dataclass
class ChapterInfo:
    level: int
    title: str
    start_page: int
    end_page: int = 0
    children: list = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class PDFExtractor:
    def __init__(self, pdf_path: str, output_dir: str):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.doc: Optional[fitz.Document] = None
        self.toc: list = []
        self.chapters: list[ChapterInfo] = []

    def open(self):
        self.doc = fitz.open(self.pdf_path)
        self.toc = self.doc.get_toc()

    def close(self):
        if self.doc:
            self.doc.close()

    def get_toc_structure(self) -> list[ChapterInfo]:
        if not self.toc:
            self.open()

        chapters = []
        chapter_stack = []

        for i, (level, title, page) in enumerate(self.toc):
            title = title.strip()
            chapter = ChapterInfo(level=level, title=title, start_page=page)

            while chapter_stack and chapter_stack[-1].level >= level:
                popped = chapter_stack.pop()
                if popped.children:
                    popped.end_page = max(c.end_page for c in popped.children)
                else:
                    popped.end_page = popped.start_page

            if chapter_stack and chapter_stack[-1].level < level:
                chapter_stack[-1].children.append(chapter)

            chapter_stack.append(chapter)

            if level <= 2:
                chapters.append(chapter)

        while chapter_stack:
            popped = chapter_stack.pop()
            if popped.children:
                popped.end_page = max(c.end_page for c in popped.children)
            else:
                popped.end_page = popped.start_page

        for i in range(len(chapters)):
            if i < len(chapters) - 1:
                chapters[i].end_page = chapters[i + 1].start_page - 1
            else:
                chapters[i].end_page = self.doc.page_count

        self.chapters = chapters
        return chapters

    def get_main_chapters(self) -> list[ChapterInfo]:
        if not self.chapters:
            self.get_toc_structure()

        main_chapters = []
        for ch in self.chapters:
            if ch.level == 2 and ch.title.startswith("Chapter"):
                main_chapters.append(ch)
        return main_chapters

    def extract_chapter_text(self, chapter: ChapterInfo) -> str:
        if not self.doc:
            self.open()

        texts = []
        start_idx = chapter.start_page - 1
        end_idx = min(chapter.end_page, self.doc.page_count)

        for page_idx in range(start_idx, end_idx):
            page = self.doc[page_idx]
            text = page.get_text("text")
            texts.append(text)

        return "\n\n".join(texts)

    def extract_all_chapters(self, skip_existing: bool = True) -> dict[str, str]:
        main_chapters = self.get_main_chapters()
        result = {}

        for ch in tqdm(main_chapters, desc="Extracting chapters"):
            chapter_id = self._chapter_id(ch)
            output_path = os.path.join(self.output_dir, "chapters", "en", f"{chapter_id}.txt")
            md_output_path = os.path.join(self.output_dir, "chapters", "en", f"{chapter_id}.md")

            if skip_existing and (os.path.exists(output_path) or os.path.exists(md_output_path)):
                if os.path.exists(output_path):
                    with open(output_path, "r", encoding="utf-8") as f:
                        result[chapter_id] = f.read()
                continue

            text = self.extract_chapter_text(ch)
            result[chapter_id] = text

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)

        return result

    def extract_page_text(self, page_num: int) -> str:
        if not self.doc:
            self.open()

        if page_num < 1 or page_num > self.doc.page_count:
            return ""

        page = self.doc[page_num - 1]
        return page.get_text("text")

    def save_chapter_structure(self):
        structure_path = os.path.join(self.output_dir, "chapter_structure.json")
        chapters_data = []
        for ch in self.chapters:
            chapters_data.append({
                "level": ch.level,
                "title": ch.title,
                "start_page": ch.start_page,
                "end_page": ch.end_page,
            })
        with open(structure_path, "w", encoding="utf-8") as f:
            json.dump(chapters_data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _chapter_id(chapter: ChapterInfo) -> str:
        title = chapter.title
        if title.startswith("Chapter "):
            parts = title.split(" ", 2)
            if len(parts) >= 3:
                num_part = parts[1]
                chapter_title = parts[2]
                try:
                    num = int(num_part)
                    safe_title = chapter_title.replace(" ", "_").replace("/", "_").replace(":", "_").replace(",", "").replace("®", "").replace("™", "").replace("?", "").replace("!", "").replace("'", "").replace('"', "")
                    return f"{num:02d}_{safe_title[:60]}"
                except ValueError:
                    pass
            elif len(parts) >= 2:
                num_part = parts[1]
                try:
                    num = int(num_part)
                    return f"{num:02d}_Chapter"
                except ValueError:
                    pass
        safe_title = title.replace(" ", "_").replace("/", "_").replace(":", "_").replace(",", "")
        return safe_title[:60]

    def page_count(self) -> int:
        if not self.doc:
            self.open()
        return self.doc.page_count