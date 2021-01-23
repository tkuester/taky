from datetime import datetime
import uuid

from lxml import etree

from taky.cot.models.event import Event

class GeoChat(object):
    def __init__(self):
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

    @staticmethod
    def build_msg(src, dst, message, parent='RootContactGroup'):
        now = datetime.utcnow()
        uid = f'GeoChat.{src.uid}.{dst.callsign}.{uuid.uuid4()}'
        evt = Event(
            uid=uid,
            etype='b-t-f',
            how='h-g-i-g-o',
            time=now,
            start=now,
            stale=now
        )
        evt.point = src.point

        evt.detail = etree.Element('detail')
        chat = etree.Element('__chat', attrib={
            'parent': parent,
            'groupOwner': 'false',
            'chatroom': dst.callsign,
            'id': dst.uid,
            'senderCallsign': src.callsign
        })
        chatgroup = etree.Element('chatgrp', attrib={
            'uid0': src.uid,
            'uid1': dst.uid,
            'id': dst.uid
        })
        chat.append(chatgroup)
        evt.detail.append(chat)

        link = etree.Element('link', attrib={
            'uid': src.uid,
            'type': src.marker,
            'relation': 'p-p'
        })
        evt.detail.append(link)

        rmk_src = f'BAO.F.ATAK.{src.uid}'
        remarks = etree.Element('remarks', attrib={
            'source': rmk_src,
            'to': dst.uid,
            'time': now.isoformat(timespec='milliseconds') + 'Z'
        })
        remarks.text = message
        evt.detail.append(remarks)

        marti = etree.Element('marti')
        dest = etree.Element('dest', attrib={
            'callsign': dst.callsign
        })
        marti.append(dest)
        evt.detail.append(marti)

        return evt.as_element

