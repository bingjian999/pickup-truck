import re
import os
from tqdm import tqdm

PAGE_HEADER_PATTERNS = [
    r"^International GAAP[\u00AE]? 2025$",
    r"^International GAAP\u00AE 2025$",
    r"^Chapter \d{2}$",
    r"^Chapter \d{1,2}$",
    r"^International GAAP$",
]

SECTION_NUMBER_PATTERN = r"^(\d+(\.\d+)*)\.?\s+"


class MarkdownConverter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def convert_text_to_markdown(self, text: str, title: str = "") -> str:
        lines = text.split("\n")
        cleaned = self._remove_page_headers(lines)
        result = []

        if title:
            result.append(f"# {title}")
            result.append("")

        state = "normal"
        pending_paragraph = []
        in_list = False
        last_was_empty = False

        for line in cleaned:
            stripped = line.strip()
            if not stripped:
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                if not last_was_empty:
                    result.append("")
                    last_was_empty = True
                in_list = False
                continue

            last_was_empty = False

            if self._is_page_number(stripped):
                continue

            if self._is_running_header(stripped):
                continue

            if self._is_chapter_title(stripped):
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                if title:
                    result.append(f"\n# {stripped}")
                else:
                    result.append(f"# {stripped}")
                result.append("")
                continue

            if self._is_section_header(stripped):
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                level = self._get_header_level(stripped)
                header_text = re.sub(SECTION_NUMBER_PATTERN, "", stripped)
                result.append(f"\n{'#' * level} {header_text}")
                result.append("")
                continue

            if self._is_toc_line(stripped):
                if state != "toc":
                    result.append("")
                    result.append("## Contents")
                    result.append("")
                    state = "toc"
                result.append(f"- {stripped}")
                continue

            if state == "toc" and self._is_likely_content(stripped):
                result.append("")
                state = "normal"

            if self._is_bullet(stripped):
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                bullet_content = re.sub(r"^[•·*-]+\s*", "", stripped)
                if bullet_content:
                    result.append(f"- {bullet_content}")
                in_list = True
                continue

            if self._is_numbered_list(stripped):
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                result.append(f"  {stripped}")
                in_list = True
                continue

            if self._is_footnote(stripped):
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                result.append(f"\n> {stripped}")
                continue

            if self._is_citation(stripped):
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                result.append(f"\n*Reference: {stripped}*")
                continue

            if self._is_emphasis_line(stripped):
                if pending_paragraph:
                    result.append(" ".join(pending_paragraph))
                    pending_paragraph = []
                result.append(f"\n**{stripped}**")
                result.append("")
                continue

            pending_paragraph.append(stripped)

        if pending_paragraph:
            result.append(" ".join(pending_paragraph))

        markdown = "\n".join(result)
        markdown = self._cleanup_markdown(markdown)
        return markdown

    def _get_header_level(self, text: str) -> int:
        match = re.match(SECTION_NUMBER_PATTERN, text)
        if match:
            number_part = match.group(1)
            level = number_part.count(".") + 1
            return min(level + 1, 6)
        return 2

    def _remove_page_headers(self, lines: list[str]) -> list[str]:
        result = []
        for line in lines:
            stripped = line.strip()
            if any(re.match(p, stripped) for p in PAGE_HEADER_PATTERNS):
                continue
            result.append(line)
        return result

    def _is_running_header(self, line: str) -> bool:
        return any(re.match(p, line) for p in PAGE_HEADER_PATTERNS)

    def _is_page_number(self, line: str) -> bool:
        s = line.strip()
        return s.isdigit() and 1 <= len(s) <= 4

    def _is_chapter_title(self, line: str) -> bool:
        return re.match(r"^Chapter \d{1,2}.*$", line, re.IGNORECASE) is not None

    def _is_toc_line(self, line: str) -> bool:
        return bool(re.match(r"^\d+(\.\d+)*[\.\s]+[A-Z].{10,}$", line)) and len(line) < 120

    def _is_likely_content(self, line: str) -> bool:
        return len(line) > 150 or (len(line) > 80 and line.count(" ") > 10)

    def _is_section_header(self, line: str) -> bool:
        if len(line) > 100:
            return False
        if line.endswith("."):
            patterns = [
                r"^\d+\.?\s+[A-Z][a-zA-Z].*$",
                r"^\d+\.\d+\.?\s+[A-Z].*$",
                r"^\d+\.\d+\.\d+\.?\s+[A-Z].*$",
                r"^\d+\.\d+\.[A-Z]\.?\s+[A-Z].*$",
                r"^[IVXLCDM]+\.\s+[A-Z].*$",
            ]
            return any(re.match(p, line) for p in patterns)
        words = line.split()
        if len(words) > 20:
            return False
        patterns = [
            r"^\d+\s+[A-Z][a-zA-Z].*$",
            r"^\d+\.\d+\s+[A-Z].*$",
            r"^\d+\.\d+\.\d+\s+[A-Z].*$",
        ]
        return any(re.match(p, line) for p in patterns)

    def _is_bullet(self, line: str) -> bool:
        return re.match(r"^[•·*-]+\s", line) is not None

    def _is_numbered_list(self, line: str) -> bool:
        return bool(re.match(r"^\(\w\)\s", line)) or bool(re.match(r"^\d+\)\s", line))

    def _is_footnote(self, line: str) -> bool:
        return bool(re.match(r"^\d+\s+[A-Z].*$", line)) and len(line) > 25 and line.endswith(".")

    def _is_citation(self, line: str) -> bool:
        patterns = [
            r"^IFRS Foundation.*",
            r"^Available on IFRS.*",
            r"^See IFRS.*",
            r"^IASB.*",
            r"^Charter of.*",
            r"^.*Constitution.*Section.*",
        ]
        return any(re.match(p, line) for p in patterns)

    def _is_emphasis_line(self, line: str) -> bool:
        if len(line) < 8 or len(line) > 80:
            return False
        return line.isupper() or line.startswith("**")

    def _cleanup_markdown(self, markdown: str) -> str:
        markdown = re.sub(r"\n{4,}", "\n\n\n", markdown)
        markdown = re.sub(r"(\n[-*]){4,}", r"\1", markdown)
        markdown = re.sub(r"^\s+", "", markdown, flags=re.MULTILINE)
        markdown = re.sub(r"\s+$", "", markdown, flags=re.MULTILINE)
        lines = markdown.split("\n")
        cleaned_lines = []
        consecutive_empty = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                consecutive_empty += 1
                if consecutive_empty <= 2:
                    cleaned_lines.append("")
            else:
                consecutive_empty = 0
                cleaned_lines.append(line)
        markdown = "\n".join(cleaned_lines).strip()
        return markdown

    def convert_all_chapters(self, skip_existing: bool = True) -> dict[str, str]:
        en_dir = os.path.join(self.output_dir, "chapters", "en")
        result = {}

        txt_files = sorted([f for f in os.listdir(en_dir) if f.endswith(".txt")])
        for txt_file in tqdm(txt_files, desc="Converting to Markdown"):
            chapter_id = txt_file.replace(".txt", "")
            md_path = os.path.join(en_dir, f"{chapter_id}.md")

            if skip_existing and os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    result[chapter_id] = f.read()
                continue

            txt_path = os.path.join(en_dir, txt_file)
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()

            chapter_title = self._extract_chapter_title(text)
            markdown_text = self.convert_text_to_markdown(text, chapter_title)
            result[chapter_id] = markdown_text

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)

        return result

    def _extract_chapter_title(self, text: str) -> str:
        lines = text.split("\n")
        for line in lines[:15]:
            stripped = line.strip()
            if stripped.lower().startswith("chapter ") and len(stripped) < 120:
                return stripped
        return ""