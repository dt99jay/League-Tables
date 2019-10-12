import requests
import os
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
        url = "https://st.hitcreative.com/education/university_guide/active/UniversityGuide/getTable/type/rank/year/"
        r = requests.get(url + str(year))
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
            columns = [value["header"].strip() for value in json_data["columns"]]
            csv_data = pd.DataFrame(data=json_data["rows"], columns=columns)
            csv_data.to_csv(os.path.join("CSV", "{}.csv".format(year)), index=False)

def concat_data(years):
    """
    Convert to long format, add 'Year' and concatenate into one DataFrame
    """
    data = []
    for year in years:
        csv_data = pd.read_csv(os.path.join("CSV", "{}.csv".format(year)))
        csv_data = pd.melt(csv_data, id_vars=["University"], var_name="Metric", value_name="Value")
        csv_data["Year"] = year
        data.append(csv_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Remove HTML tags, make earlier metric names consistent with those used in later years, add numerical values
    """
    data["Institution"] = data["University"].apply(lambda x: BeautifulSoup(x, "lxml").get_text())
    data["Metric"] = data["Metric"].apply(lambda x: BeautifulSoup(x, "lxml").get_text())
    data.drop("University", axis=1, inplace=True)
    data["Metric"].replace({
        "Completion rate": "Completion rate (%)",
        "Ucas entry points": "Entry standards (Ucas pts)",
        "Graduate prospects": "Graduate prospects (%)",
        "Firsts / 2:1s": "Firsts/2:1s (%)",
        "Research quality": "Research quality (%)",
        "Services/facilities spend": "Services/facilities spend (£)",
        "Services/ facilities spend (£)": "Services/facilities spend (£)",
        "Student experience": "Student experience (%)"
    }, inplace=True)
    data = data.loc[data["Metric"] != "Rank"] # Rank is dropped in favour of re-calculating it on the 'Total' metric
    data = data.loc[data["Metric"] != "Last Year Rank"]
    data["Numeric Value"] = data["Value"].astype(str)
    data["Numeric Value"] = data["Numeric Value"].str.replace(",", "", regex=False)
    data["Numeric Value"] = pd.to_numeric(data["Numeric Value"], errors="coerce") # Coerce will turn blanks to NaNs
    return data

def rank_metrics(data):
    """
    Calculate rank and decile for each metric by year
    """
    data_exc_ssr = data.copy().loc[data["Metric"] != "Student-staff ratio"] # All metrics except SSR are ranked descending
    data_exc_ssr["Rank"] = data_exc_ssr.groupby(["Year", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data_exc_ssr["Decile"] = data_exc_ssr.groupby(["Year", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    data_inc_ssr = data.copy().loc[data["Metric"] == "Student-staff ratio"] # SSR is ranked ascending
    data_inc_ssr["Rank"] = data_inc_ssr.groupby(["Year", "Metric"])["Numeric Value"].rank(ascending=True, method="min")
    data_inc_ssr["Decile"] = data_inc_ssr.groupby(["Year", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=list(reversed(range(1,11)))) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    return data_exc_ssr.append(data_inc_ssr)

years = [2014, 2015, 2016, 2017, 2018, 2019, 2020]
fetch_json(years)
json_to_csv(years)
data = concat_data(years)
data = clean_data(data)
data = rank_metrics(data)
data.to_csv("Times & Sunday Times Institutional.csv", index=False) # Save final CSV to disk
