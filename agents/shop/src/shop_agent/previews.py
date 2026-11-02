"""PDF preview image rendering (pypdfium2) and Shopify staged upload."""

from io import BytesIO
from pathlib import Path

import httpx
import pypdfium2 as pdfium

from shop_agent.shopify.graphql import execute, mutation_result

STAGED_UPLOAD = """
mutation StagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets {
      url
      resourceUrl
      parameters { name value }
    }
    userErrors { field message }
  }
}
"""


def preview_pngs(pdf_path: Path, limit: int = 3) -> list[bytes]:
    pdf = pdfium.PdfDocument(str(pdf_path))
    images: list[bytes] = []
    for index in range(min(limit, len(pdf))):
        image = pdf[index].render(scale=2).to_pil().convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        images.append(buffer.getvalue())
    return images


def upload_preview(png: bytes, filename: str) -> str:
    data = execute(
        STAGED_UPLOAD,
        {
            "input": [
                {
                    "filename": filename,
                    "mimeType": "image/png",
                    "resource": "PRODUCT_IMAGE",
                    "httpMethod": "POST",
                }
            ]
        },
    )
    target = mutation_result(data, "stagedUploadsCreate")["stagedTargets"][0]
    form = {item["name"]: item["value"] for item in target["parameters"]}
    httpx.post(target["url"], data=form, files={"file": png}, timeout=30.0)
    return str(target["resourceUrl"])
