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

Each script will create a JSON folder, a CSV folder and a larger CSV file. The larger CSV file contains the final data. The JSON and CSV folders and contents are an interim step and can be deleted if you don't need them.

### Caveats

Always rely on the official data available on the league table compiler's website, as errors may be introduced through the use of these scripts. If you find any errors, please raise an issue.

## Licence

The scripts (i.e. the Python files) are made available under the MIT Licence, but the resulting data is presumably the copyright of the league table compiler.