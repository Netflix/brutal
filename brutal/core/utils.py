import functools

#TODO: not using this anymore.
def decorator(plz_decorate):
    """
    create a decorator out of a function
    uh.. i hope this works the way i want it to work
    """
    @functools.wraps(plz_decorate)
    def final(func=None, **kwargs):

        def decorated(func):
            @functools.wraps(func)
            def wrapper(*a, **kw):
                return plz_decorate(func, a, kw, **kwargs)
            return wrapper

        if func is None:
            return decorated
        else:
            return decorated(func)

    return final


class PluginRoot(type):
    """
    metaclass that all plugin base classes will use
    """
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'plugins'):
            # only execs when processing mount point itself
            cls.plugins = []
        else:
            # plugin implementation, register it
            cls.plugins.append(cls)