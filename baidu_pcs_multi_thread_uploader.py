# coding=utf-8

import time
import math
import os
import io
import shutil
import json
import requests
import subprocess
import threading
import argparse

from baidupcsapi import PCS

class BaiduPCS(object):
    """
    Baidu disk uploader.
    """
    def __init__(self, filepath, username, password):
        """
        Login
        """
        (self.filepath, self.filename, self.dirname, self.filesize) = (filepath, os.path.basename(filepath), os.path.dirname(filepath), os.path.getsize(filepath))
        self.path = self.dirname + '\\' + self.filename.split('.')[0]
        self.pcs = PCS(username, password) #Login

    def create_upload(self, num):
        self.uplog['md5'][num] = (json.loads(self.pcs.upload_tmpfile(self.block((num - 1) * self.chinksize)).content)['md5'])
        self.count += 1
        with open(self.dirname +'\\'+ self.filename.split('.')[0] + '.json', 'w') as self.new_uplog:
            json.dump(self.uplog, self.new_uplog)
        print('[' + str(self.count) + '/' + str(self.fid) + ' Uploaded   BlockID: ' + str(num) + '   md5: '+ self.uplog['md5'][num] + ']')

    def read_uplog(self):
        if os.path.exists(self.dirname +'\\'+ self.filename.split('.')[0] + '.json'):
            with open(self.dirname +'\\'+ self.filename.split('.')[0] + '.json', 'r') as self.uplog_file:
                self.uplog = json.load(self.uplog_file)
            tmp_dict = {}
            for i in sorted(self.uplog['md5'].keys()):
                tmp_dict[int(i)] = self.uplog['md5'][i]
            self.uplog['md5'] = tmp_dict
        else:
            self.uplog_file = open(self.dirname +'\\'+ self.filename.split('.')[0] + '.json', 'w')
            self.uplog = {'block': 0, 'size': 0, 'md5': {}}

    def block(self, location=None):
        if location == None:
            return math.ceil(os.path.getsize(self.filepath) / self.chinksize)
        file = open(self.filepath, 'rb')
        file.seek(location, 0)
        return io.BytesIO(file.read(self.chinksize))

    def upload(self):
        """
        Biadu upload module
        """
        self.read_uplog()

        if int(self.uplog['size']) == 0:
            self.chinksize = 1024 * 1024 * 24
            self.uplog['size'] = self.chinksize
        else:
            self.chinksize = self.uplog['size']

        self.thread_num = 25

        if int(self.uplog['block']) == 0:
            self.fid = self.block()

        self.count = len(self.uplog['md5'])

        with open(self.dirname +'\\'+ self.filename.split('.')[0] + '.json', 'w') as self.new_uplog:
            json.dump(self.uplog, self.new_uplog)

        print('start uploading...')
        self.threads = []
        for i in range(self.fid):
            if not i + 1 in self.uplog['md5']:
                while len(threading.enumerate()) - 1 >= self.thread_num:
                    time.sleep(1)
                self.t = threading.Thread(target=self.create_upload,kwargs={'num': i + 1})
                self.t.setDaemon(True)
                self.t.start()
                self.threads.append(self.t)

        for self.thread in self.threads:
            self.thread.join()

    def superfile(self):
        self.pcs.upload_superfile('/' + self.filename, [(self.uplog['md5'][k]) for k in sorted(self.uplog['md5'].keys())])

    def CheckUpload(self):
        """
        Check upload status.
        Retry if file not uploaded.
        """
        if not self.fid == len(self.uplog['md5']):
            return 0
        return 1

    def GetRandomPassword(self, randomlength=4):
        """
        Get 4 bit random password.
        :return: password.
        """
        self.str = ''
        self.chars = 'qwertyuiopasdfghjklzxcvbnm01234d56789'
        self.length = len(self.chars) - 1
        self.random = Random()
        for i in range(randomlength):
            self.str += self.chars[self.random.randint(0, self.length)]
        return self.str

    def quota_remaining(self):
        self.quota_info = json.loads(self.pcs.quota().content.decode("utf-8", "ignore"))
        self.remaining = self.quota_info['total'] - self.quota_info['used']
        return self.remaining

#MAIN
parser = argparse.ArgumentParser(description='PCS_UPLOADER')
parser.add_argument('filepath', help='Input file path')
args = parser.parse_args()
filepath = args.filepath


username = ''  ## <- your user name
password = ''  ## <- your password
bpcs = BaiduPCS(filepath, username, password)

bpcs.upload()

if bpcs.quota_remaining() > bpcs.filesize:
    bpcs.superfile()
