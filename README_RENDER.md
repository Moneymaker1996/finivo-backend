Render deployment steps for Finivo AI

1. Connect repo
- On render.com, create a new Web Service.
- Choose the GitHub repo `Moneymaker1996/finivo-backend` and branch `main`.

2. Build & Start
- Build command: pip install -r requirements.txt
- Start command: gunicorn -k uvicorn.workers.UvicornWorker main:app

3. Environment variables (set in Render Dashboard)
- META_ACCESS_TOKEN: <your meta access token>
- META_VERIFY_TOKEN: finivo_verify_token (or your verify token)
- PHONE_NUMBER_ID: 848842828304712
- META_WABA_ID: <your waba id>

4. After deployment
- Verify webhook: in Meta Developer Console, set the webhook URL to https://<your-service>.onrender.com/webhook/whatsapp and verify using your verify token.
- Test sending: POST to https://<your-service>.onrender.com/send_whatsapp_message with body {"to":"<recipient>","message":"Hi"} to send a message through the WABA.

Notes:
- Make sure you never commit .env files or large model binaries. .gitignore already contains patterns to prevent this.
- Rotate any keys that were previously leaked.
