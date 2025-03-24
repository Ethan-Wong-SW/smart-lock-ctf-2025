#!/usr/bin/env python3
import sys
import asyncio
from BLEClient import BLEClient
from UserInterface import ShowUserInterface

DEVICE_NAME = "Smart Lock [Group 3]"
AUTH = [0x00]
OPEN = [0x01]
CLOSE = [0x02]
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]

# Track previously seen responses and logs
seen_responses = set()
seen_logs = set()
seen_signatures = set()

def is_interesting(command, response, logs):
    """
    Determines whether the given input/response/log combo is interesting.
    """
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

    print("\n[2] Authenticating...")
    res = await ble.write_command(AUTH + PASSCODE)
    logs = ble.read_logs()
    if is_interesting(AUTH + PASSCODE, res, logs):
        print("[+] Interesting behavior during authentication!")
    if res[0] != 0:
        print(f"[X] Failure: Wrong Passcode.")
        await ble.disconnect()
        return

    print("[!] Authenticated!!!")
    await asyncio.sleep(2)

    print("\n[3] Opening")
    res = await ble.write_command(OPEN)
    logs = ble.read_logs()
    if is_interesting(OPEN, res, logs):
        print("[+] Interesting behavior during OPEN!")

    await asyncio.sleep(2)

    print("\n[4] Closing")
    res = await ble.write_command(CLOSE)
    logs = ble.read_logs()
    if is_interesting(CLOSE, res, logs):
        print("[+] Interesting behavior during CLOSE!")

    await asyncio.sleep(2)

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()
    for line in lines:
        print(line)

    sys.exit(0)

# GUI support
if len(sys.argv) > 1 and sys.argv[1] == "--gui":
    ShowUserInterface()
else:
    try:
        asyncio.run(example_control_smartlock())
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")
