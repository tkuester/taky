from datetime import datetime
import uuid

from lxml import etree

from taky.cot.models.point import Point
from taky.cot.models.event import Event

class GeoChat(object):
    def __init__(self):
        self.src_usr = None
        self.dst_usr = None

        self.uid = None
        self.chatroom = None
        self.chat_id = None
        self.sender_cs = None
        self.remarks_to = None
        self.remarks_src = None
        self.message = None
        self.parent = 'RootContactGroup'

        self.time = None
        self.point = None

    @staticmethod
    def from_elm(elm):
        # Sanity check inputs
        if elm.detail is None:
            return

        chat = elm.detail.find('__chat')
        remarks = elm.detail.find('remarks')

        if chat is None or remarks is None:
            return

        gch = GeoChat()
        gch.uid = elm.uid
        gch.time = elm.time
        gch.point = elm.point

        gch.chat_parent = chat.get('parent')
        gch.chatroom = chat.get('chatroom')
        gch.chat_id = chat.get('id')
        gch.sender_cs = chat.get('senderCallsign')
        gch.remarks_to = remarks.get('to')
        gch.remarks_src = remarks.get('source')
        gch.message = remarks.text

        return gch

    def __str__(self):
        return "[ #%s ] < %s >: %s" % (self.chatroom, self.sender_cs, self.message)

    @property
    def as_element(self):
        now = datetime.utcnow()
        uid = f'GeoChat.{self.src_usr.uid}.{self.dst_usr.callsign}.{uuid.uuid4()}'
        evt = Event(
            uid=uid,
            etype='b-t-f',
            how='h-g-i-g-o',
            time=now,
            start=now,
            stale=now
        )
        evt.point = self.src_usr.point

        evt.detail = etree.Element('detail')
        chat = etree.Element('__chat', attrib={
            'parent': self.parent,
            'groupOwner': 'false',
            'chatroom': self.dst_usr.callsign,
            'id': self.dst_usr.uid,
            'senderCallsign': self.src_usr.callsign
        })
        chatgroup = etree.Element('chatgrp', attrib={
            'uid0': self.src_usr.uid,
            'uid1': self.dst_usr.uid,
            'id': self.dst_usr.uid
        })
        chat.append(chatgroup)
        evt.detail.append(chat)

        link = etree.Element('link', attrib={
            'uid': self.src_usr.uid,
            'type': self.src_usr.marker,
            'relation': 'p-p'
        })
        evt.detail.append(link)

        rmk_src = f'BAO.F.ATAK.{self.src_usr.uid}'
        remarks = etree.Element('remarks', attrib={
            'source': rmk_src,
            'to': self.dst_usr.uid,
            'time': now.isoformat(timespec='milliseconds') + 'Z'
        })
        remarks.text = self.message
        evt.detail.append(remarks)

        marti = etree.Element('marti')
        dest = etree.Element('dest', attrib={
            'callsign': self.dst_usr.callsign
        })
        marti.append(dest)
        evt.detail.append(marti)

        return evt.as_element

