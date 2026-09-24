"""Local AT-88 harness. Corrupt final Director JSON after a real Nemotron call.
The injection is marked in raw output. Never mounted by production app.main.
"""
import json
from dotenv import load_dotenv
load_dotenv('backend/.env',override=False)
from app.main import app,provider_router
provider=provider_router.registry['nemotron_local']
original=provider.generate
async def corrupt(messages,output_contract=None,tools=None,budget=None):
    response=await original(messages,output_contract,tools,budget)
    if (output_contract or {}).get('purpose')=='director_plan':
        response.content=json.dumps({'injected_corruption':True,'outcome':{'title':'受控故障','text':'本次为格式故障注入，不产生世界变化。'},'directive':{'target_changes':42}},ensure_ascii=False)
    return response
provider.generate=corrupt
