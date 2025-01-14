import os
import pytesseract
from PIL import Image
import PyPDF2
import pdfplumber
from docx import Document


class ExtractText:
    """Handles text extraction from different CV file types."""

    @staticmethod
    def extract_based_on_extension(file_path):
        extension = os.path.splitext(file_path)[1].lower()
        if extension in [".jpg", ".jpeg", ".png"]:
            return ExtractText._extract_from_image(file_path)
        elif extension == ".pdf":
            return ExtractText._extract_from_pdf(file_path)
        elif extension == ".docx":
            return ExtractText._extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

    @staticmethod
    def _extract_from_image(file_path):
        try:
            return pytesseract.image_to_string(Image.open(file_path))
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""

    @staticmethod
    def _extract_from_pdf(file_path):
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = "".join([page.extract_text() for page in reader.pages])
            return text
        except Exception as e:
            print(f"Error extracting text from PDF (PyPDF2): {e}")
            try:
                with pdfplumber.open(file_path) as pdf:
                    return "".join([page.extract_text() for page in pdf.pages])
            except Exception as fallback_error:
                print(f"Error extracting text from PDF (pdfplumber): {fallback_error}")
                return ""

    @staticmethod
    def _extract_from_docx(file_path):
        try:
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Error extracting text from Word document: {e}")
            return ""
