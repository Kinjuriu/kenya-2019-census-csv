"""Build every CSV in data/csv from the three KNBS PDFs in data/raw, run the checks and write data/csv/checks.txt.

    uv run python -m kenya_census.build
"""
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import checks, errata, school_age, volume2, volume3, volume4

OUT = Path('data/csv')
PDFS = {
    'Volume II': (volume2.VOLUME2, '4e4e091a67eddebc7c1158d09c02f4470e10786a269443dde97a4fcc17a4872d'),
    'Volume III': (volume3.VOLUME3, 'dc1253195cd766e42e0af6461fc20e2797ef9831301369bfc8942aee891cbb49'),
    'Volume IV': (volume4.VOLUME4, '56d36d0929299d422249bc843156bb9990a5d29b87dd50e017322a627d492ab2'),
}
ATTENDANCE = ['at_school', 'left_after_completion', 'left_before_completion', 'never_attended', 'dont_know', 'not_stated']
LEVELS_23 = ['pre_primary', 'primary', 'secondary', 'tvet', 'university', 'adult_basic_education', 'madrasa_duksi',
             'dont_know', 'not_stated']
AGE_GROUPS_NO_OVERLAP = ['age_3-5', 'age_6-13', 'age_14-17', 'age_18-22', 'age_23+', 'age_not_stated']


def volume4_checks(v4: dict, v2_county: pd.DataFrame, v2_sub: pd.DataFrame, v3: pd.DataFrame) -> dict:
    a, b, c, d = v4['2.2'], v4['2.3'], v4['2.6b'], v4['2.12']
    intersex = dict(zip(v2_county['name'], v2_county['intersex']))
    r = {
        'Volume IV 2.2: attendance statuses add up to the total': checks.parts_equal_total(a, 'total', ATTENDANCE, '2.2'),
        'Volume IV 2.2: printed per cent = count / total (0.05 tolerance)': checks.percent_matches_count(
            a, 'total', [(x, x + '_pct') for x in ATTENDANCE[:-1]], '2.2'),
        'Volume IV 2.2: Kenya male + female + intersex and rural + urban = all; below Kenya the gap is intersex':
            checks.sexes_equal_all(a, ['total'] + ATTENDANCE, '2.2', intersex),
        'Volume IV 2.2: every county equals the sum of its sub-counties': checks.county_equals_subcounties(
            a, ['total'] + ATTENDANCE, '2.2'),
        'Volume IV 2.3: levels add up to the total attending': checks.parts_equal_total(b, 'total_attending', LEVELS_23, '2.3'),
        'Volume IV 2.3: Kenya male + female + intersex and rural + urban = all; below Kenya the gap is intersex':
            checks.sexes_equal_all(b, ['total_attending'] + LEVELS_23, '2.3', intersex),
        'Volume IV 2.3: every county equals the sum of its sub-counties': checks.county_equals_subcounties(
            b, ['total_attending'] + LEVELS_23, '2.3'),
        'Volume IV 2.3 total attending = 2.2 at school': checks.matches(
            a, b, ['level', 'county', 'name', 'breakdown'], [('at_school', 'total_attending')], '2.2 vs 2.3'),
        'Volume IV 2.12: households equal Volume II conventional households (counties)': checks.matches(
            d[(d.level == 'county')][['name', 'conventional_households']], v2_county[['name', 'households_conventional']],
            ['name'], [('conventional_households', 'households_conventional')], '2.12 vs Volume II'),
        'Volume IV 2.12: roofing percentages sum to 100 (0.5 tolerance; rows with households)': checks.percents_sum_to_100(
            d[d.conventional_households > 0], [x for x in d.columns if x.endswith('_pct')], '2.12', 0.5),
        'Volume IV aged 3+ never exceeds Volume III aged 3+': checks.volume4_within_volume3(a, v3)[0],
    }
    ds = d[d.level == 'subcounty'][['county', 'name', 'conventional_households']].assign(name=lambda x: checks.norm_name(x['name']))
    vs = v2_sub[['county', 'name', 'households_conventional']].assign(name=lambda x: checks.norm_name(x['name']))
    vs = vs[vs.households_conventional > 0]
    r['Volume IV 2.12: households equal Volume II conventional households (sub-counties with households)'] = checks.matches(
        ds[ds.conventional_households > 0], vs, ['county', 'name'],
        [('conventional_households', 'households_conventional')], '2.12 vs Volume II')
    for sx in ('total', 'male', 'female'):
        r[f'Volume IV 2.6b: statuses add up to the total ({sx})'] = checks.parts_equal_total(
            c, f'total_{sx}', [f'{x}_{sx}' for x in ATTENDANCE], '2.6b')
        br = 'all' if sx == 'total' else sx
        left = a[(a.level == 'county') & (a.breakdown == br)][['name', 'total'] + ATTENDANCE]
        right = c[c.breakdown == 'all'].rename(columns={f'{x}_{sx}': x for x in ['total'] + ATTENDANCE})[['name', 'total'] + ATTENDANCE]
        r[f'Volume IV 2.6b county rows = 2.2 county rows ({sx})'] = checks.matches(
            left, right, ['name'], [(x, x) for x in ['total'] + ATTENDANCE], '2.6b vs 2.2')
    cols = [x for x in c.columns if x.endswith(('_total', '_male', '_female'))]
    grp = c[c.breakdown.isin(AGE_GROUPS_NO_OVERLAP)].groupby('name')[cols].sum()
    alls = c[c.breakdown == 'all'].set_index('name')[cols].loc[grp.index]
    r['Volume IV 2.6b: age groups 3-5, 6-13, 14-17, 18-22, 23+ and not stated add up to the county row'] = [
        f'2.6b: {n}: {col} groups sum to {grp.at[n, col]:,} but county row {alls.at[n, col]:,}'
        for n in grp.index for col in cols if grp.at[n, col] != alls.at[n, col]]
    return r


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def whole_numbers_as_int(df: pd.DataFrame) -> pd.DataFrame:
    """Columns that hold only whole numbers (with gaps for '..') are written as 10033, not 10033.0."""
    df = df.copy()
    for c in df.select_dtypes('float').columns:
        v = df[c].dropna()
        if len(v) and (v == v.round()).all():
            df[c] = df[c].astype('Int64')
    return df


def write(df: pd.DataFrame, name: str):
    whole_numbers_as_int(df).to_csv(OUT / name, index=False)


def main() -> int:
    for vol, (path, expected) in PDFS.items():
        if not Path(path).exists():
            sys.exit(f'Missing {path}. See data/raw/README.md for where to download {vol}.')
        if sha256(path) != expected:
            print(f'Warning: {path} is not the file this repository was built from (SHA-256 differs).')

    OUT.mkdir(parents=True, exist_ok=True)
    t = {k: volume2.extract(k) for k in volume2.TABLES}
    v3, skipped = volume3.extract_table_23(v2_23=t['2.3'])
    v4, stray = {}, []
    for k in volume4.TABLES:
        v4[k], s = volume4.extract(k)
        stray += s

    report = [f'Checks run {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC', '']
    results = {
        'Volume II national total is 47,564,296': checks.national_total(t['2.4']),
        'Volume II 2.4: every unit equals the sum of the units below it (as printed)': checks.children_sum_to_parent(t['2.4']),
        'Volume II 2.3: every county equals the sum of its sub-counties': checks.children_sum_to_parent(t['2.3']),
        'Volume II 2.2 and 2.3 counties agree': checks.same_values(t['2.2'], t['2.3'], 'county', '2.2 vs 2.3'),
        'Volume II 2.3 and 2.4 counties agree': checks.same_values(t['2.3'], t['2.4'], 'county', '2.3 vs 2.4'),
        'Volume II 2.3 and 2.4 sub-counties agree': checks.same_values(t['2.3'], t['2.4'], 'subcounty', '2.3 vs 2.4'),
        'Volume II 2.2a rural + 2.2b urban = 2.2 total': checks.rural_plus_urban(t['2.2'], t['2.2a'], t['2.2b']),
        'Volume III ages add up (as printed)': checks.ages_add_up(v3),
    }

    # Apply the documented corrections, then check again.
    t24 = errata.apply_volume2_24(t['2.4'])
    v3c = errata.apply_volume3_23(v3)
    results['Volume II 2.4 after errata'] = checks.children_sum_to_parent(t24.drop(columns='note'))
    results['Volume III after errata'] = checks.ages_add_up(v3c.assign(source_note=''))
    v2_county = t['2.2'][t['2.2'].level == 'county']
    v2_sub = t['2.3'][t['2.3'].level == 'subcounty']
    results.update(volume4_checks(v4, v2_county, v2_sub, v3c))

    for name, problems in results.items():
        report.append(f"{'PASS' if not problems else f'{len(problems)} issue(s)'}  {name}")
        report += [f'      {p}' for p in problems]
    report += ['', 'Volume II sub-counties with no page in Volume III:'] + [f'      {s}' for s in skipped]
    report += ['', 'Volume IV rows with numbers but no label (printing artefacts, left out):'] + [
        f"      table {x['table']} page {x['page']}: {x['printed']}" for x in stray]
    report += ['', 'Issues in the printed tables that remain after errata are listed in known_issues.csv.']
    (OUT / 'checks.txt').write_text('\n'.join(report) + '\n')
    print('\n'.join(report))

    write(t['2.2'][t['2.2'].level == 'county'].drop(columns='level'), 'kenya_2019_census_population_by_county.csv')
    for k, label in (('2.2a', 'rural'), ('2.2b', 'urban')):
        write(t[k][t[k].level == 'county'].drop(columns='level'), f'kenya_2019_census_{label}_population_by_county.csv')
    write(t['2.3'][t['2.3'].level == 'subcounty'].drop(columns='level'), 'kenya_2019_census_population_by_subcounty.csv')
    write(t24, 'kenya_2019_census_population_all_admin_levels.csv')
    write(t24[t24.level == 'sublocation'].drop(columns='level'), 'kenya_2019_census_population_by_sublocation.csv')
    write(v3c, 'kenya_2019_census_population_by_age_sex_county_subcounty.csv')
    write(school_age.school_age(v3c), 'kenya_2019_census_school_age_population_by_county_subcounty.csv')
    write(v4['2.2'], 'kenya_2019_census_school_attendance_by_county_subcounty.csv')
    write(v4['2.3'], 'kenya_2019_census_school_attendance_by_education_level_county_subcounty.csv')
    write(v4['2.6b'].drop(columns=['level', 'county']).rename(columns={'name': 'county'}), 'kenya_2019_census_school_attendance_by_age_group_county.csv')
    write(v4['2.12'], 'kenya_2019_census_roofing_material_by_county_subcounty.csv')
    write(checks.volume4_within_volume3(v4['2.2'], v3c)[1], 'volume4_vs_volume3_aged_3_plus.csv')
    write(errata.errata_table(), 'errata.csv')
    write(errata.known_issues_table(), 'known_issues.csv')

    unresolved = results['Volume II 2.4 after errata'] or results['Volume II national total is 47,564,296']
    return 1 if unresolved else 0


if __name__ == '__main__':
    sys.exit(main())
