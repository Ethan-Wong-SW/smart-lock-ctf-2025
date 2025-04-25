# Smart Lock Fuzzer Toolkit

A toolkit specifically developed for fuzzing the Bluetooth Smart Lock device for SUTD's Software Testing and Verification Course. This toolkit also includes the script for reproducing errors.

## Overview

This repository contains two main components:
1. **Smart Lock Fuzzer** - A fuzzing tool designed to discover vulnerabilities in the Bluetooth Smart Lock device
2. **Error Reproduction Script** - A tool for reliably reproducing discovered error codes

## Features

### Smart Lock Fuzzer
- Multiple fuzzing strategies (random, mutation-based, and hybrid)
- State-aware fuzzing with built-in state machine
- Error pattern detection and tracking
- Automatic saving of interesting inputs that trigger errors
- Logging of all test cases and device responses

### Error Reproduction Script / Proof-of-Concept Code
- Targeted reproduction of specific error codes
- Logging of device behavior

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Ethan-Wong-SW/smart-lock-ctf-2025.git
```
2. Install dependencies for the smart lock:
```bash
pip install -r requirements.txt
```

## Disclaimer

It is recommended to run this fuzzer on **Windows** for full functionality. The fuzzing system has not been tested on macOS, and due to a macOS-specific failsafe, the smart lock may not operate as intended on those devices.


## Running the Fuzzer for Windows

Head to the `run.bat` file located at the root directory and ensure that the file looks like the following:
```batch
@REM .\venv\python error_reproduction.py %1
.\venv\python final_fuzzer_Smartlock.py %1
```
**Ensure that the `.\venv\python error_reproduction.py` line is commented out so that only the fuzzer runs.**

The main fuzzer can be run on Windows with:
```
./run.bat
```
Available strategies (modify the main section of the script to select):

- Random fuzzing
- Mutation-based fuzzing
- Hybrid (random + mutation) fuzzing

Configuration options:

- Number of authentication attempts **(5 by default)**
- Number of command attempts **(5 by default)**
- Maximum fuzzing cycles **(None by default)**
- Run indefinitely **(False by default)**

Examples of how to run the fuzzer in the main function:
```python
# Random & Mutation fuzzing with 10 authentication & 10 command attempts in each fuzzing cycle and the fuzzer will run for 40 cycles (each cycle will run the the authentication fuzzing for 10 times and command fuzzing for 10 times)
asyncio.run(run_random_mutation_fuzzer(10, 10, max_cycles=40))         

# Random fuzzing with 5 (default value) authentication & command attempts in each fuzzing cycle and the fuzzer will run for one cycle (each cycle will run the the authentication fuzzing for 5 times and command fuzzing for 5 times)
asyncio.run(run_random_fuzzer())

# Mutation-based fuzzing with 5 authentication & command attempts in each fuzzing cycle and the fuzzer will run for indefinitely until the user breaks out with ctrl+c (each cycle will run the the authentication fuzzing for 5 times and command fuzzing for 5 times)
asyncio.run(run_mutation_fuzzer(5, 5, run_forever=True))         
```

## Running Error Reproduction Tests or Proof-of-Concept code on Windows

Head to the `run.bat` file located at the root directory and ensure that the file looks like the following:
```batch
.\venv\python error_reproduction.py %1
@REM .\venv\python final_fuzzer_Smartlock.py %1
```
**Ensure that the `.\venv\python final_fuzzer_Smartlock.py` line is commented out so that only the PoC code runs.**

The PoC code can be run on Windows with:
```
./run.bat
```

Modify the script to uncomment the specific test case you want to run (located at the end of the file):
```python
try:
    # Run a specific test:
    # asyncio.run(error_0x018374()) 
    # asyncio.run(error_0x398472()) 
    # asyncio.run(error_blue_screen()) 
    # asyncio.run(error_oserror()) 
    asyncio.run(error_0xtttttt()) 
    # asyncio.run(error_0x298173()) 
except KeyboardInterrupt:
    print("\nProgram Exited by User!")
```

> [!IMPORTANT]
> Ensure that only ONE test case is uncommented when running this script. If multiple test cases are run at once, the error may not be reproduced.

## Error Tracking System

The fuzzer automatically records discovered vulnerabilities and interesting inputs in `known_errors_and_interesting_inputs.json`. 

This system:
- Persists error patterns between sessions (unless the JSON file is moved or deleted)
- Guides mutation-based fuzzing strategies
- Captures detailed error or interesting input context including:
    - Error codes/messages
    - Input sequences that triggered them
    - Device state history

### Important Note About JSON Files:

For separate fuzzing attempts:
If you want to maintain distinct records for different fuzzing sessions, either:

- **Rename/move** the existing JSON file before starting a new session (e.g., known_errors_attempt1.json), OR
- **Delete** the file before each new fuzzing run

By default, new findings will be appended to the existing JSON file if it's present.  

File Structure Example:
```json
[
  {
    "error": "018374",
    "input": [0],
    "type": "command_code",
    "history":[
        {
            "state":"Locked before authentication",
            "command":[0,43,66,139,140,20,130],
            "response":1
        }
    ]
  }
]
```
## Logs

All test sessions generate logs in the `logs/` directory with timestamps. These include:
- Commands sent
- Responses received
- Device state changes
- Any errors encountered
- BLE smart lock logs

## State Tracking System

The fuzzer includes a state tracker that models the Smart Lock's expected behavior using a finite state machine. This ensures the fuzzer understands the device's current state and can detect anomalous transitions.

Key Components:

State Definitions (STATES dictionary):
```python
STATES = {
    'BEF_AUTH_LOCKED': 'Locked before authentication', # Initial state  
    'AUTHENTICATED': 'Authenticated', # After successful auth             
    'UNLOCKED': 'Unlocked', # After open command                        
    'LOCKED': 'Locked' # After close command                          
}
```
Transition Rules (transition_rules dictionary):

Defines valid state transitions based on `(command, response)` pairs

Example transition:
```python
# if the command is AUTH and the response is SUCCESS, move to the Authenticated state.
(COMMANDS['AUTH'][0], RESPONSES['SUCCESS']): STATES['AUTHENTICATED']
```
Expected Behavior (expected_states dictionary):

Defines the valid or expected commands/responses in each state

Example:
```python
STATES['BEF_AUTH_LOCKED']: {
    'allowed_commands': COMMANDS['AUTH'][0],
    'expected_responses': [RESPONSES['AUTHFAIL'], ...]
}
```
How It Works:

- The tracker begins in `BEF_AUTH_LOCKED` state

- For each command/response pair:

    - Validates against current state's transition rules

    - Updates state if transition is valid

    - Flags unexpected transitions as potentially interesting

- Contains a command/response history array for debugging