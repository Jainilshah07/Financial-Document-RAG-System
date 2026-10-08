import re
import unicodedata

# Control characters except \n and \t (kept, then handled below).
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES = re.compile(r"[ \t   ]+")  # includes non-breaking spaces
_BLANK_LINES = re.compile(r"\n{3,}")


# Lines that carry no information on their own: a lone currency symbol ("$") or a zero
# amount with decimals ("0.00") - typically the empty rows/cells of a form.
_NOISE_LINE = re.compile(r"^(?:[$₹€£]|[$₹€£]?\s*0+\.0+)$")
# A line that is only a list marker: "1." "2)" "–" "•"
_MARKER_ONLY = re.compile(r"^(?:\d{1,2}[.)]|[–—\-•*])$")
_MAX_LABEL_LEN = 60


def _join_orphan_lines(lines: list[str]) -> list[str]:
    """Re-attach a label or list marker to the value/text on the next line.

    PDF extraction often yields "Description:" and its value on separate lines, or
    "1." and "Standard Conditions:". Splitting them apart would sever the relationship
    at chunking time, so they are joined: "Description: D2D Electrical ...".
    """
    joined: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        following = lines[i + 1] if i + 1 < len(lines) else ""
        is_marker = bool(_MARKER_ONLY.match(line))
        is_label = line.endswith(":") and len(line) <= _MAX_LABEL_LEN
        # Do not chain labels ("E-mail:" / "Phone:" / "Fax:") into one blob.
        if line and following and (is_marker or (is_label and not following.endswith(":"))):
            joined.append(f"{line} {following}")
            i += 2
        else:
            joined.append(line)
            i += 1
    return joined


def normalise_text(text: str) -> str:
    """Clean extracted text without altering its meaning.

    Deliberately conservative for financial text: digits, commas, decimal points,
    currency symbols and case are never touched ("5,00,000" must stay "5,00,000").
    Only whitespace/encoding noise is removed:
      * Unicode NFKC folds look-alike forms (ligatures "ﬁ" -> "fi", full-width digits).
      * control characters and non-breaking spaces are replaced by plain spaces.
      * runs of spaces collapse to one; trailing spaces are dropped.
      * 3+ consecutive newlines collapse to one blank line (paragraph break).
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub(" ", text)
    text = _SPACES.sub(" ", text)
    stripped = [line.strip() for line in text.split("\n")]
    lines = _join_orphan_lines([line for line in stripped if not _NOISE_LINE.match(line)])
    text = "\n".join(lines)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()
