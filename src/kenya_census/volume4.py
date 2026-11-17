"""Volume IV: school attendance, level of schooling and roofing material, by county and sub-county.

Tables 2.2 (school attendance status, people aged 3 and over), 2.3 (people attending now, by level),
2.6b (school attendance by special age groups, county only) and 2.12 (conventional households by roofing
material, in per cent). Each unit row (Kenya, county, sub-county) is followed by breakdown rows (Male,
Female, and for Kenya also Rural, Urban, Intersex; in 2.6b the age groups). The level of a unit row is
read from its indent, as in Volume II.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pdfplumber

from .pdfrows import page_rows, to_number

VOLUME4 = 'data/raw/2019-Kenya-population-and-Housing-Census-Volume-4-Distribution-of-Population-by-Socio-Economic-Characteristics.pdf'
BREAKDOWNS = {'Male': 'male', 'Female': 'female', 'Intersex': 'intersex', 'Rural': 'rural', 'Urban': 'urban'}
STATUS = ['total', 'at_school', 'left_after_completion', 'left_before_completion', 'never_attended',
          'dont_know', 'not_stated']


@dataclass(frozen=True)
class TableSpec:
    table: str
    pages: range                 # 1-based PDF pages, end exclusive
    header_last: str             # the last header line contains this text
    levels: list                 # (x position, level) for unit rows
    columns: list
    age_groups: bool = False     # breakdown rows are age groups (table 2.6b)


TABLES = {
    '2.2': TableSpec('2.2', range(27, 57), 'Number', [(55, 'county'), (62, 'subcounty')],
                     ['total', 'at_school', 'at_school_pct', 'left_after_completion', 'left_after_completion_pct',
                      'left_before_completion', 'left_before_completion_pct', 'never_attended',
                      'never_attended_pct', 'dont_know', 'dont_know_pct', 'not_stated']),
    '2.3': TableSpec('2.3', range(57, 88), 'TVET', [(55, 'county'), (62, 'subcounty')],
                     ['total_attending', 'pre_primary', 'primary', 'secondary', 'tvet', 'university',
                      'adult_basic_education', 'madrasa_duksi', 'dont_know', 'not_stated']),
    '2.6b': TableSpec('2.6b', range(151, 173), 'Total Male Female', [(22, 'county')],
                      [f'{s}_{x}' for s in STATUS for x in ('total', 'male', 'female')], age_groups=True),
    '2.12': TableSpec('2.12', range(278, 290), 'Stated', [(54, 'national'), (62, 'county'), (69, 'subcounty'),
                                                           (73, 'subcounty')],
                      ['conventional_households', 'grass_twigs_pct', 'makuti_thatch_pct', 'dung_mud_pct',
                       'iron_sheets_pct', 'tin_cans_pct', 'asbestos_sheet_pct', 'concrete_cement_pct', 'tiles_pct',
                       'canvas_tents_pct', 'decra_versatile_pct', 'nylon_cartons_cardboard_pct', 'shingles_pct',
                       'not_stated_pct']),
}


@dataclass
class Parsed:
    rows: list = field(default_factory=list)
    stray: list = field(default_factory=list)    # rows with numbers but no label: printing artefacts


def split(row, n):
    """Return (label tokens, values) where values are the trailing numeric tokens."""
    k = 0
    for t in reversed(row.tokens):
        if to_number(t.text) is None:
            break
        k += 1
    return row.tokens[:len(row.tokens) - k], [to_number(t.text) for t in row.tokens[len(row.tokens) - k:]]


def unit_level(spec, x0):
    for x, level in spec.levels:
        if abs(x0 - x) <= 2.5:
            return level
    return None


def parse(pdf, spec: TableSpec) -> Parsed:
    out = Parsed()
    county = subcounty = None
    for pn in spec.pages:
        rows = page_rows(pdf.pages[pn - 1], pn)
        header_end = max(i for i, r in enumerate(rows) if spec.header_last in r.text)
        for r in rows[header_end + 1:]:
            if r.text.startswith('*') or r.text.startswith('Source'):
                continue
            label_tokens, values = split(r, len(spec.columns))
            label = ' '.join(t.text for t in label_tokens)
            if not label and len(values) == 1:
                continue                                  # printed page number
            if not label:
                out.stray.append({'table': spec.table, 'page': pn, 'printed': r.text})
                continue
            if len(values) != len(spec.columns):
                raise ValueError(f'table {spec.table} page {pn}: expected {len(spec.columns)} values, '
                                 f'got {len(values)}: {r.text}')
            if label in BREAKDOWNS:
                breakdown = BREAKDOWNS[label]
            elif spec.age_groups and (label[0].isdigit() or label == 'Not Stated'):
                breakdown = 'age_' + label.replace(' ', '_').lower()
            else:
                breakdown = 'all'
                level = 'national' if label == 'KENYA' else unit_level(spec, label_tokens[0].x0)
                if level is None:
                    raise ValueError(f'table {spec.table} page {pn}: unknown indent {label_tokens[0].x0:.1f}: {r.text}')
                if level == 'national':
                    county = subcounty = None
                elif level == 'county':
                    county, subcounty = label, None
                else:
                    subcounty = label
                unit = (level, county, label)
            level, unit_county, name = unit
            out.rows.append({'level': level, 'county': unit_county if level == 'subcounty' else
                             (name if level == 'county' else None), 'name': name, 'breakdown': breakdown,
                             **dict(zip(spec.columns, values)), 'page': pn})
    return out


def extract(table: str, pdf_path=VOLUME4) -> tuple[pd.DataFrame, list]:
    spec = TABLES[table]
    with pdfplumber.open(pdf_path) as pdf:
        p = parse(pdf, spec)
    return pd.DataFrame(p.rows), p.stray


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'data/csv')
    out.mkdir(parents=True, exist_ok=True)
    for t in TABLES:
        df, stray = extract(t)
        df.to_csv(out / f'v4_table_{t}.csv', index=False)
        print(t, len(df), df.groupby(['level', 'breakdown']).size().to_dict(), 'stray rows:', stray)
