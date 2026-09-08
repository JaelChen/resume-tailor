# 字体来源与许可

本目录的字体**不适用**仓库根目录的 MIT 许可，各自遵循下列条款。

| 文件 | 字体 | 许可 | 来源 |
| --- | --- | --- | --- |
| `TailorSansCN-{Regular,Medium,Bold}.ttf` | 思源黑体 Source Han Sans 的**常用字子集** | SIL OFL 1.1，见 `OFL-SourceHan.txt` | [adobe-fonts/source-han-sans](https://github.com/adobe-fonts/source-han-sans) |
| `TailorSerifCN-Bold.ttf` | 思源宋体 Source Han Serif 的**常用字子集** | SIL OFL 1.1，见 `OFL-SourceHan.txt` | [adobe-fonts/source-han-serif](https://github.com/adobe-fonts/source-han-serif) |
| `JetBrainsMono-Regular.ttf` | JetBrains Mono，未经修改 | SIL OFL 1.1，见 `OFL-JetBrainsMono.txt` | [JetBrains/JetBrainsMono](https://github.com/JetBrains/JetBrainsMono) |
| `iconfont.ttf` | LapisCV 图标子集 | MIT，随 LapisCV 分发 | [BingyanStudio/LapisCV](https://github.com/BingyanStudio/LapisCV) |

## 为什么改名叫 Tailor 而不是 SourceHan

`OFL-SourceHan.txt` 第一行声明 Adobe 保留字体名 **'Source'**。OFL 1.1 第 3 条禁止修改版沿用保留字体名，而**子集化就是 OFL 定义的「修改」**。所以子集文件的文件名和字体内部名称表（nameID 1/2/3/4/6/16/17）都已改为 `TailorSansCN` / `TailorSerifCN`，nameID 3 保留了 `subset-of-SourceHan` 以便溯源。

除此之外未做任何改动：字形轮廓、字重、度量、OpenType 排版特性全部原样保留，排出来的版面和完整字体一致。

## 子集范围

`subset-charset.txt` 是实际使用的字符集，共 7565 个字符：

- GB2312 全部汉字 6763 个（一级 3755 + 二级 3008，等同通用规范汉字表一二级）
- GB2312 符号区（中文标点、全角字符、希腊字母、俄文、注音）
- ASCII 可见字符
- 补充排版符号：`– — … · • ° ± × ÷ ≈ ≤ ≥ ← → ↑ ↓ ★ ☆ 【】《》「」『』⌘ ⌥ ⇧ ⌃ ✓ ✗ ⚠ ※ ℃ ™ © ® § € £ ¥` 等

完整思源含四万多字形共 44 MB，子集后 11 MB。**缺字不会变豆腐块**：浏览器的字体回退逐字生效，子集里没有的字会落到 CSS 栈里的下一个字体（系统装的完整思源 / 微软雅黑 / PingFang），最多那一个字观感略有出入。

## 怎么重新生成

换字体、加字，或者需要更大字符集时：

```bash
pip install fonttools
pyftsubset SourceHanSansCN-Regular.ttf \
  --text-file=subset-charset.txt \
  --output-file=TailorSansCN-Regular.ttf \
  --layout-features='*' --no-hinting --desubroutinize --name-IDs='*' --recalc-bounds
```

切完**必须改名称表**，否则违反 OFL 保留字体名条款：

```python
from fontTools.ttLib import TTFont
f = TTFont("TailorSansCN-Regular.ttf")
for r in f["name"].names:
    if   r.nameID == 1:  r.string = "TailorSansCN"
    elif r.nameID == 2:  r.string = "Regular"
    elif r.nameID == 3:  r.string = "TailorSansCN-Regular;subset-of-SourceHan"
    elif r.nameID == 4:  r.string = "TailorSansCN Regular"
    elif r.nameID == 6:  r.string = "TailorSansCN-Regular"
    elif r.nameID == 16: r.string = "TailorSansCN"
    elif r.nameID == 17: r.string = "Regular"
f.save("TailorSansCN-Regular.ttf")
```

改完记得同步 `md2html.py` 里的 `CJK` / `SERIF` 字体栈和 `FONT_FACES`。

## 许可合规说明

OFL 1.1 允许自由使用、嵌入、修改和再分发，条件是：随附许可副本（`OFL-*.txt` 已随附）、不单独售卖字体本身、修改版不沿用保留字体名（已改名）。

PDF 导出时 Chrome 会把用到的字形再子集化一次嵌入文件，这属于 OFL 明确允许的嵌入用法。
