from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "OneGrip_Play_A1_전시포스터_인쇄용.png"
PDF = ROOT / "OneGrip_Play_A1_전시포스터.pdf"
QA_PNG = ROOT / "OneGrip_Play_A1_전시포스터_pdf검수.png"

# ISO 216 A1 portrait: 594 x 841 mm
MM_TO_PT = 72.0 / 25.4
PAGE_W = 594.0 * MM_TO_PT
PAGE_H = 841.0 * MM_TO_PT

c = canvas.Canvas(str(PDF), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
c.setTitle("OneGrip Play A1 전시포스터")
c.setAuthor("동국대학교 전자전기공학부 OneGrip Play 팀")
c.setSubject("제7회 국립재활원 보조기기 해커톤 전시용 디자인물")
c.drawImage(ImageReader(str(PNG)), 0, 0, width=PAGE_W, height=PAGE_H, preserveAspectRatio=False, mask="auto")
c.showPage()
c.save()

reader = PdfReader(str(PDF))
assert len(reader.pages) == 1
box = reader.pages[0].mediabox
width = float(box.width)
height = float(box.height)
assert abs(width - PAGE_W) < 0.5
assert abs(height - PAGE_H) < 0.5

pdf = pdfium.PdfDocument(str(PDF))
page = pdf[0]
bitmap = page.render(scale=1.0)
bitmap.to_pil().save(QA_PNG)
page.close()
pdf.close()

print(f"PDF={PDF}")
print(f"QA_PNG={QA_PNG}")
print(f"pages={len(reader.pages)} size_pt={width:.2f}x{height:.2f} size_mm={width/MM_TO_PT:.2f}x{height/MM_TO_PT:.2f}")
