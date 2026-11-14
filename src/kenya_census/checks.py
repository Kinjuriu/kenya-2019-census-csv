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
