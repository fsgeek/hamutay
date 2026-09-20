import time, json
from typesafe_sdk import TypeSafeClient, Noul, Choice, Score
c = TypeSafeClient(timeout=60)
t=time.time()
try:
    print("models:", [m.name for m in c.models.list().models])
except Exception as e: print("models err", type(e).__name__, str(e)[:300])
print("models latency", round(time.time()-t,2))
state={"resident":"a long-lived AI resident that curates its own persistent state object between wakes","cycle":100,"entry_key":"persistent_notes","entry_value":json.dumps({"note":"the user prefers direct answers"}),"state_keys_at_this_cycle":[["cycle",3],["persistent_notes",40]],"recent_reply":"Understood."}
q={"keep_1":Noul(instructions="Will this entry still be present in the resident's state one wake from now?"),
   "keep_10":Noul(instructions="Will this entry still be present in the resident's state ten wakes from now?"),
   "centrality":Score(instructions="How central is this entry to what the resident is doing right now?",criteria=["peripheral","background","active","central"])}
for i in range(3):
    t=time.time(); r=c.system_one(state=state, questions=q); dt=time.time()-t
    print("latency",round(dt,3),"model",r.model,"usage",r.usage.model_dump(),"req",getattr(r,'request_id',None))
    print(json.dumps({k:v.model_dump() for k,v in r.answers.items()}))
    print("raw keys:", list(json.loads(r.raw_http_response.content).keys()) if hasattr(r,'raw_http_response') else 'n/a')
