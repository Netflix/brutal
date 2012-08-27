def catch_error(failure):
    """ used for errbacks
    """
    return failure.getErrorMessage()