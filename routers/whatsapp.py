from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import finivo_whatsapp_integration as f

router = APIRouter()

class WhatsAppMessage(BaseModel):
    to: str
    message: str

@router.post('/send_whatsapp_message')
async def send_whatsapp(msg: WhatsAppMessage):
    if not f.META_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail='META_ACCESS_TOKEN not configured')
    try:
        # Use the integration to send the message and return the raw response
        resp = f._send_message_raw(msg.to, msg.message)
        return {"status_code": resp.status_code, "body": resp.json() if resp.headers.get('content-type','').startswith('application/json') else resp.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
