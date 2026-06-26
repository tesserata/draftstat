from __future__ import annotations

import html

from draftstat import config

_NOUN_POS = {"NOUN", "PROPN"}


def token_key(token, normalize: bool) -> str:
    if normalize or token.pos_ in _NOUN_POS:
        return token.lemma_.lower()
    return token.text.lower()


def to_segments(doc, normalize: bool = True) -> list[tuple[str, str | None]]:
    segments: list[tuple[str, str | None]] = []
    for token in doc:
        key = token_key(token, normalize) if token.is_alpha else None
        segments.append((token.text_with_ws, key))
    return segments


def to_html(
    segments: list[tuple[str, str | None]],
    selected_word: str | None = None,
) -> str:
    sel = selected_word.lower().strip() if selected_word else None
    parts: list[str] = []
    hits = 0
    for text_ws, lemma in segments:
        escaped = html.escape(text_ws)
        if sel and lemma == sel:
            parts.append(
                f'<mark class="ds-hit" style="background:{config.SELECTED_COLOR};'
                f'border-radius:3px;padding:1px 2px;font-weight:600;color:#0d1f2d">{escaped}</mark>'
            )
            hits += 1
        else:
            parts.append(escaped)

    body = "".join(parts)
    nav = _nav_bar(sel, hits) if sel else ""
    autoscroll = (
        '<img src="x" alt="" style="display:none" onerror="dsNav(1)">'
        if sel and hits
        else ""
    )
    return (
        f"<div>{nav}"
        f'<div id="ds-manuscript" contenteditable="plaintext-only" spellcheck="false" '
        f'oninput="dsSyncText(this)" onbeforeinput="dsUnwrap(this)" '
        f'style="font-family:Georgia,serif;font-size:1.05em;'
        f"line-height:1.85;white-space:pre-wrap;padding:12px;border-radius:8px;"
        f"min-height:200px;max-height:58vh;overflow-y:auto;outline:none;"
        f"background:var(--input-background-fill);"
        f"border:1px solid var(--border-color-primary);"
        f'color:var(--body-text-color)">{autoscroll}{body}</div>'
        f"</div>"
    )


def _nav_bar(word: str, hits: int) -> str:
    w = html.escape(word)
    return (
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:0.85em">'
        f'<span style="opacity:0.7">“{w}” — {hits} '
        f'occurrence{"s" if hits != 1 else ""}</span>'
        '<button onclick="dsNav(-1)" '
        'style="cursor:pointer;background:var(--button-secondary-background-fill);'
        "border:1px solid var(--border-color-accent);color:var(--body-text-color);"
        'border-radius:4px;padding:1px 8px">‹ prev</button>'
        '<span id="ds-hit-counter" style="opacity:0.6;min-width:48px;text-align:center">—</span>'
        '<button onclick="dsNav(1)" '
        'style="cursor:pointer;background:var(--button-secondary-background-fill);'
        "border:1px solid var(--border-color-accent);color:var(--body-text-color);"
        'border-radius:4px;padding:1px 8px">next ›</button>'
        "</div>"
    )
