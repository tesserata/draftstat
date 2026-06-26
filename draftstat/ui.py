from __future__ import annotations

import html as _html
from pathlib import Path

import gradio as gr

from draftstat import config
from draftstat.analysis import analyze
from draftstat.highlight import to_html

_STATIC = Path(__file__).parent / "static"
_CSS = (_STATIC / "styles.css").read_text(encoding="utf-8")
_JS = (_STATIC / "app.js").read_text(encoding="utf-8")


def _parse_ignore(raw: str | None) -> frozenset[str]:
    if not raw:
        return frozenset()
    return frozenset(
        w.strip().lower() for w in raw.replace("\n", ",").split(",") if w.strip()
    )


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
            f"</div>"
        )
    return '<div class="ds-list">' + "".join(parts) + "</div>"


def _lists(result):
    flagged = _word_list_html(
        [[f.word, f.count] for f in result.flagged[:10]], "ds-ignore-words"
    )
    adverbs = _word_list_html(
        [[w, c] for w, c in result.adverbs[:10]], "ds-ignore-adverbs"
    )
    filters = _word_list_html(
        [[w, c] for w, c in result.filters[:10]], "ds-ignore-filters"
    )
    return flagged, adverbs, filters


def _compute(
    text, ceiling, ignore_words_raw, ignore_adverbs_raw, ignore_filters_raw,
    normalize, filter_adverbs,
):
    return analyze(
        text or "",
        ceiling=float(ceiling),
        ignore_words=_parse_ignore(ignore_words_raw),
        ignore_adverbs=_parse_ignore(ignore_adverbs_raw),
        ignore_filters=_parse_ignore(ignore_filters_raw),
        normalize=bool(normalize),
        filter_adverbs=bool(filter_adverbs),
    )


def _analyze(
    text, ceiling, ignore_words_raw, ignore_adverbs_raw, ignore_filters_raw,
    normalize, filter_adverbs,
):
    result = _compute(
        text, ceiling, ignore_words_raw, ignore_adverbs_raw, ignore_filters_raw,
        normalize, filter_adverbs,
    )
    flagged, adverbs, filters = _lists(result)
    return flagged, adverbs, filters, result.segments


def _load(
    text, ceiling, ignore_words_raw, ignore_adverbs_raw, ignore_filters_raw,
    normalize, filter_adverbs,
):
    result = _compute(
        text, ceiling, ignore_words_raw, ignore_adverbs_raw, ignore_filters_raw,
        normalize, filter_adverbs,
    )
    flagged, adverbs, filters = _lists(result)
    return to_html(result.segments), flagged, adverbs, filters, result.segments


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
                with gr.Tabs():
                    with gr.TabItem("Word frequency"):
                        normalize = gr.Checkbox(
                            value=True,
                            label="Normalize forms",
                            info="Group different word forms into one occurrence",
                            elem_id="ds-normalize",
                        )
                        ceiling = gr.Slider(
                            2.0,
                            7.0,
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
                        filter_adverbs = gr.Checkbox(
                            value=True,
                            label="Filter adverbs",
                            info='Only count adverbs ending with "-ly"',
                            elem_id="ds-filter-adverbs",
                        )
                        ignore_adverbs = gr.Textbox(
                            label="Ignore adverbs",
                            lines=1,
                            placeholder="word1, word2, …",
                            elem_id="ds-ignore-adverbs",
                        )
                        adverb_html = gr.HTML()

                    with gr.TabItem("Filter words"):
                        ignore_filters = gr.Textbox(
                            label="Ignore filter words",
                            lines=1,
                            placeholder="word1, word2, …",
                            elem_id="ds-ignore-filters",
                        )
                        filter_html = gr.HTML()

        with gr.Row(elem_id="ds-text-wrap"):
            ds_text = gr.Textbox(elem_id="ds-text", value=config.SAMPLE_TEXT)
        with gr.Row(elem_id="ds-sel-wrap"):
            sel_word = gr.Textbox(elem_id="ds-sel", label="")

        analysis_inputs = [
            ds_text,
            ceiling,
            ignore_words,
            ignore_adverbs,
            ignore_filters,
            normalize,
            filter_adverbs,
        ]
        list_outputs = [flagged_html, adverb_html, filter_html, segments_state]

        for component in analysis_inputs:
            component.change(_analyze, analysis_inputs, list_outputs)

        sel_word.change(_show_highlight, [sel_word, segments_state], [manuscript])

        demo.load(_load, analysis_inputs, [manuscript, *list_outputs])

    return demo


def attach(app, path: str = "/"):
    demo = build_demo()
    demo.queue()
    return gr.mount_gradio_app(app, demo, path=path, theme=THEME, css=_CSS, js=_JS)
