"""Seed explicitly synthetic fixtures, only after the API confirms isolated demo mode."""

import argparse
import io
import json
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1") or parsed.scheme != "http":
        parser.error("Only a loopback demo API is accepted")
    with httpx.Client(base_url=args.base_url, timeout=30, headers={"Origin": f"{parsed.scheme}://{parsed.netloc}"}) as client:
        session = client.get("/auth/session")
        if session.status_code != 200 or session.json().get("demo_mode") is not True:
            parser.error("The API must explicitly confirm demo_mode=true")
        results = []
        for name, amount, marker in [("approved", "60000", "CATEGORY:MEALS"),
                                     ("clarification", "65000", "LOW_CONFIDENCE"),
                                     ("review", "700000", "ordinary")]:
            image = Image.new("RGB", (900, 600), "white")
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default(size=32)
            draw.multiline_text((40, 40), f"NOTA SINTETIS TERA\nSkenario: {name}\nTotal IDR {amount}\n\nBukan transaksi nyata", fill="black", font=font, spacing=20)
            content = io.BytesIO()
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("synthetic_fixture", marker)
            image.save(content, "PNG", pnginfo=metadata)
            created = client.post("/claims", data={"employee_id": "demo-reviewer", "declared_amount": amount},
                                  files={"files": (f"synthetic-{name}.png", content.getvalue(), "image/png")})
            created.raise_for_status()
            claim_id = created.json()["claim"]["id"]
            processed = client.post(f"/claims/{claim_id}/process")
            processed.raise_for_status()
            results.append({"scenario": name, "claim_id": claim_id, "status": processed.json()["claim"]["status"]})
        print(json.dumps({"synthetic": True, "demo_confirmed": True, "claims": results}, indent=2))


if __name__ == "__main__":
    main()
