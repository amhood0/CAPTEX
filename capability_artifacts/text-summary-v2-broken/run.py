"""Deliberate regression: the summary incorrectly adds one to the word count."""
from pathlib import Path


def main():
    text = Path("input.txt").read_text(encoding="utf-8")
    # Intentional demo defect: this input has 12 words, not 13.
    summary = f"Lines: {len(text.splitlines())}\nWords: {len(text.split()) + 1}\n"
    Path("summary.txt").write_text(summary, encoding="utf-8")
    print(summary, end="")


if __name__ == "__main__":
    main()
