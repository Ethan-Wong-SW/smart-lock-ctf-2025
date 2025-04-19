import re
import pandas as pd
import matplotlib.pyplot as plt

logfile = "logs/fuzz_test_20250419_035503_fuzzing7.txt"

with open(logfile, 'r') as f:
    lines = f.readlines()

data = []
current_cycle = None
ip = ic = err = t_cycle = t_total = exec_time = None

for line in lines:
    if "Starting new fuzzing cycle" in line:
        match = re.search(r"Attempt (\d+)", line)
        if match:
            current_cycle = int(match.group(1))

    elif "Total Interesting passcodes" in line:
        ip = int(re.search(r"\d+", line).group())

    elif "Total Interesting commands" in line:
        ic = int(re.search(r"\d+", line).group())

    elif "Total Known errors" in line:
        err = int(re.search(r"\d+", line).group())

    elif "Tests done for this cycle" in line:
        t_cycle = int(re.search(r"\d+", line).group())

    elif "Total Tests done" in line:
        t_total = int(re.search(r"\d+", line).group())

    elif "Avg execution time" in line:
        exec_time = float(re.search(r"[\d.]+", line).group())

        # Only add when all fields are filled (i.e., end of current cycle)
        if all(v is not None for v in [current_cycle, ip, ic, err, t_cycle, t_total, exec_time]):
            data.append({
                "Cycle": current_cycle,
                "Interesting_Passcodes": ip,
                "Interesting_Commands": ic,
                "Errors": err,
                "Tests_This_Cycle": t_cycle,
                "Total_Tests": t_total,
                "Avg_Execution_Time": exec_time
            })

            # Reset values for next cycle
            ip = ic = err = t_cycle = t_total = exec_time = None

# Convert to DataFrame
df = pd.DataFrame(data)

# Save to CSV
df.to_csv("cycle_stats7.csv", index=False)

# Save to TXT (human-readable format)
with open("cycle_stats7.txt", "w") as txt_file:
    for index, row in df.iterrows():
        txt_file.write(f"Cycle {row['Cycle']}:\n")
        txt_file.write(f"  Interesting Passcodes: {row['Interesting_Passcodes']}\n")
        txt_file.write(f"  Interesting Commands:  {row['Interesting_Commands']}\n")
        txt_file.write(f"  Errors:                {row['Errors']}\n")
        txt_file.write(f"  Tests This Cycle:      {row['Tests_This_Cycle']}\n")
        txt_file.write(f"  Total Tests:           {row['Total_Tests']}\n")
        txt_file.write(f"  Avg Execution Time:    {row['Avg_Execution_Time']} s\n\n")

print("✅ CSV and TXT outputs saved.")

# Optional: Plotting
plt.plot(df["Total_Tests"], df["Interesting_Commands"], label="Interesting Commands", marker='o')
plt.plot(df["Total_Tests"], df["Interesting_Passcodes"], label="Interesting Passcodes", marker='s')
plt.xlabel("Total Tests")
plt.ylabel("Interesting Inputs")
plt.title("Effectiveness of Fuzzing")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
