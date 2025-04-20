#!/usr/bin/env python3
import sys
import asyncio
from BLEClient import BLEClient
from UserInterface import ShowUserInterface

DEVICE_NAME = "Smart Lock [Group 3]" # <------ Modify here to match your group. Don't hijack other groups :-)
# Commands
AUTH = [0x00]  # 7 Bytes
OPEN = [0x01]  # 1 Byte
CLOSE = [0x02]  # 1 Byte
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]  # Correct PASSCODE
WRONG_PASSCODE = [1,2,3,4,5,6,188]
# PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x07] # Wrong PASSCODE

async def print_new_logs(ble, idx):
    """Print only new logs since last index and return new last index"""
    await asyncio.sleep(0.25)  # Allow time for response
    logs = ble.read_logs()
    
    # Print only new logs since last time
    for line in logs[idx:]:
        print(line)
    
    # Return new last index
    return len(logs)

async def example_control_smartlock():
    # Use this code as template to create your fuzzer
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)
    last_log_index = 0

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)
    last_log_index = await print_new_logs(ble, last_log_index)

    print("\n[2] Authenticating...")
    res = await ble.write_command(AUTH + PASSCODE)
    # res = await ble.write_command(AUTH + WRONG_PASSCODE)
    last_log_index = await print_new_logs(ble, last_log_index)
    # if res[0] != 0:
    #     print(f"[X] Failure: Wrong Passcode.")
    #     await ble.disconnect()
    #     return

    print("[!] Authenticated!!!")
    await asyncio.sleep(2)

    try:
        print("\n[3] input: [0]")
        # print("\n[3] Opening")
        res = await ble.write_command([0])
        last_log_index = await print_new_logs(ble, last_log_index)
        await asyncio.sleep(1)
    except Exception as e:
        print(e)
        last_log_index = await print_new_logs(ble, last_log_index)

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    # TIP: Use lines[-1] to get the most recent line

    # print("\n[5] Disconnecting...")
    await ble.disconnect()

    sys.exit(0)



# Show User interface if command line contains --gui
if len(sys.argv) > 1 and sys.argv[1] == "--gui":
    ShowUserInterface()
else:
    # Ortherwise, run this example
    try:
        asyncio.run(example_control_smartlock())
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")

