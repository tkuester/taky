class XMLDeclStrip:
    '''
    Strip "<?xml" declarations from a stream of data.

    This is an ugly work around for several problems.

    1. The XML stream comes over TCP, and may be arbitrarily broken up at any
       point in time.

    2. The Android ATAK client sends every COT Event as a complete XML document
       with a declaration.

    3. The lxml XMLPullParser does not like it when you send it more than one
       declaration, or more than one root element, and drops the rest of the
       input.

    4. As far as I can tell, there's no way to disable this behavior, or
       turn the error into a warning.

    There are a few naive strategies to get around this.

    1. Feed the document character by character to the parser, and let it
       discard the invalid data. read_events() will be a stream of event
       elements.

    2. Instead of using a pull parser, try to parse the stream as a complete
       document and close the parser when the event is received. This is "more
       correct", but we have to be able to locate the end of the document.

    3. Prime the pull parser with a fake <root> element, and filter out the XML
       declaratoins. read_events() will work again.

    4. Switch to an XML parsing library that does this for us, or figure out
       a better way to use lxml.

    Strategy 4 is the best -- but lxml seems to be the heavyweight here, and
    I've given up my Google search.

    Apparently, COT will only have <event> as the root element, so strategy
    2 may be safe. This code could be changed to look for "</event>" -- but
    closing XML elements has many edge cases. (For example, "</event >" is a
    valid way of closing an element.)

    The logic here is a bit obtuse, but should be fairly efficient, and a
    little more general purpose than looking for the end of a document.

    TODO: Make this entire process transparent, and monkeypatch / subclass
          the XMLPullParser
    '''

    def __init__(self):
        # Keep the tail of the buffer if we don't have enough information to know
        # whether or not we should feed it to the client yet
        self.tail = b''
        # Handle state between calls -- are we in an XML declaration right now?
        self.in_decl = False

    def feed(self, data):
        start_tag = b'<?xml '
        end_tag = b'?>'

        ret = bytes()
        data = (self.tail + data)
        while len(data) > 0:
            if not self.in_decl:
                # If we're not in a declaration, look for the start tag
                try:
                    pos = data.index(start_tag)

                    # We found it, consume everything up to that point
                    self.in_decl = True
                    ret += data[:pos]
                    data = data[pos + len(start_tag):]
                except ValueError:
                    # We didn't find it. Let's check to see if we need to keep
                    # any part of the tail. A '<' character could be the start
                    # of an element, or the start of a declaration. We won't
                    # know until we get the next few bytes.

                    pos = data.rfind(b'<')
                    if pos < 0:
                        # We didn't find it, we can feed all of the buffer,
                        # consume all
                        self.tail = b''
                        ret += data
                    elif len(data) - pos >= len(start_tag):
                        # We found it, but far back enough that we know it's
                        # not our start condition, consume all
                        self.tail = b''
                        ret += data
                    else:
                        # We found something we're not sure about. Consume up
                        # to that point, and leave the rest in the tail.
                        self.tail = data[pos:]
                        ret += data[:pos]

                    return ret

            else:
                try:
                    pos = data.index(end_tag)

                    # We found the end tag, skip to it, trim the tail buffer,
                    # and continue processing.
                    self.in_decl = False
                    data = data[pos + len(end_tag):]
                    self.tail = b''
                    continue
                except ValueError:
                    # We didn't find our end tag... but the final characters
                    # may be a part of it. (ie: a trailing '?') We have nothing
                    # more to store, so return whatever we have left.
                    self.tail = data[-1:]
                    return ret

        # In the event we consumed everything cleanly!
        return ret
