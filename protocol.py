NO_PARAMS = 0
ONE_PARAM = 1
TWO_PARAMS = 2
THREE_PARAMS = 3

# all requests are built like this: "[command]-[param]"


def check_cmd(data):
    """
    Check if the command is defined in the protocol, including parameters
    """
    cmd_list = [['exit', NO_PARAMS], ['register', THREE_PARAMS], ['registered', NO_PARAMS], ['error_password', NO_PARAMS]
                , ['error_registering_name', NO_PARAMS], ['error_registering_pass', NO_PARAMS], ['log_in', TWO_PARAMS], ['log_in_acc', NO_PARAMS],
                ['log_in_err', NO_PARAMS], ['request_file', ONE_PARAM], ['request_file', ONE_PARAM]]
# request file: track id
    for command in cmd_list:
        if data.find(command[0]) == 0:  # if it can find the command, goes on
            data_arr = data.split("-")
            if len(data_arr) - 1 == command[1]:  # checks if the amount of params is correct
                return True
    return False
