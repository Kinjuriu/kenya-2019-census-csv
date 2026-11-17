"""Independent check: every extracted row must appear in pdfplumber's plain-text output of the same page.

The extractor rebuilds rows from character positions; extract_text() is a separate code path. We compare
with all spaces removed, because extract_text() splits some numbers ('1 ,361').
"""
import math
import re
from functools import lru_cache

import pandas as pd
import pdfplumber
import pytest

from kenya_census import volume2, volume3

CSV = 'data/csv'


@lru_cache(maxsize=None)
def page_text(pdf_path, page):
    with pdfplumber.open(pdf_path) as pdf:
        return ''.join((pdf.pages[page - 1].extract_text() or '').split())


def fmt(v):
    if isinstance(v, float) and math.isnan(v):
        return '..'
    if isinstance(v, float) and not v.is_integer():
        return f'{v}'
    return '-' if v == 0 else f'{int(v):,}'


def test_volume2_rows_in_plain_text():
    df = pd.read_csv(f'{CSV}/kenya_2019_census_population_all_admin_levels.csv')
    df = df[df['note'].isna()]
    missing = []
    for r in df.itertuples():
        nums = [r.total, r.male, r.female, r.households_total, r.households_conventional, r.group_quarters]
        needle = ''.join(r.name.split()) + ''.join(fmt(v) for v in nums)
        if needle not in page_text(volume2.VOLUME2, r.page):
            missing.append(f'page {r.page} {r.name}')
    assert not missing, f'{len(missing)} rows not found, first: {missing[:5]}'


def test_volume3_rows_in_plain_text():
    df = pd.read_csv(f'{CSV}/kenya_2019_census_population_by_age_sex_county_subcounty.csv',
                     keep_default_na=False, na_values=[''])
    df = df[df['note'].isna() & (df.age_kind == 'single')]
    # Some pages print numbers without thousands separators ('1030') or zero as '0', '-' or '_'.
    missing = []
    for r in df.itertuples():
        text = page_text(volume3.VOLUME3, r.page).replace(',', '').replace('_', '-')
        pattern = re.escape(r.age) + ''.join('(?:-|0)' if v == 0 else str(int(v)) for v in (r.male, r.female, r.total))
        if not re.search(pattern, text):
            missing.append(f'page {r.page} {r.area} age {r.age}')
    assert not missing, f'{len(missing)} of {len(df)} rows not found, first: {missing[:5]}'


V4_FILES = {
    'kenya_2019_census_school_attendance_by_county_subcounty.csv': 'total',
    'kenya_2019_census_school_attendance_by_education_level_county_subcounty.csv': 'total_attending',
    'kenya_2019_census_school_attendance_by_age_group_county.csv': 'total_total',
    'kenya_2019_census_roofing_material_by_county_subcounty.csv': 'conventional_households',
}
LABELS = {'male': 'Male', 'female': 'Female', 'intersex': 'Intersex', 'rural': 'Rural', 'urban': 'Urban'}


def v4_cell(v, is_pct):
    """Zero prints as '-' (or '0', '0.0'); per cents with one decimal; counts with thousands separators."""
    if v == 0:
        return r'(?:-|0|0\.0)'
    return re.escape(f'{v:.1f}' if is_pct else f'{int(v):,}')


def test_volume4_rows_in_plain_text():
    from kenya_census import volume4
    missing, n = [], 0
    for name, first in V4_FILES.items():
        df = pd.read_csv(f'{CSV}/{name}')
        cols = list(df.columns[df.columns.get_loc(first):df.columns.get_loc('page')])
        label_col = 'county' if 'age_group' in name else 'name'
        for r in df.itertuples(index=False):
            r = r._asdict()
            b = r['breakdown']
            label = r[label_col] if b == 'all' else LABELS.get(b, b.replace('age_', '').replace('_', ' ').title()
                                                               if b == 'age_not_stated' else b.replace('age_', ''))
            pattern = re.escape(''.join(str(label).split())) + ''.join(
                v4_cell(r[c], c.endswith('_pct')) for c in cols)
            n += 1
            if not re.search(pattern, page_text(volume4.VOLUME4, r['page'])):
                missing.append(f"{name} page {r['page']} {label} {b}")
    assert not missing, f'{len(missing)} of {n} rows not found, first: {missing[:5]}'
