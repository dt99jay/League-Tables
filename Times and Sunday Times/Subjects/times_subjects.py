import requests
import os
import json
import glob
import pandas as pd
from bs4 import BeautifulSoup

def fetch_json(years):
    """
    Fetch league table as JSON files for each year & subject & save to disk
    """
    if not os.path.exists("JSON"):
        os.makedirs("JSON")
    for year in years:
        if not os.path.exists(os.path.join("JSON", str(year))):
            os.makedirs(os.path.join("JSON", str(year)))
        for subject in range(300, 500):
            url = "https://st.hitcreative.com/education/university_guide/active/UniversityGuide/getTable/type/imported/year"
            r = requests.get("{}/{}/id/{}".format(url, year, subject))
            if r.status_code == 200:
                with open(os.path.join("JSON", str(year), "{}.json".format(r.json()["table_name"])), "w") as f:
                    json.dump(r.json(), f)

def json_to_csv(years):
    """
    Convert JSONs to CSVs and save to disk
    """
    if not os.path.exists("CSV"):
        os.makedirs("CSV")
    for year in years:
        if not os.path.exists(os.path.join("CSV", str(year))):
            os.makedirs(os.path.join("CSV", str(year)))
        for file in glob.glob(os.path.join("JSON", str(year), "*.json")):
            with open(file) as f:
                json_data = json.load(f)
                columns = [value["header"].strip() for value in json_data["columns"]]
                csv_data = pd.DataFrame(data=json_data["rows"], columns=columns)
                csv_name = os.path.splitext(os.path.basename(file))[0]
                csv_data.to_csv(os.path.join("CSV", str(year), "{}.csv".format(csv_name)), index=False)

def concat_data(years):
    """
    Convert to long format, add 'Year' & 'Subject' and concatenate into one DataFrame
    """
    data = []
    for year in years:
        for file in glob.glob(os.path.join("CSV", str(year), "*.csv")):
            csv_data = pd.read_csv(file)
            csv_data = csv_data.rename({"Institution": "University"}, axis=1) # Some subjects use 'Institution' instead
            csv_data = pd.melt(csv_data, id_vars=["University"], var_name="Metric", value_name="Value")
            csv_data["Year"] = year
            csv_data["Subject"] = os.path.splitext(os.path.basename(file))[0]
            data.append(csv_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Remove HTML tags, make earlier metric names consistent with those used in later years, add numerical values
    """
    data.dropna(subset=["Value", "University"], inplace=True)
    data["Institution"] = data["University"].apply(lambda x: BeautifulSoup(x, "lxml").get_text())
    data["Metric"] = data["Metric"].apply(lambda x: BeautifulSoup(x, "lxml").get_text())
    data.drop("University", axis=1, inplace=True)
    data["Metric"].replace({
        "Overall rating": "Total score",
        "Entry standards": "Entry points",
        "Research rating": "Research quality"
    }, inplace=True)
    data = data.loc[data["Metric"] != "Subject rank"] # Rank is dropped in favour of re-calculating it on the 'Total' metric
    data = data.loc[data["Metric"] != "Overall rank"]
    data["Numeric Value"] = data["Value"].astype(str)
    data["Numeric Value"] = data["Numeric Value"].str.replace("%", "", regex=False)
    data["Numeric Value"] = data["Numeric Value"].str.replace("*", "", regex=False)
    data["Numeric Value"] = data["Numeric Value"].str.replace("..", "", regex=False)
    data["Numeric Value"] = pd.to_numeric(data["Numeric Value"], errors="coerce") # Coerce will turn blanks to NaNs
    return data

def rank_metrics(data):
    """
    Calculate rank and decile for each metric by subject and year
    """
    data["Rank"] = data.groupby(["Year", "Subject", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data["Decile"] = data.groupby(["Year", "Subject", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    return data

years = [2014, 2015, 2016, 2017, 2018, 2019, 2020]
fetch_json(years)
json_to_csv(years)
data = concat_data(years)
data = clean_data(data)
data = rank_metrics(data)
data.to_csv("Times & Sunday Times Subject.csv", index=False) # Save final CSV to disk
