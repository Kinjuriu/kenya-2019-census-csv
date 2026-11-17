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
    ('Volume IV', '2.2 and 2.3', 'KAKAMEGA (Butere), KIAMBU (Limuru, Thika West), WAJIR (Buna); Kenya rural and urban',
     '"At school" in table 2.2 and "total attending" in table 2.3 differ by 1 person in these units and their '
     'counties. Both are published as printed in their own tables.'),
    ('Volume IV', '2.3', 'pages 61 and 62 (Mandera)',
     'Two rows print "- 0 -" with no label. They are printing artefacts and are left out; the Mandera rows around '
     'them add up without them.'),
    ('Volume IV', '2.2, 2.3, 2.6b', 'all counties and sub-counties',
     'Below national level, intersex people are counted in the "all" rows but have no row of their own (KNBS '
     'footnote), so all can exceed male + female by a few people.'),
    ('Volume IV', 'all tables', 'all areas',
     'People aged 3 and over in Volume IV are 338,960 fewer (0.77 per cent) than in Volume III. The special '
     'population (travellers, outdoor sleepers, people in hotels, lodges, schools and hospitals) was counted on short '
     'questionnaires (Volume IV page 16), so Volume IV most likely covers people counted on the main questionnaire '
     'only. KNBS does not state this in one sentence; this is our reading. The gap by area is in '
     'volume4_vs_volume3_aged_3_plus.csv.'),
    ('Volume IV', '2.2 against Volume III', 'ISIOLO county and sub-county (male), MT. KENYA FOREST in Nyeri (male), '
     'NYAKACH (female)', 'Volume IV is 1 person higher than Volume III aged 3 and over. Left as printed.'),
    ('Volume IV', '2.12', 'all rows', 'Roofing percentages are rounded to one decimal place and can sum to 99.8 to '
     '100.2. Sub-counties with no households (forests) print "-" in every column.'),
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
