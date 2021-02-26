import enum

from lxml import etree

from .detail import Detail
from .teams import Teams

ALL_CHAT_ROOMS = 'All Chat Rooms'

class ChatParents(enum.Enum):
    ROOT = 'RootContactGroup'
    TEAM = 'TeamGroups'

class GeoChat(Detail):
    '''
    Class representing a GeoChat message

    The GeoChat messages sent from Android are a bit difficult to
    parse. Many fields are redundant, or conflicting in type. This class
    attempts to unify the field names and meanings.
    '''
    def __init__(self, event, elm):
        super().__init__(event, elm)

        self.chatroom = None # detail/__chat.chatroom
        self.chat_parent = None # detail/__chat.parent
        self.group_owner = False # detail/__chat.groupOwner

        # We get these fields explicitly
        self.src_uid = None # detail/link.uid
        self.src_cs = None # detail/__chat.senderCallsign
        self.src_marker = None # detail/link.type
        self.message = None # detail/remarks

        # These fields are inferred
        # The UID (string) of the recipient (if an individual user, otherwise None)
        self.dst_uid = None
        # cot.Teams (if a group message, otherwise None)
        self.dst_team = None

    def __repr__(self):
        if self.broadcast:
            return '<GeoChat src="%s", dst="%s", msg="%s">' % (self.src_cs, ALL_CHAT_ROOMS, self.message)
        elif self.dst_team:
            return '<GeoChat src="%s", dst="%s", msg="%s">' % (self.src_cs, self.dst_team, self.message)
        else:
            return '<GeoChat src="%s", dst_uid="%s", msg="%s">' % (self.src_cs, self.dst_uid, self.message)

    @property
    def broadcast(self):
        ''' Returns true if message is sent to all chat rooms '''
        return self.chatroom == ALL_CHAT_ROOMS

    @staticmethod
    def from_elm(elm, event=None):
        chat = elm.find('__chat')
        chatgrp = None
        if chat is not None:
            chatgrp = chat.find('chatgrp')
        remarks = elm.find('remarks')
        link = elm.find('link')

        if None in [chat, chatgrp, remarks, link]:
            raise ValueError("Detail does not contain GeoChat")

        gch = GeoChat(event, elm)
        gch.chat_parent = chat.get('parent')
        gch.group_owner = (chat.get('groupOwner') == 'true')
        gch.src_uid = link.get('uid')
        gch.src_cs = chat.get('senderCallsign')
        gch.src_marker = link.get('type')

        gch.chatroom = chat.get('chatroom')
        if gch.chat_parent == ChatParents.TEAM.value:
            gch.dst_team = Teams(gch.chatroom)
        elif gch.chatroom != ALL_CHAT_ROOMS:
            # Router will have to fill out .dst
            gch.dst_uid = chat.get('id')

        gch.message = remarks.text

        return gch

    @property
    def as_element(self):
        if self.elm is not None:
            return self.elm

        # Fill in hacky destination UID
        if self.broadcast:
            dst_uid = ALL_CHAT_ROOMS
        elif self.dst_team:
            dst_uid = self.dst_team.value
        else:
            dst_uid = self.dst_uid

        detail = etree.Element('detail')
        # id is optional for All Chat Rooms?
        chat = etree.Element('__chat', attrib={
            'parent': self.chat_parent,
            'groupOwner': 'true' if self.group_owner else 'false',
            'chatroom': self.chatroom,
            'id': dst_uid,
            'senderCallsign': self.src_cs
        })
        chatgroup = etree.Element('chatgrp', attrib={
            'uid0': self.src_uid,
            'uid1': dst_uid,
            'id': dst_uid
        })
        chat.append(chatgroup)
        detail.append(chat)

        link = etree.Element('link', attrib={
            'uid': self.src_uid,
            'type': self.src_marker,
            'relation': 'p-p'
        })
        detail.append(link)

        rmk_src = f'BAO.F.ATAK.{self.src_uid}'
        remarks = etree.Element('remarks', attrib={
            'source': rmk_src,
            'to': dst_uid,
            'time': self.event.time.isoformat(timespec='milliseconds') + 'Z'
        })
        remarks.text = self.message
        detail.append(remarks)

        return detail
