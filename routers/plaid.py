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
from utils.plaid_client import get_plaid_client
from plaid.model.transactions_get_request import TransactionsGetRequest
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel
from utils.impulse_engine import scan_impulse_triggers
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from utils.plaid_security import encrypt_token, get_fernet_and_version

load_dotenv()

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox").lower()

router = APIRouter(tags=["Plaid"])

# In-memory store for access tokens (for demo only)
plaid_tokens = {}

# Use the helper so tests can toggle a MockPlaidClient with MOCK_PLAID=1
client = get_plaid_client()

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
        # Persist encrypted token to DB if ORM exists
        try:
            fernet, key_version = get_fernet_and_version()
            encrypted = fernet.encrypt(access_token.encode()).decode()
        except Exception:
            encrypted = None
            key_version = None

        try:
            db: Session = SessionLocal()
            # Ensure the user_plaid_tokens table exists on this DB bind
            try:
                models.UserPlaidToken.__table__.create(bind=db.get_bind(), checkfirst=True)
            except Exception:
                pass
            if encrypted and hasattr(models, "UserPlaidToken"):
                token_row = models.UserPlaidToken(user_id=body.user_id, access_token=encrypted, item_id=getattr(exchange_response, 'item_id', None) or (exchange_response.get('item_id') if isinstance(exchange_response, dict) else None), key_version=key_version)
                db.add(token_row)
                db.commit()
        except Exception:
            # If DB persist fails, continue but log
            pass
        finally:
            try:
                db.close()
            except Exception:
                pass

        return {"status": "success", "access_token": access_token}
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

class TransactionsPayload(BaseModel):
    transactions: Optional[List[Dict]] = None
    user_id: Optional[int] = 1


def _ensure_db():
    # Local helper to create a DB session (tests monkeypatch SessionLocal)
    return SessionLocal()


@router.post("/import-transactions")
@router.post("/transactions/import")
def import_transactions(payload: TransactionsPayload = None):
    try:
        # Determine transactions either from payload (test mode) or from Plaid
        if payload and payload.transactions:
            transactions = payload.transactions
            user_id = payload.user_id or 1
        else:
            access_token = plaid_tokens.get(1) or os.getenv("PLAID_ACCESS_TOKEN")
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token for user.")
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
            user_id = 1

        db: Session = _ensure_db()
        # Ensure relevant tables exist on the session's bind (tests may patch engines)
        try:
            models.SpendingLog.__table__.create(bind=db.get_bind(), checkfirst=True)
        except Exception:
            pass
        imported = 0
        impulsive_count = 0
        for txn in transactions:
            # normalize fields from Plaid-like txn dict
            item_name = txn.get("name") or txn.get("merchant_name")
            amount = txn.get("amount")
            txn_id = txn.get("transaction_id") or txn.get("id") or f"txn-{imported}"

            # Avoid duplicates
            try:
                exists = db.query(models.SpendingLog).filter_by(comment=txn_id).first()
            except Exception:
                # If the spending_logs table is missing in this DB session, skip duplicate check
                exists = None
            if exists:
                continue

            # Detect impulsivity using the impulse engine
            try:
                scan_input = {
                    "item_name": item_name or "",
                    "mood": None,
                    "pattern": None,
                    "urgency": None,
                    "last_purchase_days": None,
                    "situation": None,
                    "explanation": txn.get("name", "")
                }
                impulse_result = scan_impulse_triggers(scan_input)
                is_impulsive = impulse_result.get("is_impulsive", False)
            except Exception:
                is_impulsive = False

            # Heuristic boosts: very large amounts or explicit luxury categories/merchants
            try:
                if amount and float(amount) > 1000:
                    is_impulsive = True
            except Exception:
                pass
            try:
                cats = txn.get("category") or []
                if any("luxury" in str(c).lower() for c in cats):
                    is_impulsive = True
            except Exception:
                pass
            try:
                merchant = (txn.get("merchant_name") or "").lower()
                if "rolex" in merchant or "gucci" in merchant or "louis" in merchant:
                    is_impulsive = True
            except Exception:
                pass

            # Create spending log
            log = models.SpendingLog(
                user_id=user_id,
                item_name=item_name,
                amount=amount,
                decision="unreviewed",
                comment=txn_id,
            )
            db.add(log)
            imported += 1

            # If impulsive, create a NudgeLog entry
            if is_impulsive:
                try:
                    n = models.NudgeLog(user_id=user_id, spending_intent=str(txn.get("name", "")), nudge_message="impulse_detected", plan=None, source="plaid_auto")
                    db.add(n)
                    impulsive_count += 1
                except Exception:
                    pass

        db.commit()
        db.close()
        return {"imported": imported, "impulsive_transactions": impulsive_count, "message": f"Imported {imported} transactions."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# (Both endpoints /import-transactions and /transactions/import are routed to import_transactions)
