import html as html_escape

PAGE_TEMPLATE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Nueva pestaña</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{
    height: 100%;
    margin: 0;
    background: #202124;
    color: #e8eaed;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  .wrap {{
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .logo {{
    font-size: 34px;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 28px;
    color: #e8eaed;
  }}
  .logo span {{ color: #8ab4f8; }}
  form {{
    width: 100%;
    max-width: 560px;
  }}
  input[type="text"] {{
    width: 100%;
    padding: 14px 18px;
    font-size: 16px;
    border-radius: 24px;
    border: 1px solid #3c4043;
    background: #292a2d;
    color: #e8eaed;
    outline: none;
  }}
  input[type="text"]:focus {{
    border-color: #8ab4f8;
  }}
  .quick-links {{
    margin-top: 40px;
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    justify-content: center;
    max-width: 640px;
  }}
  .quick-link {{
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 92px;
    text-decoration: none;
    color: #e8eaed;
  }}
  .quick-link .bubble {{
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: #303134;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
  }}
  .quick-link:hover .bubble {{
    background: #3c4043;
  }}
  .quick-link .label {{
    font-size: 12px;
    text-align: center;
    color: #bdc1c6;
    max-width: 92px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .empty-hint {{
    margin-top: 40px;
    font-size: 13px;
    color: #5f6368;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="logo">Mini<span>Browser</span></div>
    <form action="https://www.google.com/search" method="GET">
      <input type="text" name="q" placeholder="Buscar en Google o escribir una URL" autofocus>
    </form>
    <div class="quick-links">
      {quick_links_html}
    </div>
    {empty_hint}
  </div>
</body>
</html>
"""

QUICK_LINK_TEMPLATE = """
<a class="quick-link" href="{url}" title="{title_attr}">
  <div class="bubble">{initials}</div>
  <div class="label">{label}</div>
</a>
"""


def _initials(name):
    name = (name or "?").strip()
    return (name[:2] or "?").upper()


def render_new_tab_page(bookmarks=None, max_links=8):
    """bookmarks: lista de tuplas (url, title), más reciente primero
    (mismo formato que Database.get_bookmarks())."""
    bookmarks = bookmarks or []
    links_html = []
    for url, title in bookmarks[:max_links]:
        label = title or url
        short_label = (label[:14] + "…") if len(label) > 14 else label
        links_html.append(
            QUICK_LINK_TEMPLATE.format(
                url=html_escape.escape(url, quote=True),
                title_attr=html_escape.escape(label, quote=True),
                initials=html_escape.escape(_initials(label)),
                label=html_escape.escape(short_label),
            )
        )

    empty_hint = ""
    if not bookmarks:
        empty_hint = '<div class="empty-hint">Marcá páginas con ☆ para verlas acá</div>'

    return PAGE_TEMPLATE.format(
        quick_links_html="".join(links_html),
        empty_hint=empty_hint,
    )
