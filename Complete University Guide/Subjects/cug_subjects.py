import urllib
import requests
import pandas as pd
from bs4 import BeautifulSoup

def get_cols(table):
    header = table.find_all("th")
    cols = []
    for column in header:
        try:
            col = column.find("a").get_text()
        except AttributeError:
            col = column.get_text()
        cols.append(col.strip())
        if column.get("colspan"):
            for c in range(1, int(column.get("colspan"))):
                cols.append("{} {}".format(col.strip(), c))
    return cols

def get_data(years):
    url = "https://www.thecompleteuniversityguide.co.uk/league-tables/rankings?v=wide&y="
    data = []
    for year in years:
        for index, subject in pd.read_csv("lookup.csv")["Subject"].iteritems():
            r = requests.get(url + str(year) + "&s=" + urllib.parse.quote(subject))
            soup = BeautifulSoup(r.text, "lxml")
            table = soup.find("table", {"class": "league-table-table"})
            table_cols = get_cols(table)
            table_data = []
            for row in table.find_all("tr"):
                table_row = []
                for cell in row.find_all("td"):
                    table_row.append(cell.get_text().strip())
                table_data.append(table_row)
            table_data = [l for l in table_data if len(l) > 2]
            table_data = pd.DataFrame(data=table_data, columns=table_cols)
            table_data = pd.melt(table_data, id_vars=["University Name"], var_name="Metric", value_name="Value")
            table_data["Year"] = year
            table_data["Subject"] = subject
            data.append(table_data)
    return pd.concat(data, axis=0)

def clean_data(data):
    """
    Remove unnecessary metrics, add numerical values
    """
    data.rename(columns={"University Name": "Institution"}, inplace=True)
    data = data.copy().loc[~data["Metric"].isin(["Rank", "Rank 1", "Next Steps", "Green Score"])]
    data["Numeric Value"] = data["Value"].astype(str)
    data["Numeric Value"] = data["Numeric Value"].replace("n/a", "", regex=False)
    data["Numeric Value"] = data["Numeric Value"].str.replace(",", "", regex=False)
    data["Numeric Value"] = data["Numeric Value"].str.replace(r"[a-z]", "", regex=True)
    data["Numeric Value"] = pd.to_numeric(data["Numeric Value"], errors="coerce") # Coerce will turn blanks to NaNs
    return data

def rank_metrics(data):
    """
    Calculate rank and decile for each metric by year
    """
    data["Rank"] = data.groupby(["Year", "Subject", "Metric"])["Numeric Value"].rank(ascending=False, method="min")
    data_nan = data.copy().loc[data["Numeric Value"].isnull()] # Exclude NaNs for now
    data_nan["Decile"] = pd.np.nan
    data = data.copy().loc[data["Numeric Value"].notnull()]
    data["Decile"] = data.groupby(["Year", "Subject", "Metric"])["Numeric Value"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 10, labels=range(1,11)) # Calculate deciles on ranked data to avoid duplicate bin edges as https://stackoverflow.com/a/40548606/2950747
    )
    return data.append(data_nan)

years = [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
data = get_data(years)
data = clean_data(data)
data = rank_metrics(data)
data.to_csv("Complete University Guide Subjects.csv", index=False) # Save final CSV to disk
