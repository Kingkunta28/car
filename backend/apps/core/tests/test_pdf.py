from io import BytesIO

from django.test import SimpleTestCase
from PIL import Image as PillowImage
from reportlab.lib.utils import ImageReader

from apps.core.pdf import build_pdf, fitted_image


class PdfImageTests(SimpleTestCase):
    def test_fitted_image_embeds_uploaded_image_in_pdf(self):
        source = BytesIO()
        PillowImage.new("RGB", (1200, 800), color=(20, 40, 70)).save(source, format="JPEG")
        source.seek(0)

        image = fitted_image(ImageReader(source), 48, 30)
        pdf = build_pdf([image], title="Image smoke test", author="Rafiki Car Hire")

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)
