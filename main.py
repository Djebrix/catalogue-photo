"""Impossible Gadget Catalogue Photo.

Writes the catalogue photograph of the RAIN-OFF personal rain-cloud
remote to /output/entry.png.

The photograph itself is shipped as the asset gadget.png (a studio
product shot generated at build time: a matte white and brushed
aluminium remote with one big red button, labelled RAIN-OFF, standing
on a white pedestal under the tiny rain cloud it summoned, with one
miniature yellow umbrella as its accessory). This program performs no
network access and uses only the Python standard library: it copies
the asset byte-for-byte to the output path, so the output is fully
deterministic.

Before anything is written the asset is validated as a whole PNG
(signature, IHDR dimensions, chunk structure, CRCs, IEND trailer),
and after the write the output file is read back and validated again
so a truncated or corrupted write can never pass as an entry.
"""

import hashlib
import os
import struct
import sys
import zlib

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gadget.png")
OUTPUT = "/output/entry.png"

MAX_BYTES = 1_048_576
MAX_DIMENSION = 1024

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# (colour type -> allowed bit depths), per the PNG specification.
_VALID_DEPTHS = {
    0: (1, 2, 4, 8, 16),  # greyscale
    2: (8, 16),           # truecolour
    3: (1, 2, 4, 8),      # indexed-colour
    4: (8, 16),           # greyscale + alpha
    6: (8, 16),           # truecolour + alpha
}


class InvalidPngError(ValueError):
    """Raised when a byte string is not a whole, well-formed PNG."""


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_png_dimensions(data: bytes) -> tuple[int, int]:
    """Validate the PNG structure and return its (width, height).

    Checks, in order: the 8-byte signature, a 13-byte IHDR as the
    first chunk with sane header fields, every chunk's length and CRC,
    and a terminating IEND chunk with nothing trailing it. Raises
    InvalidPngError on the first violation found.
    """
    if len(data) < len(PNG_SIGNATURE) + 25:
        raise InvalidPngError(
            f"file too short to be a PNG: {len(data)} bytes"
        )
    if not data.startswith(PNG_SIGNATURE):
        raise InvalidPngError("missing PNG signature (magic bytes)")

    offset = len(PNG_SIGNATURE)
    first = True
    saw_iend = False

    while offset < len(data):
        if offset + 8 > len(data):
            raise InvalidPngError(
                f"truncated chunk header at offset {offset}"
            )
        length, chunk_type = struct.unpack(">I4s", data[offset:offset + 8])
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise InvalidPngError(
                f"truncated {chunk_type.decode('latin-1')} chunk: "
                f"declares {length} bytes, file ends at {len(data)}"
            )
        body = data[offset + 4:offset + 8 + length]
        stored_crc, = struct.unpack(">I", data[offset + 8 + length:chunk_end])
        actual_crc = zlib.crc32(body) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            raise InvalidPngError(
                f"bad CRC in {chunk_type.decode('latin-1')} chunk "
                f"(stored {stored_crc:#010x}, computed {actual_crc:#010x})"
            )

        if first:
            if chunk_type != b"IHDR":
                raise InvalidPngError(
                    f"first chunk is {chunk_type.decode('latin-1')}, not IHDR"
                )
            if length != 13:
                raise InvalidPngError(f"IHDR length is {length}, not 13")
            width, height, depth, colour, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", data[offset + 8:offset + 21])
            )
            if width == 0 or height == 0:
                raise InvalidPngError(
                    f"IHDR dimensions are {width}x{height}"
                )
            if colour not in _VALID_DEPTHS:
                raise InvalidPngError(f"unknown PNG colour type {colour}")
            if depth not in _VALID_DEPTHS[colour]:
                raise InvalidPngError(
                    f"bit depth {depth} invalid for colour type {colour}"
                )
            if compression != 0 or filtering != 0 or interlace not in (0, 1):
                raise InvalidPngError(
                    "IHDR has unsupported compression/filter/interlace "
                    f"fields: {compression}/{filtering}/{interlace}"
                )
            first = False

        if chunk_type == b"IEND":
            if length != 0:
                raise InvalidPngError(f"IEND carries {length} bytes")
            if chunk_end != len(data):
                raise InvalidPngError(
                    f"{len(data) - chunk_end} trailing bytes after IEND"
                )
            saw_iend = True
            break

        offset = chunk_end

    if first:
        raise InvalidPngError("no IHDR chunk found")
    if not saw_iend:
        raise InvalidPngError("missing IEND chunk (truncated PNG)")

    return width, height


def validate_entry(data: bytes, label: str) -> tuple[int, int]:
    """Gate checks for a candidate entry: whole PNG, size, dimensions."""
    if len(data) > MAX_BYTES:
        raise InvalidPngError(
            f"{label} too large: {len(data)} bytes "
            f"(limit {MAX_BYTES})"
        )
    width, height = parse_png_dimensions(data)
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise InvalidPngError(
            f"{label} is {width}x{height}, over the "
            f"{MAX_DIMENSION}x{MAX_DIMENSION} limit"
        )
    return width, height


def main() -> int:
    if not os.path.isfile(ASSET):
        return _fail(f"missing asset: {ASSET}")

    try:
        with open(ASSET, "rb") as source:
            data = source.read()
    except OSError as exc:
        return _fail(f"cannot read asset {ASSET}: {exc}")

    # Validate the asset before writing so a corrupt asset can never
    # produce a bad entry.
    try:
        width, height = validate_entry(data, "asset")
    except InvalidPngError as exc:
        return _fail(f"asset {ASSET} rejected: {exc}")

    try:
        os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    except OSError as exc:
        return _fail(f"cannot create output directory: {exc}")

    # Write to a temp file in the same directory, then rename, so a
    # crash mid-write never leaves a partial entry.png behind.
    tmp_path = OUTPUT + ".tmp"
    try:
        with open(tmp_path, "wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.replace(tmp_path, OUTPUT)
    except OSError as exc:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return _fail(f"cannot write {OUTPUT}: {exc}")

    # Read the output back and validate it again: the file on disk,
    # not just the bytes in memory, must be a whole valid PNG.
    try:
        with open(OUTPUT, "rb") as written:
            written_data = written.read()
    except OSError as exc:
        return _fail(f"cannot read back {OUTPUT}: {exc}")
    if written_data != data:
        return _fail(
            f"output mismatch: {OUTPUT} differs from the asset "
            f"({len(written_data)} bytes written, {len(data)} expected)"
        )
    try:
        out_width, out_height = validate_entry(written_data, "output")
    except InvalidPngError as exc:
        return _fail(f"output {OUTPUT} rejected on re-read: {exc}")
    if (out_width, out_height) != (width, height):
        return _fail(
            f"output dimensions {out_width}x{out_height} differ from "
            f"asset {width}x{height}"
        )

    digest = hashlib.sha256(data).hexdigest()
    print(
        f"wrote {OUTPUT}: {len(data)} bytes, {width}x{height} PNG, "
        f"sha256 {digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
