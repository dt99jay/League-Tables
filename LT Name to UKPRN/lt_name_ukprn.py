import difflib
import pandas as pd
import os
from ast import literal_eval

"""
League table providers don't use consistent names for institutions and don't include UKPRNs.
This semi-automated script adds UKPRN and a consistent name to an existing league table dataset.
Once UKPRN is added, it's easier to add other metrics e.g. best research in the N8, worst NSS in the RG etc.
There are two stages:

1. Generate a lookup list of all the institution names and their UKPRNs
    • To do this, gen_names() makes a list of the strings used by league table compilers
    • Then find_ukprn() attempts to match these to UKPRN via data from http://learning-provider.data.ac.uk
    • A 'lt_names_ukprn_interim.csv' file is generated with a few possible matching UKPRNs
    • The 'Index' field of this must be manually checked in Excel or similar and updated with the correct choice
    • If none of the suggested options is correct, 'Manual UKPRN' must be completed instead
    • The checked csv file is saved as a copy and used as the lookup by final_ukprn()

2. Add a UKPRN column to requested datasets
    • add_ukprn() then loads an existing dataset and joins with the UKPRN lookup and adds a consistent name
    • Other metrics can now be added by add_group_ranks(), such as rank within Russell Group
    • The new dataset is saved with UKPRN, consistent name and any additional metrics
"""

uk_files = [
    os.path.join("..", "Complete University Guide", "Institutional", "Complete University Guide Institutional.csv"),
    os.path.join("..", "Complete University Guide", "Subjects", "Complete University Guide Subjects.csv"),
    os.path.join("..", "Guardian", "Guardian Institutional.csv"),
    os.path.join("..", "Guardian", "Guardian Subjects.csv"),
    os.path.join("..", "Times and Sunday Times", "Institutional", "Times & Sunday Times Institutional.csv"),
    os.path.join("..", "Times and Sunday Times", "Subjects", "Times & Sunday Times Subject.csv"),
]

int_files = [
    os.path.join("..", "QS", "World University Rankings", "Institutional", "QS WUR Institutional.csv"),
    os.path.join("..", "QS", "World University Rankings", "Subjects", "QS WUR Subjects.csv"),
    os.path.join("..", "Times Higher Education", "World University Rankings", "Institutional", "THE WUR Institutional.csv"),
    os.path.join("..", "Times Higher Education", "World University Rankings", "Subjects", "THE WUR Subjects.csv")
]

def gen_names(uk_files, int_files):
    names = []
    for file in uk_files:
        names.append(pd.read_csv(file)["Institution"])
    for file in int_files:
        df = pd.read_csv(file)
        names.append(df.loc[df["Location"] == "United Kingdom"]["Institution"])
    return pd.DataFrame(pd.concat(names).unique(), columns=["LT Name"])

def find_ukprn(names):
    lookup = pd.read_csv("learning-providers-plus.csv")
    lookup["PROVIDER_NAME_LOWER"] = lookup["PROVIDER_NAME"].str.lower()
    lookup["PROVIDER_NAME_SHORT"] = lookup["PROVIDER_NAME_LOWER"].str.replace("university", "")
    lookup["PROVIDER_NAME_SHORT"] = lookup["PROVIDER_NAME_SHORT"].str.replace("institute", "")
    lookup["PROVIDER_NAME_SHORT"] = lookup["PROVIDER_NAME_SHORT"].str.replace("college", "")
    lookup["PROVIDER_NAME_SHORT"] = lookup["PROVIDER_NAME_SHORT"].str.replace("school", "")
    lookup["PROVIDER_NAME_SHORT"] = lookup["PROVIDER_NAME_SHORT"].str.replace("the", "")
    lookup["PROVIDER_NAME_SHORT"] = lookup["PROVIDER_NAME_SHORT"].str.replace("of", "")
    lookup["PROVIDER_NAME_SHORT"] = lookup["PROVIDER_NAME_SHORT"].str.replace("\s{2,}", " ").str.strip()
    names["Match 1"] = names["LT Name"].apply(
        lambda x: difflib.get_close_matches(x.lower(), lookup["PROVIDER_NAME_LOWER"])
    )
    names["UKPRN 1"] = names["Match 1"].apply(
        lambda x: [lookup.loc[lookup["PROVIDER_NAME_LOWER"] == i]["UKPRN"].iloc[0] for i in x]
    )
    names["Match 2"] = names["LT Name"].apply(
        lambda x: difflib.get_close_matches(x.lower(), lookup["PROVIDER_NAME_SHORT"])
    )
    names["UKPRN 2"] = names["Match 2"].apply(
        lambda x: [lookup.loc[lookup["PROVIDER_NAME_SHORT"] == i]["UKPRN"].iloc[0] for i in x]
    )
    names["Matches"] = names["Match 1"] + names["Match 2"]
    names["Matched UKPRNs"] = names["UKPRN 1"] + names["UKPRN 2"]
    names["Index"] = 0
    names.drop(columns=["Match 1", "Match 2", "UKPRN 1", "UKPRN 2"], inplace=True)
    return names

def final_ukprn(row):
    if row["Index"] >= 0 and len(row["Matched UKPRNs"]) > 0:
        return row["Matched UKPRNs"][int(row["Index"])]
    else:
        return row["Manual UKPRN"]

def add_ukprn(uk_files, int_files, names):
    for file in uk_files + int_files:
        data = pd.read_csv(file)
        data = data.merge(names, how="left", left_on="Institution", right_on="LT Name")
        data.drop(columns="LT Name", inplace=True)
        institutions = pd.read_csv("learning-providers-plus.csv")
        institutions = institutions[["UKPRN", "VIEW_NAME"]]
        institutions.rename(columns={"VIEW_NAME": "Consistent Name"}, inplace=True)
        data = data.merge(institutions, how="left", left_on="UKPRN", right_on="UKPRN")
        data.to_csv(os.path.splitext(file)[0] + " with UKPRN.csv", index=False)

def add_group_ranks(uk_files, int_files):
    """
    Group options include: "GW4", "1994_Group", "M5_Universities", "White_Rose_University_Consortium", "Oxbridge", "Million_Plus", "N8_Research_Partnership", "ABSA", "Science_and_Engineering_South", "University_Alliance", "Russell_Group", "NCUK", "Cathedrals_Group"
    """
    institutions = pd.read_csv("learning-providers-plus.csv")
    members = institutions.loc[institutions["GROUPS"].astype(str).str.contains("Russell_Group"), "UKPRN"].tolist()
    for file in uk_files + int_files:
        file = os.path.splitext(file)[0] + " with UKPRN.csv"
        data = pd.read_csv(file)
        if "Subject" in data.columns:
            data.loc[data["UKPRN"].isin(members), "RG Rank"] = data.loc[data["UKPRN"].isin(members)].groupby(["Year", "Subject", "Metric"])["Rank"].rank(ascending=True, method="min") # Rank on existing rank rather than value to avoid detecting SSR metrics etc.
        else:
            data.loc[data["UKPRN"].isin(members), "RG Rank"] = data.loc[data["UKPRN"].isin(members)].groupby(["Year", "Metric"])["Rank"].rank(ascending=True, method="min") # Rank on existing rank rather than value to avoid detecting SSR metrics etc.
        data.to_csv(os.path.splitext(file)[0] + " & RG Rank.csv", index=False)

names = gen_names(uk_files, int_files)
names = find_ukprn(names)
names.to_csv("lt_names_ukprn_interim.csv", index=False)
names = pd.read_csv("lt_names_ukprn_interim_25-12-2019.csv", converters={"Matched UKPRNs": literal_eval})
names["UKPRN"] = names.apply(final_ukprn, axis=1)
names = names[["LT Name", "UKPRN"]]
add_ukprn(uk_files, int_files, names)
add_group_ranks(uk_files, int_files)