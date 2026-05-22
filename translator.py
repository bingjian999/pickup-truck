import os
import json
import time
import asyncio
from typing import Optional
from openai import AsyncOpenAI
from tqdm import tqdm


class Translator:
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None,
                 model: str = "gpt-4o", output_dir: str = "output"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_base = api_base or os.environ.get("OPENAI_API_BASE")
        self.model = model
        self.output_dir = output_dir
        self.checkpoint_dir = os.path.join(output_dir, "checkpoints")
        self.client: Optional[AsyncOpenAI] = None

    def _init_client(self):
        if self.client is None:
            kwargs = {"api_key": self.api_key}
            if self.api_base:
                kwargs["base_url"] = self.api_base
            self.client = AsyncOpenAI(**kwargs)

    def split_text_into_chunks(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
        # 首先尝试按段落分割
        paragraphs = text.split("\n\n")
        
        # 如果段落太大或者太少，尝试更细致的分割
        chunks = []
        current_chunk = ""
        current_size = 0

        for para in paragraphs:
            # 如果当前段落本身就很大，需要进一步分割
            if len(para) > chunk_size * 2:
                # 先加入当前累积的内容
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    current_size = 0
                
                # 将这个大段落分割成更小的块
                # 尝试按句子、句号等分割
                import re
                sentences = re.split(r'(?<=[。.!?])\s+', para)
                temp_chunk = ""
                for sent in sentences:
                    if len(temp_chunk) + len(sent) < chunk_size:
                        temp_chunk += " " + sent if temp_chunk else sent
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sent
                if temp_chunk:
                    chunks.append(temp_chunk.strip())
            else:
                # 正常处理段落
                para_size = len(para)
                if current_size + para_size > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    if overlap > 0:
                        # 重叠部分
                        overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                        current_chunk = overlap_text + "\n\n" + para
                        current_size = len(current_chunk)
                    else:
                        current_chunk = para
                        current_size = len(para)
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
                    current_size = len(current_chunk)

        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # 如果分割结果不理想，尝试备用方法
        if len(chunks) == 0 or (len(chunks) == 1 and len(chunks[0]) > chunk_size * 3):
            chunks = self._backup_split(text, chunk_size, overlap)

        return chunks

    def _backup_split(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
        """备用分割方法：当段落分割效果不好时使用"""
        chunks = []
        i = 0
        n = len(text)
        
        while i < n:
            # 找到下一个自然的分割点（标点符号或空格）
            end = min(i + chunk_size, n)
            
            # 如果不是最后一个chunk，尽量在标点符号处分割
            if end < n:
                # 寻找合适的分割点（往前找100个字符）
                split_pos = end
                for j in range(end, max(i, end - 100), -1):
                    if text[j] in ['。', '.', '!', '?', '\n', ';', '：']:
                        split_pos = j + 1
                        break
                end = split_pos
            
            chunk = text[i:end].strip()
            if chunk:
                chunks.append(chunk)
            
            i = end - overlap  # 重叠部分
        
        return chunks

    async def translate_chunk(self, text: str, chunk_index: int, total_chunks: int) -> str:
        self._init_client()

        system_prompt = (
            "You are a professional translator specializing in International Financial Reporting Standards (IFRS) "
            "and accounting documents. Translate the following English text to Simplified Chinese. "
            "Requirements:\n"
            "1. Maintain professional accounting terminology accuracy\n"
            "2. Preserve all numbers, dates, and proper nouns in their original form\n"
            "3. Keep all IFRS/IAS standard references unchanged (e.g., IFRS 15, IAS 36)\n"
            "4. Preserve formatting markers like bullet points, numbered lists\n"
            "5. Translate naturally and fluently in Chinese academic style\n"
            "6. Do NOT add any explanations or notes - pure translation only"
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Translate this accounting text (chunk {chunk_index + 1}/{total_chunks}):\n\n{text}"}
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    return f"[Translation error: {str(e)}]\n\n{text}"

    async def translate_chapters(self, chapter_texts: dict[str, str],
                                  chunk_size: int = 2000, overlap: int = 200,
                                  skip_existing: bool = True) -> dict[str, str]:
        zh_dir = os.path.join(self.output_dir, "chapters", "zh")
        os.makedirs(zh_dir, exist_ok=True)

        results = {}
        chapter_ids = list(chapter_texts.keys())

        for chapter_id in tqdm(chapter_ids, desc="Translating chapters"):
            zh_md_path = os.path.join(zh_dir, f"{chapter_id}.md")
            zh_txt_path = os.path.join(zh_dir, f"{chapter_id}.txt")

            if skip_existing and os.path.exists(zh_md_path):
                with open(zh_md_path, "r", encoding="utf-8") as f:
                    results[chapter_id] = f.read()
                continue

            text = chapter_texts[chapter_id]
            chunks = self.split_text_into_chunks(text, chunk_size, overlap)

            translated_chunks = []
            for i, chunk in enumerate(chunks):
                print(f"  [{chapter_id}] Translating chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)")
                translated = await self.translate_chunk(chunk, i, len(chunks))
                translated_chunks.append(translated)
                time.sleep(0.5)

            full_translation = "\n\n".join(translated_chunks)
            results[chapter_id] = full_translation

            with open(zh_md_path, "w", encoding="utf-8") as f:
                f.write(full_translation)

            self._save_checkpoint(chapter_id, "translated")

        return results

    def _save_checkpoint(self, chapter_id: str, stage: str):
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{chapter_id}_{stage}.json")
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump({"chapter_id": chapter_id, "stage": stage, "timestamp": time.time()}, f)

    def is_translated(self, chapter_id: str) -> bool:
        zh_md_path = os.path.join(self.output_dir, "chapters", "zh", f"{chapter_id}.md")
        return os.path.exists(zh_md_path)

    def translate_text_sync(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> str:
        chunks = self.split_text_into_chunks(text, chunk_size, overlap)
        translated_chunks = []

        for i, chunk in enumerate(tqdm(chunks, desc="Translating")):
            result = asyncio.run(self.translate_chunk(chunk, i, len(chunks)))
            translated_chunks.append(result)
            if i < len(chunks) - 1:
                time.sleep(0.3)

        return "\n\n".join(translated_chunks)