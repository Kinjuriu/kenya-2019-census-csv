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
