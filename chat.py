#!/usr/bin/python
# coding=utf-8

# Copyright (c) 2018 smtihemail@163.com. All rights reserved.
# Author：smithemail@163.com
# Time  ：2018-02-09

import os
import queue
import datetime
import threading
import wxpy


class DownloadTask(object):
    '''下载任务单元， msg为register中的msg'''
    def __init__(self, msg, save_text):
        self.msg = msg
        self.save_text = save_text


class Downloader(threading.Thread):
    def __init__(self, download_queue):
        self.download_queue = download_queue
        self.image_dir = 'images/'
        super(Downloader, self).__init__()

    def download(self, task):
        year = datetime.datetime.now().strftime("%Y")
        if not os.path.isdir(year):
            os.mkdir(year)
        if not os.path.isdir(year + '/' + self.image_dir):
            os.mkdir(year + '/' + self.image_dir)
        task.msg.get_file( year + '/' + self.image_dir + task.save_text)

    def run(self):
        while True:
            task = download_queue.get()
            self.download(task)


class MessageLog(object):
    def __init__(self, chat_name, group_mber, sname, ctime, message):
        self.chat_name = chat_name
        self.group_mber = group_mber
        self.sname = sname
        self.ctime = ctime
        self.message = message

    def __cmp__(self, other):
        '''按时间大小排序, 时间小的先写入文件'''
        return self.ctime > other.ctime


class Writer(threading.Thread):
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue
        super(Writer, self).__init__()

    def write_to_file(self, chat_name, group_mber, sname, ctime, message):
        year = datetime.datetime.now().strftime("%Y")
        if not os.path.isdir(year):
            os.mkdir(year)
        friend_file = year + '/' + chat_name
        with open(friend_file, 'a+') as fp:
            fp.write('[' + ctime.strftime("%Y-%m-%d %H:%M:%S") + ']')
            if group_mber:
                fp.write('[' + chat_name + ']')
                fp.write('[' + group_mber + ']')
            else:
                fp.write('[' + sname + "]")
            fp.write(':' + message + '\n')
            fp.flush()

    def run(self):
        while True:
            message_log = self.msg_queue.get()
            try:
                self.write_to_file(message_log.chat_name,
                                   message_log.group_mber,
                                   message_log.sname,
                                   message_log.ctime,
                                   message_log.message)
            except Exception as e:
                print("message write err:%s" % str(e))


class ChatLog(object):
    def __init__(self, msg_queue, download_queue):
        self.msg_queue = msg_queue
        self.download_queue = download_queue
        self.bot = wxpy.Bot(cache_path='/tmp/chatlog.cache', console_qr=True)
        self.bot.enable_puid()
        self.friends = [friend.name for friend in self.bot.friends()]
        self.myself = self.friends[0]

    def start(self):
        @self.bot.register(msg_types=[wxpy.TEXT, wxpy.SHARING, wxpy.PICTURE], except_self=False)
        def save_text(msg):
            chat = msg.chat
            sender = msg.sender
            ctime = msg.create_time
            group_member = msg.member.name if isinstance(chat, wxpy.Group) else ''
            message_text = msg.text
            if msg.type == wxpy.PICTURE:
                sender_name = group_member if group_member else sender.name
                message_text = ctime.strftime("%Y%m%d%H%M%S_") + chat.name + '_'+ sender_name
                message_text += '_' + msg.raw['FileName'].replace('.png', '.jpeg')
                download_task = DownloadTask(msg, message_text)
                self.download_queue.put(download_task)
                message_text = '![](' + message_text + ')'
            msg_log = MessageLog(chat.name, group_member,
                                 sender.name, ctime, message_text)
            self.msg_queue.put(msg_log)

        self.bot.join()


if __name__ == '__main__':
    msg_queue = queue.PriorityQueue(maxsize=1000)
    download_queue = queue.Queue(1000)

    writer = Writer(msg_queue)
    writer.start()
    downloader = Downloader(download_queue)
    downloader.start()

    chatlog = ChatLog(msg_queue, download_queue)
    chatlog.start()
