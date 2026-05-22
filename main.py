import argparse
import asyncio
import os
import sys
from config import Config
from extractor import PDFExtractor
from markdown_converter import MarkdownConverter
from translator import Translator
from bilingual_formatter import BilingualFormatter


def parse_args():
    parser = argparse.ArgumentParser(
        description="International GAAP 2025 - PDF to Bilingual Markdown Converter"
    )
    parser.add_argument("--pdf", type=str, default=None, help="Path to the PDF file")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--api-key", type=str, default=None, help="OpenAI API key")
    parser.add_argument("--api-base", type=str, default=None, help="OpenAI API base URL")
    parser.add_argument("--model", type=str, default=None, help="OpenAI model name (default from OPENAI_MODEL env)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    extract_parser = subparsers.add_parser("extract", help="Extract text from PDF and split by chapters")
    extract_parser.add_argument("--chapters", type=str, default=None, help="Comma-separated chapter numbers (e.g., '1,2,3')")
    extract_parser.add_argument("--no-skip", action="store_true", help="Do not skip existing files")

    convert_parser = subparsers.add_parser("convert", help="Convert extracted text to Markdown")
    convert_parser.add_argument("--no-skip", action="store_true", help="Do not skip existing files")

    translate_parser = subparsers.add_parser("translate", help="Translate chapters to Chinese")
    translate_parser.add_argument("--chapters", type=str, default=None, help="Comma-separated chapter numbers")
    translate_parser.add_argument("--no-skip", action="store_true", help="Do not skip existing files")
    translate_parser.add_argument("--chunk-size", type=int, default=2000, help="Translation chunk size")

    bilingual_parser = subparsers.add_parser("bilingual", help="Create bilingual versions")
    bilingual_parser.add_argument("--no-skip", action="store_true", help="Do not skip existing files")

    full_parser = subparsers.add_parser("full", help="Run the complete pipeline")
    full_parser.add_argument("--chapters", type=str, default=None, help="Comma-separated chapter numbers")
    full_parser.add_argument("--no-skip", action="store_true", help="Do not skip existing files")
    full_parser.add_argument("--chunk-size", type=int, default=2000, help="Translation chunk size")
    full_parser.add_argument("--no-extract", action="store_true", help="Skip extraction (use existing files)")
    full_parser.add_argument("--no-convert", action="store_true", help="Skip conversion (use existing files)")
    full_parser.add_argument("--no-translate", action="store_true", help="Skip translation (use existing files)")

    info_parser = subparsers.add_parser("info", help="Show PDF structure information")

    return parser.parse_args()


def create_config(args) -> Config:
    cfg = Config()

    if args.pdf:
        cfg.pdf_path = args.pdf
    if args.output:
        cfg.output_dir = args.output
    if args.api_key:
        cfg.openai_api_key = args.api_key
    if args.api_base:
        cfg.openai_api_base = args.api_base
    if args.model:
        cfg.openai_model = args.model

    if hasattr(args, "chunk_size") and args.chunk_size:
        cfg.translation_chunk_size = args.chunk_size

    cfg.skip_existing = not getattr(args, "no_skip", False)

    chapters_arg = getattr(args, "chapters", None)
    if chapters_arg:
        cfg.chapters_to_process = [int(c.strip()) for c in chapters_arg.split(",") if c.strip()]

    return cfg


def cmd_info(cfg: Config):
    extractor = PDFExtractor(cfg.pdf_path, cfg.output_dir)
    extractor.open()

    print(f"PDF: {cfg.pdf_path}")
    print(f"Total pages: {extractor.page_count()}")
    print(f"TOC entries: {len(extractor.toc)}")

    chapters = extractor.get_main_chapters()
    print(f"\nMain chapters ({len(chapters)}):")
    for ch in chapters:
        pages = ch.end_page - ch.start_page + 1
        print(f"  {ch.title} (pages {ch.start_page}-{ch.end_page}, {pages} pages)")

    extractor.save_chapter_structure()
    print(f"\nChapter structure saved to: {os.path.join(cfg.output_dir, 'chapter_structure.json')}")

    extractor.close()


def cmd_extract(cfg: Config):
    print("Step 1: Extracting text from PDF and splitting by chapters...")
    extractor = PDFExtractor(cfg.pdf_path, cfg.output_dir)
    extractor.open()

    if cfg.chapters_to_process:
        all_chapters = extractor.get_main_chapters()
        extractor.chapters = [c for c in all_chapters
                              if int(extractor._chapter_id(c).split("_")[-1]) in cfg.chapters_to_process]
        for ch in extractor.chapters:
            text = extractor.extract_chapter_text(ch)
            chapter_id = extractor._chapter_id(ch)
            output_path = os.path.join(cfg.output_dir, "chapters", "en", f"{chapter_id}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  Extracted: {chapter_id} ({ch.start_page}-{ch.end_page})")
    else:
        extractor.extract_all_chapters(skip_existing=cfg.skip_existing)

    extractor.save_chapter_structure()
    extractor.close()
    print("Extraction complete.")


def cmd_convert(cfg: Config):
    print("Step 2: Converting extracted text to Markdown...")
    converter = MarkdownConverter(cfg.output_dir)
    converter.convert_all_chapters(skip_existing=cfg.skip_existing)
    print("Conversion complete.")


async def cmd_translate_async(cfg: Config):
    print("Step 3: Translating chapters to Chinese...")

    if not cfg.openai_api_key:
        print("ERROR: OpenAI API key not set. Use --api-key or set OPENAI_API_KEY environment variable.")
        sys.exit(1)

    en_dir = os.path.join(cfg.output_dir, "chapters", "en")
    chapter_texts = {}

    md_files = sorted([f for f in os.listdir(en_dir) if f.endswith(".md")])
    for md_file in md_files:
        chapter_id = md_file.replace(".md", "")
        if cfg.chapters_to_process:
            try:
                ch_num = int(chapter_id.split("_")[-1])
                if ch_num not in cfg.chapters_to_process:
                    continue
            except ValueError:
                pass

        md_path = os.path.join(en_dir, md_file)
        with open(md_path, "r", encoding="utf-8") as f:
            chapter_texts[chapter_id] = f.read()

    translator = Translator(
        api_key=cfg.openai_api_key,
        api_base=cfg.openai_api_base,
        model=cfg.openai_model,
        output_dir=cfg.output_dir,
    )

    await translator.translate_chapters(
        chapter_texts,
        chunk_size=cfg.translation_chunk_size,
        overlap=cfg.translation_chunk_overlap,
        skip_existing=cfg.skip_existing,
    )
    print("Translation complete.")


def cmd_translate(cfg: Config):
    asyncio.run(cmd_translate_async(cfg))


def cmd_bilingual(cfg: Config):
    print("Step 4: Creating bilingual versions...")
    formatter = BilingualFormatter(cfg.output_dir)
    formatter.format_all_chapters(skip_existing=cfg.skip_existing)

    print("Creating full bilingual document...")
    formatter.create_full_bilingual_document()
    print("Bilingual formatting complete.")


def cmd_full(cfg: Config):
    if not getattr(cfg, "no_extract", False):
        cmd_extract(cfg)

    if not getattr(cfg, "no_convert", False):
        cmd_convert(cfg)

    if not getattr(cfg, "no_translate", False):
        cmd_translate(cfg)

    cmd_bilingual(cfg)

    print("\n" + "=" * 60)
    print("Full pipeline complete!")
    print(f"Output directory: {cfg.output_dir}")
    print(f"  - chapters/en/     : English Markdown chapters")
    print(f"  - chapters/zh/     : Chinese Markdown chapters")
    print(f"  - chapters/bilingual/ : Bilingual chapters")
    print(f"  - full/            : Combined bilingual document")
    print("=" * 60)


def main():
    args = parse_args()
    cfg = create_config(args)

    commands = {
        "info": cmd_info,
        "extract": cmd_extract,
        "convert": cmd_convert,
        "translate": cmd_translate,
        "bilingual": cmd_bilingual,
        "full": cmd_full,
    }

    if args.command in commands:
        commands[args.command](cfg)
    else:
        print("Please specify a command. Use --help for usage information.")
        print("Available commands: info, extract, convert, translate, bilingual, full")


if __name__ == "__main__":
    main()