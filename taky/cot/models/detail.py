from .errors import UnmarshalError


class Detail:
    """
    A simple class to keep track of the Detail element
    """

    def __init__(self, elm):
        self.elm = elm

    def __repr__(self):
        "<GenericDetail>"

    @staticmethod
    def is_type(tags):  # pylint: disable=unused-argument
        """
        Utility method to assist in identifying unknown events.

        @param tags A list of tags contained in the detail
        @return True if the detail contains the identifying tags
        """
        # Always return true for base class
        return True

    @property
    def has_marti(self):
        if self.elm is None:
            return False

        marti = self.elm.find("marti")
        if marti is None:
            return False

        return len(list(self.marti)) > 0

    @property
    def marti(self):
        """
        A list of callsigns and UIDs in the Marti tag, in a tuple of (type, id)

        Returns an empty list if not present
        """
        if self.elm is None:
            return

        marti = self.elm.find("marti")
        if marti is None:
            return

        for dest in marti.iterfind("dest"):
            # Prefer to use UID over Callsign
            if dest.get("uid"):
                yield ("uid", dest.get("uid"))
            else:
                yield ("callsign", dest.get("callsign"))

    @property
    def as_element(self):
        """
        Returns the element representation of the Detail object.

        If the Detail object was created with from_elm(), it should always
        return that exact element. Otherwise, the object should generate the
        element, and return that.
        """
        return self.elm

    @staticmethod
    def from_elm(elm):
        """
        Build a Detail object from an element, with the event for context
        """
        if elm.tag != "detail":
            raise UnmarshalError("Cannot create Detail from %s" % elm.tag)

        return Detail(elm)
