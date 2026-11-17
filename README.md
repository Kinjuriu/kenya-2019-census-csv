# Kenya 2019 census data in CSV: population, school attendance and housing by county, sub-county and sub-location

The 2019 Kenya Population and Housing Census tables from the Kenya National Bureau of Statistics (KNBS), extracted from the official PDF reports into clean CSV files. Every number is checked against the report it came from.

The files cover all 47 counties:

- population, households, land area and density by **county**, **sub-county**, **division**, **location** and **sub-location** (8,932 sub-locations);
- population by **single year of age and sex** for every county and sub-county;
- **school-age children** by county and sub-county;
- **school attendance** (at school, left school, never attended) and **level of schooling** by county and sub-county, and attendance by age group for each county;
- **roofing material** of households (iron sheets, concrete, tiles and others) by county and sub-county.

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
| `kenya_2019_census_school_attendance_by_county_subcounty.csv` | People aged 3 and over by school attendance status, with per cents as printed; rows for all, male and female (Kenya also rural, urban, intersex) | 1,182 | Volume IV, table 2.2 |
| `kenya_2019_census_school_attendance_by_education_level_county_subcounty.csv` | People attending school or a learning institution now, by level | 1,182 | Volume IV, table 2.3 |
| `kenya_2019_census_school_attendance_by_age_group_county.csv` | School attendance status by age group (3-5, 4-5, 6-13, 14-17, 18-22, 23+, not stated) and sex, for each county | 376 | Volume IV, table 2.6b |
| `kenya_2019_census_roofing_material_by_county_subcounty.csv` | Conventional households and the per cent under each roofing material | 395 | Volume IV, table 2.12 |
| `volume4_vs_volume3_aged_3_plus.csv` | People aged 3 and over in Volume IV against Volume III, by area (see below) | 392 | Volumes III and IV |
| `errata.csv` | Printing errors in the KNBS tables that this repository corrects, with the evidence | 3 | |
| `known_issues.csv` | Small inconsistencies in the KNBS tables left as printed | 12 | |
| `checks.txt` | Output of every check from the last build | | |

Every row has a `page` column with the page of the PDF it came from, so you can look it up.

### Columns

- `total`, `male`, `female`: people counted on census night, 24 to 25 August 2019. KNBS shows intersex people (1,524 in Kenya) only at national and county level, so below county level `total` can be slightly larger than `male + female`.
- `households_total`, `households_conventional`, `group_quarters`: households, as defined by KNBS. Group quarters are places such as hostels, barracks and prisons.
- `land_area_km2`: land area in square kilometres. Table 2.3 prints whole numbers; table 2.4 prints one decimal place.
- `density_per_km2`: persons per square kilometre, as printed. Empty where KNBS printed "..".
- `note`: filled where a value was corrected (see `errata.csv`).

### Volume IV columns

- `breakdown`: `all`, `male` or `female` for every area; Kenya also has `rural`, `urban` and `intersex`. In the age-group file, `all` or an age group such as `age_6-13`. The groups 3-5 and 4-5 overlap, as printed by KNBS.
- School attendance (table 2.2, people aged 3 and over): `total`, `at_school`, `left_after_completion`, `left_before_completion`, `never_attended`, `dont_know`, `not_stated`. Columns ending `_pct` are the per cents printed by KNBS (share of `total`).
- Level of schooling (table 2.3, people attending now): `total_attending`, `pre_primary`, `primary`, `secondary`, `tvet` (middle level and technical and vocational training), `university`, `adult_basic_education`, `madrasa_duksi`, `dont_know`, `not_stated`.
- Age-group file (table 2.6b): the attendance columns of table 2.2, each split into `_total`, `_male` and `_female`.
- Roofing (table 2.12): `conventional_households`, then the per cent of those households whose main dwelling is roofed mainly with `grass_twigs`, `makuti_thatch`, `dung_mud`, `iron_sheets`, `tin_cans`, `asbestos_sheet`, `concrete_cement`, `tiles`, `canvas_tents`, `decra_versatile`, `nylon_cartons_cardboard`, `shingles`, or `not_stated`. Per cents are rounded to one decimal place, so rows sum to between 99.8 and 100.2.

Below national level, intersex people are counted in the `all` rows but have no row of their own, so `all` can be a few people more than `male + female`.

People aged 3 and over in Volume IV are 338,960 fewer (0.77 per cent) than in Volume III. The special population (travellers, outdoor sleepers, and people in hotels, lodges, schools and hospitals) was counted on short questionnaires (Volume IV, page 16), so Volume IV most likely covers people counted on the main questionnaire only. KNBS does not state this in one sentence; this is our reading. The gap is largest in city centres (in Nairobi, Starehe sub-county: 15,497 people). `volume4_vs_volume3_aged_3_plus.csv` gives it by area.

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
6. Volume IV: attendance statuses and levels add up to their totals; printed per cents match the counts; every county equals the sum of its sub-counties; Kenya's male, female and intersex rows, and its rural and urban rows, add up to the total; the county rows of table 2.6b equal those of table 2.2, and its age groups add up to the county row; roofing households equal the conventional households in Volume II; and no area has more people aged 3 and over than in Volume III.
7. An independent test (`tests/`) finds every extracted row in the PDF's plain text, read by a separate method: all 14,167 Volume II rows, all 39,592 single-year rows in Volume III and all 3,135 Volume IV rows.

### Errors in the printed reports

The checks found three printing errors in the KNBS reports, which are corrected here and listed in `errata.csv`:

- Mikindani location (Jomvu, Mombasa): male population printed as 333; the sum of its sub-locations is 31,187.
- Mukurweini sub-county (Nyeri): male population aged 5 to 9 and 10 to 14 printed as dates ("15-Aug", "23-Jun"); the values are 4,611 and 4,923.

They also found small inconsistencies of 1 to 3 people, mostly in forest sub-counties and between Volume IV tables 2.2 and 2.3, which are left as printed and listed in `known_issues.csv`. Two rows in Volume IV table 2.3 (pages 61 and 62) print "- 0 -" with no label; they are left out. Four sub-counties with no residents (Lake Baringo, Mau Forest in Kericho and Bomet, Tinderet Forest) have no page in Volume III.

## Rebuild the files yourself

You need [uv](https://docs.astral.sh/uv/) and the three KNBS PDFs (see [`data/raw/README.md`](data/raw/README.md) for where to download them).

```bash
uv sync
uv run python -m kenya_census.build      # writes data/csv/ and data/csv/checks.txt
uv run pytest                            # the independent check, about 3 minutes
```

The extraction reads the position of every character in the PDF with [pdfplumber](https://github.com/jsvine/pdfplumber). The administrative level of a row is read from its indent. No OCR is used: the KNBS reports contain real text.

## Source and terms of use

Kenya National Bureau of Statistics (2019). *2019 Kenya Population and Housing Census, Volume II: Distribution of Population by Administrative Units*, and *Volume III: Distribution of Population by Age and Sex*, and *Volume IV: Distribution of Population by Socio-Economic Characteristics*. Nairobi: KNBS. https://www.knbs.or.ke/reports/kenya-census-2019/

The reports are © KNBS 2019, all rights reserved. Their copyright page states: "Extracts may be published if the source is duly acknowledged." **If you use these files, cite KNBS as the source of the data.** You may also cite this repository for the extraction (see [`CITATION.cff`](CITATION.cff)).

The code in this repository is released under the MIT licence ([`LICENSE`](LICENSE)). The licence covers the code only; the data remain subject to KNBS's terms.

This is an independent extraction. It is not published or endorsed by KNBS. If you find a value that differs from the printed report, please open an issue with the page number.
