"""Render the showcase and refresh every committed media file. usage: python video/publish.py [fps]

Writes media/say-hello.mp4, the README GIF and the opening still (the finished grid, which is also
the video's first frame).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"
FPS = sys.argv[1] if len(sys.argv) > 1 else "60"
GIF, GIF_WIDTH, GIF_FPS = MEDIA / "say-hello.gif", 560, 12


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def main():
    MEDIA.mkdir(exist_ok=True)
    mp4 = MEDIA / "say-hello.mp4"
    subprocess.run([sys.executable, "-X", "utf8", "-u", str(ROOT / "video" / "render.py"), "hello", str(mp4), FPS],
                   check=True, cwd=ROOT)
    mp4.with_suffix(".wav").unlink()
    filters = (f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,"
               "split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3")
    ffmpeg("-ss", "1.3", "-i", str(mp4), "-vf", filters, "-loop", "0", str(GIF))
    ffmpeg("-i", str(mp4), "-frames:v", "1", "-q:v", "3", str(MEDIA / "grid.jpg"))
    for path in (mp4, GIF, MEDIA / "grid.jpg"):
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
