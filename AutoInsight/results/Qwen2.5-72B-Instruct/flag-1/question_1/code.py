import pandas as pd
import autoinsight.tools as tools
import seaborn as sns
import matplotlib.pyplot as plt

# Load the data from the specified path
data_path = 'C:\\Users\\wxf\\Desktop\\AutoInsight\\data\\notebooks\\csvs\\flag-1.csv'  # Path to the CSV file
df = pd.read_csv(data_path)

# Convert 'closed_at' and 'opened_at' to datetime
df['closed_at'] = pd.to_datetime(df['closed_at'])
df['opened_at'] = pd.to_datetime(df['opened_at'])

# Calculate the time to resolution
df['time_to_resolution'] = df['closed_at'] - df['opened_at']  # Time difference between closed_at and opened_at

# Convert time to resolution to seconds for easier plotting
df['time_to_resolution_seconds'] = df['time_to_resolution'].dt.total_seconds()  # Total seconds in the time difference

# Group by category and calculate the mean time to resolution
mean_resolution_time = df.groupby('category')['time_to_resolution_seconds'].mean().reset_index()  # Mean time to resolution per category

# Plot the mean time to resolution for each category
plot_title = 'Average Time to Resolution by Category'
plot_column = 'category'
tools.plot_lines(df=mean_resolution_time, x_column=plot_column, plot_columns=['time_to_resolution_seconds'], plot_title=plot_title)

# Save the plot data to a JSON file
plot_data = {
    'plot type': 'line',
    'value': mean_resolution_time.to_dict(orient='records')  # Convert DataFrame to a list of dictionaries
}
tools.save_json(plot_data, ftype='stat')

# Fix the filenames of the generated plots and stats
tools.fix_fnames()