import os
import sys
import random
import asyncio
import datetime
import traceback
from BLEClient import BLEClient

ble = None
log_filename = None

# Global exception handler to log crashes
def global_exception_handler(exc_type, exc_value, exc_traceback):
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    dir = "crashlogs"
    os.makedirs(dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_log_filename = os.path.join(dir, f"crash_log_{timestamp}.txt")
    with open(crash_log_filename, "a") as file:
        file.write(f"Crash occurred at: {datetime.datetime.now()}\n")
        file.write(error_message)
        file.write("-" * 50 + "\n")
    print(f"[X] Crash occurred! Details logged to {crash_log_filename}")
    if 'ble' in globals() and ble is not None and log_filename is not None: 
        print("\n[Cleanup] Disconnecting from the smart lock...")
        log_comment(log_filename, "[Cleanup] Disconnecting from the smart lock...\n")
        asyncio.run(ble.disconnect())
        print(f"\n[Cleanup] Logs from Smart Lock (Serial Port):\n")
        log_comment(log_filename, "[Cleanup] Logs from Smart Lock (Serial Port):\n")
        lines = ble.read_logs()
        for line in lines:
            print(line)
            log_comment(log_filename, line)
    sys.exit(1)

sys.excepthook = global_exception_handler

DEVICE_NAME = "Smart Lock [Group 3]"
AUTH = [0x00]
OPEN = [0x01]
CLOSE = [0x02]
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
WRONGPASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x07]

class SmartLockState:
    LOCKED = "Locked"
    AUTHENTICATING = "Authenticating"
    AUTHENTICATED = "Authenticated"
    UNLOCKED = "Unlocked"
    AUTHENTICATED_AND_AUTHENTICATING_AGAIN = "authenticated once and authenticating again"

def is_interesting(command, response, logs, current_state, seen_responses, seen_logs, seen_signatures):
    response_tuple = tuple(response) if isinstance(response, list) else (response,)
    log_tuple = tuple(logs) if isinstance(logs, list) else (logs,)
    command_tuple = tuple(command)
    signature = (command_tuple, response_tuple, current_state, log_tuple)

    new_response = response_tuple not in seen_responses
    new_log = log_tuple not in seen_logs
    new_signature = signature not in seen_signatures

    if new_response:
        seen_responses.add(response_tuple)
    if new_log:
        seen_logs.add(log_tuple)
    if new_signature:
        seen_signatures.add(signature)

    return new_response or new_log or new_signature

def flip_bits(data):
    mutated_data = []
    for byte in data:
        for _ in range(random.randint(1, 3)):
            bit_to_flip = random.randint(0, 7)
            byte ^= 1 << bit_to_flip
        mutated_data.append(byte)
    return mutated_data

def append_or_remove_byte(data):
    if len(data) == 0:
        return data + [random.randint(0, 255)]
    action = random.choice(["append", "remove"])
    if action == "append":
        return data + [random.randint(0, 255)]
    else:
        index_to_remove = random.randint(0, len(data) - 1)
        return data[:index_to_remove] + data[index_to_remove + 1:]

def mutate_data(data):
    return append_or_remove_byte(data) if random.random() < 0.5 else flip_bits(data)

def generate_password():
    passcode = [random.randint(0, 255) for _ in range(1, 6)]
    return AUTH + passcode

def log_to_file(filename, command, response, error):
    with open(filename, "a") as file:
        file.write(f"[!] --> Command: {command}\n")
        file.write(f"[!] <-- Response: {response}\n")
        file.write(error + "\n")
        file.write("-" * 50 + "\n")

def log_comment(filename, comment):
    with open(filename, "a") as file:
        file.write(comment + "\n")

def generate_filename():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(log_dir, f"fuzz_test_{timestamp}.txt")

def write_fuzz_type(filename, fuzz_type):
    with open(filename, "a") as file:
        file.write(f"Fuzzing Function: {fuzz_type}\n")

async def fuzz_with_state_tracking():
    global ble, log_filename
    ble = BLEClient()
    ble.init_logs()
    log_filename = generate_filename()
    current_state = SmartLockState.LOCKED

    seen_responses = set()
    seen_logs = set()
    seen_signatures = set()

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)
    log_comment(log_filename, "Fuzzing Password now")

    for i in range(100):
        command_data = generate_password()
        print("\n[2] Authenticating...")
        log_comment(log_filename, "[2] Authenticating...")

        if current_state == SmartLockState.AUTHENTICATED:
            current_state = SmartLockState.AUTHENTICATED_AND_AUTHENTICATING_AGAIN
        elif current_state != SmartLockState.AUTHENTICATED_AND_AUTHENTICATING_AGAIN:
            current_state = SmartLockState.AUTHENTICATING

        print("current state:", current_state)
        res = await ble.write_command(command_data)
        error = ""

        if res[0] != 0 and current_state == SmartLockState.AUTHENTICATING:
            print("[X] Failure: Wrong Passcode.")
            current_state = SmartLockState.LOCKED
            error = current_state + "\n" + "[X] Failure: Wrong Passcode."
        elif res[0] == 0 and current_state == SmartLockState.AUTHENTICATING:
            print("[!] Authenticated!!!")
            current_state = SmartLockState.AUTHENTICATED
            error = current_state + "\n" + "[!] Authenticated!!!"

        logs = ble.read_logs()
        if is_interesting(command_data, res, logs, current_state, seen_responses, seen_logs, seen_signatures):
            print("[+] Interesting input found during authentication!")
            log_comment(log_filename, "[+] Interesting input found during authentication!")

        log_to_file(log_filename, command_data, res[0], error)

    if current_state == SmartLockState.AUTHENTICATED_AND_AUTHENTICATING_AGAIN:
        current_state = SmartLockState.AUTHENTICATED

    log_comment(log_filename, "Fuzzing command now\n")

    for _ in range(100):
        command = random.choice([OPEN, CLOSE])
        command_data = mutate_data(command)
        print("current state:", current_state)

        log_comment(log_filename, "[3] Sending command")
        print(f"[3] Sending command: {command_data}")

        if not command_data:
            state = "Current state: " + current_state
            log_to_file(log_filename, command_data, [0], state)
            continue

        res = await ble.write_command(command_data)
        print(f"[!] Response: {res}")

        if command == OPEN and res[0] == 0:
            current_state = SmartLockState.UNLOCKED
        elif command == CLOSE and res[0] == 0:
            current_state = SmartLockState.LOCKED

        logs = ble.read_logs()
        state = "Current state: " + current_state

        if is_interesting(command_data, res, logs, current_state, seen_responses, seen_logs, seen_signatures):
            print("[+] Interesting input found during command fuzzing!")
            log_comment(log_filename, "[+] Interesting input found during command fuzzing!")

        log_to_file(log_filename, command_data, res, state)
        await asyncio.sleep(random.uniform(0, 5))

    print("\n[5] Disconnecting...")
    log_comment(log_filename, "[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n")
    log_comment(log_filename, "[6] Logs from Smart Lock (Serial Port):")
    lines = ble.read_logs()
    print(len(lines))
    for line in lines:
        print(line)
        log_comment(log_filename, line)

    sys.exit(0)

# Run the fuzzer
try:
    random.seed(None)
    asyncio.run(fuzz_with_state_tracking())
except KeyboardInterrupt:
    print("\nProgram Exited by User!")
