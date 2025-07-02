import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from dotenv import load_dotenv
from plaid import Configuration, ApiClient, Environment
from plaid.model.transactions_get_request import TransactionsGetRequest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
import model as models

load_dotenv()

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox").lower()

router = APIRouter(tags=["Plaid"])

# In-memory store for access tokens (for demo only)
plaid_tokens = {}

# Plaid client setup
if PLAID_ENV == "sandbox":
    plaid_host = Environment.Sandbox
elif PLAID_ENV == "development":
    plaid_host = Environment.Development
elif PLAID_ENV == "production":
    plaid_host = Environment.Production
else:
    raise ValueError("Invalid PLAID_ENV value")

configuration = Configuration(
    host=plaid_host,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET
    }
)
api_client = ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

class PublicTokenRequest(BaseModel):
    public_token: str
    user_id: int

@router.post("/link-token/create")
def create_link_token(request: Request):
    try:
        user_id = 1  # For demo, static user_id
        link_token_request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
            client_name="FinivoAI Sandbox",
            products=[Products("transactions")],
            country_codes=[CountryCode('US')],
            language="en"
        )
        response = client.link_token_create(link_token_request)
        return {"link_token": response['link_token']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exchange-public-token")
def exchange_public_token(body: PublicTokenRequest):
    try:
        print(f"[DEBUG] Received public_token: {body.public_token} for user_id: {body.user_id}")
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=body.public_token
        )
        exchange_response = client.item_public_token_exchange(exchange_request)
        print(f"[DEBUG] Full exchange_response: {exchange_response}")
        access_token = exchange_response.get('access_token') if isinstance(exchange_response, dict) else getattr(exchange_response, 'access_token', None)
        print(f"[DEBUG] Received access_token: {access_token}")
        # Store access_token in global plaid_tokens dict with fixed user_id=1
        plaid_tokens[1] = access_token
        print(f"[DEBUG] plaid_tokens after storing: {plaid_tokens}")
        if not access_token:
            raise HTTPException(status_code=500, detail="No access token returned from Plaid.")
        return {"access_token": access_token}
    except Exception as e:
        print(f"[ERROR] Exception in exchange_public_token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accounts")
def get_accounts(user_id: int = 1):
    # Use plaid_tokens[1] if available, else fallback to PLAID_ACCESS_TOKEN from .env
    access_token = plaid_tokens.get(1) or os.getenv("PLAID_ACCESS_TOKEN")
    print(f"[DEBUG] plaid_tokens[1]: {plaid_tokens.get(1)}")
    print(f"[DEBUG] PLAID_ACCESS_TOKEN from env: {os.getenv('PLAID_ACCESS_TOKEN')}")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token for user.")
    try:
        request = AccountsGetRequest(access_token=access_token)
        response = client.accounts_get(request)
        return response.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions")
def get_transactions():
    print("[DEBUG] /transactions endpoint called", flush=True)
    access_token = plaid_tokens.get(1) or os.getenv("PLAID_ACCESS_TOKEN")
    print(f"[DEBUG] plaid_tokens[1]: {plaid_tokens.get(1)}", flush=True)
    print(f"[DEBUG] PLAID_ACCESS_TOKEN from env: {os.getenv('PLAID_ACCESS_TOKEN')}", flush=True)
    if not access_token:
        print("[ERROR] No access token for user.", flush=True)
        raise HTTPException(status_code=400, detail="No access token for user.")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        print(f"[DEBUG] start_date: {start_date}, end_date: {end_date}", flush=True)
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,  # Pass as date object
            end_date=end_date       # Pass as date object
        )
        response = client.transactions_get(request)
        print(f"[DEBUG] Plaid response: {response}", flush=True)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        return {"transactions": response_dict.get('transactions', [])}
    except Exception as e:
        print(f"[ERROR] Exception in get_transactions: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-transactions")
def import_transactions():
    access_token = plaid_tokens.get(1) or os.getenv("PLAID_ACCESS_TOKEN")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token for user.")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date
        )
        response = client.transactions_get(request)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        transactions = response_dict.get('transactions', [])
        db: Session = SessionLocal()
        imported = 0
        for txn in transactions:
            item_name = txn.get("name")
            amount = txn.get("amount")
            # Optional: Use Plaid's transaction_id to avoid duplicates
            txn_id = txn.get("transaction_id")
            # Check for duplicate by transaction_id in comment field (since model has no transaction_id field)
            exists = db.query(models.SpendingLog).filter_by(comment=txn_id).first()
            if exists:
                continue
            log = models.SpendingLog(
                user_id=1,
                item_name=item_name,
                amount=amount,
                decision="unreviewed",
                comment=txn_id
            )
            db.add(log)
            imported += 1
        db.commit()
        db.close()
        return {"imported": imported, "message": f"Imported {imported} transactions."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
