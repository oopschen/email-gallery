#!/usr/bin/env python

"""
search by conditions, call handler to dealwith results

### handler interface

class SearchHandler:
  def __init__(self, **kwargs):
    pass

  def handle(self, message):
    pass

  def post_handle(self):
    pass
"""

from imaplib import IMAP4_SSL
import imaplib
import click

COMMAND_ID_NAME = "ID"
ID_COMMAND_FIELDS = [
     "name",
     "version",
     "os",
     "os-version",
     "vendor",
     "support-url",
     "address",
     "date",
     "",
     "command",
     "arguments",
     "",
     "environment"
    ]

if COMMAND_ID_NAME not in imaplib.Commands:
  imaplib.Commands["ID"] = ('NONAUTH', 'AUTH', 'SELECTED', 'LOGOUT')

class IMAP4_SSL_RFC_2971(IMAP4_SSL):

  def id(self, **kwargs):
      """Execute "command arg ..." .

      (typ, [data]) = <instance>.id(command, arg1, arg2, ...)

      Returns response appropriate to 'command'.
      """
      command = COMMAND_ID_NAME
      if not command in imaplib.Commands:
          raise self.error("Unknown IMAP4 id command: %s" % command)

      command_args = []
      for k, v in kwargs.items():
        lower_key = k.lower()
        if lower_key not in ID_COMMAND_FIELDS:
          continue
        command_args.append('"' + lower_key + '"')
        command_args.append('"' + v + '"')

      if len(command_args) < 1:
        raise self.error("no id params found")

      return self._simple_command(command, "(" + ' '.join(command_args) + ")")

@click.command()
@click.option('--imap-server', default='imap.126.com:993', help="imap server with port, host:port")
@click.option('--email-account', required=True, help="email account")
@click.option('--email-password',  required=True, help="email password")
@click.option('--sender',  help="filter senders, seperated by ,")
@click.option('--hdl-attachment-save-dir', default='/tmp/email-attachment', help="handler AttachmentFilterDownloaderHandler destination save directory")
@click.option('--hdl-attachment-name-filter', help="handler AttachmentFilterDownloaderHandler name filters")
@click.option(
    '--hdl',
    default='email_helper.search_handler.AttachmentFilterDownloaderHandler,email_helper.search_handler.ETCSumValueHandler',
    help="handlers names"
    )
def main(imap_server, email_account, email_password, sender, hdl_attachment_save_dir,
    hdl_attachment_name_filter, hdl):
  import email
  import sys
  import importlib as ilb


  # init imap instance
  imap_server, imap_port= imap_server.split(':')
  M = IMAP4_SSL_RFC_2971(imap_server, int(imap_port))
  id_dict = {
			'name': 'ray',
			'version': '1.0.0',
			'vendor': 'chenlei-python',
			'suport-email': email_account
  }
  M.id(**id_dict)

  ## search & deal emails
  login_res, _ = M.login(email_account, email_password)
  if "OK" != login_res:
    print("login fail")
    sys.exit(1)
  print(f"email {email_account} login succeed")

  select_res,_ = M.select('INBOX')
  if "OK" != select_res:
    print("select inbox fail")
    sys.exit(1)

  print("select inbox succeed")

  if None == sender:
    search_criteria = '(UNSEEN)'
  else:
    search_criteria = '(' + ' '.join([ f'FROM "{x}"' for x in sender.split(',') ]) + ')'

  print(f'start searching emails with criteria {search_criteria}')
  search_res, data = M.search("UTF-8", search_criteria)
  if "OK" != search_res:
    print("search fail")
    sys.exit(1)

  elif len(data) < 1 or len(data[0]) < 1:
    print("no mail found")
    sys.exit(0)
  print(f'found {len(data[0].split())} emails')


  handler_args = {
      'dest-dir': hdl_attachment_save_dir,
      'name-filter': hdl_attachment_name_filter
      }

  handler_module = []
  for hname in hdl.split(','):
    last_dot_idx = hname.rfind('.')
    if 0 > last_dot_idx:
      continue
    mod = ilb.import_module(hname[0:last_dot_idx])
    handler_module.append(getattr(mod, hname[last_dot_idx+1:])(**handler_args))

  for msg_id in data[0].split():
    fetch_res, msg_data = M.fetch(msg_id, "(RFC822)")
    if "OK" != fetch_res:
      print(f'msg {msg_id} fetch fail {fetch_res}, {msg_data}')
      continue

    if len(msg_data) < 1 or len(msg_data[0]) < 2:
      print(f'email message fetch error, {msg_data}')
      continue

    raw_msg = email.message_from_bytes(msg_data[0][1])
    for part in raw_msg.walk():
      for h in handler_module:
        h.handle(part)

  for h in handler_module:
    h.post_handle()

  M.logout()
