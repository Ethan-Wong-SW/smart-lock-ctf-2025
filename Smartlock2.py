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

type_passcode = 'passcode'
type_command = 'command_code'    

# Configuration Constants
DEVICE_NAME = "Smart Lock [Group 3]"
COMMANDS = {
    'AUTH': [0x00],  # 7 Bytes (command + 6 byte passcode)
    'OPEN': [0x01],  # 1 Byte
    'CLOSE': [0x02]  # 1 Byte
}
PASSCODE = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]  # Correct PASSCODE

class Fuzzer:
    def __init__(self):
        self.ble = BLEClient()
        self.setup_logging()
        self.setup_error_tracking()
        self.interesting_passcodes = [PASSCODE]  # Start with known good passcode
        self.interesting_commands = [COMMANDS['OPEN'], COMMANDS['CLOSE']]  # Base commands
        self.load_interesting_inputs()  # Load from previous sessions
        self.unique_error_codes = set()
        
    def setup_logging(self):
        """Initialize logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = os.path.join(log_dir, f"fuzz_test_{timestamp}.txt")
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[
                logging.FileHandler(self.log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def setup_error_tracking(self):
        """Initialize error tracking system"""
        self.KNOWN_ERRORS_FILE = "known_errors.json"
        self.known_errors = set()
        self.load_known_errors()
    
    def load_known_errors(self):
        """Load known error patterns from file"""
        try:
            if os.path.exists(self.KNOWN_ERRORS_FILE):
                with open(self.KNOWN_ERRORS_FILE, 'r') as f:
                    self.known_errors = set(json.load(f))
        except Exception as e:
            print(f"Error loading known errors: {e}")

   

    def save_known_errors(self):
        """Save known error patterns to file in a more readable format"""
        try:
            # Load existing errors if file exists
            existing_errors = []
            if os.path.exists(self.KNOWN_ERRORS_FILE):
                try:
                    with open(self.KNOWN_ERRORS_FILE, 'r') as f:
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
                    print(f"Error reading existing errors: {e}")
                    existing_errors = []

            # Prepare current errors (same as your original code)
            formatted_errors = []
            for error_entry in self.known_errors:
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
            with open(self.KNOWN_ERRORS_FILE, 'w') as f:
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
            print(f"Error saving known errors: {e}")

    def is_known_error(self, message):
        """Check if a message matches a known error pattern"""
        return any(error_pattern in message for error_pattern in self.known_errors)

    def log_print(self, message):
        """Logs and prints a message, filtering known errors"""
        if not self.is_known_error(message):
            logging.info(message)
            
    def record_new_error(self, error, input_type, input):
        """Record a newly discovered error in a structured JSON format"""
        error_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'error': str(error),
            'input': input,
            'type': input_type
        }
        error_key = json.dumps(error_entry, separators=(',', ':'))
        
        if error_key not in self.known_errors:
            self.known_errors.add(error_key)
            self.save_known_errors()

    def load_interesting_inputs(self):
        """Load interesting inputs from error history"""
        try:
            if os.path.exists(self.KNOWN_ERRORS_FILE):
                with open(self.KNOWN_ERRORS_FILE, 'r') as f:
                    errors = json.load(f)
                    for error in errors:
                        cmd = error.get('command')
                        err_type = error.get('type')
                        
                        # Handle both string and dict error entries
                        if isinstance(cmd, str):
                            try:
                                cmd = json.loads(cmd.replace("'", '"'))
                            except:
                                continue
                        
                        if cmd and err_type == type_passcode:
                            if cmd not in self.interesting_passcodes:
                                self.interesting_passcodes.append(cmd)
                        elif cmd and err_type == type_command:
                            if cmd not in self.interesting_commands:
                                self.interesting_commands.append(cmd)
        except Exception as e:
            print(f"Error loading interesting inputs: {e}")

    def is_interesting(self, input_type, input, response=None):
        """
        Determine if an input is interesting enough to save
        and add to our mutation pools if it is. (This is not yet implementad)
        Returns True if the input was added to an interesting pool.
        """
        if not input:
            return False

        is_new = False

        # Track unique error codes if response is provided
        if response is not None and isinstance(response, list) and len(response) > 0:
            code = response[0]
            if code not in self.unique_error_codes:
                self.unique_error_codes.add(code)
                is_new = True

        # Add to respective interesting inputs list based on input type
        if is_new:
            if input_type == type_passcode:
                if input not in self.interesting_passcodes:
                    self.interesting_passcodes.append(input)
                    return True
            elif input_type == type_command:
                if input not in self.interesting_commands:
                    self.interesting_commands.append(input)
                    return True

        return False

    async def ensure_connection(self):
        """Helper to verify connection and attempt reconnection if needed"""
        try:
            self.log_print("[!] Attempting to reconnect...")
            await self.ble.connect(DEVICE_NAME)
            self.log_print("[!] Reconnected successfully.")
            return True
        except Exception as conn_e:
            self.log_print(f"[!] Reconnection failed: {conn_e}")
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
            self._mutate_single_byte,
            self._flip_bits,
            self._append_or_remove_byte,
            self._mutate_data
        ])
        
        mutated = mutation_strategy(command.copy())
        self._log_mutation(command, mutated)
        return mutated

    def _mutate_single_byte(self, data):
        """Original mutation: alter one random byte"""
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

    def _mutate_data(self, data):
        """
        Combination mutation: randomly selects between adding/removing bytes
        or flipping bits.
        """
        mutation_type = random.choice(["append_or_remove", "flip_bits"])
        
        if mutation_type == "append_or_remove":
            return self._append_or_remove_byte(data)
        return self._flip_bits(data)

    def _log_mutation(self, original, mutated):
        """Helper to log mutation details"""
        if len(original) != len(mutated):
            self.log_print(f'[Mutation] Changed length from {len(original)} to {len(mutated)} bytes')
        else:
            differences = []
            for i, (orig, mut) in enumerate(zip(original, mutated)):
                if orig != mut:
                    differences.append(f'Byte {i}: {orig} -> {mut}')
            
            if differences:
                self.log_print('[Mutation] ' + ', '.join(differences))

    async def run_fuzzer(self, fuzzer_type, auth_attempts=100, command_attempts=100, run_forever=False):
        """
        Main fuzzer function with indefinite running capability
        
        Args:
            fuzzer_type (str): 'random' or 'mutation'
            auth_attempts (int): Number of authentication attempts per cycle
            command_attempts (int): Number of command attempts per cycle
            run_forever (bool): Whether to run indefinitely until interrupted
        """
        try:
            while True:  # Outer loop for indefinite running
                self.ble.init_logs()
                self.log_print(f'\n{"="*50}\n[+] Starting new fuzzing cycle\n{"="*50}')
                self.log_print(f'[1] Connecting to "{DEVICE_NAME}"...')
                
                try:
                    await self.ble.connect(DEVICE_NAME)
                except Exception as e:
                    self.log_print(f'[X] Initial connection failed: {e}')
                    if not run_forever:
                        raise
                    await asyncio.sleep(5)  # Wait before retrying
                    continue

                # --- Authentication Phase ---
                authenticated = False
                try:
                    authenticated = await self.fuzz_authentication(fuzzer_type, auth_attempts)
                    
                    if not authenticated:
                        self.log_print("[!] Authentication fuzzing failed, trying with correct passcode...")
                        try:
                            res = await self.ble.write_command(COMMANDS['AUTH'] + PASSCODE)
                            if res and res[0] == 0:
                                authenticated = True
                                self.log_print("[+] Authenticated with correct passcode")
                        except Exception as e:
                            self.log_print(f"[X] Error authenticating with correct passcode: {e}")
                except Exception as e:
                    self.log_print(f'[X] Authentication phase crashed: {e}')
                    if not run_forever:
                        raise

                # --- Operational Commands Phase ---
                if authenticated:
                    try:
                        await self.fuzz_commands(fuzzer_type, command_attempts)
                    except Exception as e:
                        self.log_print(f'[X] Command phase crashed: {e}')
                        if not run_forever:
                            raise
                else:
                    self.log_print("[X] Skipping command fuzzing due to authentication failure")

                # --- Cycle Complete ---
                if not run_forever:
                    break
                    
                # Show stats before next cycle
                self.log_print(f'\n{"="*50}\n[+] Fuzzing cycle complete\n'
                            f'Interesting passcodes: {len(self.interesting_passcodes)}\n'
                            f'Interesting commands: {len(self.interesting_commands)}\n'
                            f'Known errors: {len(self.known_errors)}\n'
                            f'{"="*50}\n')
                
                # Save progress before next cycle
                self.save_known_errors()
                
                # Brief pause between cycles
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            self.log_print("\n[!] Received interrupt signal, shutting down...")
        finally:
            # Final cleanup
            self.log_print("\n[Disconnecting...]")
            await self.ble.disconnect()
            
            # Output logs from the Smart Lock
            self.log_print(f"\n[Logs from Smart Lock (Serial Port)]:\n{'-'*50}")
            for line in self.ble.read_logs():
                self.log_print(line)
            
            # Save final state
            self.save_known_errors()

            sys.exit(0)

    async def fuzz_authentication(self, fuzzer_type, attempts):
        """Authentication fuzzing using interesting passcodes"""
        attempts_made = 0
        authenticated = False
        
        while attempts_made < attempts and not authenticated:
            if fuzzer_type == 'random':
                # 50% chance to use interesting passcode as base
                if self.interesting_passcodes and random.random() < 0.5:
                    base = random.choice(self.interesting_passcodes)
                    fuzz_passcode = self.mutate_command(base)
                else:
                    fuzz_passcode = [random.randint(0, 255) for _ in range(6)]
            else:  # mutation
                base = random.choice(self.interesting_passcodes)
                fuzz_passcode = self.mutate_command(base)
            
            full_command = COMMANDS['AUTH'] + fuzz_passcode
            
            if self._command_has_known_error(full_command):
                continue
                
            self.log_print(f'\n[{fuzzer_type.capitalize()} Auth {attempts_made}] Trying: {fuzz_passcode}')
            
            try:
                res = await self.ble.write_command(full_command)
                self.log_print(f'[!] Command: {full_command}')
                self.log_print(f'[!] Response: {res[0]}')
                if res and res[0] == 0:
                    authenticated = True
                    self.log_print(f'[+] Authenticated with: {fuzz_passcode}')
                else:
                    self.log_print('[!] Authentication failed')
                    self.is_interesting(type_passcode, fuzz_passcode, response=res)
            except Exception as e:
                self.log_print(f'[!] Error: {e}')
                self.is_interesting(type_passcode, fuzz_passcode)
                # Record the error in our tracking system
                self.record_new_error(e, type_passcode, fuzz_passcode)
                if "Not connected" in str(e):
                    await self.ensure_connection()
            
            attempts_made += 1
            await asyncio.sleep(1)
        
        return authenticated

    async def fuzz_commands(self, fuzzer_type, attempts):
        """Command fuzzing using interesting commands"""
        attempts_made = 0
        
        while attempts_made < attempts:
            if fuzzer_type == 'random':
                # 50% chance to use interesting command as base
                if self.interesting_commands and random.random() < 0.5:
                    base = random.choice(self.interesting_commands)
                    fuzzed_command = self.mutate_command(base)
                else:
                    base = random.choice([COMMANDS['OPEN'], COMMANDS['CLOSE']])
                    fuzz_extra = [random.randint(0, 255) for _ in range(random.randint(0, 5))]
                    fuzzed_command = base + fuzz_extra
            else:  # mutation
                base = random.choice(self.interesting_commands)
                fuzzed_command = self.mutate_command(base)
            
            if self._command_has_known_error(fuzzed_command):
                continue
                
            self.log_print(f'\n[{fuzzer_type.capitalize()} Command {attempts_made}] Sending: {fuzzed_command}')
            
            try:
                res = await self.ble.write_command(fuzzed_command)
                self.log_print(f'[!] Command: {fuzzed_command}')
                self.log_print(f'[!] Response: {res[0]}')
                if res and res[0] != 0:  # Check for non-success response codes
                    self.is_interesting(type_command, fuzzed_command, response=res)
                elif res and res[0] == 4: 
                    # Record the error in our tracking system
                    self.record_new_error(e, type_command, fuzzed_command)
            except Exception as e:
                self.log_print(f'[!] Error: {e}')
                self.is_interesting(type_command, fuzzed_command)
                # Record the error in our tracking system
                self.record_new_error(e, type_command, fuzzed_command)
                if "Not connected" in str(e):
                    await self.ensure_connection()
            
            attempts_made += 1
            await asyncio.sleep(random.uniform(0.5, 3))

    def _command_has_known_error(self, command):
        """Check if this exact command has previously caused an error"""
        command_str = str(command)
        for error_entry in self.known_errors:
            if command_str in error_entry:
                return True
        return False

async def run_random_fuzzer(run_forever=False):
    """Run the random fuzzer"""
    fuzzer = Fuzzer()
    await fuzzer.run_fuzzer('random', 20, 20, run_forever=run_forever)

async def run_mutation_fuzzer(run_forever=False):
    """Run the mutation-based fuzzer"""
    fuzzer = Fuzzer()
    await fuzzer.run_fuzzer('mutation', 20, 20, run_forever=run_forever)

# Main execution
if __name__ == "__main__":
    try:
        # Choose which fuzzer to run
        asyncio.run(run_random_fuzzer(False))
        # asyncio.run(run_mutation_fuzzer(False))
    except KeyboardInterrupt:
        print("\nProgram Exited by User!")