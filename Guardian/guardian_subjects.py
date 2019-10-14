import os
import pandas as pd
import re

def concat_data(years):
    """
    Convert to long format, add 'Year' & 'Subject' and concatenate into one DataFrame
    (Excel sheets contain many blank rows and pd.read_excel() is slow, so this function takes several minutes)
    """
    lookup = pd.read_csv("lookup.csv", index_col=0)
    data = []
    subjects = [s for s in lookup.index.values if re.match("S\d", s)] + ["Human Geo"]
    for year in years:
        for subject in subjects:
            filename = lookup.loc["Filename", str(year)]
            sheet_name = lookup.loc[subject, str(year)]
            if type(sheet_name) == str:
                csv_data = pd.read_excel(os.path.join("Originals", filename), sheet_name=sheet_name, header=1)
                csv_data.rename(columns={
                    "Name of Institution": "Institution",
                    "Name of Provider": "Institution"
                }, inplace=True)
                csv_data = pd.melt(csv_data, id_vars=["Institution"], var_name="Metric", value_name="Value")
                csv_data["Year"] = year
                csv_data["Subject Code"] = subject[0:4]
                csv_data["Subject Name"] = subject[5:]
                data.append(csv_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Make metric names consistent, remove unecessary fields, ensure numerical values
    """
    data.dropna(subset=["Value"], inplace=True)
    data["Metric"].replace({
        "Student: staff ratio": "Student:staff ratio",
        "Continuation ": "Continuation",
        "% Satisfied overall with course": "% Satisfied with course"
    }, inplace=True)
    data = data.copy().loc[data["Metric"].isin([
        "Guardian score/100",
        "% Satisfied with Teaching",
        "% Satisfied with course",
        "Continuation",
        "Expenditure per student (FTE)",
        "Student:staff ratio",
        "Career prospects",
        "Value added score/10",
        "Average Entry Tariff",
        "% Satisfied with Assessment"
    ])]
    data["Numeric Value"] = pd.to_numeric(data["Value"], errors="coerce") # Coerce will turn blanks to NaNs
    return data

def rank_metrics(data):
    """
    Calculate rank and decile for each metric by year
    """
    data_exc_ssr = data.copy().loc[data["Metric"] != "Student:staff ratio"] # All metrics except SSR are ranked descending
    data_exc_ssr["Rank"] = data_exc_ssr.groupby(["Year", "Subject Code", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data_exc_ssr["Decile"] = data_exc_ssr.groupby(["Year", "Subject Code", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    data_inc_ssr = data.copy().loc[data["Metric"] == "Student:staff ratio"] # SSR is ranked ascending
    data_inc_ssr["Rank"] = data_inc_ssr.groupby(["Year", "Subject Code", "Metric"])["Numeric Value"].rank(ascending=True, method="min")
    data_inc_ssr["Decile"] = data_inc_ssr.groupby(["Year", "Subject Code", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=list(reversed(range(1,11)))) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    return data_exc_ssr.append(data_inc_ssr)

years = [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
data = concat_data(years)
data = clean_data(data)
data = rank_metrics(data)
data.to_csv("Guardian Subjects.csv", index=False) # Save final CSV to disk
