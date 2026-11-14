"""Turn a PDF page into rows of tokens using character positions.

KNBS typesets its tables with fixed column positions. Plain text extraction sometimes splits a number
("1 ,361"), so we rebuild tokens from the characters themselves: characters closer than GAP points belong
to the same token. Each row keeps the x position of every token, which tells us both the column of a
number and the indent (administrative level) of a name.
"""
from dataclasses import dataclass, field

GAP = 1.0        # points between characters inside one token
ROW_TOL = 2.0    # names and numbers of one row can sit up to this far apart vertically


@dataclass
class Token:
    x0: float
    x1: float
    text: str
    bold: bool


@dataclass
class Row:
    page: int        # 1-based page number in the PDF
    top: float
    tokens: list[Token] = field(default_factory=list)

    @property
    def text(self) -> str:
        return ' '.join(t.text for t in self.tokens)


def page_rows(page, page_number: int) -> list[Row]:
    chars = [c for c in page.chars if c['text'].strip()]
    chars.sort(key=lambda c: (c['top'], c['x0']))
    lines: list[list[dict]] = []
    for c in chars:
        if lines and abs(lines[-1][0]['top'] - c['top']) <= ROW_TOL:
            lines[-1].append(c)
        else:
            lines.append([c])
    rows = []
    for line in lines:
        line.sort(key=lambda c: c['x0'])
        row = Row(page=page_number, top=min(c['top'] for c in line))
        prev = None
        for c in line:
            bold = 'Bold' in c['fontname']
            if prev is None or c['x0'] - prev['x1'] > GAP:
                row.tokens.append(Token(c['x0'], c['x1'], c['text'], bold))
            else:
                t = row.tokens[-1]
                t.text += c['text']
                t.x1 = c['x1']
                t.bold = t.bold and bold
            prev = c
        rows.append(row)
    return rows


def to_number(s: str):
    """KNBS cells: '13,394' -> 13394, '13.4' -> 13.4, '-' or '_' -> 0, '..' (not computed) -> NaN.
    Anything else (a name) -> None."""
    s = s.strip()
    if s in {'-', '–', '_'}:
        return 0
    if s == '..':
        return float('nan')
    s2 = s.replace(',', '')
    try:
        return int(s2)
    except ValueError:
        pass
    try:
        return float(s2)
    except ValueError:
        return None
