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
    """
    Global exception handler to log unexpected crashes.
    """
    # Format the exception details
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Log the crash to a file
    dir = "crashlogs"
    os.makedirs(dir, exist_ok=True)

    # Generate a unique log filename based on the current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_log_filename = os.path.join(dir, f"crash_log_{timestamp}.txt")

    with open(crash_log_filename, "a") as file:
        file.write(f"Crash occurred at: {datetime.datetime.now()}\n")
        file.write(error_message)
        file.write("-" * 50 + "\n")
    
    # Print the error to the console (optional)
    print(f"[X] Crash occurred! Details logged to {crash_log_filename}")

    # Perform cleanup
    if 'ble' in globals() and ble is not None and log_filename is not None: 
        print("\n[Cleanup] Disconnecting from the smart lock...")
        log_comment(log_filename, "[Cleanup] Disconnecting from the smart lock...\n")
        asyncio.run(ble.disconnect())  # Disconnect the Bluetooth connection

        print(f"\n[Cleanup] Logs from Smart Lock (Serial Port):\n")
        log_comment(log_filename, "[Cleanup] Logs from Smart Lock (Serial Port):\n")
        lines = ble.read_logs()  # Return a list of all log lines.
        for line in lines:
            print(line)
            log_comment(log_filename, line)

    # Exit the program
    sys.exit(1)

# Set the global exception handler
sys.excepthook = global_exception_handler

DEVICE_NAME = "Smart Lock [Group 3]"
AUTH = [0x00]  # Authenticate command
OPEN = [0x01]  # Open command
CLOSE = [0x02]  # Close command
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]  # Correct passcode
WRONGPASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x07] # Wrong PASSCODE

class SmartLockState:
    LOCKED = "Locked"
    AUTHENTICATING = "Authenticating"
    AUTHENTICATED = "Authenticated"
    UNLOCKED = "Unlocked"
    AUTHENTICATED_AND_AUTHENTICATING_AGAIN = "authenticated once and authenticating again"


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
    passcode = [random.randint(0, 255) for _ in range(1, 6)]
    command_data = AUTH + passcode
    return command_data

def log_to_file(filename, command, response, error):
    """
    Logs the command, response, and logs to a file.
    """
    with open(filename, "a") as file:
        file.write(f"[!] --> Command: {command}\n")
        file.write(f"[!] <-- Response: {response}\n")
        file.write(error + "\n")
        file.write("-" * 50 + "\n")

def log_comment(filename, comment):
    """
    Logs the given string to file.
    """
    with open(filename, "a") as file:
        file.write(comment + "\n")


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

async def fuzz_with_state_tracking():
    ble = BLEClient()
    ble.init_logs()  # Collect logs from Smart Lock (Serial Port)

    # Generate a unique log file
    log_filename = generate_filename()

    # Initialize the state machine
    current_state = SmartLockState.LOCKED

    print(f'[1] Connecting to "{DEVICE_NAME}"...')
    await ble.connect(DEVICE_NAME)

    log_comment(log_filename, "Fuzzing Password now")

    index = 0

    # Fuzzing for the password
    for i in range(100):
        command_data = generate_password()

        print("\n[2] Authenticating...")
        log_comment(log_filename, "[2] Authenticating...")
        
        if current_state == SmartLockState.AUTHENTICATED:
            current_state = SmartLockState.AUTHENTICATED_AND_AUTHENTICATING_AGAIN  # Update state
        elif current_state != SmartLockState.AUTHENTICATED_AND_AUTHENTICATING_AGAIN:
            current_state = SmartLockState.AUTHENTICATING  # Update state

        print("current state: " , current_state)

        res = await ble.write_command(command_data)
        
        error = ""

        if res[0] != 0 and current_state == SmartLockState.AUTHENTICATING:
            print(f"[X] Failure: Wrong Passcode.")
            current_state = SmartLockState.LOCKED  # Revert to locked state
            error = current_state + "\n" + "[X] Failure: Wrong Passcode."
        elif res[0] == 0 and current_state == SmartLockState.AUTHENTICATING:
            print("[!] Authenticated!!!")
            current_state = SmartLockState.AUTHENTICATED  # Update state
            error = current_state + "\n" + "[!] Authenticated!!!"

        # Log the command, response, and logs
        logs = ble.read_logs()

        # this part is an attempt to try and print each log onto the log file after the command is called
        # but does not work as intended yet.
        # if len(logs) != 0:
        #     while(index < len(logs)):
        #         await log_comment(log_filename, logs[index])
        #         index += 1
        
        log_to_file(log_filename, command_data, res[0], error)
    
    # set if authenticated before and the state is currently authenticating, set it to authenticated because
    # as long as there is one instance of authentication, the smart lock will allow a command call
    if current_state == SmartLockState.AUTHENTICATED_AND_AUTHENTICATING_AGAIN:
        current_state = SmartLockState.AUTHENTICATED
    
    log_comment(log_filename, "Fuzzing command now\n")

    for _ in range(100):  # Run 100 fuzzing iterations
            # Randomly choose a command to fuzz
            command = random.choice([OPEN, CLOSE])

            # Mutate the command byte or add extra bytes
            command_data = mutate_data(command)

            print("current state: " , current_state)
            
            log_comment(log_filename, "[3] Sending command")
            # Send the mutated command
            print(f"[3] Sending command: {command_data}")

            # if command is an empty value, skip this test since we know that this will break/crash the lock
            if command_data == []:
                state = "Current state: " + current_state
                log_to_file(log_filename, command_data, [0], state)
                continue
            res = await ble.write_command(command_data)
            print(f"[!] Response: {res}")

            # Update the state based on the response
            if command == OPEN and res[0] == 0:
                current_state = SmartLockState.UNLOCKED
            elif command == CLOSE and res[0] == 0:
                current_state = SmartLockState.LOCKED

            # Check for unexpected behavior
            logs = ble.read_logs()

            state = "Current state: " + current_state
            # Log the command, response, and logs
            log_to_file(log_filename, command_data, res, state)

            await asyncio.sleep(random.uniform(0, 5))  # Randomize delay    

    print("\n[5] Disconnecting...")
    log_comment(log_filename, "[5] Disconnecting...")

    await ble.disconnect()

    print(f"\n[6] Logs from Smart Lock (Serial Port):\n")
    log_comment(log_filename, "[6] Logs from Smart Lock (Serial Port):")
    lines = ble.read_logs()  # Return a list of all log lines.
    print(len(lines))
    for line in lines:
        print(line)
        log_comment(log_filename, line)
        
    
    sys.exit(0)

# Run the fuzzer
try:
    random.seed(None)   # Set the seed here, if necessary
    asyncio.run(fuzz_with_state_tracking())
except KeyboardInterrupt:
    print("\nProgram Exited by User!")
