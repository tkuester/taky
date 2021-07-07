from .xmldeclstrip import XMLDeclStrip
from . import rotc
from . import datapackage


def seconds_to_human(sec):
    """
    Converts seconds into human readable format

    Input: seconds_to_human(142)
    Output: 00h 02m 22.000s
    """
    days = sec // (24 * 60 * 60)
    sec -= days * (24 * 60 * 60)

    hours = sec // (60 * 60)
    sec -= hours * (60 * 60)

    minutes = sec // 60
    sec -= minutes * 60

    ret = "%02dh %02dm %06.3fs" % (hours, minutes, sec)
    if days > 0:
        if days > 1:
            ret = "%dd " % days + ret
        else:
            ret = "%dd " % days + ret

    return ret


def pprinttable(rows):
    """
    Pretty Print a table of collections.namedtuples

    Kudos to @MattH on Stack Overflow

    @args rows A list of named tuples
    """
    headers = rows[0]._fields
    lens = []
    for i in range(len(rows[0])):
        lens.append(
            len(max([x[i] for x in rows] + [headers[i]], key=lambda x: len(str(x))))
        )

    formats = []
    hformats = []
    for i in range(len(rows[0])):
        if isinstance(rows[0][i], (int, float)):
            formats.append("%%%dd" % lens[i])
        else:
            formats.append("%%-%ds" % lens[i])
        hformats.append("%%-%ds" % lens[i])

    pattern = " | ".join(formats)
    hpattern = " | ".join(hformats)
    separator = "-+-".join(["-" * n for n in lens])

    print(hpattern % tuple(headers))
    print(separator)
    for line in rows:
        print(pattern % tuple(t for t in line))
