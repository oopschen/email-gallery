#!/usr/bin/env python3

import os.path
import re
import email.header as eh


def global_counter(max_value = 1000000):
  for i in range(0, max_value + 1):
    yield i

class AttachmentFilterDownloaderHandler:

  def __init__(self, **kwargs):

    self._def_defaults_val(**kwargs)

    if not os.path.exists(self.__dest_dir):
      os.makedirs(self.__dest_dir)

  def handle(self, msg_part):
    if None == msg_part.get_filename():
      return

    filename, charset = eh.decode_header(msg_part.get_filename())[0]
    if None != charset:
      filename = filename.decode(charset)

    if self.__filter_attachment(msg_part.get_content_type(), filename):
      real_filename = str(next(self.__gcounter))+ "-" + filename
      print("Create attachment: %s"%(real_filename))
      with open(os.path.join(self.__dest_dir,  real_filename), 'wb+') as f:
        f.write(msg_part.get_payload(decode=True))

  def post_handle(self):
    pass

  def _def_defaults_val(self, **kwargs):
    dest_dir_key = 'dest-dir'
    if dest_dir_key in kwargs:
      self.__dest_dir = kwargs[dest_dir_key]
    else:
      self.__dest_dir = '/tmp/email-attachment'

    name_filter_key = 'name-filter'
    if name_filter_key in kwargs and None != kwargs[name_filter_key]:
      self.__name_filter= kwargs[name_filter_key].split(',')
    else:
      self.__name_filter = None

    self.__gcounter = global_counter()

  def __filter_attachment(self, content_type, attachment_name):
    if None == self.__name_filter:
      return True

    for name in self.__name_filter:
      if attachment_name.find(name) > -1:
        return True
    return False


class ETCSumValueHandler:

  def __init__(self, **kwargs):

    self._def_defaults_val(**kwargs)

  def handle(self, msg_part):
    if msg_part.get_content_maintype().lower() == 'text':
      msg = msg_part.get_payload(decode = True).decode('utf-8')
      matcher = self.__tol_re_pattern.match(msg)
      if None == matcher:
        return
      self.__sum_amount += float(matcher.group(1))

  def post_handle(self):
    print("total etc value = %0.2f"%(self.__sum_amount))

  def _def_defaults_val(self, **kwargs):
    self.__sum_amount = 0
    self.__tol_re_pattern = re.compile('.+发票金额共计.+>([0-9][0-9.]+)<.+元', re.U | re.S | re.I)

    name_filter_key = 'name-filter'
    if name_filter_key in kwargs and None != kwargs[name_filter_key]:
      self.__name_filter= kwargs[name_filter_key].split(',')
    else:
      self.__name_filter = None
