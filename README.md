# Kenya 2019 census data in CSV: population by county, sub-county, location and sub-location

The 2019 Kenya Population and Housing Census tables from the Kenya National Bureau of Statistics (KNBS), extracted from the official PDF reports into clean CSV files. Every number is checked against the report it came from.

The files cover all 47 counties:

- population, households, land area and density by **county**, **sub-county**, **division**, **location** and **sub-location** (8,932 sub-locations);
- population by **single year of age and sex** for every county and sub-county;
- **school-age children** by county and sub-county.

KNBS publishes these tables only as PDF reports. This repository turns them into files you can open in Excel, Python, R or QGIS.

## The files

All files are in [`data/csv/`](data/csv/). Names are as printed by KNBS, in capital letters.

| File | What it holds | Rows | Source |
|---|---|---|---|
| `kenya_2019_census_population_by_county.csv` | Population (total, male, female, intersex), households, land area and density for the 47 counties | 47 | Volume II, table 2.2 |
| `kenya_2019_census_rural_population_by_county.csv` | The same for the rural population | 47 | Volume II, table 2.2a |
| `kenya_2019_census_urban_population_by_county.csv` | The same for the urban population | 47 | Volume II, table 2.2b |
| `kenya_2019_census_population_by_subcounty.csv` | Population, households, land area and density by sub-county | 349 | Volume II, table 2.3 |
| `kenya_2019_census_population_by_sublocation.csv` | Population, households, land area and density by sub-location, with its county, sub-county, division and location | 8,932 | Volume II, table 2.4 |
| `kenya_2019_census_population_all_admin_levels.csv` | Table 2.4 in full: every level from Kenya down to sub-location, in KNBS order, with a `level` column | 14,167 | Volume II, table 2.4 |
| `kenya_2019_census_population_by_age_sex_county_subcounty.csv` | Male, female and total population by single year of age (0 to 100+), five-year group and "not stated", for every county and sub-county | 48,216 | Volume III, table 2.3 |
| `kenya_2019_census_school_age_population_by_county_subcounty.csv` | Children of school age by county and sub-county, by sex, in the bands below | 392 | Built from Volume III, table 2.3 |
| `errata.csv` | Printing errors in the KNBS tables that this repository corrects, with the evidence | 3 | |
| `known_issues.csv` | Small inconsistencies in the KNBS tables left as printed | 5 | |
| `checks.txt` | Output of every check from the last build | | |

Every row has a `page` column with the page of the PDF it came from, so you can look it up.

### Columns

- `total`, `male`, `female`: people counted on census night, 24 to 25 August 2019. KNBS shows intersex people (1,524 in Kenya) only at national and county level, so below county level `total` can be slightly larger than `male + female`.
- `households_total`, `households_conventional`, `group_quarters`: households, as defined by KNBS. Group quarters are places such as hostels, barracks and prisons.
- `land_area_km2`: land area in square kilometres. Table 2.3 prints whole numbers; table 2.4 prints one decimal place.
- `density_per_km2`: persons per square kilometre, as printed. Empty where KNBS printed "..".
- `note`: filled where a value was corrected (see `errata.csv`).

### School-age bands

The school-age file counts children by age on census night, where they lived. **These are not enrolment or attendance figures.** The bands follow the entry ages of the Competency-Based Curriculum:

| Column | Ages |
|---|---|
| `pre_primary_4_5` | 4 to 5 |
| `primary_6_11` | 6 to 11 (Grades 1 to 6) |
| `junior_school_12_14` | 12 to 14 (Grades 7 to 9) |
| `senior_school_15_17` | 15 to 17 (Grades 10 to 12) |
| `school_age_4_17` | 4 to 17 |

In 2019 Kenya still ran the 8-4-4 system. To build other bands, sum the single years in the age file.

The counts describe 2019. A child aged 4 in 2019 is about 11 in 2026, so for later years these counts need projecting forward.

## Administrative units are not electoral wards

The census counts people by **administrative units**: county, sub-county, division, location and sub-location. These are different from the **IEBC constituencies and wards** used for elections. In Nairobi, for example, the census has 11 sub-counties, while there are 17 constituencies and 85 wards. Census sub-location totals cannot be matched to wards without boundary maps of both.

## How the numbers were checked

The build stops or reports if any of these fail. The results of the last run are in [`data/csv/checks.txt`](data/csv/checks.txt).

1. The national total is 47,564,296, as published.
2. In table 2.4, every county, sub-county, division and location equals the sum of the units below it.
3. County totals agree between tables 2.2, 2.3 and 2.4, and sub-county totals agree between tables 2.3 and 2.4.
4. Rural plus urban population equals the total for every county.
5. In Volume III, every page matches a Volume II county or sub-county exactly on male and female counts; the single years add up to the total; each five-year group equals its single years.
6. An independent test (`tests/`) finds every extracted row in the PDF's plain text, read by a separate method: all 14,167 Volume II rows and all 39,592 single-year rows in Volume III.

### Errors in the printed reports

The checks found three printing errors in the KNBS reports, which are corrected here and listed in `errata.csv`:

- Mikindani location (Jomvu, Mombasa): male population printed as 333; the sum of its sub-locations is 31,187.
- Mukurweini sub-county (Nyeri): male population aged 5 to 9 and 10 to 14 printed as dates ("15-Aug", "23-Jun"); the values are 4,611 and 4,923.

They also found five small inconsistencies of 1 to 3 people, mostly in forest sub-counties, which are left as printed and listed in `known_issues.csv`. Four sub-counties with no residents (Lake Baringo, Mau Forest in Kericho and Bomet, Tinderet Forest) have no page in Volume III.

## Rebuild the files yourself

You need [uv](https://docs.astral.sh/uv/) and the two KNBS PDFs (see [`data/raw/README.md`](data/raw/README.md) for where to download them).

```bash
uv sync
uv run python -m kenya_census.build      # writes data/csv/ and data/csv/checks.txt
uv run pytest                            # the independent check, about 2 minutes
```

The extraction reads the position of every character in the PDF with [pdfplumber](https://github.com/jsvine/pdfplumber). The administrative level of a row is read from its indent. No OCR is used: the KNBS reports contain real text.

## Source and terms of use

Kenya National Bureau of Statistics (2019). *2019 Kenya Population and Housing Census, Volume II: Distribution of Population by Administrative Units*, and *Volume III: Distribution of Population by Age and Sex*. Nairobi: KNBS. https://www.knbs.or.ke/reports/kenya-census-2019/

The reports are © KNBS 2019, all rights reserved. Their copyright page states: "Extracts may be published if the source is duly acknowledged." **If you use these files, cite KNBS as the source of the data.** You may also cite this repository for the extraction (see [`CITATION.cff`](CITATION.cff)).

The code in this repository is released under the MIT licence ([`LICENSE`](LICENSE)). The licence covers the code only; the data remain subject to KNBS's terms.

This is an independent extraction. It is not published or endorsed by KNBS. If you find a value that differs from the printed report, please open an issue with the page number.
