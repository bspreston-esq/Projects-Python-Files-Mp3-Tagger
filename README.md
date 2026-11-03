# Mp3 Tagger

**Category:** Files

## Problem

Modify and add ID3v1 tags to MP3 files. See if you can also add in the album art into the MP3 file's header as well as other ID3v2 tags.

## Solution

Implements ID3v2.3 text frames (TIT2, TPE1, TALB, TYER, TCON) and APIC album art in pure Python, plus the 128-byte ID3v1 trailer. Writes strip any existing ID3v2 header and v1 trailer before rebuilding them, so audio bytes are preserved and tags stay single-copy. Reading prefers v2 and falls back to v1 per field.

## How to run

Requires Python 3.8+ and no third-party packages.

```bash
python3 main.py song.mp3
python3 main.py song.mp3 --title "Song" --artist "Band" --album "Record" --year 2026 --genre Rock --picture cover.png
python3 main.py --demo
```

## Example

```text
title=Demo Song | artist=The Testers | album=Fixtures
year=2026 | genre=Rock | comment=written by Mp3-Tagger
album art: image/png 69 bytes
file size: 743 bytes
```

## Attribution

The problem statement is from [karan/Projects](https://github.com/karan/Projects), a list of practical projects that anyone can solve in any programming language (MIT License, Copyright (c) 2013 Karan Goel). The Python solution in this repository was implemented by [bspreston-esq](https://github.com/bspreston-esq).

This repository is part of the [Projects-Python-All](https://github.com/bspreston-esq/Projects-Python-All) collection.
