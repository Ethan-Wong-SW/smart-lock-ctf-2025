import os
import json
import matplotlib.pyplot as plt

# === CONFIGURATION ===
directory = "."  # set to directory where JSON files are stored
prefix = "known_errors_and_interesting_inputs_fuzzing"
output_txt = "stability_rq4_report.txt"
output_img = "stability_rq4_plot.png"
num_sessions = 8  # update this based on how many runs you have

# === STORAGE ===
interesting_counts = []
unique_crash_counts = []

# === PARSE JSON FILES ===
for i in range(1, num_sessions + 1):
    file_path = os.path.join(directory, f"{prefix}{i}.json")

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"[!] Could not read session {i} file.")
        interesting_counts.append(0)
        unique_crash_counts.append(0)
        continue

    # Count interesting test cases
    interesting_count = len(data)

    # Count unique crash types based on error message content
    crash_set = set()
    for item in data:
        if 'error' in item:
            crash_set.add(item['error'])

    interesting_counts.append(interesting_count)
    unique_crash_counts.append(len(crash_set))

# === WRITE TO TXT FILE ===
with open(output_txt, 'w') as f:
    f.write("=== Stability Metrics (RQ4) ===\n")
    for i in range(num_sessions):
        f.write(f"Session {i+1}:\n")
        f.write(f"  Interesting Test Cases: {interesting_counts[i]}\n")
        f.write(f"  Unique Crashes: {unique_crash_counts[i]}\n\n")
    f.write(f"Avg Interesting Test Cases: {sum(interesting_counts)/num_sessions:.2f}\n")
    f.write(f"Avg Unique Crashes: {sum(unique_crash_counts)/num_sessions:.2f}\n")

print(f"[✓] Stability report written to {output_txt}")

# === PLOT CHART ===
x = [f"Session {i+1}" for i in range(num_sessions)]
bar_width = 0.35
x_pos = range(len(x))

plt.figure(figsize=(12, 6))
plt.bar(x_pos, interesting_counts, width=bar_width, label='Interesting Test Cases', hatch='///')
plt.bar([p + bar_width for p in x_pos], unique_crash_counts, width=bar_width, label='Unique Crashes', hatch='\\\\\\')
plt.xlabel("Fuzzing Sessions")
plt.ylabel("#Interesting Tests / #Unique Crashes")
plt.title("RQ4 Stability: Interesting Cases & Unique Crashes per Session")
plt.xticks([p + bar_width / 2 for p in x_pos], x)
plt.legend()
plt.tight_layout()
plt.savefig(output_img)
plt.close()

print(f"[✓] Bar chart saved as {output_img}")
