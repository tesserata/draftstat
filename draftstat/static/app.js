// Injected into <head> as a self-running script (see ui.attach). Defines the
// window.ds* helpers that the inline HTML handlers call.
(() => {
    function fire(el, value) {
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }
    let syncTimer = null;
    window.dsSyncText = (div) => {
        const text = div.innerText;
        clearTimeout(syncTimer);
        syncTimer = setTimeout(() => {
            const t = document.querySelector('#ds-text textarea');
            if (t) fire(t, text);
        }, 400);
    };
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
    window.dsHighlight = (word) => {
        const e = document.querySelector('#ds-sel textarea');
        if (e) fire(e, word + String.fromCharCode(0) + Date.now());
    };
    window.dsNav = (d) => {
        const c = document.getElementById('ds-manuscript');
        if (!c) return;
        const hits = c.querySelectorAll('.ds-hit');
        if (!hits.length) return;
        let i = parseInt(c.dataset.hit || '-1', 10) + d;
        if (i >= hits.length) i = 0;
        if (i < 0) i = hits.length - 1;
        c.dataset.hit = i;
        hits.forEach(h => { h.style.outline = ''; });
        const t = hits[i];
        t.style.outline = '2px solid #f0c040';
        t.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const lbl = document.getElementById('ds-hit-counter');
        if (lbl) lbl.textContent = (i + 1) + ' / ' + hits.length;
    };
    window.dsIgnore = (word, inputId) => {
        const e = document.querySelector('#' + inputId + ' textarea');
        if (!e) return;
        const parts = e.value ? e.value.split(',').map(s => s.trim()).filter(Boolean) : [];
        if (!parts.includes(word)) parts.push(word);
        fire(e, parts.join(', '));
    };
})();
