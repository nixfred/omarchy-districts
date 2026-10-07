"""Real local WebSocket protocol fixture, never existing user provider sessions."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest

spec=importlib.util.spec_from_file_location('sessions',Path(__file__).resolve().parents[1]/'sessions.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
ID='11111111-1111-4111-8111-111111111111'
MESSAGE='22222222-2222-4222-8222-222222222222'

class Server:
 def __init__(self,home,*,approval=False,bad_accept=False):
  self.path=Path(home)/'app-server-control/app-server-control.sock';self.path.parent.mkdir();self.sock=socket.socket(socket.AF_UNIX);self.sock.bind(str(self.path));os.chmod(self.path,0o600);self.sock.listen(1);self.sock.settimeout(3)
  self.approval=approval;self.bad_accept=bad_accept;self.calls=[];self.error=None;self.done=False
  self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
 def read(self,c,n):
  b=b''
  while len(b)<n:
   d=c.recv(n-len(b))
   if not d:raise EOFError
   b+=d
  return b
 def response(self,c,j,fragment=False):
  b=json.dumps(j).encode()
  def frame(data,opcode,final):
   n=len(data);h=bytes([(128 if final else 0)|opcode,n])if n<126 else bytes([(128 if final else 0)|opcode,126])+struct.pack('!H',n)
   c.sendall(h+data)
  if fragment:
   # Ping between fragments must not lose data or cause unsolicited approval reply.
   frame(b[:12],1,False);frame(b'keepalive',9,True);frame(b[12:],0,True)
  else:frame(b,1,True)
 def run(self):
  try:
   c,_=self.sock.accept();c.settimeout(3)
   with c:
    request=b''
    while not request.endswith(b'\r\n\r\n'):request+=self.read(c,1)
    key=next(l.split(b':',1)[1].strip()for l in request.split(b'\r\n')if l.lower().startswith(b'sec-websocket-key:'))
    accept=base64.b64encode(hashlib.sha1(key+b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
    if self.bad_accept:accept=b'invalid'
    c.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+b'\r\n\r\n')
    if self.bad_accept:return
    while True:
     a,b=self.read(c,2);n=b&127
     if n==126:n=struct.unpack('!H',self.read(c,2))[0]
     elif n==127:n=struct.unpack('!Q',self.read(c,8))[0]
     if not b&128:raise AssertionError('Client must mask frames')
     mask=self.read(c,4);raw=self.read(c,n);payload=bytes(v^mask[i%4]for i,v in enumerate(raw))
     if a&15==10:continue
     j=json.loads(payload)
     if 'method'not in j:raise AssertionError('Client must not answer approval requests')
     m=j['method'];self.calls.append(j)
     if m=='initialized':continue
     if m=='initialize':r={'userAgent':'controlled fixture'}
     elif m=='thread/loaded/list':r={'data':[ID]}
     elif m=='thread/read':
      self.response(c,{'id':999,'method':'item/commandExecution/requestApproval','params':{'threadId':ID}})
      r={'thread':{'id':ID,'sessionId':ID,'status':{'type':'active'if self.approval else'idle','activeFlags':['waitingOnApproval']if self.approval else[]},'canAcceptDirectInput':True}}
     elif m=='thread/queue/add':r={'queuedSubmission':{'id':'exact-fixture-submission'}}
     elif m=='thread/items/list':r={'data':[{'item':{'id':'reply','type':'agentMessage','phase':'final_answer','text':'Controlled selected reply'}}]}
     else:raise AssertionError(m)
     self.response(c,{'id':j['id'],'result':r},fragment=True)
  except EOFError:pass
  except Exception as e:self.error=e
  finally:self.sock.close();self.done=True
 def finish(self):
  self.thread.join(4)
  if self.thread.is_alive():raise AssertionError('Fixture server leaked')
  if self.error:raise self.error

class Protocol(unittest.TestCase):
 def test_real_framing_exact_queue_and_selected_reply(self):
  with tempfile.TemporaryDirectory()as home:
   server=Server(home)
   try:
    with s.CodexConnection(home)as c:
     self.assertEqual(s.latest_codex(c,ID)['text'],'Controlled selected reply')
     r=s.send_codex(c,ID,'Fixture-only user instruction',MESSAGE)
     self.assertEqual(r['queuedSubmissionId'],'exact-fixture-submission')
   finally:server.finish()
   submissions=[j for j in server.calls if j['method']=='thread/queue/add']
   self.assertEqual(len(submissions),1);self.assertEqual(submissions[0]['params']['threadId'],ID)
   self.assertEqual(submissions[0]['params']['clientUserMessageId'],MESSAGE)
   self.assertFalse(any('resume'in j['method']or 'start'in j['method']or 'settings'in j['method']for j in server.calls))
 def test_approval_request_never_answered_or_bypassed(self):
  with tempfile.TemporaryDirectory()as home:
   server=Server(home,approval=True)
   try:
    with s.CodexConnection(home)as c:
     with self.assertRaises(ValueError):s.send_codex(c,ID,'Fixture',MESSAGE)
   finally:server.finish()
   self.assertFalse(any(j['method']=='thread/queue/add'for j in server.calls))
 def test_invalid_handshake_is_not_an_auth_bypass(self):
  with tempfile.TemporaryDirectory()as home:
   server=Server(home,bad_accept=True)
   try:
    with self.assertRaises(RuntimeError):
     with s.CodexConnection(home):pass
   finally:server.finish()
   self.assertEqual(server.calls,[])
 def test_world_readable_socket_rejected_before_connect(self):
  with tempfile.TemporaryDirectory()as home:
   p=Path(home)/'app-server-control';p.mkdir();sock=socket.socket(socket.AF_UNIX);sock.bind(str(p/'app-server-control.sock'));os.chmod(p/'app-server-control.sock',0o666)
   try:
    with self.assertRaises(RuntimeError):
     with s.CodexConnection(home):pass
   finally:sock.close()
if __name__=='__main__':unittest.main()
