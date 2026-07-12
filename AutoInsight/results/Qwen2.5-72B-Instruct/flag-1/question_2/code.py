import pandas as pd
import autoinsight.tools as tools

# Load the data from the specified path
data_path = 'C:\\Users\\wxf\\Desktop\\AutoInsight\\data\\notebooks\\csvs\\flag-1.csv'  # Path to the CSV file
df = pd.read_csv(data_path)  # DataFrame containing the data

# Convert 'closed_at' and 'opened_at' to datetime
df['closed_at'] = pd.to_datetime(df['closed_at'])  # Column with the closed_at timestamps
df['opened_at'] = pd.to_datetime(df['opened_at'])  # Column with the opened_at timestamps

# Calculate the time to resolution
df['time_to_resolution'] = df['closed_at'] - df['opened_at']  # Column for time to resolution

# Convert time to resolution to seconds for easier plotting
df['time_to_resolution_seconds'] = df['time_to_resolution'].dt.total_seconds()  # Column for time to resolution in seconds

# Group by priority and calculate the mean time to resolution
priority_ttr = df.groupby('priority')['time_to_resolution_seconds'].mean().reset_index()  # DataFrame with priority and mean time to resolution

# Plot the relationship between priority and time to resolution
plot_title = 'Priority Level vs. Mean Time to Resolution'  # Title of the plot
plot_column = 'time_to_resolution_seconds'  # Column to plot on the y-axis
x_column = 'priority'  # Column to plot on the x-axis
tools.plot_lines(priority_ttr, x_column, [plot_column], plot_title)  # Generate the line plot

# Save the stats to a JSON file
stats_data = {
    'plot type': 'line plot',
    'value': priority_ttr.to_dict(orient='records')  # Data for the plot
}
tools.save_json(stats_data, 'stat')  # Save the stats data to a JSON file

# Fix the filenames of the generated plots and stats
tools.fix_fnames()  # Rename the plot and stat files