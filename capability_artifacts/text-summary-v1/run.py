"""Csount words and save the printed summary."""
from pathlib import Path


def main():
    text = Path("input.txt").read_text(encoding="utf-8")
    summary = f"Lines: {len(text.splitlines())}\nWords: {len(text.split())}\n"
    Path("summary.txt").write_text(summary, encoding="utf-8")
    print(summary, end="")


if __name__ == "__main__":
    main()
