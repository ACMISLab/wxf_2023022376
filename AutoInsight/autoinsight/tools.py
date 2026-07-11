import matplotlib
matplotlib.use('TkAgg')      # or 'Qt5Agg', 'GTK3Agg', etc., depending on what you have installed
import matplotlib.pyplot as plt
import json, pandas as pd, os
from typing import Dict, List
from copy import deepcopy
from wordcloud import WordCloud
import seaborn as sns


def plot_countplot(df: pd.DataFrame, plot_column: str, plot_title: str) -> None:
    """
    Takes a DataFrame as input, performs a group by on plot_column and saves a count plot.
    The plot is then saved into plot.jpg

    Parameters:
    df: DataFrame containing the data.
    plot_column: Column name to plot.
    plot_title: Title of the plot.

    Example usage:
    >>> data = pd.DataFrame({
    ...     'category': ['A', 'B', 'A', 'B', 'A'],
    ... })
    >>> plot_column = 'category'
    >>> plot_title = 'Category count plot'
    >>> plot_countplot(data, plot_column)
    """
    # make countplot with plot title using seaborn
    try:
        sns.countplot(data=df, x=plot_column, hue=plot_column).set_title(plot_title)
        plt.savefig("plot.jpg")
        plt.close()
    except Exception as e:
        print(f"plot_countplot failed: {e}")


def plot_lines(
    df: pd.DataFrame, x_column: str, plot_columns: List[str], plot_title: str
) -> None:
    """
    Takes a DataFrame as input, and makes a line plot of the data in plot_columns using seaborn.
    The plot is then saved into plot.jpg

    Parameters:
    df: DataFrame containing the data.
    x_column: Column name with the x-axis data.
    plot_columns: Columns with y-axis data to plot.
    plot_title: Title of the plot.

    Example usage:
    >>> data = pd.DataFrame({
    ...     'time': [10, 20, 30, 40, 50],
    ...     'A': [1, 2, 3, 4, 5],
    ...     'B': [5, 4, 3, 2, 1],
    ... })
    >>> x_column = 'time'
    >>> plot_columns = ['A', 'B']
    >>> plot_title = 'Line plot of A and B'
    >>> plot_lines(data, x_column, plot_columns)
    """
    # make lineplot with plot title using seaborn
    try:
        for plot_column in plot_columns:
            df[x_column] = df[x_column].astype(str)
            sns.lineplot(data=df, x=x_column, y=plot_column, label=plot_column)
        # set plot title
        plt.title(plot_title)
        plt.savefig("plot.jpg")
        plt.close()
    except Exception as e:
        print(f"plot_lines failed: {e}")


def save_json(data_dict: Dict, ftype: str) -> None:
    """
    Saves data_dict to a json file.

    Parameters:
    data_dict: Dictionary containing data to be saved.
    ftype: "stat".

    Example usage:
    >>> ftype = "stat"
    >>> data_dict = {
    ...     'name': "Distribution",
    ...     'description': "ABC distribution.",
    ...     'value': {"A": 336,"B": 51,"C": 41,},
    ... }
    >>> save_json(data_dict, ftype)
    """

    try:
        def validate_dict(parent):
            """
            Goes through all the keys in the dictionary and converts the keys are strings.
            If the values are dictionaries, it recursively fixes them as well.
            """
            duplicate = deepcopy(parent)
            for k, v in duplicate.items():
                if isinstance(v, dict):
                    parent[k] = validate_dict(v)
                if not isinstance(k, str):
                    parent[str(k)] = parent.pop(k)
            return parent

        ftype = ftype.lower()
        if "stat" in ftype:
            ftype = "stat"

        assert all(isinstance(k, str) for k in data_dict.keys())
        # perform a sanity check that all the keys are strings
        validate_dict(data_dict)
        # recursively check if all the keys are strings

        # filename depends on the number of plots already in the folder
        ftype_count = len([f for f in os.listdir() if f.startswith(f"{ftype}_")])
        fname = f"{ftype}.json"
        with open(fname, "w") as f:
            json.dump(data_dict, f, indent=4)
    except Exception as e:
        print(f"save_json failed: {e}")


def generate_wordcloud(
    df: pd.DataFrame, group_by_column: str, plot_column: str
) -> None:
    """
    Generates a wordcloud by performing a groupby on df and using the plot_column.
    The plot is then saved into plot.jpg

    Parameters:
    df: DataFrame containing the data.
    group_by_column: Column name to group by.
    plot_column: Column name to plot.

    Example usage:
    >>> data = pd.DataFrame({
    ...     'category': ['A', 'B', 'A', 'B', 'A'],
    ...     'description': ['apple', 'orange', 'banana', 'grapes', 'kiwi'],
    ... })
    >>> group_by_column = 'category'
    >>> plot_column = 'description'
    >>> generate_wordcloud(data, group_by_column, plot_column)
    """
    # check if data in plot_column is a string
    try:
        assert isinstance(df[plot_column].iloc[0], str)

        # group by the column and aggregate the data
        grouped_data = df.groupby(group_by_column)[plot_column].apply(list).reset_index()
        # generate a wordcloud for each group
        plt.figure(figsize=(20, 10))
        for i, row in grouped_data.iterrows():
            wc = WordCloud(width=800, height=400).generate(" ".join(row[plot_column]))
            plt.subplot(1, len(grouped_data), i + 1)
            plt.imshow(wc, interpolation="bilinear")
            plt.title(row[group_by_column])
            plt.axis("off")
        plt.savefig("plot.jpg")
        plt.close()
    except Exception as e:
        print(f"generate_wordcloud failed: {e}")

def linear_regression(X, y):
    """
    Fits a linear regression model on the data and returns the model.

    Parameters:
    X: Features to fit the model on.
    y: Target variable to predict.

    Example usage:
    >>> X = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
    >>> y = np.array([2, 4, 6, 8, 10])
    >>> model = linear_regression(X, y)
    """
    from sklearn.linear_model import LinearRegression

    try:
        model = LinearRegression()
        model.fit(X, y)
        return model
    except Exception as e:
        print(f"linear_regression failed: {e}")
        return None


def fix_fnames():
    """
    Renames all the plot and stat files in the current directory to plot_<number>.jpg.
    """

    try:
        for i, f in enumerate([f for f in os.listdir() if f.startswith("plot")]):
            if f.startswith("plot"):
                os.rename(f, f"plot.jpg")

        for i, f in enumerate([f for f in os.listdir() if f.startswith("stat")]):
            if f.startswith("stat"):
                os.rename(f, f"stat.json")
    except Exception as e:
        print(f"fix_fnames failed: {e}")








