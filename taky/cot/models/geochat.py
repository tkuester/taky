from datetime import datetime
import enum
import uuid

from lxml import etree

from .teams import Teams
from .event import Event
from .takuser import TAKUser

class ChatParents(enum.Enum):
    ROOT = 'RootContactGroup'
    TEAM = 'TeamGroups'

class GeoChat:
    def __init__(self, chat_parent=None, group_owner=False):
        self.event = None

        self.chat_parent = chat_parent
        self.group_owner = group_owner

        self.src_uid = None
        self.src_cs = None
        self.src_marker = None
        self.src = None

        self.dst_uid = None
        self.dst_cs = None
        self.dst = None

        self.message = None

    @staticmethod
    def from_elm(elm):
        # Sanity check inputs
        if elm.detail is None:
            raise ValueError("Element does not have detail")

        chat = elm.detail.find('__chat')
        chatgrp = None
        if chat is not None:
            chatgrp = chat.find('chatgrp')
        remarks = elm.detail.find('remarks')
        link = elm.detail.find('link')

        if None in [chat, chatgrp, remarks, link]:
            raise ValueError("Detail does not contain GeoChat")

        gch = GeoChat()
        gch.event = elm

        gch.chat_parent = chat.get('parent')
        gch.group_owner = (chat.get('groupOwner') == 'true')
        gch.src_uid = link.get('uid')
        gch.src_cs = chat.get('senderCallsign')
        gch.src_marker = link.get('type')

        gch.dst_cs = chat.get('chatroom')
        if gch.chat_parent == ChatParents.TEAM.value:
            gch.dst = Teams(gch.dst_cs)
            gch.dst_uid = gch.dst.value
        elif gch.dst_cs != 'All Chat Rooms':
            gch.dst_uid = chat.get('id')

        gch.message = remarks.text

        return gch

    @staticmethod
    def build_msg(src, dst, message, time=None):
        if isinstance(dst, TAKUser):
            chat = GeoChat(chat_parent=ChatParents.ROOT.value)
            chat.dst_uid = dst.uid
            chat.dst_cs = dst.callsign
        elif isinstance(dst, Teams):
            chat = GeoChat(chat_parent=ChatParents.TEAM.value)
            chat.dst = dst
            chat.dst_uid = dst.value
            chat.dst_cs = dst.value
        elif dst == 'All Chat Rooms':
            chat = GeoChat(chat_parent=ChatParents.ROOT.value)
            chat.dst_uid = dst
            chat.dst_cs = dst
        else:
            raise ValueError("dst must be string, or TAKUser")

        if not isinstance(src, TAKUser):
            raise ValueError("src must be TAKUser")

        chat.src = src
        chat.src_uid = src.uid
        chat.src_cs = src.callsign
        chat.src_marker = src.marker
        chat.message = message

        if time is None:
            time = datetime.utcnow()
        uid = f'GeoChat.{chat.src_uid}.{chat.dst_cs}.{uuid.uuid4()}'
        chat.event = Event(
            uid=uid,
            etype='b-t-f',
            how='h-g-i-g-o',
            time=time,
            start=time,
            stale=time
        )
        chat.event.point = src.point
        chat.populate_detail()

        return chat

    def populate_detail(self):
        self.event.detail = etree.Element('detail')
        chat = etree.Element('__chat', attrib={
            'parent': self.chat_parent,
            'groupOwner': 'true' if self.group_owner else 'false',
            'chatroom': self.dst_cs,
            'id': self.dst_uid,
            'senderCallsign': self.src_cs
        })
        chatgroup = etree.Element('chatgrp', attrib={
            'uid0': self.src_uid,
            'uid1': self.dst_uid,
            'id': self.dst_uid
        })
        chat.append(chatgroup)
        self.event.detail.append(chat)

        link = etree.Element('link', attrib={
            'uid': self.src_uid,
            'type': self.src_marker,
            'relation': 'p-p'
        })
        self.event.detail.append(link)

        rmk_src = f'BAO.F.ATAK.{self.src_uid}'
        remarks = etree.Element('remarks', attrib={
            'source': rmk_src,
            'to': self.dst_uid,
            'time': self.event.time.isoformat(timespec='milliseconds') + 'Z'
        })
        remarks.text = self.message
        self.event.detail.append(remarks)

        #marti = etree.Element('marti')
        #dest = etree.Element('dest', attrib={
        #    'callsign': dst.callsign
        #})
        #marti.append(dest)
        #evt.detail.append(marti)

        return self.event.as_element

    @property
    def as_element(self):
        return self.event.as_element
