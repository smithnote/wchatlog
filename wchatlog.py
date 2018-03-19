#!/usr/bin/python
# coding=utf-8

# Copyright (c) 2018 smtihemail@163.com. All rights reserved.
# Author：smithemail@163.com
# Time  ：2018-02-09

import os
import queue
import pytz
import datetime
import threading
import wxpy

from optparse import OptionParser
from wxpy import TEXT, PICTURE, SHARING, RECORDING


class DownloadTask(object):
    '''下载任务单元， msg为register中的msg'''
    def __init__(self, msg, file_type, date_str, save_name):
        self.msg = msg
        self.file_type = file_type
        self.date_str = date_str
        self.save_name = save_name


class Downloader(threading.Thread):
    def __init__(self, download_queue, save_dir, dir_level):
        self.download_queue = download_queue
        self.save_directory = save_dir
        self.dir_level = dir_level
        super(Downloader, self).__init__()

    def _remove_empty_file(self, path):
        if os.path.exists(path) and not os.path.getsize(path):
            os.remove(path)

    def _prefix_dir(self, file_type, date_str):
        date = datetime.datetime.strptime(date_str, "%Y%m%d")
        pfdir = self.save_directory + '/' + file_type + '/'
        if self.dir_level == "year":
            pfdir += str(date.year)
        elif self.dir_level == "month":
            pfdir += str(date.year) + '/' + str(date.month)
        elif self.dir_level == "day":
            pfdir += str(date.year) + '/' + str(date.month) + '/' + str(date.day)
        else:
            pfdir += str(date.year)
        os.makedirs(pfdir, exist_ok=True)
        return pfdir

    def download(self, task):
        prefix_dir = self._prefix_dir(task.file_type, task.date_str)
        task.msg.get_file(prefix_dir + '/' + task.save_name)
        self._remove_empty_file(prefix_dir + '/' + task.save_name)

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


class MessageWriter(threading.Thread):
    def __init__(self, msg_queue, save_dir):
        self.msg_queue = msg_queue
        self.save_directory = save_dir
        super(MessageWriter, self).__init__()

    def _prefix_dir(self):
        os.makedirs(self.save_directory, exist_ok=True)
        return self.save_directory

    def write_to_file(self, chat_name, group_mber, sname, ctime, message):
        friend_file = self._prefix_dir() + '/' + chat_name
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
        self.china_tz = pytz.timezone(pytz.country_timezones['CN'][0])

    def _cn_datetime(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp, self.china_tz)

    def start(self):
        save_types = [TEXT, PICTURE, SHARING, RECORDING]
        @self.bot.register(msg_types=save_types, except_self=False)
        def save_text(msg):
            chat = msg.chat
            sender = msg.sender
            ctime = self._cn_datetime(msg.raw.get('CreateTime'))
            date_str = ctime.strftime("%Y%m%d")
            group_member = msg.member.name if isinstance(chat, wxpy.Group) else ''
            sender_name = group_member if group_member else sender.name
            message_text = msg.text

            if msg.type == PICTURE:
                message_text = ctime.strftime("%Y%m%d%H%M%S_")\
                               + chat.name + '_' + sender_name
                message_text += '_' + msg.raw['FileName'].replace('.png', '.jpeg')
                download_task = DownloadTask(msg, 'images', date_str, message_text)
                self.download_queue.put(download_task)
                message_text = '![](images/' + message_text + ')'

            if msg.type == RECORDING:
                message_text = ctime.strftime("%Y%m%d%H%M%S_")\
                               + chat.name + '_' + sender_name
                message_text += '_' + msg.raw['FileName']
                download_task = DownloadTask(msg, 'recordings', date_str, message_text)
                self.download_queue.put(download_task)
                message_text = '![](recordings/' + message_text + ')'

            msg_log = MessageLog(chat.name, group_member,
                                 sender.name, ctime, message_text)
            self.msg_queue.put(msg_log)

        self.bot.join()


def option_parser():
    parser = OptionParser()
    parser.add_option("-l", "--level", type="string", dest="dir_level", default="year",
                      help="文件夹细分粒度，year,month,day, 只对下载文件有效\
                            (the deep dir to save file, only valid for download file)")
    parser.add_option("-s", "--save", type="string", dest="save_dir", default="data",
                      help="保存日志的路径(directory where store logs)")
    return parser.parse_args()

if __name__ == '__main__':
    options, args = option_parser()
    msg_queue = queue.PriorityQueue(maxsize=1000)
    download_queue = queue.Queue(1000)

    messagewriter = MessageWriter(msg_queue, options.save_dir)
    messagewriter.start()
    downloader = Downloader(download_queue, options.save_dir, options.dir_level)
    downloader.start()

    chatlog = ChatLog(msg_queue, download_queue)
    chatlog.start()
