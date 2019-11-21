import requests
import os
import re
import json
import pandas as pd

def fetch_json(years):
    """
    Fetch league table as JSON files for each year & save to disk
    """
    if not os.path.exists("JSON"):
        os.makedirs("JSON")
    for year in years:
        url = "https://www.timeshighereducation.com/world-university-rankings"
        r = requests.get("{}/{}/world-ranking".format(url, year))
        json_url = re.search("world_university_rankings_[\w]*\.json", r.text).group(0)
        url = "https://www.timeshighereducation.com/sites/default/files/the_data_rankings/"
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
            csv_data.to_csv(os.path.join("CSV", "{}.csv".format(year)), index=False)

def concat_data(years):
    """
    Convert to long format, add 'Year' and concatenate into one DataFrame
    """
    data = []
    for year in years:
        csv_data = pd.read_csv(os.path.join("CSV", "{}.csv".format(year)))
        csv_data = pd.melt(csv_data, id_vars=["name", "location"], var_name="Metric", value_name="Value")
        csv_data["Year"] = year
        data.append(csv_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Rename columns, tidy metric names, add numerical values
    """
    data.rename({"name": "Institution", "location": "Location"}, axis=1, inplace=True)
    metrics = ["scores_citations", "scores_industry_income", "scores_international_outlook", "scores_overall", "scores_research", "scores_teaching", "rank"]
    data = data.copy().loc[data["Metric"].isin(metrics)]
    data["Metric"] = data["Metric"].apply(lambda x: " ".join([w.capitalize() for w in x.replace("scores_", "").split("_")]))
    data["Value"] = data["Value"].astype(str).str.replace("\u2013", "-", regex=False)
    data["Value"] = data["Value"].astype(str).str.replace("\u2014", "-", regex=False)
    data.drop_duplicates(inplace=True)
    overall_ranks = data.copy().loc[data["Metric"] == "Rank", ["Institution", "Value", "Year"]]
    overall_ranks.rename({"Value": "Rank"}, axis=1, inplace=True)
    overall_ranks["Metric"] = "Overall"
    overall_ranks["Rank"] = overall_ranks["Rank"].str.extract("(\d+)", expand=False) # Get first number i.e. '501' from '501-510'
    data = data.loc[data["Metric"] != "Rank"]
    data["Numeric Value"] = pd.to_numeric(data["Value"].str.extract("([\d.]+)", expand=False), errors="coerce") # Also capture lowest score from banded 'Overall' scores
    return data, overall_ranks

def rank_metrics(data, overall_ranks):
    """
    Calculate rank and decile for each metric by year
    """
    data["Rank"] = data.groupby(["Year", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data.loc[data["Metric"] != "Overall", "Decile"] = data.loc[data["Metric"] != "Overall"].groupby(["Year", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    data.set_index(keys=["Institution", "Year", "Metric"], inplace=True)
    overall_ranks.set_index(keys=["Institution", "Year", "Metric"], inplace=True)
    data.drop_duplicates(inplace=True)
    overall_ranks.drop_duplicates(inplace=True)
    data.update(overall_ranks)
    return data.reset_index()

years = [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
fetch_json(years)
json_to_csv(years)
data = concat_data(years)
data, overall_ranks = clean_data(data)
data = rank_metrics(data, overall_ranks)
data.to_csv("THE WUR Institutional.csv", index=False) # Save final CSV to disk
