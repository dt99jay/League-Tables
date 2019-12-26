# University League Table Scripts

Download and process university league table data for further analysis

## Getting Started

These scripts download, aggregate and process university league table data. They might be of use to analysts and researchers working in higher education.

Each script creates a single CSV file with fields for year, subject, metric, institution, with measures including original value/score, numeric value/score, rank and decile within each group.

### Prerequisites

You'll need Python 3 with Requests, Pandas and Beautiful Soup installed. Run the scripts as (for example):

```
python3 times_institutional.py
```

Most of the scripts create folders for source and intermediate JSON and CSV files (which can be deleted if not required) as well as a larger CSV file (named e.g. 'THE WUR Institutional.csv'). The larger CSV file contains the final data.

### League tables, source data and years

#### UK League Tables

| Publisher | League Tables | Source | Available Years
| --- | --- | --- | --- |
| Complete University Guide | Institutional and subject | CUG Website | 2009 onwards |
| Guardian | Institutional and subject | Published spreadsheets | 2010 onwards |
| Times and Sunday Times | Institutional and subject | Times Website | 2014 onwards |

#### International League Tables

| Publisher | League Tables | Source | Available Years
| --- | --- | --- | --- |
| Times Higher Education | WUR Institutional and subject | THE Website | 2011 onwards |
| QS | WUR Institutional and subject | QS Website | 2012 onwards |

### UKPRNs

A separate script is available to add UKPRN (UK Provider Reference Number) and consistent name to each institution to aid analysis over time. This also allows ranks to be calculated within groups (e.g. rank within the Russell Group or N8 for specific metrics).

Example files are included with Russell Group rank.

(Be careful if grouping/pivoting by UKPRN on its own, as mergers have occured so more than one institution's results might be collected together e.g. University of Glamorgan and University of Wales, Newport are both collected under the University of South Wales' UKPRN.)

### Caveats

Always rely on the official data available on the league table compiler's website, as errors may be introduced through the use of these scripts. If you find any errors, please raise an issue.

## Licence

The scripts (i.e. the Python files) are made available under the MIT Licence, but the resulting data is presumably the copyright of the league table compiler.