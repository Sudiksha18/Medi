import io
import logging
from typing import List, Dict, Any
from PIL import Image
import pypdf

logger = logging.getLogger("medical_rag.doc_processor")

# Try importing pytesseract with fallback warning
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    logger.warning("pytesseract not installed. Image OCR will fall back to image metadata description.")

def extract_text_from_pdf(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Extract text page by page from PDF file bytes."""
    pages_data = []
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(pdf_file)
        
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages_data.append({
                    "page": idx + 1,
                    "text": text,
                    "filename": filename,
                    "document_type": "PDF Document"
                })
        return pages_data
    except Exception as e:
        logger.error(f"Error parsing PDF file {filename}: {e}")
        raise ValueError(f"Failed to read PDF document: {e}")

def extract_text_from_image(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Extract text from image using PyTesseract OCR with fallback."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        extracted_text = ""
        
        if HAS_TESSERACT:
            try:
                extracted_text = pytesseract.image_to_string(image)
            except Exception as ocr_err:
                logger.warning(f"Tesseract OCR failed: {ocr_err}. Falling back to image summary.")
                extracted_text = f"[Image Document: {filename} ({image.format}, {image.size[0]}x{image.size[1]} px). Note: OCR engine unavailable.]"
        else:
            extracted_text = f"[Medical Image Artifact: {filename} ({image.format}, {image.size[0]}x{image.size[1]} px). Note: Install Tesseract OCR to read embedded text.]"

        extracted_text = extracted_text.strip()
        if not extracted_text:
            extracted_text = f"[Image Document: {filename} - No readable text extracted by OCR]"

        return [{
            "page": 1,
            "text": extracted_text,
            "filename": filename,
            "document_type": "Medical Image / Scan"
        }]
    except Exception as e:
        logger.error(f"Error processing image file {filename}: {e}")
        raise ValueError(f"Failed to process image file: {e}")

def extract_text_from_plaintext(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Extract a UTF-8 (or common Windows-encoded) plain-text document."""
    text = ""
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = file_bytes.decode(encoding).strip()
            break
        except UnicodeDecodeError:
            continue
    if not text:
        raise ValueError(f"Text document {filename} is empty or uses an unsupported encoding.")
    return [{
        "page": 1,
        "text": text,
        "filename": filename,
        "document_type": "Plain Text Document"
    }]

def chunk_text(pages_data: List[Dict[str, Any]], patient_id: str, chunk_size: int = 600, overlap: int = 100) -> List[Dict[str, Any]]:
    """Split extracted page text into overlapping chunks for embedding."""
    chunks = []
    global_chunk_idx = 0
    
    for page_info in pages_data:
        text = page_info["text"]
        filename = page_info["filename"]
        page_num = page_info["page"]
        doc_type = page_info["document_type"]
        
        if len(text) <= chunk_size:
            chunks.append({
                "patient_id": patient_id,
                "filename": filename,
                "page": page_num,
                "chunk_index": global_chunk_idx,
                "text": text,
                "document_type": doc_type
            })
            global_chunk_idx += 1
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_str = text[start:end]
            
            # Try to break at a sentence or line boundary if available
            if end < len(text):
                last_space = chunk_str.rfind(" ")
                if last_space > chunk_size // 2:
                    end = start + last_space
                    chunk_str = text[start:end]

            chunks.append({
                "patient_id": patient_id,
                "filename": filename,
                "page": page_num,
                "chunk_index": global_chunk_idx,
                "text": chunk_str.strip(),
                "document_type": doc_type
            })
            global_chunk_idx += 1
            start = end - overlap if (end - overlap) > start else end

    return chunks
