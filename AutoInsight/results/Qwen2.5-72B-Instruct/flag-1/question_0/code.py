import pandas as pd
import autoinsight.tools as tools

# Path to the CSV file
data_path = 'C:\\Users\\wxf\\Desktop\\AutoInsight\\data\\notebooks\\csvs\\flag-1.csv'

# Load the data from the CSV file
df = pd.read_csv(data_path)

# Column to plot
plot_column = 'category'

# Title of the plot
plot_title = 'Distribution of Incidents Across Categories'

# Generate a count plot for the category column
tools.plot_countplot(df, plot_column, plot_title)

# Prepare the data for the JSON file
data_dict = {
    'plot type': 'countplot',
    'value': df[plot_column].value_counts().to_dict()
}

# Save the data to a JSON file
tools.save_json(data_dict, 'stat')

# Fix the filenames of the generated plots and stats
tools.fix_fnames()