VERSION = (4, 0, 1, "final", 0)
__AUTHOR__ = "Sebastian Major"
__AUTHOR_EMAIL__ = "sebastian.major@charite.de"


def get_version():
    if VERSION[3] == "final":
        return "%s.%s.%s" % (VERSION[0], VERSION[1], VERSION[2])
    elif VERSION[3] == "dev":
        if VERSION[2] == 0:
            return "%s.%s.%s%s" % (VERSION[0], VERSION[1], VERSION[3],
                                   VERSION[4])
        return "%s.%s.%s.%s%s" % (VERSION[0], VERSION[1], VERSION[2],
                                  VERSION[3], VERSION[4])
    else:
        return "%s.%s.%s%s" % (VERSION[0], VERSION[1], VERSION[2], VERSION[3])

__version__ = get_version()
