#!/usr/bin/env python3
"""简历 markdown -> 可打印 HTML。零依赖。

版式 1:1 复刻 LapisCV（https://github.com/BingyanStudio/LapisCV，MIT）：
正文 10pt / 行高 1.8、字号层级 16 / 12 / 10.5 / 9.5pt、正文 #353a42、
强调 #4870ad、边框 #dae3ea、页边距 13mm × 15mm、右浮动圆形头像。

用法:
  python md2html.py 输入.md 输出.html [--accent #RRGGBB] [--photo 照片] [--keep-marks]

  --accent      强调色，默认 #4870ad
  --photo       证件照（jpg/png），内嵌为 data URI。
                不给则保留头像框位置：屏幕上显示虚线占位，打印时隐藏但仍占位，
                保证屏幕与打印的排版一致。
  --keep-marks  保留 [← 来源 | 相关度] 标记（审草稿用），默认去掉

markdown 约定:
  # 姓名
  短行 -> 副标题；含 @ 或电话的行 -> 联系方式；求职意向… -> 意向；长段 -> 摘要
  ## 章节                        标题按关键词自动配图标
  ### 单位 ｜ 角色 ｜ 时间         左侧单位加粗，右侧时间同色同号
  普通段落                       条目下的整体描述
  - 条目                         列表
"""
import re, sys, base64, pathlib, mimetypes

MARK = re.compile(r'\s*`?\[←[^\]]*\]`?')
SPLIT = re.compile(r'\s*[｜|]\s*')
PHONE = re.compile(r'\d{3}[-\s]?\d{4}')

# LapisCV iconfont.ttf 的码位（该字体共 21 个字形）
CONTACT_ICONS = {"phone": "e60f", "mail": "e7ca", "chat": "e611", "pin": "e600"}

SECTION_ICONS = [
    (("教育", "学历"), "e80c"),
    (("技能", "专业", "能力"), "ecfa"),
    (("实习", "工作", "职业"), "e618"),
    (("项目", "作品", "主导"), "e635"),
    (("语言", "证书", "获奖", "荣誉"), "e638"),
]
FALLBACK_ICON = "e631"


def ico(code):
    return '<span class="ico">&#x%s;</span>' % code


def contact_kind(text):
    if '@' in text:
        return 'mail'
    if PHONE.search(text):
        return 'phone'
    if '微信' in text or 'wechat' in text.lower():
        return 'chat'
    return 'pin'


def section_icon(title):
    for keys, code in SECTION_ICONS:
        if any(k in title for k in keys):
            return ico(code)
    return ico(FALLBACK_ICON)


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
    """### 单位 ｜ 角色 ｜ 时间 -> 左侧单位与角色，右侧时间。"""
    parts = SPLIT.split(text)
    right = ''
    if len(parts) > 1 and re.search(r'\d{4}[.\-/]', parts[-1]):
        right, parts = parts[-1], parts[:-1]
    left = ' - '.join(parts) if parts else text
    return ('<div class="entry-title"><h3>%s</h3><p class="when">%s</p></div>'
            % (inline(left), inline(right)))


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
            out.append('<p class="desc">%s</p>' % inline(text))
    close()
    return '\n'.join(out)


def section_html(sec):
    return ('<section><h2>%s<span>%s</span></h2>\n%s\n</section>'
            % (section_icon(sec['title']), inline(sec['title']), render_items(sec['items'])))


# ---------- 样式：1:1 对齐 LapisCV ----------

CSS = """
@page {{ size:A4; margin:13mm 15mm; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}

body {{
  font-family:{cjk};
  font-size:10pt; line-height:1.8; color:{ink}; background:#fff;
}}
.sheet {{ width:210mm; min-height:297mm; margin:0 auto; padding:13mm 15mm; background:#fff; }}

/* 抬头：全部左对齐 */
h1 {{ font-family:{serif}; font-size:22pt; font-weight:700; line-height:1.4;
      color:{ink}; letter-spacing:1px; }}
.sub {{ font-size:9.5pt; color:{muted}; }}
.cts {{ font-size:9.5pt; line-height:1.9; margin-top:.6mm; }}
.cts .item {{ white-space:nowrap; margin-right:6mm; font-family:{mono}; }}
.ico {{ font-family:LapisIcon; font-style:normal; color:{accent}; }}
.cts .ico {{ font-size:10pt; margin-right:1.2mm; }}
.intent {{ font-size:9.5pt; color:{accent}; font-weight:700; margin-top:1mm; }}
.summary {{ font-size:9.5pt; text-align:justify; margin-top:1.8mm; }}

/* 证件照：右上角方形，一寸比例，不占布局流 */
.avatar-line {{ height:0; }}
.avatar, .avatar-slot {{
  display:block; position:relative; top:0; right:0; z-index:9;
  float:right; width:25mm; height:35mm;
  object-fit:cover; overflow:hidden;
  border:1px solid {rule}; margin:0 0 2mm 5mm;
}}
.avatar-slot {{ border-style:dashed; }}
.avatar-slot::after {{ content:"照片"; position:absolute; inset:0;
  display:flex; align-items:center; justify-content:center;
  color:{rule}; font-size:9pt; }}

/* 章节：标题走宋体 */
h2 {{
  display:flex; align-items:center; gap:1.8mm;
  font-family:{serif}; font-size:13pt; font-weight:700; color:{accent}; line-height:1;
  margin:3.4mm 0 1.9mm; padding:1mm 0;
  border-bottom:1px solid {faint};
}}
h2 .ico {{ flex:none; font-size:12pt; line-height:1; }}

/* 条目 */
.entry-title {{ display:flex; justify-content:space-between; align-items:center; gap:4mm; }}
.entry-title h3 {{ font-family:{serif}; font-size:11pt; font-weight:700;
                   color:{ink}; line-height:1.8; }}
.entry-title .when {{ font-size:10pt; color:{ink}; white-space:nowrap; font-family:{mono}; }}
.desc {{ font-size:10pt; }}

/* 列表 */
ul {{ list-style-type:'\\2022'; padding-inline-start:3mm; padding-inline-end:1mm; }}
li {{ padding-left:1.5mm; }}
ul ::marker {{ font-weight:bolder; color:{accent}; }}

strong {{ color:{ink}; }}
em {{ font-style:normal; color:{muted}; font-size:9.5pt; }}

/* 分页 */
h1, h2, h3, .entry-title {{ break-after:avoid-page; break-inside:avoid; }}
li, p {{ break-inside:avoid; orphans:3; widows:3; }}

.foot {{ margin-top:8mm; text-align:center; color:#b8c2cc; font-size:8pt; }}
@media print {{
  .foot {{ display:none; }}
  .sheet {{ padding:0; width:auto; min-height:0; }}
  .avatar-slot {{ visibility:hidden; }}
}}
"""

CJK = ('SourceHanSansCN,"Source Han Sans SC","Noto Sans SC","PingFang SC",'
       '"Microsoft YaHei","Hiragino Sans GB",sans-serif')
SERIF = ('SourceHanSerifCN,"Source Han Serif SC","Noto Serif SC","Songti SC",'
         'SimSun,Georgia,serif')
MONO = 'JetBrainsMono,"JetBrains Mono","SF Mono",Consolas,' + CJK

# 字体放在本 skill 的 fonts/ 下，用绝对 file:// 引用。
# HTML 因此不便携（发给别人会掉字体），但 PDF 会把字形嵌进去，投递的是 PDF，没问题。
FONT_FACES = [
    ("SourceHanSansCN", "SourceHanSansCN-Regular.ttf", "400", "normal"),
    ("SourceHanSansCN", "SourceHanSansCN-Medium.ttf", "500", "normal"),
    ("SourceHanSansCN", "SourceHanSansCN-Bold.ttf", "700", "normal"),
    ("SourceHanSerifCN", "SourceHanSerifCN-Bold.ttf", "700", "normal"),
    ("JetBrainsMono", "JetBrainsMono-Regular.ttf", "400", "normal"),
    ("LapisIcon", "iconfont.ttf", "400", "normal"),
]


def font_faces():
    d = pathlib.Path(__file__).resolve().parent / 'fonts'
    out = []
    for family, fname, weight, style in FONT_FACES:
        f = d / fname
        if f.exists():
            out.append('@font-face{font-family:"%s";src:url("%s") format("truetype");'
                       'font-weight:%s;font-style:%s;font-display:block;}'
                       % (family, f.as_uri(), weight, style))
    return '\n'.join(out)


def rgba(hexcolor, alpha):
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return 'rgba(%d,%d,%d,%s)' % (r, g, b, alpha)


def build_css(accent):
    return font_faces() + CSS.format(
        ink="#353a42", accent=accent, rule="#dae3ea",
        faint=rgba(accent, "0.4"), muted="#6b7480",
        cjk=CJK, serif=SERIF, mono=MONO)


def photo_uri(path):
    if not path:
        return ''
    p = pathlib.Path(path)
    mime = mimetypes.guess_type(p.name)[0] or 'image/jpeg'
    return 'data:%s;base64,%s' % (mime, base64.b64encode(p.read_bytes()).decode())


def build(d, photo):
    cts = ''.join('<span class="item">%s%s</span>'
                  % (ico(CONTACT_ICONS[contact_kind(c)]), inline(c))
                  for c in d['contacts'])
    avatar = ('<img class="avatar" src="%s" alt="">' % photo if photo
              else '<span class="avatar-slot"></span>')
    head = ['<h1>%s</h1>' % inline(d['name'])]
    if d['subtitle']:
        head.append('<p class="sub">%s</p>' % inline(d['subtitle']))
    if cts:
        head.append('<p class="cts">%s</p>' % cts)
    if d['intent']:
        head.append('<p class="intent">求职意向：%s</p>' % inline(d['intent']))
    if d['summary']:
        head.append('<p class="summary">%s</p>' % inline(d['summary']))
    return ('<div class="sheet"><p class="avatar-line">%s</p>\n%s\n%s</div>'
            % (avatar, '\n'.join(head),
               '\n'.join(section_html(s) for s in d['sections'])))


# ---------- 自动转 PDF ----------

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
CHROME_NAMES = ["google-chrome", "chromium", "chromium-browser", "microsoft-edge", "chrome"]


def find_chrome():
    import os, shutil
    local = os.environ.get("LOCALAPPDATA", "")
    cands = list(CHROME_PATHS)
    if local:
        cands.insert(0, os.path.join(local, r"Google\Chrome\Application\chrome.exe"))
    for p in cands:
        if pathlib.Path(p).exists():
            return p
    for n in CHROME_NAMES:
        p = shutil.which(n)
        if p:
            return p
    return None


def to_pdf(html_path, pdf_path):
    """无头 Chrome / Edge 打印成 PDF。返回 (成功, 说明)。"""
    import subprocess, tempfile
    exe = find_chrome()
    if not exe:
        return False, "没找到 Chrome 或 Edge，请手动打开 HTML 按 Ctrl/⌘+P 导出"
    with tempfile.TemporaryDirectory() as prof:
        cmd = [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--allow-file-access-from-files",
               "--user-data-dir=" + prof,
               "--no-pdf-header-footer",
               "--print-to-pdf=" + str(pdf_path),
               pathlib.Path(html_path).resolve().as_uri()]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=120)
        except Exception as e:
            return False, "调用失败：%s" % e
    if pathlib.Path(pdf_path).exists() and pathlib.Path(pdf_path).stat().st_size > 1000:
        return True, exe
    return False, (r.stderr.decode("utf-8", "replace")[-300:] or "未知错误")


def pdf_pages(pdf_path):
    """数 PDF 页数，用于如实报给用户。"""
    try:
        d = pathlib.Path(pdf_path).read_bytes()
        n = len(re.findall(rb'/Type\s*/Page[^sR]', d))
        return n or None
    except Exception:
        return None


def safe_name(s, cjk_only=False):
    """文件名片段：去非法字符与空格；cjk_only 时只取开头的中文姓名。"""
    s = re.sub(r'[\\/:*?"<>|]+', '', s)
    if cjk_only:
        m = re.match(r'[一-龥·\s]+', s)
        if m:
            s = m.group(0)
    return re.sub(r'\s+', '', s).strip(' -')


def main():
    a = sys.argv[1:]
    opts = {'--accent': '#4870ad', '--photo': '', '--company': '', '--out-dir': ''}
    for flag in list(opts):
        if flag in a:
            i = a.index(flag)
            opts[flag] = a[i + 1]
            del a[i:i + 2]
    keep = '--keep-marks' in a
    want_pdf = '--pdf' in a
    files = [x for x in a if not x.startswith('--')]
    if not files:
        print(__doc__)
        sys.exit(1)

    d = parse(pathlib.Path(files[0]).read_text(encoding='utf-8'), keep)

    if len(files) > 1:
        out_html = pathlib.Path(files[1])
    else:
        stem = '-'.join(x for x in (safe_name(d['name'], cjk_only=True),
                                    safe_name(opts['--company']),
                                    safe_name(d['intent'])) if x) or '简历'
        out_dir = pathlib.Path(opts['--out-dir'] or pathlib.Path(files[0]).parent)
        out_html = out_dir / (stem + '.html')
    out_html.parent.mkdir(parents=True, exist_ok=True)

    html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<title>%s</title><style>%s</style></head><body>%s'
            '<p class="foot">Ctrl / ⌘ + P 导出 PDF：纸张 A4、边距「默认」、缩放「默认」、'
            '取消页眉页脚</p></body></html>'
            % (out_html.stem, build_css(opts['--accent']),
               build(d, photo_uri(opts['--photo']))))
    out_html.write_text(html, encoding='utf-8')
    print('HTML -> %s  (%d bytes%s)'
          % (out_html, len(html), '，含照片' if opts['--photo'] else '，头像框留位'))

    if want_pdf:
        pdf = out_html.with_suffix('.pdf')
        ok, info = to_pdf(out_html, pdf)
        if ok:
            n = pdf_pages(pdf)
            print('PDF  -> %s  (%.1f KB，用 %s)'
                  % (pdf, pdf.stat().st_size / 1024, pathlib.Path(info).name))
            print('页数 -> %s 页  ← 如实告诉用户，超一页且第二页不足半页就按 SKILL.md 的顺序压缩'
                  % (n if n else '数不出来，请用户打开确认'))
        else:
            print('PDF  x  %s' % info)


main()
