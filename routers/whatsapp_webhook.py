from fastapi import APIRouter, Request, HTTPException
import os
import logging


def _load_dotenv(path='.env'):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except FileNotFoundError:
        pass


# Load .env if present so META_VERIFY_TOKEN can be set
_load_dotenv()

router = APIRouter()

# Load verify token from environment
META_VERIFY_TOKEN = os.getenv('META_VERIFY_TOKEN')

logger = logging.getLogger('whatsapp_webhook')

@router.get('/whatsapp')
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get('hub.mode')
    token = params.get('hub.verify_token')
    challenge = params.get('hub.challenge')

    if mode == 'subscribe' and token and challenge and token == META_VERIFY_TOKEN:
        logger.info('[WhatsApp Webhook] Verification successful')
        return int(challenge) if challenge.isdigit() else challenge
    else:
        logger.warning('[WhatsApp Webhook] Verification failed')
        raise HTTPException(status_code=403, detail={'status': 'forbidden'})


@router.post('/whatsapp')
async def receive_webhook(request: Request):
    payload = await request.json()
    # Basic logging of the incoming webhook for debugging
    logger.info('[WhatsApp Webhook] Received payload: %s', payload)

    # Parse status updates if present
    try:
        entry = payload.get('entry', [])[0]
        changes = entry.get('changes', [])
        for change in changes:
            value = change.get('value', {})
            statuses = value.get('statuses') or []
            for s in statuses:
                message_id = s.get('id')
                status = s.get('status')
                timestamp = s.get('timestamp')
                recipient = s.get('recipient_id') or s.get('to') or s.get('recipient_phone_number')
                logger.info('[WhatsApp Webhook] Status update: %s for %s', status, message_id)
    except Exception as e:
        logger.exception('Error parsing webhook payload: %s', e)

    return {'status': 'received'}
