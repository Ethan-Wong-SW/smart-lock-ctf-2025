#!/usr/bin/env python3
import sys
import asyncio
from BLEClient import BLEClient
from UserInterface import ShowUserInterface

DEVICE_NAME = "Smart Lock [Group 3]"
# Commands
AUTH = [0x00]  # 7 Bytes
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]  # Correct PASSCODE
WRONG_PASSCODE = [1, 2, 3, 4, 5, 6, 188]

async def print_new_logs(ble, idx):
    """Print only new logs since last index and return new last index"""
    await asyncio.sleep(0.25)  # Allow time for response
    logs = ble.read_logs()
    
    # Print only new logs since last time
    for line in logs[idx:]:
        print(line)
    
    # Return new last index
    return len(logs)

async def run_test_case(test_name, auth_input, commands):
    """Generic function to run a test case"""
    ble = BLEClient()
    ble.init_logs()
    last_log_index = 0

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)
    last_log_index = await print_new_logs(ble, last_log_index)

    print(f"\n[2] Authenticating for {test_name}...")
    res = await ble.write_command(AUTH + auth_input)
    last_log_index = await print_new_logs(ble, last_log_index)

    if auth_input == PASSCODE:
        print("[!] Authenticated!!!")
    else:
        print("[!] Used alternative authentication input")
    
    await asyncio.sleep(2)

    try:
        for i, cmd in enumerate(commands, 3):
            print(f"\n[{i}] Sending command: {cmd}")
            res = await ble.write_command(cmd)
            last_log_index = await print_new_logs(ble, last_log_index)
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Exception occurred: {e}")
        last_log_index = await print_new_logs(ble, last_log_index)

    print(f"\n[Final] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()
    for line in lines:
        print(line)

    print("\n[Disconnecting...]\n")
    await ble.disconnect()

# Test case for 0x018374
async def error_0x018374():
    print("\n=== Running test for error code 0x018374 ===")
    await run_test_case("0x018374", PASSCODE, [[0]])

# Test case for 0x398472
async def error_0x398472():
    print("\n=== Running test for error code 0x398472 ===")
    await run_test_case("0x398472", PASSCODE, [[1, 2], [1, 193, 113, 38, 195]])

# Test case for blue screen (0x******)
async def error_blue_screen():
    print("\n=== Running test for blue screen error ===")
    await run_test_case("blue screen", WRONG_PASSCODE, [])

# Test case for 0xtttttt
async def error_0xtttttt():
    print("\n=== Running test for error code 0xtttttt ===")
    await run_test_case("0xtttttt", PASSCODE, [[255, 255, 255, 255, 0, 8]])

# Test case for OSError: [WinError -2147023673] The operation was canceled by the user
async def error_oserror():
    print("\n=== Running test for OSError ===")
    await run_test_case("OSError", PASSCODE, [[2,47,162,72,162,72,65], [0, 243, 32, 1, 32, 146, 133, 130, 117]])

# Test case for 0x298173
async def error_0x298173():
    print("\n=== Running test for error code 0x298173 ===")
    await run_test_case("0x298173", PASSCODE, [[]])

try:
    # Run a specific test:
    # asyncio.run(error_0x018374()) 
    # asyncio.run(error_0x398472()) 
    # asyncio.run(error_blue_screen()) 
    # asyncio.run(error_oserror()) 
    # asyncio.run(error_0xtttttt()) 
    asyncio.run(error_0x298173()) 
except KeyboardInterrupt:
    print("\nProgram Exited by User!")