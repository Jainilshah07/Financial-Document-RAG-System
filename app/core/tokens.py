def estimate_tokens(text: str) -> int:
    """Rough token count (~4 characters per token for English).

    Good enough for sizing chunks and for pacing API rate limits; avoids depending on a
    model-specific tokenizer. Numbers and punctuation tokenise denser, so treat it as an
    approximation that errs slightly low for financial text.
    """
    return max(1, round(len(text) / 4))
