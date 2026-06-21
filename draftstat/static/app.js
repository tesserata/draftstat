() => {
    function fire(el, value) {
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }
    window.dsSyncText = (div) => {
        const t = document.querySelector('#ds-text textarea');
        if (t) fire(t, div.innerText);
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
    window.dsIgnore = (word, inputId) => {
        const e = document.querySelector('#' + inputId + ' textarea');
        if (!e) return;
        const parts = e.value ? e.value.split(',').map(s => s.trim()).filter(Boolean) : [];
        if (!parts.includes(word)) parts.push(word);
        fire(e, parts.join(', '));
    };
}
