#!/usr/bin/env python3
"""Louisa Weather Center: server-side 5-minute NWS monitoring, no third-party dependencies."""
import json, os, time, threading, logging, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

BASE=Path(__file__).resolve().parent
LAT,LON=38.1094,-82.6034
INTERVAL=max(60,int(os.getenv('POLL_SECONDS','300')))
PORT=int(os.getenv('PORT','8000'))
STATE_PATH=Path(os.getenv('STATE_PATH',str(BASE/'weather-state.json')))
WEBHOOK=os.getenv('ALERT_WEBHOOK_URL','')
USER_AGENT=os.getenv('NWS_USER_AGENT','LouisaWeatherCenter/4.1 (https://github.com/Jdiamond0005/Louisa-Weather-Center)')
lock=threading.Lock()
state={'checked_at':None,'last_success_at':None,'forecast':[],'hourly':[],'alerts':[], 'errors':[], 'changes':[]}
if STATE_PATH.exists():
    try: state.update(json.loads(STATE_PATH.read_text()))
    except (ValueError,OSError): pass

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/geo+json, application/json','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=18) as resp: return json.load(resp)

def alert_summary(f):
    p=f.get('properties',{})
    return {k:p.get(k) for k in ('id','event','headline','severity','urgency','certainty','effective','expires','description','instruction','areaDesc')}

def notify(change):
    if not WEBHOOK:return
    payload=json.dumps({'text':'Louisa Weather Center: '+change['message'],'event':change}).encode()
    try:
        req=urllib.request.Request(WEBHOOK,data=payload,headers={'Content-Type':'application/json'},method='POST')
        urllib.request.urlopen(req,timeout=10).close()
    except Exception as exc: logging.warning('Webhook delivery failed: %s',exc)

def poll():
    global state
    now=datetime.now(timezone.utc).isoformat()
    with lock: previous=dict(state)
    errors=[]; updated={}; changes=[]
    try:
        point=fetch(f'https://api.weather.gov/points/{LAT},{LON}')['properties']
        urls={'forecast':point['forecast'],'hourly':point['forecastHourly'],'alerts':f'https://api.weather.gov/alerts/active?point={LAT},{LON}'}
    except Exception as exc:
        urls={'alerts':f'https://api.weather.gov/alerts/active?point={LAT},{LON}'}
        errors.append('NWS grid discovery: '+str(exc))
    for key,url in urls.items():
        try:
            doc=fetch(url)
            updated[key]=[alert_summary(x) for x in doc.get('features',[])] if key=='alerts' else doc['properties'].get('periods',[])
        except Exception as exc:errors.append(key+': '+str(exc))
    if 'alerts' in updated:
        old={a.get('id') for a in previous.get('alerts',[])}
        for a in updated['alerts']:
            if a.get('id') not in old:
                changes.append({'at':now,'kind':'new_alert','message':f"NEW {a.get('event','weather alert')}: {a.get('headline') or a.get('areaDesc') or 'Louisa area'}"})
    if 'hourly' in updated and previous.get('hourly'):
        a=updated['hourly'][0]; b=previous['hourly'][0]
        if a.get('startTime')==b.get('startTime') and abs((a.get('temperature') or 0)-(b.get('temperature') or 0))>=8:
            changes.append({'at':now,'kind':'forecast_shift','message':'Hourly forecast temperature changed at least 8°F for the same forecast hour.'})
    next_state={**previous,**updated,'checked_at':now,'errors':errors,'changes':(changes+previous.get('changes',[]))[:30]}
    if updated:next_state['last_success_at']=now
    with lock:
        state=next_state
        temp=STATE_PATH.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2));temp.replace(STATE_PATH)
    for change in changes:notify(change)
    logging.info('Poll complete: %s; errors=%s',list(updated),errors)

def loop():
    while True:
        try:poll()
        except Exception:logging.exception('Unexpected polling error')
        time.sleep(INTERVAL)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(BASE),**kwargs)
    def do_GET(self):
        if self.path.split('?')[0]=='/health':
            data=b'{"status":"ok"}'
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        if self.path.split('?')[0]=='/api/status':
            with lock: data=json.dumps(state).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        super().do_GET()

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    threading.Thread(target=loop,daemon=True).start()
    print(f'Louisa Weather Center running on http://localhost:{PORT}; poll interval {INTERVAL}s')
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
