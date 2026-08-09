CONTROL_CHARS_TO_STRIP = {"\x00", "\x0b", "\x0c"}


def normalize_user_content(text: str) -> str:
    """Strip null/control bytes from user-submitted text before persisting it.

    This is deliberately NOT an HTML/tag stripper: users legitimately paste HTML, XML,
    and code snippets (e.g. asking ASE AI to explain a <script> tag), and that content
    must round-trip intact. XSS protection lives at render time in the frontend
    (react-markdown + rehype-sanitize renders text as markdown, never as raw HTML), not
    by mutilating stored input.
    """
    return "".join(ch for ch in text if ch not in CONTROL_CHARS_TO_STRIP)
