import re
import glob
import os
import matplotlib.pyplot as plt

CUSTOM_LABELS = {
    'fuzz_test_20250422_183714_rm_1.txt': 'Mutation, Random & State tracker',
    'fuzz_test_20250422_185942_random_state.txt': 'Random & State tracker',
    'fuzz_test_20250422_192644_mutation_state.txt': 'Mutation & State tracker',
    'fuzz_test_20250422_200546_random.txt' : 'Random Only',
    'fuzz_test_20250422_205334_mutation.txt' : 'Mutation Only'
}

def parse_fuzzing_log(filename):
    total_tests = []
    total_interesting = []

    with open(filename, 'r') as file:
        text = file.read()

        cycle_summaries = re.findall(
            r'Total Interesting passcodes:\s*(\d+)\s*'
            r'Total Interesting commands:\s*(\d+)\s*'
            r'Total Known errors:\s*(\d+)\s*'
            r'Tests done for this cycle:\s*(\d+)\s*'
            r'Total Tests done:\s*(\d+)',
            text
        )

        for summary in cycle_summaries:
            interesting_passcodes = int(summary[0])
            interesting_commands = int(summary[1])
            total_tests_done = int(summary[4])

            total_interesting.append(interesting_passcodes + interesting_commands)
            total_tests.append(total_tests_done)

    return total_tests, total_interesting

def plot_graph_for_directory(directory_path):
    log_files = glob.glob(os.path.join(directory_path, '*.txt'))
    
    all_data = []

    # Step 1: Parse and collect data
    for log_file in log_files:
        total_tests, total_interesting = parse_fuzzing_log(log_file)
        if total_tests and total_interesting:
            all_data.append({
                'filename': os.path.basename(log_file),
                'total_tests': total_tests,
                'total_interesting': total_interesting
            })

    if not all_data:
        print("[ERROR] No valid data found in logs.")
        return

    # Step 2: Find shortest max total tests across all logs
    min_xmax = min(max(data['total_tests']) for data in all_data)
    print(f"[INFO] Truncating all graphs to Total Tests Done ≤ {min_xmax}")

    # Step 3: Plot with truncation
    for data in all_data:
        truncated_x = []
        truncated_y = []
        for x, y in zip(data['total_tests'], data['total_interesting']):
            if x <= min_xmax:
                truncated_x.append(x)
                truncated_y.append(y)
        label = CUSTOM_LABELS.get(data['filename'], data['filename'])
        plt.plot(truncated_x, truncated_y, label=label, marker='o', markersize=1)


    plt.xlabel('Total Tests Done')
    plt.ylabel('Total Interesting Inputs (Commands + Passcodes)')
    plt.title('RQ3 Baseline (Ablation)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('ablation.png')

if __name__ == '__main__':
    logs_directory = './ablation_logs'
    plot_graph_for_directory(logs_directory)
