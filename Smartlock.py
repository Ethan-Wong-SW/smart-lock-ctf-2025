#!/usr/bin/env python3
import sys
import asyncio
import random
from BLEClient import BLEClient
from UserInterface import ShowUserInterface

DEVICE_NAME = "Smart Lock [Group 3]" # <------ Modify here to match your group. Don't hijack other groups :-)
# Commands
AUTH = [0x00]  # 7 Bytes
OPEN = [0x01]  # 1 Byte
CLOSE = [0x02]  # 1 Byte
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]  # Correct PASSCODE
# PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x07] # Wrong PASSCODE

def mutate_command(command):
    """Randomly alter a command by either mutating a byte or appending an extra one."""
    mutated = command.copy()
    if mutated and random.random() < 0.5:
        # Mutate one byte in the command.
        idx = random.randint(0, len(mutated) - 1)
        original = mutated[idx]
        mutated[idx] = random.randint(0, 255)
        print(f'[Mutation] Byte at index {idx} changed from {original} to {mutated[idx]}')
    else:
        # Append an extra random byte at the end.
        extra = random.randint(0, 255)
        mutated.append(extra)
        print(f'[Mutation] Appended extra byte: {extra}')
    return mutated

async def ensure_connection(ble):
    """Helper to verify connection and attempt reconnection if needed."""
    try:
        print("[!] Attempting to reconnect...")
        await ble.connect(DEVICE_NAME)
        print("[!] Reconnected successfully.")
    except Exception as conn_e:
        print(f"[!] Reconnection failed: {conn_e}")

async def example_control_smartlock():
    """Original fuzzer: fuzzes authentication with random passcodes
    and appends extra bytes to operational commands."""
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    # --- Fuzzing Authentication ---
    authenticated = False
    for i in range(5):
        # Create a random 6-byte passcode
        fuzz_passcode = [random.randint(0, 255) for _ in range(6)]
        print(f'[Fuzz Auth {i}] Sending AUTH command with passcode: {fuzz_passcode}')
        try:
            res = await ble.write_command(AUTH + fuzz_passcode)
        except Exception as e:
            print(f'[Fuzz Auth {i}] Error sending AUTH command: {e}')
            if "Not connected" in str(e):
                await ensure_connection(ble)
            await asyncio.sleep(1)
            continue
        if res and res[0] == 0:
            print(f'[Fuzz Auth {i}] Authenticated with fuzzed passcode: {fuzz_passcode}')
            authenticated = True
            break
        else:
            print(f'[Fuzz Auth {i}] Authentication failed with fuzzed passcode.')
        await asyncio.sleep(1)  # Short delay before retrying

    if not authenticated:
        print("[X] Fuzzing authentication did not succeed after several attempts. Exiting.")
        await ble.disconnect()
        return

    # --- Fuzzing Operational Commands ---
    command_choices = [OPEN, CLOSE]
    
    # Ensure correct passcode is input before fuzzing operational commands
    print("[Fuzz Command] Sending correct passcode for authentication before fuzzing commands.")
    try:
        res = await ble.write_command(AUTH + PASSCODE)
        if res and res[0] == 0:
            print("[Fuzz Command] Successfully authenticated with correct passcode.")
        else:
            print("[Fuzz Command] Failed to authenticate with correct passcode. Exiting.")
            await ble.disconnect()
            return
    except Exception as e:
        print(f"[Fuzz Command] Error sending correct passcode: {e}")
        if "Not connected" in str(e):
            await ensure_connection(ble)
        await ble.disconnect()
        return

    for i in range(10):
        # Append between 0 and 5 random extra bytes to the command to fuzz the structure.
        fuzz_extra = [random.randint(0, 255) for _ in range(random.randint(0, 5))]
        fuzzed_command = random.choice(command_choices) + fuzz_extra
        print(f'[Fuzz Command {i}] Sending fuzzed command: {fuzzed_command}')
        try:
            res = await ble.write_command(fuzzed_command)
        except Exception as e:
            print(f'[Fuzz Command {i}] Error sending command: {e}')
            if "Not connected" in str(e):
                await ensure_connection(ble)
            await asyncio.sleep(random.uniform(0.5, 3))
            continue
        print(f'[Fuzz Command {i}] Received response: {res}')
        # Wait a random time between commands to simulate unpredictable timing.
        await asyncio.sleep(random.uniform(0.5, 3))
    
    print("\n[Disconnecting...]")
    await ble.disconnect()

    # Output logs from the Smart Lock (Serial Port)
    print(f"\n[Logs from Smart Lock (Serial Port)]:\n{'-'*50}")
    for line in ble.read_logs():
        print(line)

    sys.exit(0)

async def example_mutation_based_fuzzer():
    """Mutation-based fuzzer: uses a valid authentication and then
    mutates valid operational commands."""
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    # --- Mutation Fuzzing for Authentication ---
    authenticated = False
    for i in range(5):
        # Mutate the valid passcode.
        mutated_passcode = mutate_command(PASSCODE)
        print(f'[Mutation Auth {i}] Sending AUTH command with mutated passcode: {mutated_passcode}')
        try:
            res = await ble.write_command(AUTH + mutated_passcode)
        except Exception as e:
            print(f'[Mutation Auth {i}] Error sending AUTH command: {e}')
            if "Not connected" in str(e):
                await ensure_connection(ble)
            await asyncio.sleep(1)
            continue
        if res and res[0] == 0:
            print(f'[Mutation Auth {i}] Authenticated with mutated passcode: {mutated_passcode}')
            authenticated = True
            break
        else:
            print(f'[Mutation Auth {i}] Authentication failed with mutated passcode.')
        await asyncio.sleep(1)  # Short delay before retrying

    if not authenticated:
        print("[X] Mutation-based authentication did not succeed after several attempts. Exiting.")
        await ble.disconnect()
        return

    # --- Mutation Fuzzing for Operational Commands ---
    command_choices = [OPEN, CLOSE]
    
    # Ensure correct passcode is input before fuzzing operational commands
    print("[Mutation Fuzz] Sending correct passcode for authentication before fuzzing commands.")
    try:
        res = await ble.write_command(AUTH + PASSCODE)
        if res and res[0] == 0:
            print("[Mutation Fuzz] Successfully authenticated with correct passcode.")
        else:
            print("[Mutation Fuzz] Failed to authenticate with correct passcode. Exiting.")
            await ble.disconnect()
            return
    except Exception as e:
        print(f"[Mutation Fuzz] Error sending correct passcode: {e}")
        if "Not connected" in str(e):
            await ensure_connection(ble)
        await ble.disconnect()
        return

    for i in range(10):
        base_cmd = random.choice(command_choices)
        mutated_command = mutate_command(base_cmd)
        print(f'[Mutation Fuzz {i}] Sending mutated command: {mutated_command}')
        try:
            res = await ble.write_command(mutated_command)
        except Exception as e:
            print(f'[Mutation Fuzz {i}] Error sending command: {e}')
            if "Not connected" in str(e):
                await ensure_connection(ble)
            await asyncio.sleep(random.uniform(0.5, 3))
            continue
        print(f'[Mutation Fuzz {i}] Received response: {res}')
        # Wait for a random time between commands to simulate unpredictable timing.
        await asyncio.sleep(random.uniform(0.5, 3))
    
    print("\n[Disconnecting...]")
    await ble.disconnect()

    # Output logs from the Smart Lock (Serial Port)
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
        # asyncio.run(example_control_smartlock())
        asyncio.run(example_mutation_based_fuzzer())
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")
