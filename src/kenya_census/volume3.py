"""Volume III, table 2.3: population by single year of age and sex, for every county and sub-county.

One area per page. The page holds two halves (ages 0 to 50 on the left; 51 to 100+ and 'Not Stated' on
the right), each with columns Age, Male, Female, Total. Five-year group rows ('0 - 4') sit between the
single years. County and sub-county pages look the same, so the level of each page is taken from the order
of Volume II table 2.3 (a county followed by its sub-counties) and checked against its male and female counts.
Intersex people are not in this table (KNBS footnote), so Total = Male + Female here.
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

from .pdfrows import page_rows, to_number
from . import volume2

VOLUME3 = 'data/raw/2019-Kenya-population-and-Housing-Census-Volume-3-Distribution-of-Population-by-Age-and-Sex.pdf'
TABLE_23_PAGES = range(30, 422)
SPLIT_X = 330          # left half / right half


def age_kind(label: str) -> str:
    if label == 'Total':
        return 'total'
    if label == 'Not Stated':
        return 'not_stated'
    if label == '100+':
        return 'single'          # open-ended last age
    if re.fullmatch(r'\d+', label):
        return 'single'
    if re.fullmatch(r'\d+-\d+', label):
        return 'group'
    raise ValueError(f'unknown age label {label!r}')


def parse_page(page, pn: int):
    rows = page_rows(page, pn)
    area = next(r for r in rows if r.tokens[0].bold and r.tokens[0].x0 < 80 and not r.text.startswith('Table'))
    header = next(i for i, r in enumerate(rows) if r.text.startswith('Age'))
    out = []
    for r in rows[header + 1:]:
        if r.text.startswith('*'):
            continue
        for half in ([t for t in r.tokens if t.x0 < SPLIT_X], [t for t in r.tokens if t.x0 >= SPLIT_X]):
            if not half:
                continue
            if len(half) < 4:
                raise ValueError(f'page {pn}: short row: {r.text}')
            label = re.sub(r'\s*-\s*', '-', ' '.join(t.text for t in half[:-3]))
            cells = [t.text for t in half[-3:]]
            values = [to_number(c) for c in cells]
            # A few cells were printed as dates ('15-Aug'): an error in the source PDF. Keep them as missing
            # and record the printed text; errata.py derives the value from the other columns.
            note = '; '.join(f'{col} printed as {c!r}' for col, c, v in zip(('male', 'female', 'total'), cells, values)
                             if v is None)
            values = [float('nan') if v is None else v for v in values]
            out.append({'area': area.text, 'age': label, 'age_kind': age_kind(label),
                        'male': values[0], 'female': values[1], 'total': values[2], 'page': pn,
                        'source_note': note})
    return out


def assign_levels(df: pd.DataFrame, v2_23: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Match pages, in order, to the county and sub-county rows of Volume II table 2.3.

    Each page is matched to the next Volume II unit with the same male and female counts. Volume II units
    that are passed over have no page in Volume III; they are returned so the README can list them.
    """
    units = v2_23[v2_23.level != 'national'].reset_index(drop=True)
    pages = df[df.age_kind == 'total'].reset_index(drop=True)
    page_info, skipped, j = {}, [], 0
    for _, p in pages.iterrows():
        start = j
        while j < len(units) and (units.at[j, 'male'], units.at[j, 'female']) != (p.male, p.female):
            j += 1
        if j == len(units):
            raise ValueError(f'page {p.page} {p.area}: no Volume II unit with male/female {p.male:,}/{p.female:,}')
        skipped += [f"{units.at[k, 'level']} {units.at[k, 'name']} ({units.at[k, 'county']}), "
                    f"{units.at[k, 'total']:,} people" for k in range(start, j)]
        u = units.loc[j]
        page_info[p.page] = {'level': u.level, 'county': u.county if u.level == 'subcounty' else u['name'],
                             'name_volume2': u['name']}
        j += 1
    skipped += [f"{units.at[k, 'level']} {units.at[k, 'name']} ({units.at[k, 'county']})" for k in range(j, len(units))]
    info = pd.DataFrame.from_dict(page_info, orient='index')
    df = df.join(info, on='page')
    cols = ['level', 'county', 'area', 'name_volume2', 'age', 'age_kind', 'male', 'female', 'total', 'page', 'source_note']
    return df[cols], skipped


def extract_table_23(pdf_path=VOLUME3, v2_23: pd.DataFrame | None = None) -> pd.DataFrame:
    with pdfplumber.open(pdf_path) as pdf:
        recs = [rec for pn in TABLE_23_PAGES for rec in parse_page(pdf.pages[pn - 1], pn)]
    df = pd.DataFrame(recs)
    if v2_23 is None:
        v2_23 = volume2.extract('2.3')
    return assign_levels(df, v2_23)


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'data/csv')
    out.mkdir(parents=True, exist_ok=True)
    v2 = pd.read_csv(out / 'v2_table_2.3.csv') if (out / 'v2_table_2.3.csv').exists() else None
    df, skipped = extract_table_23(v2_23=v2)
    print('Volume II units with no page in Volume III:', *skipped, sep='\n  ')
    df.to_csv(out / 'v3_table_2.3.csv', index=False)
    print(len(df), df.groupby('level')['page'].nunique().to_dict())
