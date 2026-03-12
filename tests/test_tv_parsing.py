
import os
import sys
import re

# Simulate the parsing logic
def parse_tv_title(raw_name: str):
    """Parses a torrent name into (Show Name, Season Number)."""
    # Patterns for S01E05, 1x05, etc.
    s_match = re.search(r'(.*?)[. ]s(\d{1,2})[e. ]', raw_name, re.IGNORECASE)
    if not s_match:
        s_match = re.search(r'(.*?)[. ](\d{1,2})x', raw_name, re.IGNORECASE)
    
    if s_match:
        show_name = s_match.group(1).replace(".", " ").strip()
        season_num = int(s_match.group(2))
        return show_name, season_num
    
    return raw_name, None

def test_parsing():
    test_cases = [
        ("True.Blood.S03.1080p.HMAX.WEB-DL.DD5.1.H.264-playWEB", ("True Blood", 3)),
        ("The.Simpsons.S32E01.720p.HDTV.x264-SYNCOPY", ("The Simpsons", 32)),
        ("The.Office.US.1x05.Basketball.DVDRip.XviD-OSi", ("The Office US", 1)),
        ("Stranger.Things.S04.2160p.NF.WEB-DL.DDP5.1.Atmos.HDR.HEVC-MZABI", ("Stranger Things", 4)),
        ("Movie.Title.2023.1080p.BluRay.x264-SPARKS", ("Movie.Title.2023.1080p.BluRay.x264-SPARKS", None))
    ]
    
    for raw, expected in test_cases:
        result = parse_tv_title(raw)
        print(f"Input: {raw}")
        print(f"Result: {result}")
        assert result == expected
    
    print("Parsing logic verification successful!")

if __name__ == "__main__":
    test_parsing()
