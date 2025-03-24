#!/usr/bin/env python3
import sys
import asyncio
import random
from BLEClient import BLEClient
from UserInterface import ShowUserInterface

DEVICE_NAME = "Smart Lock [Group 3]"
AUTH = [0x00]
OPEN = [0x01]
CLOSE = [0x02]
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]

def mutate_command(command):
    mutated = command.copy()
    if mutated and random.random() < 0.5:
        idx = random.randint(0, len(mutated) - 1)
        original = mutated[idx]
        mutated[idx] = random.randint(0, 255)
        print(f'[Mutation] Byte at index {idx} changed from {original} to {mutated[idx]}')
    else:
        extra = random.randint(0, 255)
        mutated.append(extra)
        print(f'[Mutation] Appended extra byte: {extra}')
    return mutated

def is_interesting(command, response, logs, seen_responses, seen_logs, seen_signatures):
    response_tuple = tuple(response) if isinstance(response, list) else (response,)
    log_tuple = tuple(logs) if isinstance(logs, list) else (logs,)
    command_tuple = tuple(command)

    signature = (command_tuple, response_tuple, log_tuple)

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

async def example_control_smartlock():
    ble = BLEClient()
    ble.init_logs()

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    seen_responses = set()
    seen_logs = set()
    seen_signatures = set()

    authenticated = False
    for i in range(5):
        fuzz_passcode = [random.randint(0, 255) for _ in range(6)]
        print(f'[Fuzz Auth {i}] Sending AUTH command with passcode: {fuzz_passcode}')
        res = await ble.write_command(AUTH + fuzz_passcode)
        logs = ble.read_logs()
        if is_interesting(AUTH + fuzz_passcode, res, logs, seen_responses, seen_logs, seen_signatures):
            print("[+] Interesting input found during authentication!")

        if res and res[0] == 0:
            print(f'[Fuzz Auth {i}] Authenticated with fuzzed passcode: {fuzz_passcode}')
            authenticated = True
            break
        else:
            print(f'[Fuzz Auth {i}] Authentication failed with fuzzed passcode.')
        await asyncio.sleep(1)

    if not authenticated:
        print("[X] Fuzzing authentication did not succeed after several attempts. Exiting.")
        await ble.disconnect()
        return

    command_choices = [OPEN, CLOSE]
    for i in range(10):
        base_cmd = random.choice(command_choices)
        fuzz_extra = [random.randint(0, 255) for _ in range(random.randint(0, 5))]
        fuzzed_command = base_cmd + fuzz_extra
        print(f'[Fuzz Command {i}] Sending fuzzed command: {fuzzed_command}')
        res = await ble.write_command(fuzzed_command)
        logs = ble.read_logs()
        if is_interesting(fuzzed_command, res, logs, seen_responses, seen_logs, seen_signatures):
            print("[+] Interesting input found during command fuzzing!")
        print(f'[Fuzz Command {i}] Received response: {res}')
        await asyncio.sleep(random.uniform(0.5, 3))

    print("\n[Disconnecting...]")
    await ble.disconnect()

    print(f"\n[Logs from Smart Lock (Serial Port)]:\n{'-'*50}")
    for line in ble.read_logs():
        print(line)

    sys.exit(0)

async def example_mutation_based_fuzzer():
    ble = BLEClient()
    ble.init_logs()

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    seen_responses = set()
    seen_logs = set()
    seen_signatures = set()

    authenticated = False
    for i in range(5):
        mutated_passcode = mutate_command(PASSCODE)
        print(f'[Mutation Auth {i}] Sending AUTH command with mutated passcode: {mutated_passcode}')
        res = await ble.write_command(AUTH + mutated_passcode)
        logs = ble.read_logs()
        if is_interesting(AUTH + mutated_passcode, res, logs, seen_responses, seen_logs, seen_signatures):
            print("[+] Interesting input found during authentication!")

        if res and res[0] == 0:
            print(f'[Mutation Auth {i}] Authenticated with mutated passcode: {mutated_passcode}')
            authenticated = True
            break
        else:
            print(f'[Mutation Auth {i}] Authentication failed with mutated passcode.')
        await asyncio.sleep(1)

    if not authenticated:
        print("[X] Mutation-based authentication did not succeed after several attempts. Exiting.")
        await ble.disconnect()
        return

    command_choices = [OPEN, CLOSE]
    for i in range(10):
        base_cmd = random.choice(command_choices)
        mutated_command = mutate_command(base_cmd)
        print(f'[Mutation Fuzz {i}] Sending mutated command: {mutated_command}')
        res = await ble.write_command(mutated_command)
        logs = ble.read_logs()
        if is_interesting(mutated_command, res, logs, seen_responses, seen_logs, seen_signatures):
            print("[+] Interesting input found during command fuzzing!")
        print(f'[Mutation Fuzz {i}] Received response: {res}')
        await asyncio.sleep(random.uniform(0.5, 3))

    print("\n[Disconnecting...]")
    await ble.disconnect()

    print(f"\n[Logs from Smart Lock (Serial Port)]:\n{'-'*50}")
    for line in ble.read_logs():
        print(line)

    sys.exit(0)

# Show User interface if command line contains --gui
if len(sys.argv) > 1 and sys.argv[1] == "--gui":
    ShowUserInterface()
else:
    try:
        # Uncomment one of the following lines to choose the fuzzer mode:
        asyncio.run(example_control_smartlock())
        # asyncio.run(example_mutation_based_fuzzer())
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")
