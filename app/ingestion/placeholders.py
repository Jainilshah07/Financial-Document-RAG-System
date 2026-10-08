import re

# "<Company Name>", "<Address>", "[Company Name]" : unfilled template slots.
_ANGLE_OR_SQUARE = re.compile(r"^[<\[{][^<>\[\]{}]{1,60}[>\]}]$")
# Date templates: nn/dd/yyyy, mm/dd/yyyy, dd-mm-yy, yyyy.mm.dd ...
_DATE_TEMPLATE = re.compile(r"^(?:[dmny]{1,4}[/\-.]){1,2}[dmny]{1,4}$", re.IGNORECASE)
_FILLER = {"n/a", "na", "tbd", "xxx", "xxxx", "-", "--", "—", "off"}


# Tokens inside body text. Letters only (no digits) so "[23423423]" (an item number)
# survives while "[Street Address]" and "<Contact Number>" are removed.
_BODY_TOKEN = re.compile(r"[<\[]\s*[A-Za-z][A-Za-z ,./&'-]{0,50}[>\]]")
_BODY_DATE_TEMPLATE = re.compile(r"\b(?:nn|mm|dd)/(?:nn|mm|dd)/(?:yyyy|yy)\b", re.IGNORECASE)
# Captions of PDF form buttons leak into extracted text.
_FORM_BUTTONS = re.compile(r"\b(?:Reset|Save|Print) Form\b")


def strip_placeholders(text: str) -> str:
    """Remove unfilled-template tokens from extracted body text.

    Leaves the rest of the line intact (callers normalise whitespace afterwards).
    """
    for pattern in (_BODY_TOKEN, _BODY_DATE_TEMPLATE, _FORM_BUTTONS):
        text = pattern.sub(" ", text)
    return text


def is_placeholder(value: str) -> bool:
    """True if a form-field value is template filler, not real data.

    A placeholder must never be indexed as if it were a fact ("Vendor: <Company Name>").
    A value can contain several lines (an address block): it is a placeholder only if
    *every* non-empty line is one.
    """
    lines = [ln.strip() for ln in value.replace("\r", "\n").split("\n") if ln.strip()]
    if not lines:
        return True
    return all(_is_placeholder_line(ln) for ln in lines)


def _is_placeholder_line(line: str) -> bool:
    return (
        bool(_ANGLE_OR_SQUARE.match(line))
        or bool(_DATE_TEMPLATE.match(line))
        or line.lower() in _FILLER
    )
