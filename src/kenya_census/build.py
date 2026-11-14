"""Build every CSV in data/csv from the two KNBS PDFs in data/raw, run the checks and write data/csv/checks.txt.

    uv run python -m kenya_census.build
"""
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import checks, errata, school_age, volume2, volume3

OUT = Path('data/csv')
PDFS = {
    'Volume II': (volume2.VOLUME2, '4e4e091a67eddebc7c1158d09c02f4470e10786a269443dde97a4fcc17a4872d'),
    'Volume III': (volume3.VOLUME3, 'dc1253195cd766e42e0af6461fc20e2797ef9831301369bfc8942aee891cbb49'),
}


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

    for name, problems in results.items():
        report.append(f"{'PASS' if not problems else f'{len(problems)} issue(s)'}  {name}")
        report += [f'      {p}' for p in problems]
    report += ['', 'Volume II sub-counties with no page in Volume III:'] + [f'      {s}' for s in skipped]
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
    write(errata.errata_table(), 'errata.csv')
    write(errata.known_issues_table(), 'known_issues.csv')

    unresolved = results['Volume II 2.4 after errata'] or results['Volume II national total is 47,564,296']
    return 1 if unresolved else 0


if __name__ == '__main__':
    sys.exit(main())
