#!/usr/bin/env python3
"""Build index.html for the morning-commute book library from books.json."""
import json, html, pathlib

ROOT = pathlib.Path(__file__).parent
data = json.loads((ROOT / "books.json").read_text())

def card(b):
    audio_block = (
        f'<audio controls preload="none" src="{b["audio"]}"></audio>'
        if b.get("audio") else
        '<p class="pending-note">🎙️ Podcast episode coming soon — the summary is ready below.</p>'
    )
    return f"""
    <article class="card" id="episode-{b['episode']}">
      <div class="ep">Episode {b['episode']}</div>
      <h2>{html.escape(b['title'])}</h2>
      <p class="author">{html.escape(b['author'])}</p>
      <p class="blurb">{html.escape(b['blurb'])}</p>
      {audio_block}
      <div class="actions">
        <a class="btn primary" href="{b['summary_pdf']}">📖 Read the 20-minute summary (PDF)</a>
        {f'<a class="btn" href="{b["audio"]}" download>⬇ Download episode (MP3)</a>' if b.get("audio") else ""}
        <button class="btn share-btn" type="button" data-episode="{b['episode']}" aria-label="Share episode {b['episode']}">🔗 Share</button>
      </div>
      <p class="date">Delivered {b['date']}</p>
    </article>"""

upcoming = "\n".join(
    f"<li><span class='ep-sm'>#{u['episode']}</span> <strong>{html.escape(u['title'])}</strong>{' — ' + html.escape(u['author']) if u.get('author') else ''}</li>"
    for u in data["upcoming"]
)

books_desc = list(reversed(data["books"]))
PAGE_SIZE = 7

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(data['series'])}</title>
<style>
  :root {{ --bg:#12100c; --card:#1d1a14; --ink:#f0e9da; --muted:#a89f8d; --accent:#e0a458; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         background:var(--bg); color:var(--ink); line-height:1.55; }}
  header {{ text-align:center; padding:3rem 1.5rem 1.5rem; }}
  header img {{ width:120px; height:120px; border-radius:24px; object-fit:cover;
               box-shadow:0 8px 32px rgba(224,164,88,.25); }}
  h1 {{ margin:1rem 0 .25rem; font-size:2rem; }}
  .sub {{ color:var(--muted); margin:0 0 2rem; }}
  main {{ max-width:860px; margin:0 auto; padding:0 1.25rem 3rem; }}
  .card {{ background:var(--card); border:1px solid #2e2a21; border-radius:16px;
          padding:1.5rem; margin-bottom:1.25rem; }}
  .ep {{ display:inline-block; font-size:.75rem; letter-spacing:.12em; text-transform:uppercase;
        color:var(--accent); border:1px solid var(--accent); border-radius:999px;
        padding:.15rem .75rem; margin-bottom:.5rem; }}
  .card h2 {{ margin:.25rem 0 .1rem; font-size:1.4rem; }}
  .author {{ color:var(--muted); margin:0 0 .75rem; font-style:italic; }}
  .blurb {{ margin:.5rem 0 1rem; }}
  audio {{ width:100%; margin:.25rem 0 1rem; }}
  .pending-note {{ background:#2a2415; border:1px dashed var(--accent); border-radius:10px;
                  padding:.75rem 1rem; color:var(--muted); }}
  .actions {{ display:flex; flex-wrap:wrap; gap:.6rem; margin-bottom:.5rem; }}
  .btn {{ text-decoration:none; padding:.55rem 1rem; border-radius:10px; font-size:.95rem;
         border:1px solid #3a352a; color:var(--ink); }}
  .btn.primary {{ background:var(--accent); color:#1a1408; border-color:var(--accent); font-weight:600; }}
  button.btn {{ background:transparent; cursor:pointer; font-family:inherit; }}
  .card.flash {{ animation:flash 2.4s ease-out; }}
  @keyframes flash {{ 0%,35% {{ box-shadow:0 0 0 3px var(--accent); border-color:var(--accent); }} 100% {{ box-shadow:none; }} }}
  #toast {{ position:fixed; left:50%; bottom:1.5rem; transform:translateX(-50%) translateY(1rem);
           background:var(--accent); color:#1a1408; font-weight:600; padding:.6rem 1.15rem;
           border-radius:999px; opacity:0; pointer-events:none;
           transition:opacity .25s ease, transform .25s ease; z-index:50; }}
  #toast.show {{ opacity:1; transform:translateX(-50%) translateY(0); }}
  .date {{ color:var(--muted); font-size:.85rem; margin:.25rem 0 0; }}
  .upcoming {{ background:var(--card); border:1px dashed #3a352a; border-radius:16px;
              padding:1.5rem; }}
  .upcoming h2 {{ margin-top:0; }}
  .upcoming ul {{ list-style:none; padding:0; margin:0; }}
  .upcoming li {{ padding:.4rem 0; border-bottom:1px solid #2e2a21; }}
  .upcoming li:last-child {{ border-bottom:none; }}
  .ep-sm {{ color:var(--accent); font-weight:600; margin-right:.4rem; }}
  .pager {{ display:flex; gap:.6rem; align-items:center; justify-content:center;
           margin:1.75rem 0 .4rem; flex-wrap:wrap; }}
  .pager button {{ cursor:pointer; padding:.55rem 1rem; border-radius:10px; font-size:.95rem;
                   border:1px solid #3a352a; color:var(--ink); font-family:inherit; }}
  .pager button.ghost {{ background:var(--card); }}
  .pager button:disabled {{ opacity:.35; cursor:default; }}
  .pager .page-num {{ background:transparent; min-width:2.5rem; }}
  .pager .page-num.active {{ background:var(--accent); color:#1a1408; border-color:var(--accent);
                             font-weight:600; }}
  .page-info {{ text-align:center; color:var(--muted); font-size:.85rem; margin:0 0 1.5rem; }}
  footer {{ text-align:center; color:var(--muted); font-size:.85rem; padding:2rem 1rem; }}
</style>
</head>
<body>
<header>
  <img src="assets/img/series-cover.webp" alt="Series cover art">
  <h1>{html.escape(data['series'])}</h1>
  <p class="sub">One book a day — a ~30-minute Maya &amp; Dev podcast episode plus a 20-minute read summary.</p>
</header>
<main>
<section id="episodes" aria-label="Episodes">
{"".join(card(b) for b in books_desc)}
<nav class="pager" id="pager" aria-label="Episode pages">
  <button id="prevBtn" class="ghost">← Prev</button>
  <span id="pageNums"></span>
  <button id="nextBtn" class="ghost">Next →</button>
</nav>
<p class="page-info" id="pageInfo"></p>
</section>
<section class="upcoming">
  <h2>📚 Coming up next</h2>
  <ul>{upcoming}</ul>
</section>
</main>
<footer>Built for the morning commute · new episodes land ~7 AM</footer>
<script>
(function(){{
  const PAGE_SIZE = {PAGE_SIZE};
  const section = document.getElementById('episodes');
  const cards = Array.from(section.querySelectorAll('.card'));
  const pager = document.getElementById('pager');
  const pageNums = document.getElementById('pageNums');
  const pageInfo = document.getElementById('pageInfo');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const total = Math.max(1, Math.ceil(cards.length / PAGE_SIZE));
  function pageFromHash(){{
    const m = location.hash.match(/^#page-(\\d+)$/);
    if (m) {{ const p = parseInt(m[1], 10); if (p >= 1 && p <= total) return p; }}
    return null;
  }}
  function deepEpisode(){{
    const m = location.hash.match(/^#episode-(\\d+)$/);
    if (m) return parseInt(m[1], 10);
    const q = new URLSearchParams(location.search).get('episode');
    const n = q !== null ? parseInt(q, 10) : NaN;
    return Number.isFinite(n) ? n : null;
  }}
  let page = 1;
  let flashCard = null;
  const targetEp = deepEpisode();
  if (targetEp !== null) {{
    const idx = cards.findIndex(c => c.id === 'episode-' + targetEp);
    if (idx >= 0) {{
      page = Math.floor(idx / PAGE_SIZE) + 1;
      flashCard = cards[idx];
    }} else {{
      const p = pageFromHash();
      if (p) page = p;
    }}
  }} else {{
    const p = pageFromHash();
    if (p) page = p;
  }}
  function render(){{
    cards.forEach((c, i) => {{
      c.style.display = (Math.floor(i / PAGE_SIZE) + 1 === page) ? '' : 'none';
    }});
    pageNums.innerHTML = '';
    for (let i = 1; i <= total; i++){{
      const b = document.createElement('button');
      b.className = 'page-num' + (i === page ? ' active' : '');
      b.textContent = i;
      b.setAttribute('aria-label', 'Page ' + i);
      b.onclick = () => go(i);
      pageNums.appendChild(b);
    }}
    prevBtn.disabled = page === 1;
    nextBtn.disabled = page === total;
    pageInfo.textContent = 'Page ' + page + ' of ' + total + ' · ' + cards.length + ' episodes';
    pager.style.display = total > 1 ? '' : 'none';
  }}
  function go(p){{
    page = p;
    render();
    if (history.replaceState) history.replaceState(null, '', p === 1 ? location.pathname : '#page-' + p);
    section.scrollIntoView();
  }}
  prevBtn.onclick = () => {{ if (page > 1) go(page - 1); }};
  nextBtn.onclick = () => {{ if (page < total) go(page + 1); }};
  render();
  if (flashCard) {{
    setTimeout(() => flashCard.scrollIntoView({{ behavior: 'smooth', block: 'center' }}), 80);
    flashCard.classList.add('flash');
    setTimeout(() => flashCard.classList.remove('flash'), 2600);
  }}
  const toast = document.createElement('div');
  toast.id = 'toast';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  document.body.appendChild(toast);
  let toastTimer = null;
  function showToast(msg){{
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2000);
  }}
  function deepLink(n){{
    return location.origin + location.pathname + '#episode-' + n;
  }}
  async function copyLink(url){{
    try {{
      await navigator.clipboard.writeText(url);
      showToast('Link copied');
    }} catch (e) {{
      const ta = document.createElement('textarea');
      ta.value = url;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {{ document.execCommand('copy'); showToast('Link copied'); }}
      catch (e2) {{ showToast('Could not copy link'); }}
      document.body.removeChild(ta);
    }}
  }}
  section.addEventListener('click', (ev) => {{
    const btn = ev.target.closest('.share-btn');
    if (!btn) return;
    const n = btn.getAttribute('data-episode');
    const card = btn.closest('.card');
    const title = card ? card.querySelector('h2').textContent.trim() : ('Episode ' + n);
    const url = deepLink(n);
    if (navigator.share) {{
      navigator.share({{ title: title + ' — Zains Morning Commute Books', text: title, url: url }}).catch(() => {{}});
    }} else {{
      copyLink(url);
    }}
  }});
}})();
</script>
</body>
</html>"""

(ROOT / "index.html").write_text(page)
print(f"wrote index.html with {len(data['books'])} books")
