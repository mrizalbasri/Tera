"""Image metadata sanitization at the provider boundary (M7, FR-13).

The receipt image is the submitted source document, so its pixels must reach
the vision model untouched — text masking cannot protect data embedded AROUND
the pixels. This module strips that envelope in the same choke point as text
masking, before any bytes leave the process:

- JPEG: all APPn metadata segments (EXIF with GPS/device info, XMP, IPTC,
  vendor markers) and COM comments, except APP0 (JFIF) and APP14 (Adobe
  colour transform) which carry no personal data but affect decoding.
- PNG: ancillary text chunks (tEXt, zTXt, iTXt), eXIf, and tIME.

Entropy-coded JPEG data after SOS and PNG critical chunks are copied
verbatim. An image that cannot be parsed fails closed: the caller raises a
classified non-retryable error instead of sending unsanitized bytes.
"""

_JPEG_SOI = b"\xff\xd8"
_JPEG_STANDALONE_MARKERS = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7}
_JPEG_SOS_MARKER = 0xDA
_JPEG_EOI_MARKER = 0xD9
_JPEG_COM_MARKER = 0xFE
# APP0 (JFIF) and APP14 (Adobe transform) are kept; APP1-APP13, APP15 carry
# EXIF/XMP/IPTC/vendor metadata and are dropped.
_JPEG_METADATA_APP_MARKERS = set(range(0xE1, 0xEE)) | {0xEF}

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_METADATA_CHUNKS = {b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"}


def strip_image_metadata(content: bytes, media_type: str) -> bytes:
    """Return ``content`` without privacy-bearing metadata for its format."""
    if media_type == "image/jpeg":
        return _strip_jpeg(content)
    if media_type == "image/png":
        return _strip_png(content)
    raise ValueError(f"unsupported image media type: {media_type}")


def _strip_jpeg(data: bytes) -> bytes:
    if len(data) < 4 or data[:2] != _JPEG_SOI:
        raise ValueError("not a JPEG image")
    out = bytearray(_JPEG_SOI)
    i = 2
    size = len(data)
    while i < size:
        if data[i] != 0xFF:
            raise ValueError("corrupt JPEG marker stream")
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
            out += data[segment_start:i]
            break
        if i + 2 > size:
            raise ValueError("truncated JPEG segment")
        segment_length = int.from_bytes(data[i : i + 2], "big")
        segment_end = i + segment_length
        if segment_length < 2 or segment_end > size:
            raise ValueError("truncated JPEG segment")
        if marker == _JPEG_SOS_MARKER:
            # Entropy-coded scan data carries no metadata; copy verbatim.
            out += data[segment_start:segment_end]
            out += data[segment_end:]
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
    while i + 8 <= size:
        chunk_length = int.from_bytes(data[i : i + 4], "big")
        chunk_type = data[i + 4 : i + 8]
        chunk_end = i + 12 + chunk_length
        if chunk_end > size:
            raise ValueError("truncated PNG chunk")
        if chunk_type not in _PNG_METADATA_CHUNKS:
            out += data[i:chunk_end]
        if chunk_type == b"IEND":
            return bytes(out)
        i = chunk_end
    raise ValueError("truncated PNG image")
