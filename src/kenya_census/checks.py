"""Checks that the extracted tables add up. Every check returns a list of problems (empty means it passed)."""
import pandas as pd

ORDER = ['national', 'county', 'subcounty', 'division', 'location', 'sublocation']
SUMMED = ['total', 'male', 'female', 'households_total', 'households_conventional', 'group_quarters']
KENYA_TOTAL = 47_564_296   # Volume II table 1.1 and table 2.2


def children_sum_to_parent(df: pd.DataFrame) -> list[str]:
    """Each unit's values should equal the sum of the units one level below it (levels present in this table)."""
    problems = []
    order = [lvl for lvl in ORDER if lvl in set(df['level'])]
    rows = df.to_dict('records')
    for i, parent in enumerate(rows):
        depth = order.index(parent['level'])
        if depth == len(order) - 1:
            continue
        child_level = order[depth + 1]
        sums = dict.fromkeys(SUMMED, 0)
        n = 0
        for r in rows[i + 1:]:
            d = order.index(r['level'])
            if d <= depth:
                break
            if r['level'] == child_level:
                n += 1
                for c in SUMMED:
                    sums[c] += r[c]
        if n == 0:
            problems.append(f"{parent['level']} {parent['name']} (page {parent['page']}) has no {child_level} rows")
            continue
        for c in SUMMED:
            if sums[c] != parent[c]:
                problems.append(f"{parent['level']} {parent['name']} (page {parent['page']}): {c} {parent[c]:,} but its "
                                f"{n} {child_level} rows sum to {sums[c]:,}")
    return problems


def national_total(df: pd.DataFrame) -> list[str]:
    total = int(df.loc[df.level == 'national', 'total'].iloc[0])
    return [] if total == KENYA_TOTAL else [f'national total {total:,}, expected {KENYA_TOTAL:,}']


def sex_adds_up(df: pd.DataFrame) -> list[str]:
    """Total can exceed male + female by the intersex count, which KNBS shows only nationally (footnote *)."""
    bad = df[(df.male + df.female > df.total) | (df.total - df.male - df.female > 1000)]
    return [f"{r.level} {r['name']} (page {r.page}): total {r.total:,}, male + female {r.male + r.female:,}"
            for _, r in bad.iterrows()]


def same_values(a: pd.DataFrame, b: pd.DataFrame, level: str, label: str,
                cols=('total', 'male', 'female', 'households_total', 'households_conventional', 'group_quarters')) -> list[str]:
    """Rows of one level in two tables should match one to one, in order (names may be abbreviated differently)."""
    a, b = a[a.level == level].reset_index(drop=True), b[b.level == level].reset_index(drop=True)
    if len(a) != len(b):
        return [f'{label}: {len(a)} {level} rows against {len(b)}']
    problems = []
    for i in range(len(a)):
        for c in cols:
            if a.at[i, c] != b.at[i, c]:
                problems.append(f"{label}: {level} {a.at[i, 'name']} / {b.at[i, 'name']}: {c} {a.at[i, c]:,} against {b.at[i, c]:,}")
    return problems


def rural_plus_urban(total: pd.DataFrame, rural: pd.DataFrame, urban: pd.DataFrame) -> list[str]:
    problems = []
    for c in ('total', 'male', 'female', 'intersex', 'households_total'):
        s = rural[c].to_numpy() + urban[c].to_numpy()
        for name, t, v in zip(total['name'], total[c], s):
            if t != v:
                problems.append(f'2.2a + 2.2b: {name} {c} {t:,} but rural + urban = {v:,}')
    return problems


def ages_add_up(v3: pd.DataFrame) -> list[str]:
    """Volume III: single years + not stated = Total; each five-year group = its single years; Total = Male + Female."""
    problems = []
    for page, g in v3.groupby('page', sort=True):
        area = g['area'].iloc[0]
        tot = g[g.age_kind == 'total'].iloc[0]
        parts = g[g.age_kind.isin(['single', 'not_stated'])]
        single = g[g.age_kind == 'single'].set_index('age')
        for c in ('male', 'female', 'total'):
            s = parts[c].sum(min_count=1)
            if parts[c].notna().all() and s != tot[c]:
                problems.append(f'page {page} {area}: {c} Total {tot[c]:,.0f} but ages sum to {s:,.0f}')
        for _, grp in g[g.age_kind == 'group'].iterrows():
            lo, hi = map(int, grp['age'].split('-'))
            ages = [str(a) for a in range(lo, hi + 1)] if hi < 100 else []
            for c in ('male', 'female', 'total'):
                vals = single.loc[[a for a in ages if a in single.index], c]
                if len(vals) == hi - lo + 1 and pd.notna(grp[c]) and vals.notna().all() and vals.sum() != grp[c]:
                    problems.append(f"page {page} {area}: {c} age {grp['age']} {grp[c]:,.0f} but single years sum to {vals.sum():,.0f}")
        rows_bad = g[(g.male + g.female != g.total) & g[['male', 'female', 'total']].notna().all(axis=1)]
        problems += [f"page {page} {area}: age {r.age} male + female {r.male + r.female:,.0f} but total {r.total:,.0f}"
                     for _, r in rows_bad.iterrows()]
    return problems


# ---------- Volume IV ----------

def _fmt(v):
    return f'{v:,.0f}' if float(v).is_integer() else f'{v}'


def parts_equal_total(df: pd.DataFrame, total: str, parts: list, label: str) -> list[str]:
    s = df[parts].sum(axis=1)
    bad = df[s != df[total]]
    return [f"{label}: {r.level} {r['name']} {r.breakdown} (page {r.page}): {total} {_fmt(r[total])} "
            f"but parts sum to {_fmt(s[i])}" for i, r in bad.iterrows()]


def percent_matches_count(df: pd.DataFrame, total: str, pairs: list, label: str, tol=0.051) -> list[str]:
    problems = []
    for n, pct in pairs:
        calc = 100 * df[n] / df[total]
        bad = df[(df[total] > 0) & ((calc - df[pct]).abs() > tol)]
        problems += [f"{label}: {r.level} {r['name']} {r.breakdown} (page {r.page}): {pct} printed {r[pct]} "
                     f"but {n}/{total} = {calc[i]:.2f}" for i, r in bad.iterrows()]
    return problems


def sexes_equal_all(df: pd.DataFrame, cols: list, label: str, intersex_by_county: dict | None = None) -> list[str]:
    """Kenya: male + female + intersex = all, and rural + urban = all, exactly.

    Below national level intersex people are in the 'all' row but have no row of their own (KNBS footnote),
    so there the gap all - (male + female) must be 0 or more, and a county's gap in the total column can be no
    larger than its intersex count in Volume II table 2.2 (all ages).
    """
    problems = []
    for (level, county, name), g in df.groupby(['level', 'county', 'name'], dropna=False, sort=False):
        b = g.set_index('breakdown')
        if level == 'national':
            for grp in (['male', 'female', 'intersex'], ['rural', 'urban']):
                for c in cols:
                    if set(grp) <= set(b.index) and b.loc[grp, c].sum() != b.at['all', c]:
                        problems.append(f"{label}: Kenya: {c} all {_fmt(b.at['all', c])} but {' + '.join(grp)} = "
                                        f"{_fmt(b.loc[grp, c].sum())}")
            continue
        for c in cols:
            gap = b.at['all', c] - b.loc[['male', 'female'], c].sum()
            if gap < 0:
                problems.append(f'{label}: {level} {name}: {c} male + female exceeds all by {_fmt(-gap)}')
        if intersex_by_county is not None and level == 'county':
            gap = b.at['all', cols[0]] - b.loc[['male', 'female'], cols[0]].sum()
            if gap > intersex_by_county.get(name, 0):
                problems.append(f'{label}: county {name}: {_fmt(gap)} people not in male or female, more than its '
                                f'{intersex_by_county.get(name, 0)} intersex people in Volume II')
    return problems


def county_equals_subcounties(df: pd.DataFrame, cols: list, label: str) -> list[str]:
    problems = []
    sub = df[df.level == 'subcounty'].groupby(['county', 'breakdown'])[cols].sum()
    cty = df[df.level == 'county'].set_index(['name', 'breakdown'])[cols]
    for key, row in cty.iterrows():
        if key not in sub.index:
            problems.append(f'{label}: county {key[0]} has no sub-counties')
            continue
        for c in cols:
            if sub.at[key, c] != row[c]:
                problems.append(f'{label}: county {key[0]} {key[1]}: {c} {_fmt(row[c])} but sub-counties sum to '
                                f'{_fmt(sub.at[key, c])}')
    return problems


def percents_sum_to_100(df: pd.DataFrame, pct_cols: list, label: str, tol: float) -> list[str]:
    s = df[pct_cols].sum(axis=1)
    bad = df[(s - 100).abs() > tol]
    return [f"{label}: {r.level} {r['name']} {r.breakdown} (page {r.page}): percentages sum to {s[i]:.1f}"
            for i, r in bad.iterrows()]


def matches(a: pd.DataFrame, b: pd.DataFrame, keys: list, pairs: list, label: str) -> list[str]:
    """Rows of a and b with the same keys must have equal values in each (column in a, column in b) pair."""
    m = a.merge(b, on=keys, how='outer', suffixes=('_a', '_b'), indicator=True)
    problems = [f"{label}: {dict(zip(keys, r[keys]))} only in {'first' if r._merge == 'left_only' else 'second'} table"
                for _, r in m[m._merge != 'both'].iterrows()]
    m = m[m._merge == 'both']
    for ca, cb in pairs:
        xa, xb = (ca + '_a', cb + '_b') if ca == cb else (ca, cb)
        bad = m[m[xa] != m[xb]]
        problems += [f"{label}: {dict(zip(keys, r[keys]))}: {ca} {_fmt(r[xa])} against {cb} {_fmt(r[xb])}"
                     for _, r in bad.iterrows()]
    return problems


def norm_name(s: pd.Series) -> pd.Series:
    """Spellings differ between volumes ('MT. KENYA FOREST', 'MOUNT KENYA FOREST', 'LUNGALUNGA')."""
    return (s.str.replace('MOUNT ', 'MT ', regex=False).str.replace('.', '', regex=False)
            .str.replace(' ', '', regex=False))


def volume4_within_volume3(v4_22: pd.DataFrame, v3: pd.DataFrame) -> tuple[list[str], pd.DataFrame]:
    """Volume IV covers people aged 3 and over on the main questionnaire. It should never exceed Volume III's
    count of people aged 3 and over. Returns problems and the comparison table (for the README)."""
    s = v3[v3.age_kind == 'single'].copy()
    s['a'] = s['age'].str.replace('+', '', regex=False).astype(int)
    g = s[s.a >= 3].groupby(['level', 'county', 'name_volume2'])[['male', 'female']].sum().reset_index()
    g['key'] = norm_name(g['name_volume2'])
    g = g.drop(columns='county').assign(ckey=norm_name(g['county']))
    a = v4_22[v4_22.breakdown.isin(['male', 'female']) & (v4_22.level != 'national')]
    a = a.pivot_table(index=['level', 'county', 'name'], columns='breakdown', values='total').reset_index()
    a['key'] = norm_name(a['name'])
    a['ckey'] = norm_name(a['county'])
    m = a.merge(g, on=['level', 'ckey', 'key'], how='left', suffixes=('_v4', '_v3'))
    problems = [f"{r.level} {r['name']} has no Volume III match" for _, r in m[m.male_v3.isna()].iterrows()]
    for sx in ('male', 'female'):
        bad = m[m[f'{sx}_v4'] > m[f'{sx}_v3']]
        problems += [f"{r.level} {r['name']}: {sx} aged 3+ {r[f'{sx}_v4']:,.0f} in Volume IV, more than "
                     f"{r[f'{sx}_v3']:,.0f} in Volume III" for _, r in bad.iterrows()]
    m['male_gap'] = m.male_v3 - m.male_v4
    m['female_gap'] = m.female_v3 - m.female_v4
    return problems, m[['level', 'county', 'name', 'male_v4', 'male_v3', 'male_gap', 'female_v4', 'female_v3', 'female_gap']]
