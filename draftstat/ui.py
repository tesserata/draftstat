from __future__ import annotations

import html as _html

import gradio as gr

from draftstat import config
from draftstat.analysis import analyze
from draftstat.highlight import to_html

_CSS = """
footer { visibility: hidden; }
body { background: var(--body-background-fill, #0d1117) !important; }
.gradio-container { background: var(--body-background-fill, #0d1117) !important; }
.contain { background: transparent !important; }

/* app accent: drives slider fill + selected-tab underline (var --*-accent) */
.gradio-container {
    --slider-color: #7ed4ff !important;
    --border-color-accent: #7ed4ff !important;
    --color-accent: #7ed4ff !important;
    --loader-color: #7ed4ff !important;
    --border-color-accent-subdued: #7ed4ff !important;
}
input[type="range"] { accent-color: #7ed4ff; }

/* hide bridge textboxes (kept in DOM so JS can reach them) */
#ds-sel-wrap, #ds-text-wrap { display: none !important; }

/* tabs: accent in the app color */
.tab-nav button.selected,
[role="tab"].selected,
[role="tab"][aria-selected="true"] {
    color: #7ed4ff !important;
    border-bottom-color: #7ed4ff !important;
}
.tab-nav button.selected::after,
[role="tab"].selected::after,
[role="tab"][aria-selected="true"]::after {
    background: #7ed4ff !important;
}
.tab-nav button:hover,
[role="tab"]:hover { color: #a6e2ff !important; }

/* word list rows */
.ds-list { display: flex; flex-direction: column; gap: 0; }
.ds-row {
    display: flex; align-items: center; gap: 8px;
    padding: 4px 6px; border-radius: 4px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.ds-row:hover { background: rgba(255,255,255,0.05); }
.ds-word {
    flex: 1; text-align: left; background: none; border: none;
    cursor: pointer; font-size: 0.9em; color: inherit; padding: 0;
}
.ds-word:hover { text-decoration: underline; }
.ds-count { font-size: 0.8em; opacity: 0.5; min-width: 20px; text-align: right; }
.ds-x {
    background: none; border: none; cursor: pointer;
    font-size: 1em; opacity: 0.4; padding: 0 2px; color: inherit;
    line-height: 1;
}
.ds-x:hover { opacity: 1; }

#ds-normalize input[type="checkbox"] {
    appearance: none; -webkit-appearance: none;
    position: relative; cursor: pointer;
    width: 40px; height: 22px; border-radius: 22px;
    background: var(--neutral-600, #4b5563);
    border: none; transition: background 0.2s; flex: none;
}
#ds-normalize input[type="checkbox"]::before {
    content: ""; position: absolute; top: 2px; left: 2px;
    width: 18px; height: 18px; border-radius: 50%;
    background: #fff; transition: transform 0.2s;
}
#ds-normalize input[type="checkbox"]:checked {
    background: #7ed4ff;
}
#ds-normalize input[type="checkbox"]:checked::before {
    transform: translateX(18px);
}
"""

_JS = """
() => {
    function fire(el, value) {
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }
    // push the editable div's plain text into the hidden source textbox -> re-analyze
    window.dsSyncText = (div) => {
        const t = document.querySelector('#ds-text textarea');
        if (t) fire(t, div.innerText);
    };
    // caret position as a character offset within the div
    function caretOffset(div) {
        const sel = window.getSelection();
        if (!sel.rangeCount) return null;
        const r = sel.getRangeAt(0).cloneRange();
        const pre = r.cloneRange();
        pre.selectNodeContents(div);
        pre.setEnd(r.endContainer, r.endOffset);
        return pre.toString().length;
    }
    function setCaret(div, offset) {
        const walk = document.createTreeWalker(div, NodeFilter.SHOW_TEXT);
        let n = 0, node;
        while ((node = walk.nextNode())) {
            const len = node.textContent.length;
            if (n + len >= offset) {
                const r = document.createRange();
                r.setStart(node, offset - n);
                r.collapse(true);
                const s = window.getSelection();
                s.removeAllRanges();
                s.addRange(r);
                return;
            }
            n += len;
        }
    }
    // strip highlight <mark>s before an edit lands, preserving the caret
    window.dsUnwrap = (div) => {
        const marks = div.querySelectorAll('mark.ds-hit');
        if (!marks.length) return;
        const off = caretOffset(div);
        marks.forEach(m => m.replaceWith(document.createTextNode(m.textContent)));
        div.normalize();
        if (off != null) setCaret(div, off);
        const sel = document.querySelector('#ds-sel textarea');
        if (sel) sel.value = '';  // clear selection state silently
    };
    // word clicked in a list -> trigger the lemma-aware highlight.
    // a nonce guarantees the value always changes, so re-clicking the same word re-fires.
    window.dsHighlight = (word) => {
        const e = document.querySelector('#ds-sel textarea');
        if (e) fire(e, word + '\\u0000' + Date.now());
    };
    window.dsIgnore = (word, inputId) => {
        const e = document.querySelector('#' + inputId + ' textarea');
        if (!e) return;
        const parts = e.value ? e.value.split(',').map(s => s.trim()).filter(Boolean) : [];
        if (!parts.includes(word)) parts.push(word);
        fire(e, parts.join(', '));
    };
}
"""


def _parse_ignore(raw: str | None) -> frozenset[str]:
    if not raw:
        return frozenset()
    return frozenset(w.strip().lower() for w in raw.replace("\n", ",").split(",") if w.strip())


def _js_str(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _js_highlight(word: str) -> str:
    w = _js_str(word)
    return (
        "(function(){"
        "var e=document.querySelector('#ds-sel textarea');"
        "if(!e)return;"
        f"e.value='{w}'+String.fromCharCode(0)+Date.now();"
        "e.dispatchEvent(new Event('input',{bubbles:true}));"
        "})()"
    )


def _js_ignore(word: str, ignore_id: str) -> str:
    w = _js_str(word)
    return (
        "(function(){"
        f"var e=document.querySelector('#{ignore_id} textarea');"
        "if(!e)return;"
        "var c=e.value?e.value.split(',').map(function(x){return x.trim();}).filter(Boolean):[];"
        f"if(c.indexOf('{w}')<0)c.push('{w}');"
        "e.value=c.join(', ');"
        "e.dispatchEvent(new Event('input',{bubbles:true}));"
        "})()"
    )


def _word_list_html(rows: list, ignore_id: str) -> str:
    if not rows:
        return '<p style="opacity:0.5;padding:8px 0;font-style:italic;font-size:0.9em">Nothing flagged.</p>'
    parts = []
    for word, count in rows:
        w = _html.escape(word)
        hl = _html.escape(_js_highlight(word), quote=True)
        ig = _html.escape(_js_ignore(word, ignore_id), quote=True)
        parts.append(
            f'<div class="ds-row">'
            f'<button class="ds-word" onclick="{hl}">{w}</button>'
            f'<span class="ds-count">{count}</span>'
            f'<button class="ds-x" onclick="{ig}" title="ignore">×</button>'
            f'</div>'
        )
    return '<div class="ds-list">' + "".join(parts) + "</div>"


def _lists(result):
    flagged = _word_list_html(
        [[f.word, f.count] for f in result.flagged[:10]], "ds-ignore-words"
    )
    adverbs = _word_list_html(
        [[w, c] for w, c in result.adverbs[:10]], "ds-ignore-adverbs"
    )
    return flagged, adverbs


def _compute(text, ceiling, ignore_words_raw, ignore_adverbs_raw, normalize):
    return analyze(
        text or "",
        ceiling=float(ceiling),
        ignore_words=_parse_ignore(ignore_words_raw),
        ignore_adverbs=_parse_ignore(ignore_adverbs_raw),
        normalize=bool(normalize),
    )


def _analyze(text, ceiling, ignore_words_raw, ignore_adverbs_raw, normalize):
    result = _compute(text, ceiling, ignore_words_raw, ignore_adverbs_raw, normalize)
    flagged, adverbs = _lists(result)
    return flagged, adverbs, result.segments


def _load(text, ceiling, ignore_words_raw, ignore_adverbs_raw, normalize):
    result = _compute(text, ceiling, ignore_words_raw, ignore_adverbs_raw, normalize)
    flagged, adverbs = _lists(result)
    return to_html(result.segments), flagged, adverbs, result.segments


def _show_highlight(word: str | None, segments):
    clean = word.split("\x00")[0] if word else None
    return to_html(segments, selected_word=clean or None)


THEME = gr.themes.Ocean()


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="DraftStat") as demo:
        gr.Markdown("# DraftStat\nAnalyze word frequency against actual rarity.")

        segments_state = gr.State([])

        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("Your writing goes below")
                manuscript = gr.HTML()

            with gr.Column(scale=1):
                normalize = gr.Checkbox(
                    value=True,
                    label="Normalize forms",
                    info="Group different word forms into one occurrence",
                    elem_id="ds-normalize",
                )
                with gr.Tabs():
                    with gr.TabItem("Word frequency"):
                        ceiling = gr.Slider(
                            2.0, 7.0,
                            value=config.DEFAULT_CEILING,
                            step=0.1,
                            label="Rarity (Rare → Common)",
                        )
                        ignore_words = gr.Textbox(
                            label="Ignore words",
                            lines=1,
                            placeholder="word1, word2, …",
                            elem_id="ds-ignore-words",
                        )
                        flagged_html = gr.HTML()

                    with gr.TabItem("Adverbs"):
                        ignore_adverbs = gr.Textbox(
                            label="Ignore adverbs",
                            lines=1,
                            placeholder="word1, word2, …",
                            elem_id="ds-ignore-adverbs",
                        )
                        adverb_html = gr.HTML()

        with gr.Row(elem_id="ds-text-wrap"):
            ds_text = gr.Textbox(elem_id="ds-text", value=config.SAMPLE_TEXT)
        with gr.Row(elem_id="ds-sel-wrap"):
            sel_word = gr.Textbox(elem_id="ds-sel", label="")

        analysis_inputs = [ds_text, ceiling, ignore_words, ignore_adverbs, normalize]
        list_outputs = [flagged_html, adverb_html, segments_state]

        for component in analysis_inputs:
            component.change(_analyze, analysis_inputs, list_outputs)

        sel_word.change(_show_highlight, [sel_word, segments_state], [manuscript])

        demo.load(_load, analysis_inputs, [manuscript, *list_outputs])

    return demo


def attach(app, path: str = "/"):
    demo = build_demo()
    demo.queue()
    return gr.mount_gradio_app(
        app, demo, path=path, theme=THEME, css=_CSS, js=_JS
    )
