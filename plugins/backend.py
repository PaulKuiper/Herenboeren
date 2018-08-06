from bottle import get
import datetime
from mongoengine import Document, connect
from mongoengine import StringField, DateTimeField, FileField

mount_url = "/backend/"

DB_NAME = 'test'
PAGE_SIZE = 5

# Data models

class Message(Document):
    nickname = StringField(required=True)
    text = StringField(required=True)
    date = DateTimeField(required=True, default=datetime.datetime.now)
    image_filename = StringField()
    image = FileField()
    thumb = FileField()

connect(DB_NAME, host='server', port=27017)
# msg = Message()
# msg.nickname = 'test'
# msg.text = 'test'
# msg.save()


# Data API


@get("/")
def root():
    return "<a href='./messages'>Messages</a>"


@get(["/messages", '/messages/<page:int>'])
def messages(page=0):
    page = int(page)
    prev_page = None
    next_page = None
    if page > 0:
        prev_page = page - 1
    if Message.objects.count() > (page + 1) * PAGE_SIZE:
        next_page = page + 1
    msgs = (Message.objects
            .order_by('-date')
            .skip(page * PAGE_SIZE)
            .limit(PAGE_SIZE))
    return {'messages': [m.nickname for m in msgs],
            'prev_page': prev_page,
            'next_page': next_page,
           }
