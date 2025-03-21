def is_interesting(command, response, logs, current_state, seen_responses, seen_logs, seen_behavior_signatures):
    """
    Determines whether the current fuzz input triggered an interesting (new) behavior.
    Tracks:
      - New responses
      - New logs
      - New command/response/state/log combo
    """
    response_tuple = tuple(response) if isinstance(response, list) else (response,)
    log_tuple = tuple(logs) if isinstance(logs, list) else (logs,)
    command_tuple = tuple(command)

    is_new_response = response_tuple not in seen_responses
    is_new_log = log_tuple not in seen_logs

    behavior_signature = (command_tuple, response_tuple, current_state, log_tuple)
    is_new_behavior = behavior_signature not in seen_behavior_signatures

    # Track seen values
    if is_new_response:
        seen_responses.add(response_tuple)
    if is_new_log:
        seen_logs.add(log_tuple)
    if is_new_behavior:
        seen_behavior_signatures.add(behavior_signature)

    return is_new_response or is_new_log or is_new_behavior

# on top of fuzz_with_state_tracking function before the loop
seen_responses = set()
seen_logs = set()
seen_behavior_signatures = set()

#after each test add:
# if is_interesting(command_data, res, logs, current_state, seen_responses, seen_logs, seen_behavior_signatures):
#     print("[+] Interesting behavior found!")
#     log_comment(log_filename, "[+] Interesting behavior found!")
#     # Optionally, call save_interesting_input(...)

#save intersting inputs:
# def save_interesting_input(command, response, logs, state):
#     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
#     fname = os.path.join("logs", f"interesting_{timestamp}.txt")
#     with open(fname, "w") as f:
#         f.write(f"Command: {command}\n")
#         f.write(f"Response: {response}\n")
#         f.write(f"State: {state}\n")
#         f.write("Logs:\n")
#         if isinstance(logs, list):
#             for line in logs:
#                 f.write(line + "\n")
#         else:
#             f.write(str(logs) + "\n")
