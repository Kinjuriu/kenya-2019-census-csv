"""School-age population by county and sub-county, from the single-year ages in Volume III table 2.3.

These are children of school age on census night (24/25 August 2019), counted where they lived. They are not
school enrolment or attendance figures. Bands follow the official entry ages of the Competency-Based
Curriculum (pre-primary from 4, Grade 1 at 6, Junior School at 12, Senior School at 15). The single-year
file lets anyone build other bands, for example the 8-4-4 system in place in 2019 (primary 6 to 13,
secondary 14 to 17).
"""
import pandas as pd

BANDS = {
    'pre_primary_4_5': (4, 5),
    'primary_6_11': (6, 11),
    'junior_school_12_14': (12, 14),
    'senior_school_15_17': (15, 17),
    'school_age_4_17': (4, 17),
}


def school_age(v3: pd.DataFrame) -> pd.DataFrame:
    single = v3[(v3.age_kind == 'single') & (v3.age != '100+')].copy()
    single['age_years'] = single['age'].astype(int)
    rows = []
    for (page, level, county, area), g in single.groupby(['page', 'level', 'county', 'name_volume2'], sort=False):
        total = v3[(v3.page == page) & (v3.age_kind == 'total')]['total'].iloc[0]
        rec = {'level': level, 'county': county, 'name': area, 'total_population': int(total)}
        for band, (lo, hi) in BANDS.items():
            sel = g[g.age_years.between(lo, hi)]
            for sex in ('male', 'female', 'total'):
                col = band if sex == 'total' else f'{band}_{sex}'
                rec[col] = int(sel[sex].sum())
        rec['school_age_4_17_share_pct'] = round(100 * rec['school_age_4_17'] / total, 1)
        rec['page_volume3'] = page
        rows.append(rec)
    return pd.DataFrame(rows)
