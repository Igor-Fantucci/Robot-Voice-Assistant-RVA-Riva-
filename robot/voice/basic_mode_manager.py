import config_manager

def compare(text):
    """
    returns True if a matching hot word is found
    :param text:
    :return: comparison result
    """
    return text in config_manager.config['hot-words']
