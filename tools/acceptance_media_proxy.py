"""Local-only fault harness: forward genuine app/media bytes, delay or fail MP4 transport.
Run with backend/.venv/bin/python -m uvicorn tools.acceptance_media_proxy:app --port 9004.
This is not mounted by the product server and never substitutes model output.
"""
import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
app=FastAPI()
mode='pass'
@app.post('/acceptance/mode')
async def set_mode(data:dict):
    global mode
    if data.get('mode') not in ('pass','delay','fail'):return {'ok':False}
    mode=data['mode'];return {'ok':True,'mode':mode}
@app.api_route('/{path:path}',methods=['GET','POST','PUT','PATCH','DELETE'])
async def proxy(path:str,request:Request):
    if path.startswith('media/'):
        if mode=='delay':await asyncio.sleep(8)
        if mode=='fail':return Response('injected media transport failure',status_code=503,headers={'Cache-Control':'no-store'})
    headers={k:v for k,v in request.headers.items() if k.lower() not in ('host','connection','content-length')}
    async with httpx.AsyncClient(timeout=180) as c:
        r=await c.request(request.method,'http://127.0.0.1:9002/'+path,params=request.query_params,headers=headers,content=await request.body())
    selected={k:v for k,v in r.headers.items() if k.lower() in ('content-type','content-range','accept-ranges')}
    selected['Cache-Control']='no-store'
    return Response(r.content,status_code=r.status_code,headers=selected)
