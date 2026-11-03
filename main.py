#!/usr/bin/env python3
"""Read and write ID3v1 and ID3v2.3 tags, including embedded album art."""
import argparse
import os
import struct
import tempfile

TEXT_FRAMES = {"TIT2": "title", "TPE1": "artist", "TALB": "album", "TYER": "year", "TCON": "genre"}
V1_GENRES = ["Blues", "Classic Rock", "Country", "Dance", "Disco", "Funk", "Grunge",
             "Hip-Hop", "Jazz", "Metal", "New Age", "Oldies", "Other", "Pop", "R&B",
             "Rap", "Reggae", "Rock"]

def syncsafe(value: int) -> bytes:
    return bytes(((value >> 21) & 0x7F, (value >> 14) & 0x7F, (value >> 7) & 0x7F, value & 0x7F))

def unsyncsafe(data: bytes) -> int:
    return (data[0] << 21) | (data[1] << 14) | (data[2] << 7) | data[3]

def read_v2(handle):
    header = handle.read(10)
    if len(header) < 10 or header[:3] != b"ID3":
        return None, {}
    size = unsyncsafe(header[6:10])
    body = handle.read(size)
    tags, picture = {}, None
    position = 0
    while position + 10 <= len(body):
        frame_id = body[position:position + 4]
        if frame_id == b"\x00\x00\x00\x00":
            break
        frame_size = int.from_bytes(body[position + 4:position + 8], "big")
        data = body[position + 10:position + 10 + frame_size]
        position += 10 + frame_size
        try:
            name = frame_id.decode("ascii")
        except UnicodeDecodeError:
            continue
        if name in TEXT_FRAMES and data:
            encoding, payload = data[0], data[1:]
            if encoding == 1:
                text = payload.decode("utf-16", errors="replace").rstrip("\x00")
            else:
                text = payload.decode("latin-1", errors="replace").rstrip("\x00")
            tags[TEXT_FRAMES[name]] = text
        elif name == "APIC" and data:
            # encoding(1) mime\0 picture-type(1) description\0 image data
            _, rest = data[0], data[1:]
            mime, _, rest = rest.partition(b"\x00")
            if not rest:
                continue
            picture_type, rest = rest[0], rest[1:]
            _, _, image = rest.partition(b"\x00")
            picture = {"mime": mime.decode("latin-1"), "type": picture_type, "data": image}
    return size, {"tags": tags, "picture": picture}

def read_v1(handle):
    handle.seek(0, os.SEEK_END)
    if handle.tell() < 128:
        return {}
    handle.seek(-128, os.SEEK_END)
    block = handle.read(128)
    if block[:3] != b"TAG":
        return {}
    def text(chunk):
        return chunk.decode("latin-1", errors="replace").strip("\x00 ").strip()
    genre = block[127] if block[127] < len(V1_GENRES) else ""
    return {"title": text(block[3:33]), "artist": text(block[33:63]),
            "album": text(block[63:93]), "year": text(block[93:97]),
            "comment": text(block[97:127]), "genre": genre}

def read_tags(path: str):
    with open(path, "rb") as handle:
        v2_size, v2 = read_v2(handle)
        result = dict(v2.get("tags", {}))
        result["picture"] = v2.get("picture")
        for key, value in read_v1(handle).items():
            if value:
                result.setdefault(key, value)
        result.setdefault("comment", "")
        return result

def build_v2(tags, picture=None) -> bytes:
    frames = b""
    for frame_id, key in TEXT_FRAMES.items():
        value = tags.get(key)
        if value:
            payload = b"\x00" + str(value).encode("latin-1", errors="replace")
            frames += frame_id.encode() + struct.pack(">I", len(payload)) + b"\x00\x00" + payload
    if picture:
        payload = (b"\x00" + picture["mime"].encode("latin-1") + b"\x00"
                   + bytes([picture.get("type", 3)]) + b"Cover\x00" + picture["data"])
        frames += b"APIC" + struct.pack(">I", len(payload)) + b"\x00\x00" + payload
    return b"ID3\x03\x00\x00" + syncsafe(len(frames)) + frames

def build_v1(tags) -> bytes:
    def field(value, width):
        return str(value or "").encode("latin-1", errors="replace")[:width].ljust(width, b"\x00")
    genre_index = V1_GENRES.index(tags["genre"]) if tags.get("genre") in V1_GENRES else 255
    return (b"TAG" + field(tags.get("title"), 30) + field(tags.get("artist"), 30)
            + field(tags.get("album"), 30) + field(tags.get("year"), 4)
            + field(tags.get("comment"), 30) + bytes([genre_index]))

def write_tags(path: str, tags, picture=None) -> None:
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:3] == b"ID3" and len(data) >= 10:
        data = data[10 + unsyncsafe(data[6:10]):]
    if data[-128:-125] == b"TAG":
        data = data[:-128]
    with open(path, "wb") as handle:
        handle.write(build_v2(tags, picture) + data + build_v1(tags))

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
       b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0"
       b"\x00\x00\x00\x00IEND\xaeB`\x82")

def demo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "demo.mp3")
        # One MPEG-1 Layer III frame header plus padding: enough for a tag demo.
        with open(path, "wb") as handle:
            handle.write(b"\xff\xfb\x90\x64" + b"\x00" * 413)
        write_tags(path, {"title": "Demo Song", "artist": "The Testers", "album": "Fixtures",
                          "year": "2026", "genre": "Rock", "comment": "written by Mp3-Tagger"},
                   {"mime": "image/png", "type": 3, "data": PNG})
        tags = read_tags(path)
        print(f"title={tags['title']} | artist={tags['artist']} | album={tags['album']}")
        print(f"year={tags['year']} | genre={tags['genre']} | comment={tags['comment']}")
        print(f"album art: {tags['picture']['mime']} {len(tags['picture']['data'])} bytes")
        print("file size:", os.path.getsize(path), "bytes")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?")
    parser.add_argument("--title"); parser.add_argument("--artist")
    parser.add_argument("--album"); parser.add_argument("--year")
    parser.add_argument("--genre"); parser.add_argument("--comment")
    parser.add_argument("--picture", help="image file to embed as album art")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo or not args.file:
        demo(); return
    try:
        if any([args.title, args.artist, args.album, args.year, args.genre, args.comment, args.picture]):
            tags = {key: getattr(args, key) for key in ("title", "artist", "album", "year", "genre", "comment") if getattr(args, key)}
            picture = None
            if args.picture:
                picture = {"mime": "image/png" if args.picture.lower().endswith(".png") else "image/jpeg",
                           "type": 3, "data": open(args.picture, "rb").read()}
            write_tags(args.file, tags, picture)
        tags = read_tags(args.file)
        if args.json:
            import json
            picture = tags.pop("picture", None)
            tags["picture"] = {"mime": picture["mime"], "bytes": len(picture["data"])} if picture else None
            print(json.dumps(tags, indent=2))
        else:
            for key, value in tags.items():
                if key == "picture":
                    print(f"{key:<8} {value['mime'] + ' ' + str(len(value['data'])) + ' bytes' if value else '-'}")
                else:
                    print(f"{key:<8} {value}")
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Error: {exc}")

if __name__ == "__main__":
    main()
