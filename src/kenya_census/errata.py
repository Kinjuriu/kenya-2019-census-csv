"""Known errors in the printed KNBS tables, and the value we publish in their place.

Each correction is derived from other numbers in the same report and the derivation is recorded, so anyone
can repeat it. Cells we could not correct with certainty are left as printed and listed in KNOWN_ISSUES.
"""
import pandas as pd

# (source, table, page, area, field, printed, corrected, how the corrected value was derived)
CORRECTIONS = [
    ('Volume II', '2.4', 32, 'location MIKINDANI (Jomvu, Mombasa)', 'male', '333', 31187,
     'Sum of its two sub-locations (Birikani 10,977 + Kwa Shee 20,210). With it, the Jomvu division also adds up '
     '(83,002). Total minus female gives 31,188; the 1-person gap is intersex, which KNBS shows only nationally.'),
    ('Volume III', '2.3', 185, 'sub-county MUKURWEINI (Nyeri), age 5-9', 'male', '15-Aug', 4611,
     'Total minus female (9,078 - 4,467), and equal to the sum of single years 5 to 9. The printed cell is a date.'),
    ('Volume III', '2.3', 185, 'sub-county MUKURWEINI (Nyeri), age 10-14', 'male', '23-Jun', 4923,
     'Total minus female (9,516 - 4,593), and equal to the sum of single years 10 to 14. The printed cell is a date.'),
]

KNOWN_ISSUES = [
    ('Volume II', '2.3 and 2.4', 'sub-counties MARIGAT and TIATY EAST (Baringo)',
     'Table 2.3 gives Marigat 90,955 and Tiaty East 73,424; table 2.4 gives 90,958 and 73,421. The Baringo total '
     'agrees. Both are published as printed in their own tables.'),
    ('Volume III', '2.3', 'sub-county MT. KENYA FOREST (Nyeri), page 187',
     'Male total 123 but single years sum to 122; age 10 male 1 + female 0 printed with total 2. Left as printed.'),
    ('Volume III', '2.3', 'sub-county KAKAMEGA FOREST (Kakamega), page 337',
     'Female age group 20-24 printed as 0 but single years 20 to 24 sum to 1. Left as printed.'),
    ('Volume III', '2.3', 'all areas',
     'Intersex people are excluded from the age tables (KNBS footnote), so totals here are male + female and can be '
     'slightly below Volume II.'),
    ('Volume III', '2.3', 'LAKE BARINGO, MAU FOREST (Kericho), TINDERET FOREST, MAU FOREST (Bomet)',
     'Sub-counties with 0 people have no page in Volume III.'),
]


def errata_table() -> pd.DataFrame:
    return pd.DataFrame(CORRECTIONS, columns=['source', 'table', 'page', 'area', 'field', 'printed', 'corrected', 'derivation'])


def known_issues_table() -> pd.DataFrame:
    return pd.DataFrame(KNOWN_ISSUES, columns=['source', 'table', 'area', 'issue'])


def apply_volume2_24(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['note'] = ''
    m = (df.level == 'location') & (df['name'] == 'MIKINDANI') & (df.page == 32)
    assert m.sum() == 1 and df.loc[m, 'male'].iloc[0] == 333
    df.loc[m, 'male'] = 31187
    df.loc[m, 'note'] = 'male corrected from printed 333 (see errata.csv)'
    return df


def apply_volume3_23(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['note'] = df['source_note'].fillna('')
    for age, value in (('5-9', 4611), ('10-14', 4923)):
        m = (df.page == 185) & (df.age == age)
        assert m.sum() == 1 and pd.isna(df.loc[m, 'male'].iloc[0])
        df.loc[m, 'male'] = value
        df.loc[m, 'note'] = df.loc[m, 'note'] + ' (corrected, see errata.csv)'
    return df.drop(columns='source_note')
