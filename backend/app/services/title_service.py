MAX_TITLE_LENGTH = 60


def generate_title_from_message(content: str) -> str:
    text = " ".join(content.strip().split())
    if not text:
        return "New chat"
    if len(text) <= MAX_TITLE_LENGTH:
        return text
    truncated = text[:MAX_TITLE_LENGTH].rsplit(" ", 1)[0]
    return f"{truncated}…"
