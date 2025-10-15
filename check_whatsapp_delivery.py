import finivo_whatsapp_integration as f
import requests

TO = '91899554776'
TEXT = 'Delivery status check: Finivo AI'

print('Sending message...')
resp = f._send_message_raw(TO, TEXT)
print('POST ->', resp.status_code)
print(resp.text)

mid = None
try:
    data = resp.json()
    if isinstance(data, dict) and data.get('messages'):
        mid = data['messages'][0].get('id')
except Exception:
    pass

if not mid:
    print('No message id found; cannot query status.')
else:
    print('Message ID:', mid)
    token = f.META_ACCESS_TOKEN
    if not token:
        print('META_ACCESS_TOKEN not available for status check')
    else:
        status_r = requests.get(f'https://graph.facebook.com/v21.0/{mid}', headers={'Authorization':f'Bearer {token}'}, params={'fields':'status,recipient_type'})
        print('STATUS ->', status_r.status_code)
        print(status_r.text)
