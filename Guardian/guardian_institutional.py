import os
import pandas as pd

def concat_data(years):
    """
    Convert to long format, add 'Year' and concatenate into one DataFrame
    """
    lookup = pd.read_csv("lookup.csv", index_col=0)
    data = []
    for year in years:
        filename = lookup.loc["Filename", str(year)]
        sheet_name = lookup.loc["Institutional", str(year)]
        header = int(lookup.loc["Institutional Header", str(year)])
        csv_data = pd.read_excel(os.path.join("Originals", filename), sheet_name=sheet_name, header=header)
        csv_data.rename(columns={"Name of Provider": "Institution"}, inplace=True)
        csv_data = pd.melt(csv_data, id_vars=["Institution"], var_name="Metric", value_name="Value")
        csv_data["Year"] = year
        data.append(csv_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Make metric names consistent, remove unecessary fields, ensure numerical values
    """
    data.dropna(subset=["Institution"], inplace=True)
    data["Metric"].replace({
        "satisfied with teaching (%)": "NSS Teaching (%)",
        "% Satisfied with Teaching": "NSS Teaching (%)",
        "satisfied with course (%)": "NSS Overall (%)",
        "% Satisfied with course": "NSS Overall (%)",
        "Expenditure per student (fte)": "Expenditure per student / 10",
        "Student: staff ratio": "Student:staff ratio",
        "Career prospects": "Career prospects (%)",
        "Average Entry Tariff": "Entry Tariff",
        "% Satisfied with Assessment": "NSS Feedback (%)",
        "satisfied with feedback (%)": "NSS Feedback (%)"
    }, inplace=True)
    data = data.copy().loc[data["Metric"].isin([
        "Average Teaching Score",
        "NSS Teaching (%)",
        "NSS Overall (%)",
        "Continuation",
        "Expenditure per student / 10",
        "Student:staff ratio",
        "Career prospects (%)",
        "Value added score/10",
        "Entry Tariff",
        "NSS Feedback (%)"
    ])]
    data["Numeric Value"] = pd.to_numeric(data["Value"], errors="coerce") # Coerce will turn blanks to NaNs
    return data

def rank_metrics(data):
    """
    Calculate rank and decile for each metric by year
    """
    data_exc_ssr = data.copy().loc[data["Metric"] != "Student:staff ratio"] # All metrics except SSR are ranked descending
    data_exc_ssr["Rank"] = data_exc_ssr.groupby(["Year", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data_exc_ssr["Decile"] = data_exc_ssr.groupby(["Year", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    data_inc_ssr = data.copy().loc[data["Metric"] == "Student:staff ratio"] # SSR is ranked ascending
    data_inc_ssr["Rank"] = data_inc_ssr.groupby(["Year", "Metric"])["Numeric Value"].rank(ascending=True, method="min")
    data_inc_ssr["Decile"] = data_inc_ssr.groupby(["Year", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=list(reversed(range(1,11)))) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    return data_exc_ssr.append(data_inc_ssr)

years = [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
data = concat_data(years)
data = clean_data(data)
data = rank_metrics(data)
data.to_csv("Guardian Institutional.csv", index=False) # Save final CSV to disk
