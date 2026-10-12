"""Laying out a menu text (DECISIONS §103): lines broken to fit a box, with
the Japanese rules for where a line may not start or end (kinsoku), and the
characters of vertical text.

Measuring is the caller's: `measure(s)` gives the width of `s` in pixels as
it will be drawn.
"""

# a line does not start with these (closing brackets, stops, small kana,
# the long vowel mark, iteration marks; JIS X 4051's line-start prohibited
# classes, without the optional ones)
NO_START = set(
    "、。，．,.:;?!：；？！‼⁇⁈⁉・゠–〜～ー"
    ")]}）〕］｝〉》」』】〙〗〟’”»"
    "ヽヾゝゞ々〻"
    "ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ"
    "%‰℃°′″")
# ... and does not end with these (opening brackets)
NO_END = set("([{（〔［｛〈《「『【〘〖〝‘“«")

# vertical text: characters drawn as their vertical presentation forms
# (Unicode's Vertical Forms and CJK Compatibility Forms blocks) when the
# font has them
VERTICAL = {
    "、": "︑", "。": "︒", "，": "︐", "：": "︓", "；": "︔",
    "！": "︕", "？": "︖", "〖": "︗", "〗": "︘", "…": "︙",
    "‥": "︰", "—": "︱", "―": "︱", "ー": "︱", "–": "︲",
    "（": "︵", "）": "︶", "｛": "︷", "｝": "︸", "〔": "︹",
    "〕": "︺", "【": "︻", "】": "︼", "《": "︽", "》": "︾",
    "〈": "︿", "〉": "﹀", "「": "﹁", "」": "﹂", "『": "﹃",
    "』": "﹄", "［": "﹇", "］": "﹈",
}
# small kana sit in the upper right of their square in vertical text
SMALL_KANA = set("ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶ")


def wide(ch):
    """A character set solid (CJK): a line may break before or after it."""
    cp = ord(ch)
    return (0x2E80 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF or 0xF900 <= cp <= 0xFAFF
            or 0xFE30 <= cp <= 0xFE4F or 0xFF00 <= cp <= 0xFFEF or 0x20000 <= cp <= 0x3FFFF)


def _pieces(line):
    """A line cut where it may break: each wide character alone, a run of
    other letters (a word) whole, each space alone."""
    out, word = [], ""
    for ch in line:
        if ch == " " or wide(ch):
            if word:
                out.append(word)
                word = ""
            out.append(ch)
        else:
            word += ch
    if word:
        out.append(word)
    return out


def _split_long(piece, measure, width):
    """A word wider than the box, cut by character."""
    out, cur = [], ""
    for ch in piece:
        if cur and measure(cur + ch) > width:
            out.append(cur)
            cur = ""
        cur += ch
    return out + ([cur] if cur else [])


def wrap(text, measure, width):
    """`text` with its lines broken to fit `width` pixels: at spaces between
    words, and between wide characters, keeping NO_START characters off the
    start of a line and NO_END ones off its end (the character before is
    taken down with them). A line's own newlines stay."""
    if not width or width <= 0:
        return text
    out = []
    for line in text.split("\n"):
        pieces = []
        for p in _pieces(line):
            pieces += _split_long(p, measure, width) if measure(p) > width else [p]
        rows, cur = [], []
        for p in pieces:
            if cur and p != " " and measure("".join(cur + [p])) > width:
                # a forbidden start takes what is before it down with it;
                # a forbidden end goes down with what follows
                carry, head = [], p
                while len(cur) > 1 and head[0] in NO_START:
                    head = cur.pop()
                    carry.insert(0, head)
                while len(cur) > 1 and cur[-1][-1] in NO_END:
                    carry.insert(0, cur.pop())
                rows.append("".join(cur).rstrip(" "))
                cur = carry
            if p == " " and not cur:
                continue                      # (no space at a line's start)
            cur.append(p)
        rows.append("".join(cur).rstrip(" "))
        out += rows
    return "\n".join(out)


def vertical_char(ch, has_glyph):
    """The character drawn for `ch` in vertical text: its vertical form when
    the font has one."""
    v = VERTICAL.get(ch)
    return v if v and has_glyph(v) else ch
