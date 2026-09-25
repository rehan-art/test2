from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
PDF_WIDTH, PDF_HEIGHT = 3840, 2400

def create_pdf(image_path, pdf_path):
    image_path, pdf_path = Path(image_path), Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(pdf_path), pagesize=(PDF_WIDTH, PDF_HEIGHT), pageCompression=1)
    pdf.drawImage(ImageReader(str(image_path)), 0, 0, width=PDF_WIDTH, height=PDF_HEIGHT, preserveAspectRatio=False)
    pdf.showPage(); pdf.save()
    return pdf_path
