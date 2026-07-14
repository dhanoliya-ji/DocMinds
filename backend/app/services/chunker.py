import re
import tiktoken
from typing import List, Dict, Any

class ChunkerService:
    # Use standard cl100k_base tokenizer (used by OpenAI text-embedding-3-small)
    _encoder = tiktoken.get_encoding("cl100k_base")

    @classmethod
    def count_tokens(cls, text: str) -> int:
        return len(cls._encoder.encode(text))

    @classmethod
    def chunk_document(
        cls, 
        text: str, 
        strategy: str = "fixed_size", 
        chunk_size: int = 500, 
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Splits raw text into layout-aware logical chunks.
        Splits by PDF/OCR page markers first to chunk each page independently.
        """
        page_pattern = re.compile(r'(?:\n|^)--- PAGE (?:BREAK|\d+ \((?:OCR|ocr)\)) ---\n?')
        
        # Split by page boundaries
        parts = page_pattern.split(text)
        parts = [p.strip() for p in parts if p.strip()]
        
        if not parts:
            return []
            
        all_chunks = []
        chunk_index = 0
        strategy = strategy.lower()
        
        # Markdown documents are processed as a single continuous document
        if strategy == "markdown":
            return cls._markdown_chunking(text)
            
        for page_idx, page_text in enumerate(parts, 1):
            if strategy == "fixed_size":
                page_chunks = cls._fixed_size_chunking_single_page(
                    page_text, chunk_size, chunk_overlap, page_idx, chunk_index
                )
            elif strategy == "sentence":
                page_chunks = cls._sentence_chunking_single_page(
                    page_text, chunk_size, chunk_overlap, page_idx, chunk_index
                )
            else:
                raise ValueError(f"Unsupported chunking strategy: {strategy}")
                
            all_chunks.extend(page_chunks)
            chunk_index += len(page_chunks)
            
        return all_chunks

    @classmethod
    def _fixed_size_chunking_single_page(
        cls, 
        text: str, 
        chunk_size: int, 
        chunk_overlap: int,
        page_number: int,
        start_chunk_index: int
    ) -> List[Dict[str, Any]]:
        tokens = cls._encoder.encode(text)
        chunks = []
        num_tokens = len(tokens)
        
        if num_tokens == 0:
            return []
            
        step = chunk_size - chunk_overlap
        if step <= 0:
            step = chunk_size
            
        chunk_index = start_chunk_index
        for i in range(0, num_tokens, step):
            chunk_tokens = tokens[i : i + chunk_size]
            chunk_text = cls._encoder.decode(chunk_tokens)
            
            chunks.append({
                "content": chunk_text,
                "chunk_index": chunk_index,
                "page_number": page_number,
                "meta_data": {
                    "token_count": len(chunk_tokens),
                    "character_count": len(chunk_text),
                }
            })
            chunk_index += 1
            if i + chunk_size >= num_tokens:
                break
                
        return chunks

    @classmethod
    def _sentence_chunking_single_page(
        cls, 
        text: str, 
        chunk_size: int, 
        chunk_overlap: int,
        page_number: int,
        start_chunk_index: int
    ) -> List[Dict[str, Any]]:
        # Split by sentence boundaries, keeping punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        
        current_sentences = []
        current_tokens = 0
        chunk_index = start_chunk_index
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            sentence_tokens = cls.count_tokens(sentence)
            if sentence_tokens > chunk_size:
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "page_number": page_number,
                        "meta_data": {
                            "token_count": current_tokens,
                            "character_count": len(chunk_text),
                        }
                    })
                    chunk_index += 1
                    current_sentences = []
                    current_tokens = 0
                
                chunks.append({
                    "content": sentence,
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "meta_data": {
                        "token_count": sentence_tokens,
                        "character_count": len(sentence),
                    }
                })
                chunk_index += 1
                continue
                
            if current_tokens + sentence_tokens > chunk_size:
                chunk_text = " ".join(current_sentences)
                chunks.append({
                    "content": chunk_text,
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "meta_data": {
                        "token_count": current_tokens,
                        "character_count": len(chunk_text),
                    }
                })
                chunk_index += 1
                
                # Apply sliding sentence overlap
                overlap_sentences = []
                overlap_tokens = 0
                for s in reversed(current_sentences):
                    s_tok = cls.count_tokens(s)
                    if overlap_tokens + s_tok <= chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tok
                    else:
                        break
                current_sentences = overlap_sentences
                current_tokens = overlap_tokens
                
            current_sentences.append(sentence)
            current_tokens += sentence_tokens

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append({
                "content": chunk_text,
                "chunk_index": chunk_index,
                "page_number": page_number,
                "meta_data": {
                    "token_count": current_tokens,
                    "character_count": len(chunk_text),
                }
            })
            
        return chunks

    @classmethod
    def _markdown_chunking(cls, text: str) -> List[Dict[str, Any]]:
        # Remove page breaks to parse headers continuously
        clean_text = re.sub(r'(?:\n|^)--- PAGE (?:BREAK|\d+ \((?:OCR|ocr)\)) ---\n?', "\n", text)
        lines = clean_text.splitlines()
        chunks = []
        
        current_header = "Intro"
        current_block = []
        chunk_index = 0
        header_pattern = re.compile(r'^(#{1,6})\s+(.*)$')
        
        for line in lines:
            match = header_pattern.match(line)
            if match:
                if current_block:
                    chunk_text = f"Header: {current_header}\n" + "\n".join(current_block)
                    chunks.append({
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "page_number": 1,
                        "meta_data": {
                            "token_count": cls.count_tokens(chunk_text),
                            "character_count": len(chunk_text),
                            "header_section": current_header,
                        }
                    })
                    chunk_index += 1
                    current_block = []
                current_header = match.group(2).strip()
                
            current_block.append(line)

        if current_block:
            chunk_text = f"Header: {current_header}\n" + "\n".join(current_block)
            chunks.append({
                "content": chunk_text,
                "chunk_index": chunk_index,
                "page_number": 1,
                "meta_data": {
                    "token_count": cls.count_tokens(chunk_text),
                    "character_count": len(chunk_text),
                    "header_section": current_header,
                }
            })
            
        return chunks
