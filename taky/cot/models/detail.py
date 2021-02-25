class Detail:
    elm = None

    def __init__(self, event, elm):
        self.event = event
        self.elm = elm

    def __repr__(self):
        '<GenericDetail>'

    @property
    def marti_cs(self):
        ret = []
        if self.elm is None:
            return ret

        marti = self.elm.find('marti')
        if marti is not None:
            for dest in marti.iterfind('dest'):
                ret.append(dest.get('callsign'))

        return ret

    @property
    def as_element(self):
        return self.elm

    @staticmethod
    def from_elm(elm, event=None):
        return Detail(event, elm)
