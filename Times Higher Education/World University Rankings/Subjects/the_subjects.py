import requests
import os
import re
import json
import glob
import pandas as pd

def fetch_json(years, subjects):
    """
    Fetch league table as JSON files for each year and subject & save to disk
    """
    subjects = {
        "Arts & Humanities": "arts-and-humanities",
        "Clinical, Pre-clinical & Health": "clinical-pre-clinical-health",
        "Life Sciences": "life-sciences",
        "Physical sciences": "physical-sciences",
        "Psychology": "psychology",
        "Education": "education",
        "Law": "law",
        "Social Sciences": "social-sciences",
        "Business & Economics": "business-and-economics",
        "Computer Science": "computer-science",
        "Engineering & Technology": "engineering-and-IT"
    }
    for year in years:
        if not os.path.exists(os.path.join("JSON", str(year))):
            os.makedirs(os.path.join("JSON", str(year)))
        for subject_name, subject_slug in subjects.items():
            url = "https://www.timeshighereducation.com/world-university-rankings"
            r = requests.get("{}/{}/subject-ranking/{}".format(url, year, subject_slug), headers = {"User-Agent": None}) # U-A required to avoid 403
            json_url = re.search(r"the_data_rankings\\/([\w]*\.json)", r.text) # JSON filename doesn't always match subject_slug
            if json_url:
                url = "https://www.timeshighereducation.com/sites/default/files/the_data_rankings/"
                r = requests.get(url + json_url.group(1), headers = {"User-Agent": None})
                with open(os.path.join("JSON", str(year), "{}.json".format(subject_name)), "w") as f:
                    json.dump(r.json(), f)

def json_to_csv(years):
    """
    Convert JSONs to CSVs and save to disk
    """
    for year in years:
        if not os.path.exists(os.path.join("CSV", str(year))):
            os.makedirs(os.path.join("CSV", str(year)))
        for file in glob.glob(os.path.join("JSON", str(year), "*.json")):
            with open(file) as f:
                json_data = json.load(f)
                csv_data = pd.DataFrame(data=json_data["data"])
                csv_name = os.path.splitext(os.path.basename(file))[0]
                csv_data.to_csv(os.path.join("CSV", str(year), "{}.csv".format(csv_name)), index=False)

def concat_data(years):
    """
    Convert to long format, add 'Year' and concatenate into one DataFrame
    """
    data = []
    for year in years:
        for file in glob.glob(os.path.join("CSV", str(year), "*.csv")):
            csv_data = pd.read_csv(file)
            csv_data = pd.melt(csv_data, id_vars=["name", "location"], var_name="Metric", value_name="Value")
            csv_data["Year"] = year
            csv_data["Subject"] = os.path.splitext(os.path.basename(file))[0]
            data.append(csv_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Rename columns, correct encoding issues, add numerical values
    """
    data.rename({"name": "Institution", "location": "Location"}, axis=1, inplace=True)
    metrics = ["scores_citations", "scores_industry_income", "scores_international_outlook", "scores_overall", "scores_research", "scores_teaching", "rank"]
    data = data.copy().loc[data["Metric"].isin(metrics)]
    data["Metric"] = data["Metric"].apply(lambda x: " ".join([w.capitalize() for w in x.replace("scores_", "").split("_")]))
    data["Value"] = data["Value"].astype(str).str.replace("\u2013", "-", regex=False)
    data["Value"] = data["Value"].astype(str).str.replace("\u2014", "-", regex=False)
    data.drop_duplicates(inplace=True)
    overall_ranks = data.copy().loc[data["Metric"] == "Rank", ["Institution", "Subject", "Value", "Year"]]
    overall_ranks.rename({"Value": "Rank"}, axis=1, inplace=True)
    overall_ranks["Metric"] = "Overall"
    overall_ranks["Rank"] = overall_ranks["Rank"].str.extract("(\d+)", expand=False) # Get first number i.e. '501' from '501-510'
    data = data.loc[data["Metric"] != "Rank"]
    data["Numeric Value"] = data["Value"].astype(str)
    data["Numeric Value"] = data["Numeric Value"].astype(str).str.replace("-", "", regex=False)
    data["Numeric Value"] = pd.to_numeric(data["Value"].str.extract("([\d.]+)", expand=False), errors="coerce") # Also capture lowest score from banded 'Overall' scores
    return data, overall_ranks

def rank_metrics(data):
    """
    Calculate rank and decile for each metric by year
    """
    data["Rank"] = data.groupby(["Year", "Subject", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data.loc[data["Metric"] != "Overall", "Decile"] = data.loc[data["Metric"] != "Overall"].groupby(["Year", "Subject", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    data.set_index(keys=["Institution", "Subject", "Year", "Metric"], inplace=True)
    overall_ranks.set_index(keys=["Institution", "Subject", "Year", "Metric"], inplace=True)
    data.drop_duplicates(inplace=True)
    overall_ranks.drop_duplicates(inplace=True)
    data.update(overall_ranks)
    return data.reset_index()

years = [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
fetch_json(years)
json_to_csv(years)
data = concat_data(years)
data, overall_ranks = clean_data(data)
data = rank_metrics(data)
data.to_csv("THE WUR Subjects.csv", index=False) # Save final CSV to disk
