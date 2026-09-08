"""
Semantic Personal File Navigator — Aurora UI
Start with:  python run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from semantic_navigator.agent import search_library
from semantic_navigator.store import FileLibrary
from semantic_navigator.watcher import FolderWatcher

st.set_page_config(
    page_title="File Navigator",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Aurora palette ────────────────────────────────────────────────────────────
# bg: #030d1a  surface: #081423  border: #112236
# teal:  #00d4aa   green: #34d399   purple: #a78bfa   pink: #f0abfc
# text:  #dde6f0   muted: #4a6080   subtle: #1d3450

st.markdown("""
<style>
:root{
  --bg:       #030d1a;
  --surface:  #081423;
  --border:   #112236;
  --teal:     #00d4aa;
  --green:    #34d399;
  --purple:   #a78bfa;
  --pink:     #f0abfc;
  --text:     #dde6f0;
  --muted:    #4a6080;
  --subtle:   #1d3450;
}

html,body,[class*="css"]{
  font-family:'Segoe UI',system-ui,sans-serif;
  background:var(--bg)!important;
  color:var(--text);
}
.block-container{
  max-width:680px!important;
  padding:2rem 1.2rem 7rem!important;
}
[data-testid="InputInstructions"],
#MainMenu,footer,header{display:none!important}

/* ── Search input ─────────────────────── */
div[data-testid="stTextInput"] input{
  font-size:.95rem!important;
  height:50px!important;
  border-radius:14px!important;
  border:1.5px solid #2a3f58!important;
  background:#0e1f33!important;
  color:var(--text)!important;
  padding:0 1rem!important;
  box-shadow:none!important;
  transition:border-color .2s,box-shadow .2s;
}
div[data-testid="stTextInput"] input:focus{
  border-color:var(--teal)!important;
  box-shadow:0 0 0 3px #00d4aa18!important;
}
div[data-testid="stTextInput"] input::placeholder{
  color:var(--muted)!important;
  font-size:.85rem!important;
}

/* ── Buttons ──────────────────────────── */
div[data-testid="stButton"]>button{
  border-radius:10px!important;
  font-size:.85rem!important;
  height:40px!important;
  border:1px solid var(--border)!important;
  background:var(--surface)!important;
  color:#b0c4d8!important;
  transition:all .15s!important;
}
div[data-testid="stButton"]>button:hover{
  border-color:var(--teal)!important;
  color:var(--teal)!important;
  background:var(--subtle)!important;
}
/* Streamlit captions and small text */
[data-testid="stCaptionContainer"] p,
small, .stCaption, [data-testid="caption"]{
  color:#8aaac8!important;
}
/* Primary / Search button */
div[data-testid="stButton"]>button[kind="primary"],
div[data-testid="stButton"]>button[data-testid="baseButton-primary"]{
  background:linear-gradient(135deg,#00d4aa,#a78bfa)!important;
  border:none!important;
  color:#030d1a!important;
  font-weight:700!important;
  letter-spacing:.01em!important;
  box-shadow:0 0 18px #00d4aa33!important;
  transition:opacity .15s,box-shadow .15s!important;
}
div[data-testid="stButton"]>button[kind="primary"]:hover,
div[data-testid="stButton"]>button[data-testid="baseButton-primary"]:hover{
  opacity:.88!important;
  box-shadow:0 0 28px #00d4aa55!important;
}

/* ── Result cards ─────────────────────── */
.rcard{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:14px;
  padding:14px 18px;
  margin-bottom:10px;
  transition:border-color .15s,box-shadow .15s;
}
.rcard:hover{
  border-color:var(--subtle);
  box-shadow:0 0 18px #00d4aa0d;
}
.rcard-title{font-weight:700;font-size:.94rem;color:var(--text)}
.rcard-path{font-size:.72rem;color:var(--muted);margin-top:1px;word-break:break-all}
.rcard-why{font-size:.8rem;color:#6b86a8;margin-top:5px}
.excerpt{
  background:#030d1a;
  border-left:3px solid var(--teal);
  padding:7px 11px;
  margin-top:8px;
  font-size:.8rem;
  color:#7a96b8;
  border-radius:0 8px 8px 0;
  line-height:1.6;
}
.score-pill{
  display:inline-block;
  border-radius:20px;
  padding:2px 10px;
  font-size:.7rem;
  font-weight:700;
  white-space:nowrap;
}

/* Status chip */
.status-chip{
  display:inline-flex;align-items:center;gap:7px;
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:20px;
  padding:4px 13px;
  font-size:.73rem;
  color:#b0c4d8;
  margin-bottom:1.2rem;
}
.dot-teal{width:7px;height:7px;border-radius:50%;background:var(--teal);flex-shrink:0}
.dot-amber{width:7px;height:7px;border-radius:50%;background:#fbbf24;flex-shrink:0;
  animation:blink 1.6s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}

/* ── Folder expander ─────────────────── */
[data-testid="stExpander"]{
  background:var(--surface)!important;
  border:1px solid var(--border)!important;
  border-radius:12px!important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span{
  font-size:.88rem!important;
  color:#b0c4d8!important;
  font-weight:600!important;
}
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:hover p{
  color:var(--teal)!important;
}

/* ── File list ────────────────────────── */
.frow{
  display:flex;justify-content:space-between;align-items:center;
  background:var(--surface);border:1px solid var(--border);
  border-radius:9px;padding:6px 12px;margin-bottom:5px;
  font-size:.82rem;color:#c8d8e8;gap:10px;flex-wrap:wrap;
}
.frow .meta{color:#7a96b8;font-size:.72rem}

/* ── Empty state ─────────────────────── */
.empty-state{text-align:center;padding:2.5rem 0 1.5rem;color:var(--muted)}
.empty-state .ico{font-size:2.2rem;margin-bottom:.4rem}
.empty-state h3{color:#7a96b8;margin:.2rem 0;font-size:1rem;font-weight:600}

/* ── Aurora glow accent on title ──────── */
.aurora-title{
  font-size:1.5rem;font-weight:800;letter-spacing:-.03em;
  background:linear-gradient(135deg,var(--teal),var(--purple),var(--pink));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}

/* Sidebar */
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border)!important}
</style>
""", unsafe_allow_html=True)

# ── Singletons ────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_lib() -> FileLibrary:
    return FileLibrary("local")

@st.cache_resource(show_spinner=False)
def _get_watcher() -> FolderWatcher:
    lib = _get_lib()
    w = FolderWatcher(lib)
    for folder in w.folders:
        w._q.put(("SCAN", folder))
    return w

lib     = _get_lib()
watcher = _get_watcher()
snap    = watcher.status.snapshot()

# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:.8rem 0 .5rem">
  <div style="font-size:1.8rem;margin-bottom:.2rem">🔍</div>
  <div class="aurora-title">File Navigator</div>
</div>
""", unsafe_allow_html=True)

# ── Status chip ───────────────────────────────────────────────────────────────
n_files = len(lib.files)
if snap["scanning"]:
    fname = snap["current_file"]
    short = fname[:38] + "…" if len(fname) > 38 else fname
    chip = f'<span class="dot-amber"></span>Indexing&nbsp;{short}'
elif n_files:
    f_count = len(watcher.folders)
    chip = f'<span class="dot-teal"></span>{n_files} file(s) indexed' + (f' · {f_count} folder(s)' if f_count else '')
else:
    chip = '<span style="color:#a78bfa">⊕</span>&nbsp;Add a folder below to start'

st.markdown(f'<div style="text-align:center"><span class="status-chip">{chip}</span></div>',
            unsafe_allow_html=True)

# ── Search box ────────────────────────────────────────────────────────────────
query = st.text_input(
    "q",
    placeholder="e.g.  offer letter  ·  Q3 report  ·  notes about API design",
    label_visibility="collapsed",
    key="main_q",
)
search_btn = st.button("Search files", type="primary", use_container_width=True)

st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

# ── Folder management — always inline, no JS tricks ───────────────────────────
with st.expander("📁  Manage watched folders", expanded=(n_files == 0)):
    # Quick-add row
    quick = {
        "Desktop":   Path.home() / "Desktop",
        "Documents": Path.home() / "Documents",
        "Downloads": Path.home() / "Downloads",
        "OneDrive":  Path.home() / "OneDrive",
        "OneDrive – AMDOCS": Path.home() / "OneDrive - AMDOCS",
    }
    watching_strs = {str(f) for f in watcher.folders}
    available = [(lbl, p) for lbl, p in quick.items() if p.exists() and str(p) not in watching_strs]
    if available:
        cols = st.columns(len(available))
        for col, (lbl, path) in zip(cols, available):
            with col:
                if st.button(f"+ {lbl}", key=f"qa_{lbl}", use_container_width=True):
                    watcher.add_folder(path)
                    st.rerun()

    # Manual path entry
    c1, c2 = st.columns([5, 1])
    with c1:
        fi = st.text_input("Custom path", placeholder=r"C:\Users\you\Documents",
                           label_visibility="collapsed", key="fi")
    with c2:
        if st.button("Add", key="add_custom", use_container_width=True) and fi.strip():
            err = watcher.add_folder(Path(fi.strip()))
            if err:
                st.error(err)
            else:
                st.success("Added!")
                st.rerun()

    # Current watched folders
    if watcher.folders:
        st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
        for f in watcher.folders:
            c_name, c_rm = st.columns([6, 1])
            with c_name:
                st.markdown(f'<div class="frow">📁 <span style="flex:1">{f}</span></div>',
                            unsafe_allow_html=True)
            with c_rm:
                if st.button("✕", key=f"rm_{f}", help="Stop watching"):
                    watcher.remove_folder(f)
                    st.rerun()
    else:
        st.caption("No folders watched yet.")

# ── Results ───────────────────────────────────────────────────────────────────
st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

if search_btn and query.strip():
    if not lib.is_ready:
        st.info("Still indexing — please wait a moment, then try again.")
    else:
        with st.spinner(""):
            result = search_library(lib, query.strip())

        if result.blocked:
            st.error(result.block_reason)
        elif not result.hits:
            st.markdown("""
<div class="empty-state">
  <div class="ico">🗂</div>
  <h3>No matching files found</h3>
  <p style="font-size:.82rem">Try different keywords, or make sure the relevant folders are being watched.</p>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(
                f'<p style="color:var(--muted);font-size:.78rem;margin-bottom:.7rem">'
                f'{len(result.hits)} file(s) matched</p>',
                unsafe_allow_html=True,
            )
            for hit in result.hits:
                if hit.relevance >= 70:
                    pill_bg, pill_col = "#00d4aa18", "#00d4aa"
                elif hit.relevance >= 45:
                    pill_bg, pill_col = "#a78bfa18", "#a78bfa"
                else:
                    pill_bg, pill_col = "#f0abfc18", "#f0abfc"

                excerpts_html = "".join(
                    f'<div class="excerpt">…{ex.strip()[:300]}…</div>'
                    for ex in hit.excerpts[:3]
                )
                rec = next((r for r in lib.files.values() if r.filename == hit.filename), None)
                name_html = (
                    f'<a href="file:///{rec.source_path.replace(chr(92),"/")}" '
                    f'style="color:#00d4aa;text-decoration:none" target="_blank">{hit.filename}</a>'
                    if rec and rec.source_path else
                    f'<span class="rcard-title">{hit.filename}</span>'
                )
                path_html = (
                    f'<div class="rcard-path">{rec.source_path}</div>'
                    if rec and rec.source_path else ""
                )

                st.markdown(f"""
<div class="rcard">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap">
    <div style="flex:1;min-width:0">
      <div class="rcard-title">{name_html}</div>
      {path_html}
      <div class="rcard-why">{hit.why}</div>
    </div>
    <span class="score-pill" style="background:{pill_bg};color:{pill_col}">{hit.relevance}%</span>
  </div>
  {excerpts_html}
</div>
""", unsafe_allow_html=True)

            if result.used_llm:
                st.caption("Answer sourced from document excerpts only.")

elif n_files == 0 and not watcher.folders:
    st.markdown("""
<div class="empty-state">
  <div class="ico">📂</div>
  <h3>No folders watched yet</h3>
  <p style="font-size:.82rem">Use the panel above to add Desktop, Documents,<br>
  or any folder on this machine.</p>
  <p style="margin-top:1rem;font-size:.75rem;color:#1d3450">
  Everything stays on your laptop — nothing is uploaded.</p>
</div>""", unsafe_allow_html=True)

# ── Library list (collapsed by default) ──────────────────────────────────────
if lib.files:
    with st.expander(f"🗃  Indexed files ({n_files})", expanded=False):
        filt = st.text_input("Filter", placeholder="type to filter…",
                             label_visibility="collapsed", key="lib_filt")
        files = sorted(lib.files.values(), key=lambda r: r.added_at, reverse=True)
        if filt:
            files = [f for f in files if filt.lower() in f.filename.lower()]
        for rec in files:
            st.markdown(
                f'<div class="frow">'
                f'<span>{rec.filename}</span>'
                f'<span class="meta">{rec.ext.upper()} · {rec.size_bytes//1024} KB · {rec.added_at}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if lib.files and st.button("Clear index", use_container_width=True):
            lib.clear()
            st.cache_resource.clear()
            st.rerun()
