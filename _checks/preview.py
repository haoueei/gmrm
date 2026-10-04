"""Local static preview with video Range support: python3 _checks/preview.py [build-root]."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import os,re,sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gmrm-site-preview"
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=ROOT,**kw)
 def send_head(self):
  path=self.translate_path(self.path)
  if not os.path.isfile(path):return super().send_head()
  size=os.path.getsize(path);start,end=0,size-1
  match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
  if match:
   start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
   if start>=size:self.send_error(416);return
  self.send_response(206 if match else 200)
  self.send_header('Content-Type',self.guess_type(path));self.send_header('Accept-Ranges','bytes')
  self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(end-start+1))
  if match:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  self.end_headers();f=open(path,'rb');f.seek(start);self.remaining=end-start+1;return f
 def copyfile(self,source,outputfile):
  if not hasattr(self,'remaining'):return super().copyfile(source,outputfile)
  try:
   while self.remaining:
    data=source.read(min(self.remaining,65536))
    if not data:break
    outputfile.write(data);self.remaining-=len(data)
  except (BrokenPipeError,ConnectionResetError):pass
ThreadingHTTPServer(('127.0.0.1',4002),Handler).serve_forever()
