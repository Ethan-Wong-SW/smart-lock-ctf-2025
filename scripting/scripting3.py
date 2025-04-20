import os
import json
import matplotlib.pyplot as plt

# Set this to your folder if not current directory
directory = "../"
file_prefix = "json/known_errors_and_interesting_inputs_fuzzing"
file_suffix = ".json"

baseline_data = {}

# Loop over available files
for i in range(1, 30):  # Extend range if needed
    filename = f"{file_prefix}{i}{file_suffix}"
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        continue

    with open(path, 'r') as file:
        try:
            data = json.load(file)
            interesting_count = len(data)
            baseline_data[f"Fuzzing {i}"] = interesting_count
        except json.JSONDecodeError:
            print(f"[!] Skipping unreadable JSON: {filename}")
            continue

# Plotting
plt.figure(figsize=(10, 6))
labels = list(baseline_data.keys())
values = list(baseline_data.values())

plt.plot(labels, values, marker='o', linestyle='-', color='green', label="Interesting Cases")
plt.xticks(rotation=45)
plt.ylabel("#interesting test cases")
plt.xlabel("Fuzzing Iteration")
plt.title("Interesting Test Cases per Fuzzing Attempt")
plt.grid(True)
plt.tight_layout()
plt.legend()
plt.savefig("interesting_cases_plot.png")
plt.show()

# Write to TXT
with open("baseline_summary.txt", "w") as f:
    f.write("=== Baseline Summary ===\n")
    for key, val in baseline_data.items():
        f.write(f"{key}: {val} interesting test cases\n")
    f.write(f"\nTotal: {sum(values)}\n")
    f.write(f"Average per run: {sum(values)/len(values):.2f}\n")
