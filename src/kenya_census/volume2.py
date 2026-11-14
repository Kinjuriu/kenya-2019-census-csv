"""Volume II: population, households, land area and density by administrative unit.

Tables 2.2 (county; 2.2a rural, 2.2b urban), 2.3 (sub-county) and 2.4 (down to sub-location). In each
table the level of a row (county, sub-county, ...) is shown only by its indent, so we read it from the
x position of the name. Positions were measured from the PDF and are listed in each TableSpec.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pdfplumber

from .pdfrows import page_rows, to_number

VOLUME2 = 'data/raw/2019-Kenya-population-and-Housing-Census-Volume-2-Distribution-of-Population-by-Administrative-Units.pdf'
ORDER = ['national', 'county', 'subcounty', 'division', 'location', 'sublocation']
BASE_COLUMNS = ['total', 'male', 'female', 'households_total', 'households_conventional',
                'group_quarters', 'land_area_km2', 'density_per_km2']


@dataclass(frozen=True)
class TableSpec:
    table: str
    title: str
    pages: range                # 1-based PDF pages, end exclusive
    levels: dict                # x position of the name -> level
    name_right: float           # tokens starting left of this are the name
    columns: list
    header_last: str = 'Quarters'   # the last header line contains this word


TABLES = {
    '2.2': TableSpec('2.2', 'Population, households, land area and density by county', range(22, 23),
                     {55: 'national', 63: 'county'}, 145,
                     ['total', 'male', 'female', 'intersex'] + BASE_COLUMNS[3:]),
    '2.2a': TableSpec('2.2a', 'Rural population, households, land area and density by county', range(23, 24),
                      {55: 'national', 63: 'county'}, 145,
                      ['total', 'male', 'female', 'intersex'] + BASE_COLUMNS[3:]),
    '2.2b': TableSpec('2.2b', 'Urban population, households, land area and density by county', range(24, 25),
                      {55: 'national', 63: 'county'}, 145,
                      ['total', 'male', 'female', 'intersex'] + BASE_COLUMNS[3:]),
    '2.3': TableSpec('2.3', 'Population, households, land area and density by sub-county', range(25, 32),
                     {54: 'national', 62: 'county', 69: 'subcounty'}, 180, BASE_COLUMNS),
    '2.4': TableSpec('2.4', 'Population, households, land area and density by sub-location', range(32, 252),
                     {44: 'national', 51: 'county', 58: 'subcounty', 65: 'division', 72: 'location',
                      80: 'sublocation'}, 185, BASE_COLUMNS),
}


def level_of(spec: TableSpec, x0: float):
    for x, name in spec.levels.items():
        if abs(x0 - x) <= 2.5:
            return name
    return None


def parse_rows(pdf, spec: TableSpec):
    """Yield one record per data row: page, level, name and the table's values."""
    pending = None
    for pn in spec.pages:
        rows = page_rows(pdf.pages[pn - 1], pn)
        header_end = max(i for i, r in enumerate(rows) if spec.header_last in r.text)
        for r in rows[header_end + 1:]:
            if r.text.startswith('*') or r.text.startswith('Source') or r.text.startswith('Note'):
                continue
            if len(r.tokens) == 1 and r.tokens[0].text.isdigit():    # printed page number
                continue
            # The last len(columns) tokens are the values and everything before them is the name, so a name
            # may contain a dash ("BILBUR - BOR"). A row with no number column at all is a name whose
            # numbers sit on the next line.
            n = len(spec.columns)
            in_number_columns = [t for t in r.tokens if t.x0 >= spec.name_right]
            if not in_number_columns:
                names, values = r.tokens, []
            elif len(r.tokens) >= n:
                names = r.tokens[:-n]
                values = [to_number(t.text) for t in r.tokens[-n:]]
            else:
                raise ValueError(f'table {spec.table} page {pn}: expected {n} values: {r.text}')
            if any(v is None for v in values):
                raise ValueError(f'table {spec.table} page {pn}: text in a number column: {r.text}')
            name = ' '.join(t.text for t in names)
            if names and not values:
                pending = (names[0].x0, name)      # name on its own line, numbers on the next
                continue
            if values and not names:
                if pending is None:
                    raise ValueError(f'table {spec.table} page {pn}: numbers without a name: {r.text}')
                x0, name = pending
            else:
                x0 = names[0].x0
            pending = None
            level = level_of(spec, x0)
            if level is None:
                raise ValueError(f'table {spec.table} page {pn}: unknown indent {x0:.1f}: {r.text}')
            if len(values) != len(spec.columns):
                raise ValueError(f'table {spec.table} page {pn}: expected {len(spec.columns)} values, '
                                 f'got {len(values)}: {r.text}')
            yield {'page': pn, 'level': level, 'name': name, **dict(zip(spec.columns, values))}


def add_hierarchy(df: pd.DataFrame, spec: TableSpec) -> pd.DataFrame:
    """Fill the parent units of every row from the rows above it."""
    levels = [lvl for lvl in ORDER if lvl in spec.levels.values()]
    parents = [lvl for lvl in levels if lvl != 'national'][:-1]
    current = dict.fromkeys(parents)
    out = []
    for rec in df.to_dict('records'):
        depth = ORDER.index(rec['level'])
        for lvl in parents:
            if ORDER.index(lvl) >= depth:
                current[lvl] = None
        out.append({**current, **rec})
        if rec['level'] in current:
            current[rec['level']] = rec['name']
    res = pd.DataFrame(out)
    return res[['level'] + parents + ['name'] + spec.columns + ['page']]


def extract(table: str, pdf_path=VOLUME2) -> pd.DataFrame:
    spec = TABLES[table]
    with pdfplumber.open(pdf_path) as pdf:
        df = pd.DataFrame(parse_rows(pdf, spec))
    return add_hierarchy(df, spec)


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'data/csv')
    out.mkdir(parents=True, exist_ok=True)
    for t in TABLES:
        df = extract(t)
        df.to_csv(out / f'v2_table_{t}.csv', index=False)
        print(t, len(df), df['level'].value_counts().to_dict())
