import os
import re
from glob import glob

log_dir = "../logs/"
output_file = "../stats/combined_efficiency_metrics.txt"

log_files = glob(os.path.join(log_dir, "fuzz_test_*.txt"))

# Global aggregates
global_exec_times = {}
global_gen_times = []
first_crash_cycles = []

for logfile in log_files:
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

    # Append results from this file
    global_exec_times.update(exec_times)
    global_gen_times.extend(gen_times)
    if first_crash_cycle is not None:
        first_crash_cycles.append(first_crash_cycle)

# Combined Metrics
avg_gen_time = sum(global_gen_times) / len(global_gen_times) if global_gen_times else None
overall_avg_exec = sum(global_exec_times.values()) / len(global_exec_times) if global_exec_times else None
earliest_crash = min(first_crash_cycles) if first_crash_cycles else None

# Write combined results
with open(output_file, 'w') as out:
    out.write("=== Combined Efficiency Metrics ===\n")
    out.write(f"Time to First Crash (Earliest Cycle): {earliest_crash if earliest_crash else 'N/A'}\n")

    if avg_gen_time is not None:
        out.write(f"Avg Time to Generate Test: {avg_gen_time:.10f}s\n")
    else:
        out.write("Avg Time to Generate Test: N/A\n")

    out.write("Avg Time to Run Test (per cycle across all files):\n")
    for cycle in sorted(global_exec_times.keys()):
        out.write(f"  Cycle {cycle}: {global_exec_times[cycle]:.5f}s\n")

    if overall_avg_exec is not None:
        out.write(f"\nOverall Avg Time to Run Test: {overall_avg_exec:.5f}s\n")

print(f"[✓] Combined efficiency metrics written to {output_file}")
