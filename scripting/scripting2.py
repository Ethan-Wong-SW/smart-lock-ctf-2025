import re

logfile = "logs/fuzz_test_20250419_030123_fuzzing4.txt"
output_file = "stats/efficiency_metrics4.txt"

with open(logfile, 'r') as f:
    lines = f.readlines()

exec_times = {}
gen_times = []
first_crash_cycle = None
current_cycle = None

for line in lines:
    if "Starting new fuzzing cycle" in line:
        match = re.search(r"Attempt (\d+)", line)
        if match:
            current_cycle = int(match.group(1))

    elif "Avg execution time" in line:
        match = re.search(r"[\d\.]+", line)
        if match and current_cycle is not None:
            exec_times[current_cycle] = float(match.group())

    elif "Avg generation time" in line or "Avg time to generate" in line:
        match = re.search(r"[\d\.]+", line)
        if match:
            val = float(match.group())
            if val > 0:
                gen_times.append(val)

    elif "Known errors" in line:
        match = re.search(r"(\d+)", line)
        if match and first_crash_cycle is None:
            if int(match.group()) > 0:
                first_crash_cycle = current_cycle

# Calculate averages
avg_gen_time = sum(gen_times) / len(gen_times) if gen_times else None
overall_avg_exec = sum(exec_times.values()) / len(exec_times) if exec_times else None

# Write to file
with open(output_file, 'w') as out:
    out.write("=== Efficiency Metrics ===\n")
    out.write(f"Time to First Crash: Cycle {first_crash_cycle if first_crash_cycle else 'N/A'}\n")

    if avg_gen_time is not None:
        out.write(f"Avg Time to Generate Test: {avg_gen_time:.10f}s\n")
    else:
        out.write("Avg Time to Generate Test: N/A\n")

    out.write("Avg Time to Run Test (per cycle):\n")
    for cycle in sorted(exec_times.keys()):
        out.write(f"  Cycle {cycle}: {exec_times[cycle]:.5f}s\n")

    if overall_avg_exec is not None:
        out.write(f"\nOverall Avg Time to Run Test: {overall_avg_exec:.5f}s\n")

print(f"[✓] Efficiency metrics written to {output_file}")
