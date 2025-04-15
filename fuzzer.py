import os
import sys
import random
import asyncio
import datetime
from BLEClient import BLEClient

DEVICE_NAME = "Smart Lock [Group 3]"
AUTH = [0x00]  # Authenticate command
OPEN = [0x01]  # Open command
CLOSE = [0x02]  # Close command
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]  # Correct passcode
WRONGPASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x07] # Wrong PASSCODE

def flip_bits(data):
    """
    Randomly flips bits in the given byte array.
    """
    mutated_data = []
    for byte in data:
        # Randomly flip 1-3 bits in each byte
        for _ in range(random.randint(1, 3)):
            bit_to_flip = random.randint(0, 7)  # Choose a bit to flip (0-7)
            byte ^= 1 << bit_to_flip  # Flip the bit using XOR
        mutated_data.append(byte)
    return mutated_data

def append_or_remove_byte(data):
    """
    Randomly appends or removes a byte from the given byte array.
    """
    if len(data) == 0:
        # If the data is empty, just append a random byte
        return data + [random.randint(0, 255)]
    
    action = random.choice(["append", "remove"])
    
    if action == "append":
        # Append a random byte
        return data + [random.randint(0, 255)]
    else:
        # Remove a random byte
        index_to_remove = random.randint(0, len(data) - 1)
        return data[:index_to_remove] + data[index_to_remove + 1:]

def mutate_data(data):
    """
    Randomly selects between adding a byte, removing a byte, or flipping bits.
    """
    mutation_type = random.choice(["append_or_remove", "flip_bits"])
    
    if mutation_type == "append_or_remove":
        return append_or_remove_byte(data)
    else:
        return flip_bits(data)

def generate_password():
    # generate the passcode
    passcode = [random.randint(0, 255) for _ in range(6)]
    command_data = AUTH + passcode
    return command_data

def log_to_file(filename, response, logs):
    """
    Logs the command, response, and logs to a file.
    """
    with open(filename, "a") as file:
        file.write(f"Response: {response}\n")
        if (logs != ""):
            file.write(f"Errors/Logs: {logs}\n")
        file.write("-" * 50 + "\n")

def log_command(filename, command):
    """
    Logs the command, response, and logs to a file.
    """
    with open(filename, "a") as file:
        file.write(f"Timestamp: {datetime.datetime.now()}\n")
        file.write(f"Command: {command}\n")

def generate_filename():
    """
    Generates a unique filename using the current timestamp.
    """
    
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Generate a unique log filename based on the current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"fuzz_test_{timestamp}.txt")

    return log_filename

def write_fuzz_type(filename, fuzz_type):
    with open(filename, "a") as file:
        file.write(f"Fuzzing Function: {fuzz_type}\n")

async def fuzz_random_w_auth():
    authSuccess = False
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)

    # Generate a unique log file
    log_filename = generate_filename()

    write_fuzz_type(log_filename, fuzz_random_w_auth.__name__)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    # Fuzzing for the password
    for _ in range(100):
        command_data = generate_password()

        log_command(log_filename, command_data)
        print("\n[2] Authenticating...")
        res = await ble.write_command(command_data)
        
        if res[0] != 0:
            print(f"[X] Failure: Wrong Passcode.")
        else:
            print("[!] Authenticated!!!")
            authSuccess = True

        # Log the command, response, and logs
        logs = ble.read_logs()
        log_to_file(log_filename, res, logs)

    # Fuzzing loop only once authentication is approved
    if authSuccess:
        for _ in range(100):  # Run 100 fuzzing iterations
            # Randomly choose a command to fuzz
            command = random.choice([OPEN, CLOSE])

            # Mutate the command byte or add extra bytes
            command_data = command + [random.randint(0, 255) for _ in range(random.randint(0, 5))]
            
            log_command(log_filename, command_data)

            # Send the mutated command
            print(f"[!] Sending mutated command: {command_data}")
            res = await ble.write_command(command_data)
            print(f"[!] Response: {res}")

            # Log the command, response, and logs
            log_to_file(log_filename, res, logs)

            await asyncio.sleep(random.uniform(0, 5))  # Randomize delay

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    
    sys.exit(0)

async def fuzz_random_order_w_auth():
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)
    logs = ""

    # Generate a unique log file
    log_filename = generate_filename()
    write_fuzz_type(log_filename, fuzz_random_order_w_auth.__name__)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    print("\n[2] Authenticating...")
    res = await ble.write_command(AUTH + PASSCODE)

    # Fuzzing loop only once authentication is approved
    for _ in range(100):  # Run 100 fuzzing iterations
        # Randomly choose a command to fuzz
        command_data = random.choice([OPEN, CLOSE])
        
        log_command(log_filename, command_data)

        # Send the mutated command
        print(f"[!] Sending mutated command: {command_data}")
        res = await ble.write_command(command_data)
        print(f"[!] Response: {res}")

        # Log the command, response, and logs
        log_to_file(log_filename, res, logs)

        await asyncio.sleep(random.uniform(0, 5))  # Randomize delay

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    
    sys.exit(0)

async def fuzz_random_without_auth():
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)

    # Generate a unique log file
    log_filename = generate_filename()
    write_fuzz_type(log_filename, fuzz_random_without_auth.__name__)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    # Fuzzing loop without approved authentication    
    for _ in range(100):  # Run 100 fuzzing iterations
        # Randomly choose a command to fuzz
        command = random.choice([OPEN, CLOSE])

        # Mutate the command byte or add extra bytes
        command_data = command + [random.randint(0, 255) for _ in range(random.randint(0, 5))]
        
        log_command(log_filename, command_data)

        # Send the mutated command
        print(f"[!] Sending mutated command: {command_data}")
        res = await ble.write_command(command_data)
        print(f"[!] Response: {res}")

        if res[0] != 3:
            logs = "[X] Unexpected Error detected!"
        else:
            logs = ""

        # Log the command, response, and logs
        log_to_file(log_filename, res, logs)

        await asyncio.sleep(random.uniform(0, 5))  # Randomize delay

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    
    sys.exit(0)

async def fuzz_random_with_incorrect_auth():
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)

    # Generate a unique log file
    log_filename = generate_filename()
    write_fuzz_type(log_filename, fuzz_random_with_incorrect_auth.__name__)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    print("\n[2] Authenticating...")
    res = await ble.write_command(AUTH + WRONGPASSCODE)

    # Fuzzing loop without approved authentication    
    for _ in range(100):  # Run 100 fuzzing iterations
        # Randomly choose a command to fuzz
        command = random.choice([OPEN, CLOSE])

        # Mutate the command byte or add extra bytes
        command_data = command + [random.randint(0, 255) for _ in range(random.randint(0, 5))]
        
        log_command(log_filename, command_data)

        # Send the mutated command
        print(f"[!] Sending mutated command: {command_data}")
        res = await ble.write_command(command_data)
        print(f"[!] Response: {res}")

        # Check for unexpected behavior. since authentication is incorrect, the response should be 3 (Command Not Allowed (Not Authenticated))
        if res[0] != 3:
            logs = "[X] Unexpected Error detected!"
        else:
            logs = ""

        # Log the command, response, and logs
        log_to_file(log_filename, res, logs)

        await asyncio.sleep(random.uniform(0, 5))  # Randomize delay

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    
    sys.exit(0)

async def fuzz_mutation():
    authSuccess = False
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)

    # Generate a unique log file
    log_filename = generate_filename()
    write_fuzz_type(log_filename, fuzz_mutation.__name__)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    command_data = PASSCODE

    # Fuzzing for the password
    for _ in range(100):
        command_data = mutate_data(command_data)  # mutate prev passcode

        log_command(log_filename, command_data)

        print("\n[2] Authenticating...")
        res = await ble.write_command(command_data)
        
        if res[0] != 0:
            print(f"[X] Failure: Wrong Passcode.")
        else:
            print("[!] Authenticated!!!")
            authSuccess = True

        # Log the command, response, and logs
        logs = ble.read_logs()
        log_to_file(log_filename, res, logs)

    # Fuzzing loop only once authentication is approved
    if authSuccess:
        for _ in range(100):  # Run 100 fuzzing iterations
            # Randomly choose a command to fuzz
            command = random.choice([OPEN, CLOSE])

            # Mutate the command byte or add extra bytes
            command_data = mutate_data(command)
            
            log_command(log_filename, command_data)

            # Send the mutated command
            print(f"[!] Sending mutated command: {command_data}")
            res = await ble.write_command(command_data)
            print(f"[!] Response: {res}")

            # Log the command, response, and logs
            log_to_file(log_filename, res, logs)

            await asyncio.sleep(random.uniform(0, 5))  # Randomize delay

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    
    sys.exit(0)

# there might be some bugs with this function, especially if the input for the command is just 0 or empty. 0 will cause the smart lock to hang
async def fuzz_mutation_without_auth():
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)
    logs = ""

    # Generate a unique log file
    log_filename = generate_filename()
    write_fuzz_type(log_filename, fuzz_mutation_without_auth.__name__)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    # Fuzzing loop without approved authentication    
    for _ in range(100):  # Run 100 fuzzing iterations
        # Randomly choose a command to fuzz
        command = random.choice([OPEN, CLOSE])

        # Mutate the command byte
        command_data = mutate_data(command)
        
        log_command(log_filename, command_data)

        if (len(command_data) == 0):
            log_to_file(log_filename, "", "Command is NULL/empty")
            continue

        # Send the mutated command
        print(f"[!] Sending mutated command: {command_data}")
        res = await ble.write_command(command_data)
        print(f"[!] Response: {res}")

        if res[0] != 3 and res[0] != 2:
            logs = "[X] Unexpected Error detected!"
        else:
            logs = ""

        # Log the command, response, and logs
        log_to_file(log_filename, res, logs)

        await asyncio.sleep(random.uniform(0, 5))  # Randomize delay

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    
    sys.exit(0)

# there might be some bugs with this function, especially if the input for the command is just 0 or empty. 0 will cause the smart lock to hang
async def fuzz_mutation_with_incorrect_auth():
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)
    logs = ""

    # Generate a unique log file
    log_filename = generate_filename()
    write_fuzz_type(log_filename, fuzz_mutation_with_incorrect_auth.__name__)

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    print("\n[2] Authenticating...")
    res = await ble.write_command(AUTH + WRONGPASSCODE)

    # Fuzzing loop without approved authentication    
    for _ in range(100):  # Run 100 fuzzing iterations
        # Randomly choose a command to fuzz
        command = random.choice([OPEN, CLOSE])

        # Mutate the command byte
        command_data = mutate_data(command)
        
        log_command(log_filename, command_data)

        if (len(command_data) == 0):
            log_to_file(log_filename, "", "Command is NULL/empty")
            continue

        # Send the mutated command
        print(f"[!] Sending mutated command: {command_data}")
        res = await ble.write_command(command_data)
        print(f"[!] Response: {res}")

        if res[0] != 3 and res[0] != 2:
            logs = "[X] Unexpected Error detected!"
        else:
            logs = ""

        # Log the command, response, and logs
        log_to_file(log_filename, res, logs)

        await asyncio.sleep(random.uniform(0, 5))  # Randomize delay

    print("\n[5] Disconnecting...")
    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n{'-'*50}")
    lines = ble.read_logs()  # Return a list of all log lines.
    for line in lines:
        print(line)
    
    sys.exit(0)

# Run the fuzzer
try:
    random.seed(None)   # Set the seed here, if necessary
    asyncio.run(fuzz_random_w_auth())      # random fuzzing
    # asyncio.run(fuzz_random_order_w_auth())      # random fuzzing
    # asyncio.run(fuzz_random_with_incorrect_auth())      # random fuzzing
    # asyncio.run(fuzz_random_without_auth())      # random fuzzing
    # asyncio.run(fuzz_mutation())    # mutation fuzzing
except KeyboardInterrupt:
    print("\nProgram Exited by User!")

