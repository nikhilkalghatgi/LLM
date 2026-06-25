"""PDF loading and sentence-aware chunking using NLTK punkt tokenizer."""

import os
from typing import List, Dict

import fitz  # PyMuPDF
import nltk

# Ensure punkt tokenizer is available
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


def load_pdf(pdf_path: str) -> List[Dict]:
    """Load a PDF and return a list of dicts with text, page number, and source filename.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        List of dicts, one per page, with keys: text, page, source.
    """
    doc = fitz.open(pdf_path)
    source = os.path.basename(pdf_path)
    pages: List[Dict] = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text").strip()
        if text:
            pages.append({
                "text": text,
                "page": page_num + 1,  # 1-indexed
                "source": source,
            })

    doc.close()
    return pages


def chunk_document(
    pages: List[Dict],
    chunk_size: int = 300,
    chunk_overlap: int = 50,
) -> List[Dict]:
    """Split page-level text into overlapping chunks using sentence boundaries.

    Strategy:
        1. Sentence-tokenize each page's text using NLTK punkt.
        2. Greedily accumulate sentences into a chunk until word count >= chunk_size.
        3. Start the next chunk by carrying over enough trailing sentences from
           the previous chunk to cover ~chunk_overlap words.

    Args:
        pages: Output of load_pdf — list of dicts with text, page, source.
        chunk_size: Target word count per chunk.
        chunk_overlap: Approximate word overlap between consecutive chunks.

    Returns:
        List of chunk dicts with keys: text, page, source, chunk_index.
    """
    # Flatten all pages into (sentence, page, source) triples
    sentence_records: List[Dict] = []
    for page_dict in pages:
        sentences = nltk.sent_tokenize(page_dict["text"])
        for sent in sentences:
            sentence_records.append({
                "sentence": sent,
                "page": page_dict["page"],
                "source": page_dict["source"],
            })

    if not sentence_records:
        return []

    chunks: List[Dict] = []
    chunk_index = 0
    i = 0  # pointer into sentence_records

    while i < len(sentence_records):
        current_sentences: List[str] = []
        current_word_count = 0
        start_page = sentence_records[i]["page"]
        source = sentence_records[i]["source"]

        # Greedily add sentences until we hit chunk_size words
        j = i
        while j < len(sentence_records) and current_word_count < chunk_size:
            sent = sentence_records[j]["sentence"]
            word_count = len(sent.split())
            current_sentences.append(sent)
            current_word_count += word_count
            j += 1

        chunk_text = " ".join(current_sentences)
        chunks.append({
            "text": chunk_text,
            "page": start_page,
            "source": source,
            "chunk_index": chunk_index,
        })
        chunk_index += 1

        # Determine how many trailing sentences to carry over for overlap
        if j >= len(sentence_records):
            break

        overlap_word_count = 0
        overlap_start = len(current_sentences) - 1
        while overlap_start >= 0 and overlap_word_count < chunk_overlap:
            overlap_word_count += len(current_sentences[overlap_start].split())
            overlap_start -= 1
        overlap_start += 1  # point to the first sentence to carry over

        # Move pointer back so those sentences are included in the next chunk
        overlap_sentence_count = len(current_sentences) - overlap_start
        i = j - overlap_sentence_count

        # Safety: always advance at least one sentence
        if i <= (j - len(current_sentences)):
            i = j

    return chunks


def chunk_documents(
    pdf_paths: List[str],
    chunk_size: int = 300,
    chunk_overlap: int = 50,
) -> List[Dict]:
    """Load and chunk multiple PDFs into a flat list of chunks.

    Each chunk is assigned a globally unique chunk_index across all documents.

    Args:
        pdf_paths: List of paths to PDF files.
        chunk_size: Target word count per chunk.
        chunk_overlap: Approximate word overlap between consecutive chunks.

    Returns:
        Flat list of chunk dicts across all PDFs.
    """
    all_chunks: List[Dict] = []
    global_index = 0

    for pdf_path in pdf_paths:
        pages = load_pdf(pdf_path)
        chunks = chunk_document(pages, chunk_size, chunk_overlap)

        # Re-index chunks with global index
        for chunk in chunks:
            chunk["chunk_index"] = global_index
            global_index += 1
            all_chunks.append(chunk)

    return all_chunks
