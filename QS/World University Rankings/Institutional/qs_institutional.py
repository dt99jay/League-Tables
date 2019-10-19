import requests
import os
import re
import json
import pandas as pd
from bs4 import BeautifulSoup

def fetch_json(years):
    """
    Fetch league table as JSON files for each year & save to disk
    """
    if not os.path.exists("JSON"):
        os.makedirs("JSON")
    for year in years:
        url = "https://www.topuniversities.com/university-rankings/world-university-rankings"
        r = requests.get("{}/{}".format(url, year))
        json_url = re.search("[\d]*_indicators.txt", r.text).group(0)
        url = "https://www.topuniversities.com/sites/default/files/qs-rankings-data/"
        r = requests.get(url + json_url)
        with open(os.path.join("JSON", "{}.json".format(year)), "w") as f:
            json.dump(r.json(), f)

def json_to_csv(years):
    """
    Convert JSONs to CSVs and save to disk
    """
    if not os.path.exists("CSV"):
        os.makedirs("CSV")
    for year in years:
        with open(os.path.join("JSON", "{}.json".format(year))) as f:
            json_data = json.load(f)
            csv_data = pd.DataFrame(data=json_data["data"])
            csv_columns = dict(zip(
                [i["data"] for i in json_data["columns"]],
                [BeautifulSoup(i["title"], "lxml").get_text() for i in json_data["columns"]]
            ))
            csv_data.rename(columns=csv_columns, inplace=True)
            csv_data.to_csv(os.path.join("CSV", "{}.csv".format(year)), index=False)

def concat_data(years):
    """
    Convert to long format, add 'Year' and concatenate into one DataFrame
    """
    data = []
    for year in years:
        csv_data = pd.read_csv(os.path.join("CSV", "{}.csv".format(year)))
        csv_data = pd.melt(csv_data, id_vars=["UNIVERSITY", "LOCATION", "REGION"], var_name="Metric", value_name="Value")
        csv_data["Year"] = year
        data.append(csv_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Rename columns, tidy metric names, add numerical values
    """
    data.rename({"UNIVERSITY": "Institution", "LOCATION": "Location", "REGION": "Region"}, axis=1, inplace=True)
    metrics = ["Academic Reputation", "Employer Reputation", "Faculty Student", "International Faculty", "International Students", "Citations per Faculty", "OVERALL SCORE"]
    data = data.copy().loc[data["Metric"].isin(metrics)]
    data["Institution"] = data["Institution"].apply(lambda x: BeautifulSoup(x, "lxml").get_text())
    data["Value"] = data["Value"].apply(lambda x: BeautifulSoup(x, "lxml").get_text() if type(x) is str else x)
    data["Numeric Value"] = pd.to_numeric(data["Value"], errors="coerce") # Coerce will turn blanks to NaNs
    return data

def rank_metrics(data):
    """
    Calculate rank and decile for each metric by year
    """
    data["Rank"] = data.groupby(["Year", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data["Decile"] = data.groupby(["Year", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    return data

years = [2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
fetch_json(years)
json_to_csv(years)
data = concat_data(years)
data = clean_data(data)
data = rank_metrics(data)
data.to_csv("QS WUR Institutional.csv", index=False) # Save final CSV to disk
