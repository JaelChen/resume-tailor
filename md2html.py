#!/usr/bin/env python3
"""简历 markdown -> 可打印 HTML。零依赖。

用法:
  python md2html.py 输入.md 输出.html [--layout L] [--accent #RRGGBB] [--photo 照片] [--keep-marks]

  --layout   版式骨架，默认 sidebar
             sidebar   满高彩色侧栏 + 照片 + 反白姓名（Reactive-Resume gengar 式）
             banner    顶部整块色底抬头 + 圆形照片 + 联系方式色带 + 双栏（leafish 式）
  --accent   强调色，默认 #1f3a5f
  --photo    证件照路径（jpg/png），内嵌为 data URI。
             不给则两种版式都自动收掉照片位，不留空块。
  --keep-marks  保留 [← 来源 | 相关度] 标记（审草稿用）

markdown 约定:
  # 姓名
  短行 -> 副标题（学校专业）；含 @ 或电话的行 -> 联系方式；求职意向… -> 意向；长段 -> 摘要
  ## 章节    技能/教育/语言/证书/获奖 自动进侧栏，其余进主栏
  ### 单位 ｜ 角色 ｜ 时间    渲染成两行，时间右对齐
  *斜体行* -> 规模注释    - 列表 -> 条目
"""
import re, sys, base64, pathlib, mimetypes

SIDEBAR_SECTIONS = ("技能", "教育", "语言", "证书", "获奖")
MARK = re.compile(r'\s*`?\[←[^\]]*\]`?')
SPLIT = re.compile(r'\s*[｜|]\s*')
PHONE = re.compile(r'\d{3}[-\s]?\d{4}')

ICONS = {
    "mail": '<path d="M2 4h12v8H2z" fill="none" stroke="currentColor" stroke-width="1.3"/>'
            '<path d="M2 4l6 5 6-5" fill="none" stroke="currentColor" stroke-width="1.3"/>',
    "phone": '<path d="M3 3h3l1.5 3.5-2 1.5a9 9 0 004.5 4.5l1.5-2L15 12v3h-1'
             'A11 11 0 013 4z" fill="currentColor"/>',
    "chat": '<path d="M2 3h12v8H6l-4 3z" fill="none" stroke="currentColor" stroke-width="1.3"/>',
    "pin": '<path d="M8 1.5c2.2 0 4 1.8 4 4 0 3-4 8.5-4 8.5S4 8.5 4 5.5c0-2.2 1.8-4 4-4z"'
           ' fill="none" stroke="currentColor" stroke-width="1.3"/>'
           '<circle cx="8" cy="5.5" r="1.4" fill="currentColor"/>',
}


def icon(kind):
    return ('<svg viewBox="0 0 16 16" width="10" height="10" aria-hidden="true">%s</svg>'
            % ICONS[kind])


def classify(text):
    if '@' in text:
        return 'mail'
    if PHONE.search(text):
        return 'phone'
    if '微信' in text or 'wechat' in text.lower():
        return 'chat'
    return 'pin'


# ---------- 解析 ----------

def parse(md, keep):
    name, subtitle, contacts, intent, summary, sections = '', '', [], '', '', []
    cur = None
    for raw in md.splitlines():
        line = raw.rstrip()
        if not keep:
            line = MARK.sub('', line)
        s = line.strip()
        if not s or s in ('---', '***'):
            continue
        if s.startswith('# '):
            name = s[2:].strip()
        elif s.startswith('## '):
            cur = {'title': s[3:].strip(), 'items': []}
            sections.append(cur)
        elif s.startswith('### '):
            if cur:
                cur['items'].append(('h3', s[4:].strip()))
        elif s.startswith('- '):
            if cur:
                cur['items'].append(('li', s[2:].strip()))
        elif cur is None:
            if s.startswith('求职意向'):
                intent = s.split('：', 1)[-1].strip()
            elif '@' in s or PHONE.search(s):
                contacts = [p for p in SPLIT.split(s) if p]
            elif len(s) > 55:
                summary = s
            elif not subtitle:
                subtitle = s
        else:
            cur['items'].append(('p', s))
    return dict(name=name, subtitle=subtitle, contacts=contacts,
                intent=intent, summary=summary, sections=sections)


def inline(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s.replace('`', '')


def entry_head(text):
    """### 单位 ｜ 角色 ｜ 时间  ->  两行，右侧对齐时间。"""
    p = SPLIT.split(text)
    when = ''
    if len(p) > 1 and re.search(r'\d{4}[.\-/]', p[-1]):
        when, p = p[-1], p[:-1]
    org = p[0] if p else text
    role = ' · '.join(p[1:])
    out = ['<div class="entry">',
           '<div class="row"><span class="org">%s</span>'
           '<span class="when">%s</span></div>' % (inline(org), inline(when))]
    if role:
        out.append('<div class="row"><span class="role">%s</span></div>' % inline(role))
    out.append('</div>')
    return '\n'.join(out)


def render_items(items):
    out, in_ul = [], False

    def close():
        nonlocal in_ul
        if in_ul:
            out.append('</ul>')
            in_ul = False

    for kind, text in items:
        if kind == 'li':
            if not in_ul:
                out.append('<ul>')
                in_ul = True
            out.append('<li>%s</li>' % inline(text))
        elif kind == 'h3':
            close()
            out.append(entry_head(text))
        else:
            close()
            out.append('<p>%s</p>' % inline(text))
    close()
    return '\n'.join(out)


def section_html(sec):
    return '<section><h2>%s</h2>\n%s\n</section>' % (inline(sec['title']),
                                                     render_items(sec['items']))


# ---------- 样式 ----------

COMMON = """
@page {{ size:A4; margin:0; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font:{size}/{lh} {font}; color:{ink}; background:#fff; }}
.sheet {{ width:210mm; min-height:297mm; margin:0 auto; background:#fff;
          display:{sheetdisp}; }}
h2 {{ font-size:{h2}; font-weight:700; letter-spacing:.6px; }}
.entry {{ margin:{entrymt} 0 .8mm; }}
.row {{ display:flex; justify-content:space-between; align-items:baseline; gap:4mm; }}
.org {{ font-weight:700; font-size:{h3}; }}
.role {{ color:{muted}; font-size:{meta}; }}
.when {{ color:{muted}; font-size:{meta}; white-space:nowrap; }}
em {{ font-style:normal; color:{muted}; font-size:{meta}; }}
ul {{ list-style:none; }}
li {{ position:relative; padding-left:3.4mm; margin-bottom:{gap}; }}
li::before {{ content:""; position:absolute; left:.6mm; top:2.1mm;
              width:1.3mm; height:1.3mm; border-radius:50%; background:{accent}; }}
p {{ margin:.6mm 0; }}
.ct {{ display:flex; align-items:center; gap:1.6mm; font-size:{meta}; }}
.ct svg {{ flex:none; opacity:.85; }}
h2, .entry {{ break-after:avoid-page; break-inside:avoid; }}
li, p {{ break-inside:avoid; orphans:3; widows:3; }}
.foot {{ padding:4mm 0; text-align:center; color:#bbb; font-size:8pt; }}
@media print {{ .foot {{ display:none; }} .sheet {{ margin:0; }} }}
"""

SIDEBAR = """
.sheet {{ display:grid; grid-template-columns:62mm 1fr; }}
.side {{ background:{accent}; color:#fff; padding:0 0 8mm; }}
.side .photo {{ width:62mm; height:62mm; object-fit:cover; display:block; }}
.side .idbox {{ padding:5mm 6mm 4mm; }}
.side .idbox:first-child {{ padding-top:10mm; }}
.side h1 {{ font-size:{h1}; font-weight:700; letter-spacing:1px; line-height:1.15; }}
.side .sub {{ font-size:{meta}; opacity:.82; margin-top:1.5mm; line-height:1.45; }}
.side .intent {{ font-size:{meta}; margin-top:2mm; padding-top:2mm;
                 border-top:1px solid rgba(255,255,255,.35); opacity:.95; }}
.side .cts {{ padding:0 6mm; display:flex; flex-direction:column; gap:1.6mm; }}
.side .ct {{ opacity:.92; }}
.side section {{ padding:0 6mm; margin-top:5mm; }}
.side h2 {{ font-size:{h2s}; padding-bottom:1mm; margin-bottom:2mm;
            border-bottom:1px solid rgba(255,255,255,.4); }}
.side .org, .side li, .side p {{ font-size:{meta}; }}
.side .role, .side .when, .side em {{ color:rgba(255,255,255,.75); }}
.side .row {{ display:block; }}
.side li::before {{ background:rgba(255,255,255,.8); }}
.main {{ padding:9mm 10mm 8mm; }}
.main .summary {{ font-size:{meta}; color:#444; margin-bottom:4mm;
                  padding-bottom:3mm; border-bottom:1px solid {rule}; }}
.main section + section {{ margin-top:5mm; }}
.main h2 {{ color:{accent}; padding-bottom:.8mm; margin-bottom:2mm;
            border-bottom:1.5px solid {accent}; }}
"""

BANNER = """
.sheet {{ display:block; }}
.top {{ background:{tint}; padding:7mm 12mm 5mm; display:flex; gap:6mm; align-items:center; }}
.top .photo {{ width:26mm; height:26mm; border-radius:50%; object-fit:cover;
               flex:none; border:2px solid #fff; }}
.top h1 {{ font-size:{h1}; color:{accent}; letter-spacing:1px; }}
.top .sub {{ font-size:{meta}; color:#555; margin-top:1mm; }}
.top .intent {{ font-size:{meta}; font-weight:700; color:{accent}; margin-top:1.5mm; }}
.top .summary {{ font-size:{meta}; color:#444; margin-top:2.5mm; line-height:1.5; }}
.band {{ background:{band}; padding:2.4mm 12mm; display:flex; flex-wrap:wrap;
         gap:6mm; color:{accent}; }}
.body {{ display:grid; grid-template-columns:1fr 58mm; gap:8mm; padding:6mm 12mm 8mm; }}
section + section {{ margin-top:4.5mm; }}
h2 {{ color:{accent}; padding-bottom:.7mm; margin-bottom:2mm;
      border-bottom:1.5px solid {accent}; }}
aside h2 {{ font-size:{h2s}; }}
aside .org, aside li, aside p {{ font-size:{meta}; }}
aside .row {{ display:block; }}
"""

LAYOUTS = {"sidebar": SIDEBAR, "banner": BANNER}

METRICS = {
    "sidebar": dict(size="10pt", lh="1.42", h1="19pt", h2="11pt", h2s="9.6pt", h3="10pt",
                    meta="8.6pt", gap=".9mm", entrymt="3mm", sheetdisp="grid",
                    font='-apple-system,"PingFang SC","Microsoft YaHei",sans-serif'),
    "banner": dict(size="10.2pt", lh="1.42", h1="21pt", h2="11pt", h2s="9.8pt", h3="10.2pt",
                   meta="8.8pt", gap=".9mm", entrymt="3mm", sheetdisp="block",
                   font='-apple-system,"PingFang SC","Microsoft YaHei",sans-serif'),
}


def shade(hexcolor, ratio, toward=255):
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    f = lambda c: round(c + (toward - c) * ratio)
    return '#%02x%02x%02x' % (f(r), f(g), f(b))


def css(layout, accent):
    v = dict(METRICS[layout], accent=accent, ink="#1a1a1a", muted="#666", rule="#d0d4da",
             tint=shade(accent, .90), band=shade(accent, .80), dark=shade(accent, .25, 0))
    return (COMMON + LAYOUTS[layout]).format(**v)


def photo_uri(path):
    if not path:
        return ''
    p = pathlib.Path(path)
    mime = mimetypes.guess_type(p.name)[0] or 'image/jpeg'
    return 'data:%s;base64,%s' % (mime, base64.b64encode(p.read_bytes()).decode())


def contacts_html(items):
    return '\n'.join('<div class="ct">%s<span>%s</span></div>'
                     % (icon(classify(c)), inline(c)) for c in items)


def build(layout, d, photo):
    side = [s for s in d['sections'] if s['title'].startswith(SIDEBAR_SECTIONS)]
    main = [s for s in d['sections'] if s not in side]
    name, sub, intent, summary = (inline(d['name']), inline(d['subtitle']),
                                  inline(d['intent']), inline(d['summary']))
    cts = contacts_html(d['contacts'])

    if layout == 'sidebar':
        img = '<img class="photo" src="%s" alt="">' % photo if photo else ''
        return ('<div class="sheet"><div class="side">%s'
                '<div class="idbox"><h1>%s</h1><div class="sub">%s</div>'
                '<div class="intent">求职意向：%s</div></div>'
                '<div class="cts">%s</div>%s</div>'
                '<div class="main"><p class="summary">%s</p>%s</div></div>'
                % (img, name, sub, intent, cts,
                   '\n'.join(section_html(s) for s in side),
                   summary, '\n'.join(section_html(s) for s in main)))

    if layout == 'banner':
        img = '<img class="photo" src="%s" alt="">' % photo if photo else ''
        return ('<div class="sheet"><div class="top">%s<div><h1>%s</h1>'
                '<div class="sub">%s</div><div class="intent">求职意向：%s</div>'
                '<div class="summary">%s</div></div></div>'
                '<div class="band">%s</div>'
                '<div class="body"><main>%s</main><aside>%s</aside></div></div>'
                % (img, name, sub, intent, summary, cts,
                   '\n'.join(section_html(s) for s in main),
                   '\n'.join(section_html(s) for s in side)))

    raise ValueError('unknown layout: %s' % layout)


def main():
    a = sys.argv[1:]
    opts = {'--layout': 'sidebar', '--accent': '#1f3a5f', '--photo': ''}
    for flag in list(opts):
        if flag in a:
            i = a.index(flag)
            opts[flag] = a[i + 1]
            del a[i:i + 2]
    keep = '--keep-marks' in a
    files = [x for x in a if not x.startswith('--')]
    layout = opts['--layout']
    if len(files) < 2 or layout not in LAYOUTS:
        print(__doc__)
        sys.exit(1)
    d = parse(pathlib.Path(files[0]).read_text(encoding='utf-8'), keep)
    html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<title>%s</title><style>%s</style></head><body>%s'
            '<p class="foot">版式 %s｜Ctrl / ⌘ + P 导出 PDF：纸张 A4、边距「无」、缩放「默认」、'
            '勾选「背景图形」、取消页眉页脚</p></body></html>'
            % (d['name'] or '简历', css(layout, opts['--accent']),
               build(layout, d, photo_uri(opts['--photo'])), layout))
    pathlib.Path(files[1]).write_text(html, encoding='utf-8')
    print('ok [%s] -> %s  %d bytes%s'
          % (layout, files[1], len(html), '  含照片' if opts['--photo'] else '  无照片'))


main()
