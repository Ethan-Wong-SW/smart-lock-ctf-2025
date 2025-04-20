import os
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIG ===
directory = "../stats"
file_prefix = "cycle_stats"
file_suffix = ".csv"

all_dataframes = []

# === LOAD CSVs ===
for file in os.listdir(directory):
    if file.startswith(file_prefix) and file.endswith(file_suffix):
        full_path = os.path.join(directory, file)
        print(f"Loading {file}...")
        try:
            df = pd.read_csv(full_path)
            all_dataframes.append(df)
        except Exception as e:
            print(f"⚠️ Error reading {file}: {e}")

if not all_dataframes:
    print("❌ No valid CSV files found. Check the file names or directory.")
    exit()

# === COMBINE + AVERAGE ===
combined_df = pd.concat(all_dataframes, ignore_index=True)
average_df = combined_df.groupby("Cycle").mean(numeric_only=True).reset_index()

# Save average CSV
avg_csv_path = os.path.join(directory, "average_cycle_stats.csv")
average_df.to_csv(avg_csv_path, index=False)
print(f"✅ Saved average stats to {avg_csv_path}")

# Save TXT summary
txt_path = os.path.join(directory, "average_cycle_stats.txt")
with open(txt_path, "w") as f:
    for index, row in average_df.iterrows():
        f.write(f"Cycle {int(row['Cycle'])}:\n")
        f.write(f"  Avg Interesting Passcodes: {row['Interesting_Passcodes']:.2f}\n")
        f.write(f"  Avg Interesting Commands:  {row['Interesting_Commands']:.2f}\n")
        f.write(f"  Avg Errors:                {row['Errors']:.2f}\n")
        f.write(f"  Avg Tests This Cycle:      {row['Tests_This_Cycle']:.2f}\n")
        f.write(f"  Avg Total Tests:           {row['Total_Tests']:.2f}\n")
        f.write(f"  Avg Execution Time:        {row['Avg_Execution_Time']:.5f} s\n\n")
print(f"✅ Saved average summary to {txt_path}")

# === PLOT ===
plt.figure(figsize=(10, 6))
plt.plot(average_df["Cycle"], average_df["Interesting_Commands"], label="Avg Interesting Commands", marker='o')
plt.plot(average_df["Cycle"], average_df["Interesting_Passcodes"], label="Avg Interesting Passcodes", marker='s')
plt.xlabel("Fuzzing Cycle")
plt.ylabel("Average Interesting Inputs")
plt.title("Average Fuzzing Effectiveness Across Runs")
plt.legend()
plt.grid(True)
plt.tight_layout()

img_path = os.path.join(directory, "average_fuzzing_plot.png")
plt.savefig(img_path)
print(f"✅ Plot saved as {img_path}")
plt.show()
