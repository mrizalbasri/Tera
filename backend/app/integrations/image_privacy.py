"""Image metadata sanitization at the provider boundary (M7, FR-13).

The receipt image is the submitted source document, so its pixels must reach
the vision model untouched — text masking cannot protect data embedded AROUND
the pixels. This module strips that envelope in the same choke point as text
masking, before any bytes leave the process:

- JPEG: all APPn metadata segments (EXIF with GPS/device info, XMP, IPTC,
  vendor markers) and COM comments, except APP0 (JFIF) and APP14 (Adobe
  colour transform) which carry no personal data but affect decoding.
- PNG: ancillary text chunks (tEXt, zTXt, iTXt), eXIf, and tIME.

Entropy-coded JPEG data after SOS is copied verbatim up to the FIRST
end-of-image marker; anything after EOI is discarded — trailing payloads
must never cross the boundary. PNG chunks are validated fail-closed: every
CRC must match, IHDR must come first, at least one IDAT must precede IEND,
and IEND must end the stream exactly. Structural validation alone cannot
prove an image renders, so the sanitized bytes are then fully decoded with
a trusted decoder (Pillow) under a pixel-count guard — a payload that does
not decode is rejected, not forwarded. Any failure raises: the caller
turns it into a classified non-retryable error instead of sending
unsanitized bytes.
"""

import zlib
from io import BytesIO

from PIL import Image

_JPEG_SOI = b"\xff\xd8"
_JPEG_EOI_BYTES = b"\xff\xd9"
_JPEG_STANDALONE_MARKERS = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7}
_JPEG_SOS_MARKER = 0xDA
_JPEG_EOI_MARKER = 0xD9
_JPEG_COM_MARKER = 0xFE
# Frame headers (SOF0-SOF15) minus DHT (C4), JPG (C8), and DAC (CC).
_JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}
# APP0 (JFIF) and APP14 (Adobe transform) are kept; APP1-APP13, APP15 carry
# EXIF/XMP/IPTC/vendor metadata and are dropped.
_JPEG_METADATA_APP_MARKERS = set(range(0xE1, 0xEE)) | {0xEF}

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_METADATA_CHUNKS = {b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"}
_PNG_IHDR = b"IHDR"
_PNG_IDAT = b"IDAT"
_PNG_IEND = b"IEND"
_PNG_IHDR_LENGTH = 13

# ~30 MP: phone-photo receipts are far below this; the guard bounds
# decompression work (decompression-bomb protection) before full decode.
_MAX_IMAGE_PIXELS = 30_000_000
Image.MAX_IMAGE_PIXELS = _MAX_IMAGE_PIXELS


def strip_image_metadata(content: bytes, media_type: str) -> bytes:
    """Return ``content`` without privacy-bearing metadata for its format."""
    if media_type == "image/jpeg":
        sanitized = _strip_jpeg(content)
    elif media_type == "image/png":
        sanitized = _strip_png(content)
    else:
        raise ValueError(f"unsupported image media type: {media_type}")
    _verify_decodable(sanitized)
    return sanitized


def _verify_decodable(sanitized: bytes) -> None:
    """Fully decode the sanitized bytes with a trusted decoder.

    Structural checks above cannot prove the image renders (e.g. a PNG with
    valid CRCs but garbage IDAT), so decoding is the fail-closed backstop.
    Failure messages are static — no payload content ever reaches them.
    """
    try:
        with Image.open(BytesIO(sanitized)) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > _MAX_IMAGE_PIXELS:
                raise ValueError("image dimensions out of range")
            image.load()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("image failed to decode") from exc


def _strip_jpeg(data: bytes) -> bytes:
    if len(data) < 4 or data[:2] != _JPEG_SOI:
        raise ValueError("not a JPEG image")
    out = bytearray(_JPEG_SOI)
    saw_frame = False
    saw_scan = False
    i = 2
    size = len(data)
    while i < size:
        if data[i] != 0xFF:
            raise ValueError("corrupt JPEG marker stream")
        if i + 1 >= size:
            raise ValueError("truncated JPEG marker")
        marker = data[i + 1]
        if marker == 0xFF:  # padding fill byte
            i += 1
            continue
        segment_start = i
        i += 2
        if marker in _JPEG_STANDALONE_MARKERS:
            out += data[segment_start:i]
            continue
        if marker == _JPEG_EOI_MARKER:
            if not (saw_frame and saw_scan):
                # Fail closed: a marker stream without frame and scan data
                # carries no image, so nothing here is a receipt to parse.
                raise ValueError("JPEG without frame or scan data")
            out += data[segment_start:i]
            break
        if i + 2 > size:
            raise ValueError("truncated JPEG segment")
        segment_length = int.from_bytes(data[i : i + 2], "big")
        segment_end = i + segment_length
        if segment_length < 2 or segment_end > size:
            raise ValueError("truncated JPEG segment")
        if marker in _JPEG_SOF_MARKERS:
            saw_frame = True
        if marker == _JPEG_SOS_MARKER:
            saw_scan = True
            if not saw_frame:
                raise ValueError("JPEG scan without frame data")
            # Entropy-coded scan data carries no metadata; copy up to the
            # first end-of-image marker. A raw 0xFFD9 cannot occur inside a
            # legal scan (byte stuffing turns 0xFF into 0xFF 0x00, restart
            # markers are FFD0-FFD7), so the first hit is the true EOI.
            out += data[segment_start:segment_end]
            eoi = data.find(_JPEG_EOI_BYTES, segment_end)
            if eoi == -1:
                raise ValueError("truncated JPEG scan")
            out += data[segment_end : eoi + 2]
            break
        keeps_metadata = (
            marker == _JPEG_COM_MARKER or marker in _JPEG_METADATA_APP_MARKERS
        )
        if not keeps_metadata:
            out += data[segment_start:segment_end]
        i = segment_end
    else:
        raise ValueError("truncated JPEG image")
    return bytes(out)


def _strip_png(data: bytes) -> bytes:
    if data[:8] != _PNG_SIGNATURE:
        raise ValueError("not a PNG image")
    out = bytearray(_PNG_SIGNATURE)
    i = 8
    size = len(data)
    seen_ihdr = False
    seen_idat = False
    idat_closed = False
    while i + 8 <= size:
        chunk_length = int.from_bytes(data[i : i + 4], "big")
        chunk_type = data[i + 4 : i + 8]
        chunk_end = i + 12 + chunk_length
        if chunk_end > size:
            raise ValueError("truncated PNG chunk")
        stored_crc = int.from_bytes(data[chunk_end - 4 : chunk_end], "big")
        if zlib.crc32(data[i + 4 : chunk_end - 4]) != stored_crc:
            raise ValueError("corrupt PNG chunk CRC")
        if chunk_type == _PNG_IHDR:
            if seen_ihdr or i != 8 or chunk_length != _PNG_IHDR_LENGTH:
                raise ValueError("invalid PNG IHDR placement")
            seen_ihdr = True
        elif chunk_type == _PNG_IDAT:
            if not seen_ihdr or idat_closed:
                raise ValueError("invalid PNG IDAT placement")
            seen_idat = True
        elif seen_idat:
            idat_closed = True
        if chunk_type not in _PNG_METADATA_CHUNKS:
            out += data[i:chunk_end]
        if chunk_type == _PNG_IEND:
            if not (seen_ihdr and seen_idat):
                raise ValueError("PNG without image data")
            if chunk_length != 0:
                raise ValueError("non-empty PNG IEND")
            if chunk_end != size:
                raise ValueError("trailing data after PNG IEND")
            return bytes(out)
        i = chunk_end
    raise ValueError("truncated PNG image")
