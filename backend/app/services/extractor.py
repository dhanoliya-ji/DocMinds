import os
import csv
import zipfile
import uuid
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from pptx import Presentation
import openpyxl
from bs4 import BeautifulSoup
from email import message_from_bytes
from email.policy import default as default_email_policy
from langdetect import detect
from typing import Dict, Any

from app.core.config import settings
from app.services.ocr import OCRService


class ExtractionResult:
    def __init__(self, text: str, metadata: Dict[str, Any], language: str, needs_ocr: bool = False):
        self.text = text
        self.metadata = metadata
        self.language = language
        self.needs_ocr = needs_ocr

class DocumentExtractor:
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detect language of a text block. Falls back to 'en'.
        """
        if not text or len(text.strip()) < 10:
            return "en"
        try:
            return detect(text)
        except Exception:
            return "en"

    @classmethod
    def extract(cls, file_path: str, file_type: str) -> ExtractionResult:
        """
        Route file to its appropriate parser based on extension.
        """
        file_type = file_type.lower()
        if file_type == "pdf":
            return cls.extract_pdf(file_path)
        elif file_type in ["png", "jpg", "jpeg", "tiff", "bmp", "gif"]:
            return cls.extract_image(file_path, file_type)
        elif file_type == "docx":
            return cls.extract_docx(file_path)
        elif file_type == "pptx":
            return cls.extract_pptx(file_path)
        elif file_type in ["xlsx", "xls"]:
            return cls.extract_xlsx(file_path)
        elif file_type in ["html", "htm"]:
            return cls.extract_html(file_path)
        elif file_type == "eml":
            return cls.extract_eml(file_path)
        elif file_type in ["txt", "md", "markdown"]:
            return cls.extract_txt_or_md(file_path)
        elif file_type == "csv":
            return cls.extract_csv(file_path)
        elif file_type == "zip":
            return cls.extract_zip(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @classmethod
    def extract_image(cls, file_path: str, file_type: str) -> ExtractionResult:
        """
        Directly run OCR on uploaded image files.
        """
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            text = OCRService.ocr_image(img_bytes)
            metadata = {"image_ocr": True, "ocr_provider": settings.OCR_PROVIDER}
        except Exception as e:
            text = f"Image OCR extraction failed: {str(e)}"
            metadata = {"error": str(e)}
            
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text),
            needs_ocr=True
        )

    @classmethod
    def extract_pdf(cls, file_path: str) -> ExtractionResult:
        text = ""
        metadata = {}
        needs_ocr = False
        try:
            doc = fitz.open(file_path)
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "creator": doc.metadata.get("creator", ""),
                "page_count": len(doc),
            }
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())
            text = "\n--- PAGE BREAK ---\n".join(pages_text)
            
            # Heuristic: If average character count per page is very low, it's likely scanned
            if len(doc) > 0 and len(text.strip()) < 100 * len(doc):
                print(f"[Extractor] Low text density detected in PDF. Triggering OCR pipeline fallback...")
                ocr_text, _ = OCRService.ocr_pdf(file_path)
                text = ocr_text
                needs_ocr = True
                metadata["ocr_applied"] = True
                metadata["ocr_provider"] = settings.OCR_PROVIDER
        except Exception as e:
            print(f"[Extractor] PDF extraction failed: {e}. Attempting OCR fallback...")
            try:
                ocr_text, _ = OCRService.ocr_pdf(file_path)
                text = ocr_text
                needs_ocr = True
                metadata["ocr_applied"] = True
                metadata["ocr_provider"] = settings.OCR_PROVIDER
            except Exception as ocr_err:
                text = f"PDF extraction and OCR fallback failed: {str(ocr_err)}"
                needs_ocr = True

        
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text),
            needs_ocr=needs_ocr
        )


    @classmethod
    def extract_docx(cls, file_path: str) -> ExtractionResult:
        text = ""
        metadata = {}
        try:
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            
            # Simple table extraction
            table_texts = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells])
                    table_texts.append(row_text)
            
            text = "\n".join(paragraphs)
            if table_texts:
                text += "\n\nTables:\n" + "\n".join(table_texts)
                
            metadata = {
                "paragraph_count": len(paragraphs),
                "table_count": len(doc.tables),
            }
        except Exception as e:
            text = f"DOCX extraction failed: {str(e)}"
            
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text)
        )

    @classmethod
    def extract_pptx(cls, file_path: str) -> ExtractionResult:
        text = ""
        metadata = {}
        try:
            prs = Presentation(file_path)
            slides_text = []
            for i, slide in enumerate(prs.slides, 1):
                slide_text = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text.strip())
                slides_text.append(f"Slide {i}:\n" + "\n".join(slide_text))
            
            text = "\n\n".join(slides_text)
            metadata = {"slide_count": len(prs.slides)}
        except Exception as e:
            text = f"PPTX extraction failed: {str(e)}"
            
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text)
        )

    @classmethod
    def extract_xlsx(cls, file_path: str) -> ExtractionResult:
        text = ""
        metadata = {}
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheets_text = []
            for name in wb.sheetnames:
                sheet = wb[name]
                rows_text = []
                for row in sheet.iter_rows(values_only=True):
                    if any(row):  # Skip completely empty rows
                        rows_text.append(" | ".join([str(val) if val is not None else "" for val in row]))
                sheets_text.append(f"Sheet '{name}':\n" + "\n".join(rows_text))
            
            text = "\n\n".join(sheets_text)
            metadata = {"sheet_names": wb.sheetnames}
        except Exception as e:
            text = f"Excel extraction failed: {str(e)}"
            
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text)
        )

    @classmethod
    def extract_html(cls, file_path: str) -> ExtractionResult:
        text = ""
        metadata = {}
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
                raw_text = soup.get_text(separator="\n")
                text = "\n".join([line.strip() for line in raw_text.splitlines() if line.strip()])
                metadata = {"title": soup.title.string if soup.title else ""}
        except Exception as e:
            text = f"HTML extraction failed: {str(e)}"
            
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text)
        )

    @classmethod
    def extract_eml(cls, file_path: str) -> ExtractionResult:
        text = ""
        metadata = {}
        try:
            with open(file_path, "rb") as f:
                msg = message_from_bytes(f.read(), policy=default_email_policy)
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get_params())
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            body += part.get_payload(decode=True).decode(errors="ignore")
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                
                metadata = {
                    "subject": msg.get("Subject", ""),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "date": msg.get("Date", ""),
                }
                text = f"From: {metadata['from']}\nTo: {metadata['to']}\nDate: {metadata['date']}\nSubject: {metadata['subject']}\n\nBody:\n{body}"
        except Exception as e:
            text = f"Email extraction failed: {str(e)}"
            
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text)
        )

    @classmethod
    def extract_txt_or_md(cls, file_path: str) -> ExtractionResult:
        text = ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            text = f"Text extraction failed: {str(e)}"
        return ExtractionResult(
            text=text,
            metadata={},
            language=cls.detect_language(text)
        )

    @classmethod
    def extract_csv(cls, file_path: str) -> ExtractionResult:
        text = ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                rows = [" , ".join(row) for row in reader]
                text = "\n".join(rows)
        except Exception as e:
            text = f"CSV extraction failed: {str(e)}"
        return ExtractionResult(
            text=text,
            metadata={},
            language=cls.detect_language(text)
        )

    @classmethod
    def extract_zip(cls, file_path: str) -> ExtractionResult:
        texts = []
        metadata = {"files_extracted": []}
        try:
            temp_dir = os.path.join(os.path.dirname(file_path), f"zip_temp_{uuid.uuid4().hex}")
            os.makedirs(temp_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    sub_file_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lstrip(".").lower()
                    if ext in ["pdf", "docx", "pptx", "xlsx", "xls", "html", "htm", "eml", "txt", "md", "csv"]:
                        try:
                            res = cls.extract(sub_file_path, ext)
                            texts.append(f"--- File: {file} ---\n{res.text}")
                            metadata["files_extracted"].append(file)
                        except Exception as sub_e:
                            texts.append(f"--- File: {file} (Extraction failed: {sub_e}) ---")
                            
                    # Clean up temporary sub files
                    try:
                        os.remove(sub_file_path)
                    except Exception:
                        pass
                        
            text = "\n\n=================================\n\n".join(texts)
            
            # Clean up temp folder
            try:
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(temp_dir)
            except Exception:
                pass
        except Exception as e:
            text = f"ZIP extraction failed: {str(e)}"
            
        return ExtractionResult(
            text=text,
            metadata=metadata,
            language=cls.detect_language(text)
        )
