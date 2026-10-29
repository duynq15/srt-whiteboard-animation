#!/usr/bin/env python3
"""
Xuất bản TikTok: 1080x1920, ghép giọng đọc, in phụ đề, hook mở đầu, nhãn AI.

Video whiteboard (không tiếng) được đặt giữa khung dọc nền tối. Nếu video ngắn
hơn audio, giữ khung cuối tới hết lời đọc.

Cách dùng:
  python export_tiktok.py <video.mp4> <voice.wav> <voice.srt> <out.mp4>
      [--hook "Câu mở đầu\\nxuống dòng"] [--hook-sec 2.5] [--no-ai-label]

Nhãn "Giọng đọc được tạo bằng AI" bật mặc định: điều khoản CIT Voice Studio
bắt buộc ghi khi đăng công khai. Chỉ tắt nếu đã ghi trong caption.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

W, H = 1080, 1920
FONT = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
# Toạ độ theo PlayResY=288 của libass. MarginV 70 ≈ 470px đáy: tránh vùng caption/nút của TikTok
# FontSize 10: dòng ~42 ký tự của CIT vừa 1 dòng, không bị tự ngắt thành 4 dòng đè lên tranh
# Nền tối quanh tranh: tranh giấy sáng nổi như tấm thẻ, chữ trắng đọc rõ (nền giấy nhạt bị loá, khó nhìn)
BG = "0x22201D"
SUB_STYLE = ("FontName=Noto Sans,Bold=1,FontSize=10,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=70")


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def build_filter(hook: bool, hook_sec: float, ai_label: bool) -> str:
    # Đường dẫn trong filter dùng tên tương đối (cwd = thư mục tạm) để khỏi escape ký tự đặc biệt
    # gamma<1 làm đậm nét chì mảnh, giấy gần trắng gần như giữ nguyên
    f = (f"[0:v]eq=gamma=0.75:contrast=1.15,"
         f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BG},setsar=1,"
         f"tpad=stop_mode=clone:stop=-1,"
         f"subtitles=subs.srt:force_style='{SUB_STYLE}'")
    if hook:
        f += (f",drawtext=fontfile={FONT}:textfile=hook.txt:fontsize=76:fontcolor=0x1E1E1E:"
              f"line_spacing=16:box=1:boxcolor=0xFFD54F:boxborderw=28:"
              f"x=(w-tw)/2:y=h*0.14:enable='lt(t,{hook_sec})'")
    if ai_label:
        f += (f",drawtext=fontfile={FONT}:text='Giọng đọc được tạo bằng AI':fontsize=30:"
              f"fontcolor=0xBBBBBB:x=(w-tw)/2:y=h*0.06")
    return f + "[v]"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("audio", type=Path)
    p.add_argument("srt", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--hook", default="", help="chữ hiện ở đầu video, \\n để xuống dòng")
    p.add_argument("--hook-sec", type=float, default=2.5)
    p.add_argument("--no-ai-label", action="store_true")
    args = p.parse_args()

    total = max(duration(args.video), duration(args.audio))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(args.srt, Path(tmp, "subs.srt"))
        Path(tmp, "hook.txt").write_text(args.hook.replace("\\n", "\n"), encoding="utf-8")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(args.video.resolve()), "-i", str(args.audio.resolve()),
            "-filter_complex", build_filter(bool(args.hook), args.hook_sec, not args.no_ai_label),
            "-map", "[v]", "-map", "1:a", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(args.output.resolve()),
        ], cwd=tmp, check=True)
    print(f"{args.output} ({total:.1f}s, {W}x{H})")


if __name__ == "__main__":
    main()
