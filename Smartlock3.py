#!/usr/bin/env python3
import sys
import os
import datetime
import asyncio
import random
from BLEClient import BLEClient
from UserInterface import ShowUserInterface
import logging
import json

BLUE = '\033[94m'
RESET = '\033[0m'  # This resets the color back to default

type_passcode = 'passcode'
type_command = 'command_code'    

# Configuration Constants
DEVICE_NAME = "Smart Lock [Group 3]"

RESPONSES = {
    'SUCCESS': 0x00,
    'AUTHFAIL': 0x01,
    'INVALID_COMMAND': 0x02,
    'COMMAND_NOT_ALLOWED_BEF_AUTH': 0x03,
    'LOCK_ERROR': 0x04,
}

COMMANDS = {
    'AUTH': [0x00],  # 7 Bytes (command + 6 byte passcode)
    'OPEN': [0x01],  # 1 Byte
    'CLOSE': [0x02]  # 1 Byte
}
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]  # Correct PASSCODE

interesting_passcodes = [PASSCODE]  # Start with known good passcode
interesting_commands = [COMMANDS['OPEN'], COMMANDS['CLOSE']]  # Base commands

def setup_logging():
    """Initialize logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"fuzz_test_{timestamp}.txt")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )

def log_print(message):
    """Logs and prints a message, filtering known errors"""
    logging.info(message)


# Initialize error tracking system 
KNOWN_ERRORS_FILE = "known_errors_and_interesting_inputs.json"
known_errors = set()
similar_inputs = set()

def setup_error_tracking():
    """Load known error patterns from file, storing only the error messages"""
    global known_errors, similar_inputs

    try:
        if os.path.exists(KNOWN_ERRORS_FILE):
            with open(KNOWN_ERRORS_FILE, 'r') as f:
                error_list = json.load(f)  # Load the list of error objects
                # Extract just the "error" field from each object
                known_errors = {error_obj["error"] for error_obj in error_list if "error" in error_obj}
                similar_inputs = {tuple(obj["input"]) for obj in error_list if "input" in obj}
            print(f"number of known errors from the json file: {len(known_errors)}")
            print(f"number of similar inputs from the json file: {len(similar_inputs)}")
            print("Similar inputs:", similar_inputs)
            print("Known errors:", known_errors)
    except Exception as e:
        print(f"{BLUE}Error loading known errors: {e}{RESET}")

def save_known_errors():
    """Save known error patterns to file in a more readable format"""
    global known_errors, similar_inputs

    try:
        # Load existing errors if file exists
        existing_errors = []
        if os.path.exists(KNOWN_ERRORS_FILE):
            try:
                with open(KNOWN_ERRORS_FILE, 'r') as f:
                    existing_content = f.read().strip()
                    if existing_content.startswith('[') and existing_content.endswith(']'):
                        existing_content = existing_content[1:-1]  # Remove brackets
                        if existing_content:
                            # Parse each line separately
                            for line in existing_content.split('\n'):
                                line = line.strip().rstrip(',')
                                if line:
                                    try:
                                        existing_errors.append(json.loads(line))
                                    except json.JSONDecodeError:
                                        continue
            except Exception as e:
                print(f"{BLUE}Error reading existing errors: {e}{RESET}")
                existing_errors = []

        # Prepare current errors (same as your original code)
        formatted_errors = []
        for error_entry in known_errors:
            if isinstance(error_entry, str):
                try:
                    formatted_errors.append(json.loads(error_entry))
                except json.JSONDecodeError:
                    continue
            else:
                formatted_errors.append(error_entry)

        # Combine and remove duplicate
        combined_errors = existing_errors + formatted_errors
        unique_errors = []
        seen = set()
        
        for error in combined_errors:
            error_key = json.dumps(error, sort_keys=True)
            if error_key not in seen:
                seen.add(error_key)
                unique_errors.append(error)

        # Write back into file
        with open(KNOWN_ERRORS_FILE, 'w') as f:
            f.write("[\n")  # Start of JSON array
            
            for i, error in enumerate(unique_errors):
                line = json.dumps(
                    error,
                    separators=(',', ':'),
                    ensure_ascii=False
                )
                f.write(f"  {line}")
                if i < len(unique_errors) - 1:
                    f.write(",")
                f.write("\n")
            
            f.write("]\n")  # End of JSON array
            
    except Exception as e:
        print(f"{BLUE}Error saving known errors: {e}{RESET}")

def is_known_error(message):
    """Check if a message matches a known error pattern"""
    global known_errors, similar_inputs
    return any(error_pattern in message for error_pattern in known_errors)

def has_similar_input(input):
    """Check if any part of the input_array matches any part of any array in the set."""
    global similar_inputs
    
    if not input or not similar_inputs:
        return False
    
    input_tuple = tuple(input)

    # Special case: if input starts with 0
    # if input_tuple[0] == 0:
    #     for arr in similar_inputs:
    #         if arr and arr[0] == 0:
    #             return True

    if len(input_tuple) >= 2 and input_tuple[0] == 0 and input_tuple[1] == 0:
        for arr in similar_inputs:
            if len(arr) >= 2 and arr[0] == 0 and arr[1] == 0:
                return True  # Early exit if any array starts with two zeros
    
    # Compare first 6 elements (or full length if shorter)
    compare_length = min(6, len(input_tuple))
    
    for arr in similar_inputs:
        if not arr:  # Skip empty arrays
            continue
            
        # Get the comparable portion (first 6 elements or full length)
        arr_portion = arr[:compare_length]
        input_portion = input_tuple[:compare_length]
        
        # Must match exactly for the comparison length
        if len(arr_portion) >= compare_length and arr_portion == input_portion:
            return True

        # if arr == input:
        #     return True
            
    return False

# def has_similar_input(input):
#     """
#     Check if:
#     1. The input array starts with 0 AND any array in the set starts with 0, OR
#     2. Any part of the input array matches any part of any array in the set.
#     """
#     global similar_inputs
#     # Convert input to tuple for consistency
#     input_tuple = tuple(input)

#     if not input or not similar_inputs:
#         return False
    
#     # if len(input) > 1 and input[0] == 0:
#     #     return True
    
#     if len(input_tuple) >= 2 and input_tuple[0] == 0 and input_tuple[1] == 0:
#         for arr in similar_inputs:
#             if len(arr) >= 2 and arr[0] == 0 and arr[1] == 0:
#                 return True  # Early exit if any array starts with two zeros

#     # Special case: if input starts with 0
#     # if input_tuple[0] == 0:
#     #     for arr in similar_inputs:
#     #         if arr and arr[0] == 0:
#     #             return True

#     # Original behavior (check for overlapping parts)
#     for arr in similar_inputs:
#         arr_tuple = tuple(arr)
#         # Check if the shorter array is a subset of the longer one
#         if len(input_tuple) <= len(arr_tuple):
#             if input_tuple == arr_tuple[:len(input_tuple)]:
#                 return True
#         else:
#             if arr_tuple == input_tuple[:len(arr_tuple)]:
#                 return True
    
#     compare_length = min(6, len(input_tuple))
#     for arr in similar_inputs:
#         if not arr:  # Skip empty arrays
#             continue
            
#         # Get the comparable portion (first 6 elements or full length)
#         arr_portion = arr[:compare_length]
#         input_portion = input_tuple[:compare_length]
        
#         # Must match exactly for the comparison length
#         if len(arr_portion) >= compare_length and arr_portion == input_portion:
#             return True

#         if arr == input_tuple:
#             return True

#     return False

        
def record_new_error(error, input_type, input, history):
    """Record a newly discovered error in a structured JSON format"""
    global known_errors, similar_inputs
    error_entry = {
        'error': str(error),
        'input': input,
        'type': input_type,
        'history': history
    }
    error_key = json.dumps(error_entry, separators=(',', ':'))
    
    if error_key not in known_errors:
        known_errors.add(error_key)
        save_known_errors()

def load_interesting_inputs():
    """Load interesting inputs from error history"""
    try:
        if os.path.exists(KNOWN_ERRORS_FILE):
            with open(KNOWN_ERRORS_FILE, 'r') as f:
                errors = json.load(f)
                for error in errors:
                    # Get the input and type from the error entry
                    cmd = error.get('input')
                    err_type = error.get('type')
                    
                    # Skip if no input or type
                    if cmd is None or err_type is None:
                        continue
                    
                    # Handle case where input might be a string representation
                    if isinstance(cmd, str):
                        try:
                            cmd = json.loads(cmd.replace("'", '"'))
                        except:
                            continue
                    
                    # Add to appropriate list based on type
                    if err_type == type_passcode:
                        if cmd not in interesting_passcodes:
                            interesting_passcodes.append(cmd)
                    elif err_type == type_command:
                        if cmd not in interesting_commands:
                            interesting_commands.append(cmd)

                print(f"{BLUE}Loaded {str(len(interesting_passcodes))} interesting passcodes{RESET}")
                print(f"{BLUE}Loaded {str(len(interesting_commands))} interesting commands{RESET}")
    except Exception as e:
        print(f"{BLUE}Error loading interesting inputs: {e}{RESET}")

setup_logging()

class Fuzzer:
    def __init__(self):
        self.ble = BLEClient()
        setup_error_tracking()
        load_interesting_inputs()  # Load from previous sessions
        self.unique_error_codes = set()
        self.state_checker = StateChecker()
        self.testcases = 0
        self.total_testcases = 0
        self.idx = 0

    async def print_new_logs(self, ble, input_type=None, input=None):
        """Print only new logs since last index and return new last index"""
        await asyncio.sleep(0.3)  # Allow time for response
        logs = ble.read_logs()
        
        # log_print(f"\nBLE Logs - idx:{self.idx}, total: {len(logs)}")
        # Print only new logs since last time
        for line in logs[self.idx:]:
            # log_print(line)
            if "[Error] Code: 0x" in line and input_type is not None and input is not None:
                # Extract the error code
                error_code = line.split("0x")[1].strip()
                if has_similar_input(input) == False:
                    record_new_error(error_code, input_type, input, self.state_checker.command_history)
                    similar_inputs.add(input)

        # Return new last index
        self.idx = len(logs)

    def is_interesting(self, e, input_type, input, response=None):
        """
        Determine if an input is interesting enough to save
        and add to our mutation pools if it is. (This is not yet implemented)
        Returns True if the input was added to an interesting pool.
        """
        if not input:
            return False

        # is_new = True
        is_new = False

        # Track unique error codes if response is provided
        # if response is not None and isinstance(response, list) and len(response) > 0:
        #     code = response[0]
        #     if code not in self.unique_error_codes:
        #         log_print(f"New input is interesting!")
        #         self.unique_error_codes.add(code)
        #         is_new = True
        
        if has_similar_input(input):
            log_print(f"{input} is similar to inputs in json file")
            is_new = False
        else:
            is_new = True

        # Add to respective interesting inputs list based on input type if the error is new
        if is_new:
            if input_type == type_passcode:
                if input not in interesting_passcodes:
                    interesting_passcodes.append(input)
                    similar_inputs.add(tuple(input))
                    log_print(f"[!] {input} added to json file")
                    record_new_error(e, input_type, input, self.state_checker.command_history)
                    return True
            elif input_type == type_command:
                if input not in interesting_commands:
                    interesting_commands.append(input)
                    log_print(f"[!] {input} added to json file")
                    similar_inputs.add(tuple(input))
                    record_new_error(e, input_type, input, self.state_checker.command_history)
                    return True
        return False

    async def ensure_connection(self):
        """Helper to verify connection and attempt reconnection if needed"""
        try:
            log_print("[!] Attempting to reconnect...")
            await self.ble.connect(DEVICE_NAME)
            await self.print_new_logs(self.ble)
            log_print("[!] Reconnected successfully.")
            self.state_checker.current_state = self.state_checker.STATES['BEF_AUTH_LOCKED']
            log_print(f"[!] Current state: {self.state_checker.current_state}")

            # self.idx = 0
            # self.ble.init_logs()
            return True
        except Exception as conn_e:
            log_print(f"[!] Reconnection failed: {conn_e}")
            return False

    def mutate_command(self, command):
        """
        Main mutation entry point that randomly selects a mutation strategy
        and applies it to the command.
        """
        if not command:
            return command.copy()

        # Select a mutation strategy
        mutation_strategy = random.choice([
            self._randomize_single_byte,
            self._flip_bits,
            self._append_or_remove_byte,
            self._swap_bytes,
            self._repeat_sequence,
            self._boundary_mutation,
            self._bitwise_operations
        ])
        
        mutated = mutation_strategy(command.copy())
        self._log_mutation(command, mutated)
        return mutated

    def _randomize_single_byte(self, data):
        """Alter one random byte"""
        idx = random.randint(0, len(data) - 1)
        data[idx] = random.randint(0, 255)
        return data

    def _flip_bits(self, data):
        """
        Randomly flips bits in the given byte array.
        Each byte has 1-3 bits flipped.
        """
        for i in range(len(data)):
            # Randomly flip 1-3 bits in each byte
            for _ in range(random.randint(1, 3)):
                bit_to_flip = random.randint(0, 7)
                data[i] ^= 1 << bit_to_flip
        return data

    def _append_or_remove_byte(self, data):
        """
        Randomly appends or removes a byte from the given byte array.
        """
        action = random.choice(["append", "remove"])
        
        if action == "append":
            # Append a random byte
            return data + [random.randint(0, 255)]
        else:
            if len(data) <= 1:
                return data  # Don't remove if it would empty the command
            # Remove a random byte
            index_to_remove = random.randint(0, len(data) - 1)
            return data[:index_to_remove] + data[index_to_remove + 1:]

    def _swap_bytes(self, data):
        """Swap two random bytes in the data"""
        if len(data) < 2:
            return data
        idx1, idx2 = random.sample(range(len(data)), 2)
        data[idx1], data[idx2] = data[idx2], data[idx1]
        return data
    
    def _repeat_sequence(self, data):
        """Repeat a random subsequence of bytes"""
        if len(data) < 2:
            return data
        start = random.randint(0, len(data)-2)
        end = random.randint(start+1, len(data)-1)
        repeat_count = random.randint(1, 3)
        return data[:end] + data[start:end]*repeat_count + data[end:]

    def _boundary_mutation(self, data):
        """Set a random byte to minimum or maximum values"""
        idx = random.randint(0, len(data)-1)
        data[idx] = random.choice([0x00, 0xFF, 0x7F, 0x80])
        return data

    def _bitwise_operations(self, data):
        """Apply bitwise operations to random bytes"""
        idx = random.randint(0, len(data)-1)
        operation = random.choice(['and', 'or', 'xor', 'not'])
        operand = random.randint(0, 255)
        
        if operation == 'and':
            data[idx] &= operand
        elif operation == 'or':
            data[idx] |= operand
        elif operation == 'xor':
            data[idx] ^= operand
        elif operation == 'not':
            data[idx] = ~data[idx] & 0xFF
            
        return data

    def _log_mutation(self, original, mutated):
        """Helper to log mutation details"""
        if len(original) != len(mutated):
            log_print(f'\n[Mutation] Changed length from {len(original)} to {len(mutated)} bytes')
        else:
            differences = []
            for i, (orig, mut) in enumerate(zip(original, mutated)):
                if orig != mut:
                    differences.append(f'Byte {i}: {orig} -> {mut}')
            
            if differences:
                log_print('\n[Mutation] ' + ', '.join(differences))

    async def run_fuzzer(self, fuzzer_type, auth_attempts=100, command_attempts=100, run_forever=False):
        """
        Main fuzzer function with indefinite running capability
        
        Args:
            fuzzer_type (str): 'random' or 'mutation'
            auth_attempts (int): Number of authentication attempts per cycle
            command_attempts (int): Number of command attempts per cycle
            run_forever (bool): Whether to run indefinitely until interrupted
        """
        global known_errors, similar_inputs
        try:
            loop_number = 1
            while True:  # Outer loop for indefinite running
                self.ble.init_logs()
                log_print(f'\n{"="*50}\n[+] Starting new fuzzing cycle: Attempt {loop_number}\n{"="*50}')
                log_print(f'[1] Connecting to "{DEVICE_NAME}"...')
                
                try:
                    await self.ble.connect(DEVICE_NAME)
                    await self.print_new_logs(self.ble)
                except Exception as e:
                    log_print(f'[X] Initial connection failed: {e}')
                    if not run_forever:
                        raise
                    await asyncio.sleep(5)  # Wait before retrying
                    continue

                # --- Authentication Phase ---
                authenticated = False
                try:
                    authenticated = await self.fuzz_authentication(fuzzer_type, auth_attempts)
                    
                    if not authenticated:
                        log_print("\n[!] Authentication fuzzing failed, trying with correct passcode...")
                        try:
                            res = await self.ble.write_command(COMMANDS['AUTH'] + PASSCODE)
                            self.state_checker.update_state(COMMANDS['AUTH'] + PASSCODE, res)
                            await self.print_new_logs(self.ble, type_passcode, COMMANDS['AUTH'] + PASSCODE)
                            authenticated = True
                            log_print("[+] Authenticated with correct passcode")
                        except Exception as e:
                            log_print(f"[X] Error authenticating with correct passcode: {e}")
                            await self.print_new_logs(self.ble, type_passcode, COMMANDS['AUTH'] + PASSCODE)
                except Exception as e:
                    log_print(f'[X] Authentication phase crashed: {e}')
                    if not run_forever:
                        raise

                # --- Operational Commands Phase ---
                if authenticated:
                    try:
                        await self.fuzz_commands(fuzzer_type, command_attempts)
                    except Exception as e:
                        log_print(f'[X] Command phase crashed: {e}')
                        if not run_forever:
                            raise
                else:
                    log_print("[X] Skipping command fuzzing due to authentication failure")

                # --- Cycle Complete ---
                if not run_forever:
                    break
                
                # Show stats before next cycle
                log_print(f'\n{"="*50}\n[+] Fuzzing cycle {loop_number} complete\n'
                            f'Total Interesting passcodes: {len(interesting_passcodes)}\n'
                            f'Total Interesting commands: {len(interesting_commands)}\n'
                            f'Total Known errors: {len(known_errors)}\n'
                            f'Tests done for this cycle: {self.testcases}\n'
                            f'Total Tests done: {self.total_testcases}\n'
                            f'{"="*50}\n')
                
                log_print(f"current pool of interesting passcodes: {interesting_passcodes}")
                log_print(f"current pool of interesting commands: {interesting_commands}")
                
                log_print(f"\n[Logs from Smart Lock (Serial Port)]:\n{'-'*50}")
                for line in self.ble.read_logs():
                    log_print(line)
                
                self.idx = 0

                # Save progress before next cycle
                save_known_errors()
                
                loop_number = loop_number + 1

                self.state_checker.command_history.clear()
                self.testcases = 0

                # Brief pause between cycles
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            log_print("\n[!] Received interrupt signal, shutting down...")
        finally:
            log_print("\n[!] Ending fuzzing...")
            
            # Output logs from the Smart Lock
            log_print(f"\n[Logs from Smart Lock (Serial Port)]:\n{'-'*50}")
            for line in self.ble.read_logs():
                log_print(line)

            # Final cleanup
            log_print("\n[Disconnecting...]")
            await self.ble.disconnect()
            
            # Save final state
            save_known_errors()

            # Show all stats
            log_print(f'\n{"="*50}\n[+] Total number of Fuzzing cycles completed: {loop_number} \n'
                        f'Total Interesting passcodes found: {len(interesting_passcodes)}\n'
                        f'Total Interesting commands found: {len(interesting_commands)}\n'
                        f'Total Known errors found: {len(known_errors)}\n'
                        f'Total tests done: {self.total_testcases}\n'
                        f'{"="*50}\n')

            sys.exit(0)

    async def fuzz_authentication(self, fuzzer_type, attempts):
        """Authentication fuzzing using interesting passcodes"""
        attempts_made = 0
        authenticated = False
        
        while attempts_made < attempts and not authenticated:
            if fuzzer_type == 'random':
                # 50% chance to use interesting passcode as base
                if interesting_passcodes and random.random() < 0.5:
                    base = random.choice(interesting_passcodes)
                    fuzz_passcode = self.mutate_command(base)
                else:
                    fuzz_passcode = [random.randint(0, 255) for _ in range(6)]
            else:  # mutation
                base = random.choice(interesting_passcodes)
                fuzz_passcode = self.mutate_command(base)
            
            full_command = COMMANDS['AUTH'] + fuzz_passcode
            
            if self._command_has_known_error(full_command):
                continue
                
            log_print(f'[{fuzzer_type.capitalize()} Auth {attempts_made}] Trying: {fuzz_passcode}')
            
            try:
                res = await self.ble.write_command(full_command)
                self.state_checker.update_state(full_command, res)
                log_print(f'[!] Command: {full_command}')
                log_print(f'[!] Response: {res[0]}')
                if res and res[0] == 0:
                    authenticated = True
                    log_print(f'[+] Authenticated with: {fuzz_passcode}')
                    self.is_interesting("Response: Success", type_passcode, fuzz_passcode, response=res)
                else:
                    log_print('[!] Authentication failed')
                
                await self.print_new_logs(self.ble, type_passcode, full_command)

            except Exception as e:
                log_print(f'[!] Error: {e}')
                if "Not connected" in str(e):
                    await self.ensure_connection()
                    self.state_checker.command_history.clear()  # clear the command history after a crash

                    log_print(f'\n[!] Send request with the same input again')

                    # if the error is Not connected, try the same input again
                    try:
                        res = await self.ble.write_command(fuzz_passcode)
                        self.state_checker.update_state(fuzz_passcode, res)
                        await self.print_new_logs(self.ble, type_passcode, fuzz_passcode)
                    except Exception as e:
                        self.is_interesting(e, type_passcode, fuzz_passcode, response=res)
                        await self.print_new_logs(self.ble, type_passcode, fuzz_passcode)
                        # Record the error in our tracking system
                        # record_new_error(e, type_passcode, fuzz_passcode)
                    continue
                
                self.is_interesting(e, type_passcode, fuzz_passcode)
                # Record the error in our tracking system
                # record_new_error(e, type_passcode, fuzz_passcode)
            
            attempts_made += 1
            self.testcases += 1
            self.total_testcases += 1
            await asyncio.sleep(1)
        
        return authenticated

    async def fuzz_commands(self, fuzzer_type, attempts):
        """Command fuzzing using interesting commands"""
        attempts_made = 0
        
        while attempts_made < attempts:
            if fuzzer_type == 'random':
                # 50% chance to use interesting command as base
                if interesting_commands and random.random() < 0.5:
                    base = random.choice(interesting_commands)
                    fuzzed_command = self.mutate_command(base)
                else:
                    base = random.choice([COMMANDS['OPEN'], COMMANDS['CLOSE'], ""])
                    fuzz_extra = [random.randint(0, 255) for _ in range(random.randint(0, 5))]
                    fuzzed_command = base + fuzz_extra
            else:  # mutation
                base = random.choice(interesting_commands)
                fuzzed_command = self.mutate_command(base)
            
            if self._command_has_known_error(fuzzed_command):
                continue
                
            log_print(f'\n[{fuzzer_type.capitalize()} Command {attempts_made}] Sending: {fuzzed_command}')
            
            try:
                res = await self.ble.write_command(fuzzed_command)
                self.state_checker.update_state(fuzzed_command, res)
                log_print(f'[!] Command: {fuzzed_command}')
                log_print(f'[!] Response: {res[0]}')
                if res and res[0] == 0:  # Check for non-success response codes
                    self.is_interesting("Response: Success", type_passcode, fuzzed_command, response=res)

                await self.print_new_logs(self.ble, type_command, fuzzed_command)
            except Exception as e:
                log_print(f'[!] Error: {e}')
                if "Not connected" in str(e):
                    await self.ensure_connection()
                    self.state_checker.command_history.clear()  # clear the command history after a crash
                    try:
                        res = await self.ble.write_command(COMMANDS['AUTH'] + PASSCODE)
                        await self.print_new_logs(self.ble, type_passcode, COMMANDS['AUTH'] + PASSCODE)
                        self.state_checker.update_state(COMMANDS['AUTH'] + PASSCODE, res)
                        if res and res[0] == 0:
                            log_print("[+] Authenticated with correct passcode")
                    except Exception as e:
                        log_print(f"[X] Error authenticating with correct passcode: {e}")
                    log_print(f'\n[!] Send request with the same input again')

                    # if the error is Not connected, try the same input again
                    try:
                        res = await self.ble.write_command(fuzzed_command)
                        await self.print_new_logs(self.ble, type_command, fuzzed_command)
                        self.state_checker.update_state(fuzzed_command, res)
                    except Exception as e:
                        self.is_interesting(e, type_command, fuzzed_command, response=res)
                        # Record the error in our tracking system
                        # record_new_error(e, type_command, fuzzed_command)
                    continue

                self.is_interesting(e, type_command, fuzzed_command)
                await self.print_new_logs(self.ble, type_command, fuzzed_command)
                # Record the error in our tracking system
                # record_new_error(e, type_command, fuzzed_command)
            
            attempts_made += 1
            self.testcases += 1
            self.total_testcases += 1
            await asyncio.sleep(random.uniform(0.5, 3))

    def _command_has_known_error(self, command):
        """Check if this exact command has previously caused an error"""
        global known_errors, similar_inputs
        command_str = str(command)
        for error_entry in known_errors:
            if command_str in error_entry:
                return True
        return False

async def run_random_fuzzer(auth_attempts=50, command_attempts=50, run_forever=False):
    """Run the random fuzzer"""
    fuzzer = Fuzzer()
    await fuzzer.run_fuzzer('random', auth_attempts, command_attempts, run_forever=run_forever)

async def run_mutation_fuzzer(auth_attempts=50, command_attempts=50, run_forever=False):
    """Run the mutation-based fuzzer"""
    fuzzer = Fuzzer()
    await fuzzer.run_fuzzer('mutation', auth_attempts, command_attempts, run_forever=run_forever)

class StateChecker:
    def __init__(self):
        self.STATES = {
            'BEF_AUTH_LOCKED' : 'Locked before authentication',     # Initial state
            'AUTHENTICATED': 'Authenticated',     # Auth successful
            'UNLOCKED': 'Unlocked',         # Unlocked state
            'LOCKED': 'Locked'
        }

        self.transition_rules = {
            self.STATES['BEF_AUTH_LOCKED']: {    # PASSCODE CHECK NEEDS TO BE DONE ELSEWHERE
                (COMMANDS['AUTH'][0], RESPONSES['SUCCESS']): self.STATES['AUTHENTICATED'],
                (COMMANDS['AUTH'][0], RESPONSES['AUTHFAIL']): self.STATES['BEF_AUTH_LOCKED'],
                (COMMANDS['OPEN'][0], RESPONSES['COMMAND_NOT_ALLOWED_BEF_AUTH']): self.STATES['BEF_AUTH_LOCKED'],
                (COMMANDS['CLOSE'][0], RESPONSES['COMMAND_NOT_ALLOWED_BEF_AUTH']): self.STATES['BEF_AUTH_LOCKED'],
                (None, RESPONSES['INVALID_COMMAND']): self.STATES['BEF_AUTH_LOCKED'],   # need to do a check where the command is none of the valid commands
            },
            self.STATES['AUTHENTICATED']: {
                (COMMANDS['OPEN'][0], RESPONSES['SUCCESS']): self.STATES['UNLOCKED'],   # Open command received
                (COMMANDS['CLOSE'][0], RESPONSES['SUCCESS']): self.STATES['LOCKED'],   # Close command received
                (None, RESPONSES['INVALID_COMMAND']): self.STATES['AUTHENTICATED']
            },
            self.STATES['UNLOCKED']: {
                (COMMANDS['CLOSE'][0], RESPONSES['SUCCESS']): self.STATES['LOCKED'],     # closing
                (COMMANDS['OPEN'][0], RESPONSES['LOCK_ERROR']): self.STATES['UNLOCKED'],     # opening again, so lock error
                (None, RESPONSES['INVALID_COMMAND']): self.STATES['UNLOCKED']
            },
            self.STATES['LOCKED']: {
                (COMMANDS['OPEN'][0], RESPONSES['SUCCESS']): self.STATES['UNLOCKED'],
                (COMMANDS['CLOSE'][0], RESPONSES['LOCK_ERROR']): self.STATES['LOCKED'],
                (None, RESPONSES['INVALID_COMMAND']): self.STATES['LOCKED']
            }
        }

        self.expected_states = {
            self.STATES['BEF_AUTH_LOCKED']: {
                'allowed_commands': COMMANDS['AUTH'][0],  # Only authenticate
                'expected_responses': [RESPONSES['AUTHFAIL'], 
                                       RESPONSES['INVALID_COMMAND'], 
                                       RESPONSES['COMMAND_NOT_ALLOWED_BEF_AUTH']]  # Auth fail, invalid cmd, cmd not allowed
            },
            self.STATES['AUTHENTICATED']: {
                'allowed_commands': [COMMANDS['OPEN'][0], COMMANDS['CLOSE'][0]],  # Open/close
                'expected_responses': [RESPONSES['SUCCESS'], RESPONSES['LOCK_ERROR'],RESPONSES['INVALID_COMMAND']]  # Success or lock error or invalid
            },
            self.STATES['UNLOCKED']: {
                'allowed_commands': [COMMANDS['OPEN'][0], COMMANDS['CLOSE'][0]],  # Open/close
                'expected_responses': [RESPONSES['SUCCESS'], RESPONSES['LOCK_ERROR'],RESPONSES['INVALID_COMMAND']]  # Success or lock error or invalid
            },
            self.STATES['LOCKED']: {
                'allowed_commands': [COMMANDS['OPEN'][0], COMMANDS['CLOSE'][0]],  # Open/close
                'expected_responses': [RESPONSES['SUCCESS'], RESPONSES['LOCK_ERROR'],RESPONSES['INVALID_COMMAND']]  # Success or lock error or invalid
            }
        }
        
        self.current_state = self.STATES['BEF_AUTH_LOCKED']
        self.prev_state = None
        self.command_history = []
        
        
    def update_state(self, command, response):
        """Update internal state based on command/response"""

        comm_byte = command[0] if command else None
        res_byte = response[0] if response else None

        # if the first byte is open/close command but the length > 1, should not be allowed
        if (comm_byte == COMMANDS['OPEN'][0] or comm_byte == COMMANDS['CLOSE'][0]):
            if len(command) > 1:
                comm_byte = None

        # if the first byte is auth command but the length > 7, should not be allowed
        if (comm_byte == COMMANDS['AUTH'][0]):
            if len(command) > 7:
                comm_byte = None
                # print(f"\n{BLUE}len(command): {len(command)}{RESET}")


        transition_key = (comm_byte, res_byte)

        # print(f"\n{BLUE}comm_byte: {comm_byte}{RESET}")
        # print(f"\n{BLUE}res: {res_byte}{RESET}")
        # print(f"\n{BLUE}transition_key: {transition_key}{RESET}")

        current_rules = self.transition_rules.get(self.current_state, {})
        # print(f"\n{BLUE}current_rules: {current_rules}{RESET}")

        self.command_history.append({
            'state' : self.current_state,
            'command': command,
            'response': res_byte,
        })

        if transition_key in current_rules:
            log_print(f"[!] Previous state '{self.prev_state}' is now state '{current_rules[transition_key]}'! ")
            self.prev_state = self.current_state
            self.current_state = current_rules[transition_key]
        else:
            self.is_interesting_state_check(command, res_byte, self.command_history)
            log_print(f"[!] Current state: '{self.current_state}'! ")
    
    def is_interesting_state_check(self, command, response, command_history):
        # input is interesting since response or transition is unexpected
        if self.current_state == self.STATES['LOCKED'] or self.current_state == self.STATES['UNLOCKED'] or self.current_state == self.STATES['AUTHENTICATED']:
            state_info = self.expected_states[self.current_state]
            # print(f"state_info: {state_info}")
            if (response not in state_info['expected_responses'] and has_similar_input(command) == False):
                log_print(f"[!] Interesting input found at {self.current_state}! ")
                log_print(f"[!] {command} added to json file")
                interesting_commands.append(command)
                similar_inputs.add(tuple(command))
                record_new_error("Unexpected transition for commands", type_command, command, command_history)
        elif self.current_state == self.STATES['BEF_AUTH_LOCKED']:
            state_info = self.expected_states[self.current_state]
            # print(f"state_info: {state_info}")
            if (response not in state_info['expected_responses'] and has_similar_input(command[1:]) == False):
                interesting_passcodes.append(command)
                similar_inputs.add(tuple(command))
                log_print(f"[!] Interesting input found at {self.current_state}! ")
                log_print(f"[!] {command} added to json file")
                record_new_error("Unexpected transition for passcode", type_passcode, command[1:], command_history)
    

# Main execution
if __name__ == "__main__":
    try:
        # Choose which fuzzer to run
        # asyncio.run(run_random_fuzzer(True))
        asyncio.run(run_mutation_fuzzer(5, 5, True))
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")