import pymupdf
import pytesseract

from PIL import Image


def extract_text_from_pdf(file_path: str):
    document = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(document):

        # Primero intentamos obtener el texto normal
        text = page.get_text("text")

        # Si el texto parece corrupto, usamos OCR
        if is_text_corrupted(text):
            print(
                f"Página {page_number + 1}: "
                "texto sospechoso, ejecutando OCR..."
            )

            text = extract_text_with_ocr(page)

        # Eliminar caracteres problemáticos
        text = text.replace("\x00", "")

        pages.append({
            "page": page_number + 1,
            "text": text
        })

    document.close()

    return pages


def extract_text_with_ocr(page):
    """
    Convierte la página PDF en imagen y ejecuta OCR.
    """

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    image = Image.frombytes(
        "RGB",
        [pixmap.width, pixmap.height],
        pixmap.samples
    )

    text = pytesseract.image_to_string(
        image,
        lang="eng"
    )

    return text


def is_text_corrupted(text: str) -> bool:
    """
    Detecta algunos casos en los que la capa de texto
    del PDF parece estar corrupta.
    """

    if not text:
        return True

    # Texto demasiado pequeño
    if len(text.strip()) < 20:
        return True

    # Caracteres NUL
    if "\x00" in text:
        return True

    # Caracteres típicos de extracción corrupta
    suspicious_chars = [
        "�",
        "￾"
    ]

    for char in suspicious_chars:
        if char in text:
            return True

    # Muchos underscores suelen indicar problemas
    # de codificación en algunos PDFs
    underscore_ratio = text.count("_") / len(text)

    if underscore_ratio > 0.03:
        return True

    return False