#!/usr/bin/env python3
"""
Tạo giọng đọc + SRT bằng CIT Voice Studio (phải đang mở, API ở 127.0.0.1:8001).

SRT sinh ra khớp từng câu với audio, dùng làm đầu vào cho parse_srt.py.

Cách dùng:
  python tts_cit.py <kịch-bản.txt> <out-prefix> [--voice "Hải Đăng"] [--speed 1.0] [--seed 42]
Kết quả: <out-prefix>.wav và <out-prefix>.srt
Danh sách giọng: http://127.0.0.1:8001/voices
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("script", type=Path)
    p.add_argument("out_prefix", type=Path)
    p.add_argument("--voice", default=None, help="voice_id, bỏ trống = giọng mặc định")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=None, help="cố định để đọc lại ra cùng audio")
    p.add_argument("--api", default="http://127.0.0.1:8001")
    args = p.parse_args()

    body = {"text": args.script.read_text(encoding="utf-8").strip(), "speed": args.speed, "format": "wav"}
    if args.voice:
        body["voice_id"] = args.voice
    if args.seed is not None:
        body["seed"] = args.seed
    req = urllib.request.Request(
        f"{args.api}/api/tts/generate-with-subtitles",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        # CPU int8 đọc chậm; kịch bản 90s có thể mất vài phút
        with urllib.request.urlopen(req, timeout=1800) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"CIT lỗi {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"Không gọi được CIT ở {args.api} ({e.reason}). Mở CIT Voice Studio trước.")

    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    wav, srt = args.out_prefix.with_suffix(".wav"), args.out_prefix.with_suffix(".srt")
    wav.write_bytes(base64.b64decode(res["audio_base64"]))
    srt.write_text(res["srt"], encoding="utf-8")
    print(f"{wav} ({res['duration_seconds']:.1f}s, {len(res['cues'])} câu)\n{srt}")


if __name__ == "__main__":
    main()
