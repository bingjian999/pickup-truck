import os
import re
from tqdm import tqdm


class BilingualFormatter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def create_bilingual_paragraph(self, en_text: str, zh_text: str, title: str = "") -> str:
        en_paragraphs = self._split_paragraphs(en_text)
        zh_paragraphs = self._split_paragraphs(zh_text)

        result = []
        if title:
            result.append(f"# {title} (中英文对照 / Bilingual)")
            result.append("")

        max_len = max(len(en_paragraphs), len(zh_paragraphs))
        for i in range(max_len):
            en_para = en_paragraphs[i].strip() if i < len(en_paragraphs) else ""
            zh_para = zh_paragraphs[i].strip() if i < len(zh_paragraphs) else ""

            if en_para or zh_para:
                if self._is_header(en_para) or self._is_header(zh_para):
                    if en_para:
                        result.append(f"## {en_para}")
                    if zh_para:
                        result.append(f"## {zh_para}")
                elif self._is_list_item(en_para) or self._is_list_item(zh_para):
                    if en_para:
                        result.append(f"- **EN:** {en_para}")
                    if zh_para:
                        result.append(f"- **中文:** {zh_para}")
                else:
                    if en_para:
                        result.append(f"**EN:** {en_para}")
                    if zh_para:
                        result.append(f"**中文:** {zh_para}")
                result.append("")

        return "\n".join(result)

    def _is_header(self, text: str) -> bool:
        text = text.strip()
        return (text.startswith("#") or 
                re.match(r"^\d+(\.\d+)*\s+[A-Z].*$", text) or
                len(text) < 60 and text.isupper())

    def _is_list_item(self, text: str) -> bool:
        text = text.strip()
        return text.startswith(("- ", "• ", "* ", "1. ", "(a) ", "(i) ")) or \
               re.match(r"^\d+\)\s", text)

    def format_all_chapters(self, skip_existing: bool = True) -> dict[str, str]:
        en_dir = os.path.join(self.output_dir, "chapters", "en")
        zh_dir = os.path.join(self.output_dir, "chapters", "zh")
        bilingual_dir = os.path.join(self.output_dir, "chapters", "bilingual")

        en_files = sorted([f for f in os.listdir(en_dir) if f.endswith(".md")])
        result = {}

        for md_file in tqdm(en_files, desc="Creating bilingual versions"):
            chapter_id = md_file.replace(".md", "")
            bilingual_path = os.path.join(bilingual_dir, f"{chapter_id}.md")

            if skip_existing and os.path.exists(bilingual_path):
                with open(bilingual_path, "r", encoding="utf-8") as f:
                    result[chapter_id] = f.read()
                continue

            en_path = os.path.join(en_dir, md_file)
            zh_path = os.path.join(zh_dir, md_file)

            with open(en_path, "r", encoding="utf-8") as f:
                en_text = f.read()

            zh_text = ""
            if os.path.exists(zh_path):
                with open(zh_path, "r", encoding="utf-8") as f:
                    zh_text = f.read()

            chapter_title = self._extract_title(en_text)
            if zh_text:
                bilingual_text = self.create_bilingual_paragraph(en_text, zh_text, chapter_title)
            else:
                bilingual_text = en_text
            result[chapter_id] = bilingual_text

            with open(bilingual_path, "w", encoding="utf-8") as f:
                f.write(bilingual_text)

        return result

    def create_full_bilingual_document(self) -> str:
        bilingual_dir = os.path.join(self.output_dir, "chapters", "bilingual")
        full_dir = os.path.join(self.output_dir, "full")
        full_path = os.path.join(full_dir, "International_GAAP_2025_bilingual.md")

        bilingual_files = sorted([f for f in os.listdir(bilingual_dir) if f.endswith(".md")])

        full_content = []
        full_content.append("# International GAAP 2025 - 中英文对照版 (Bilingual Edition)\n")
        full_content.append("---\n")

        for bf in bilingual_files:
            bf_path = os.path.join(bilingual_dir, bf)
            with open(bf_path, "r", encoding="utf-8") as f:
                content = f.read()
            full_content.append(content)
            full_content.append("\n---\n")

        combined = "\n".join(full_content)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(combined)

        return combined

    def _split_paragraphs(self, text: str) -> list[str]:
        paragraphs = re.split(r"\n\n+", text)
        cleaned = []
        for p in paragraphs:
            p = p.replace("\n", " ").strip()
            p = re.sub(r"\s+", " ", p)
            if p:
                cleaned.append(p)
        return cleaned

    def _extract_title(self, text: str) -> str:
        for line in text.split("\n")[:5]:
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped.lstrip("# ")
            if stripped.lower().startswith("chapter "):
                return stripped
        return ""