def process_mention(arg):
    """
    Processes the mention at the start of commands

    Parameters:
    - arg (str): The command argument.

    Returns:
    - str: The updated processed mention
    """

    if arg is None:
        return ""

    elif arg.startswith('@'):
        return arg + ", "

    else:
        return '@' + arg + ", "