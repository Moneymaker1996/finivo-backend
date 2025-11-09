import os
from fastapi import APIRouter, HTTPException, Request, Depends, Body
from loguru import logger
import logging
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
from sqlalchemy.orm import Session, sessionmaker
import database as database
import models
from models import ImpulseAlert
from utils.impulse_detector import evaluate_impulse

# helper to inject a Plaid client in tests or DI-enabled runtime
from utils.plaid_client import get_plaid_client

# Security helpers for encrypting/decrypting Plaid access tokens
from utils.plaid_security import encrypt_token, decrypt_token, get_fernet_and_version

# New imports for adapted Plaid import flow
from utils.transaction_adapter import normalize_plaid_transaction
from utils.impulse import is_impulsive_purchase
from utils.db_types import assign_response_script
import json
from utils.earn_engine import generate_earn_script


load_dotenv()

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox").lower()

router = APIRouter(tags=["Plaid"])


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# In-memory store left for very short-lived fallbacks (rarely used)
plaid_tokens = {}

# Plaid client setup (use utils.get_plaid_client which may return a mock)
try:
    client = get_plaid_client()
except Exception:
    # If building a real client fails at import time (e.g., missing SDK in test env),
    # set client to None; endpoints will raise appropriate errors when invoked.
    client = None

class PublicTokenRequest(BaseModel):
    public_token: str
    user_id: int


def _redact_token(t: str) -> str:
    """Redact token strings leaving first 6 and last 4 chars visible.

    If token is shorter than 12 chars, redact entirely.
    """
    if not t:
        return ""
    if len(t) < 12:
        return "*" * len(t)
    return t[:6] + ("*" * (len(t) - 10)) + t[-4:]

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
async def exchange_public_token(request: Request):
    """Exchange a public_token for an access_token.

    This handler reads the raw request body (for DEBUG logging), then parses
    into the PublicTokenRequest pydantic model. DEBUG logging is gated by
    the DEBUG env var and always redacts tokens when printing.
    """
    # Read raw body bytes first so we can log/redact before parsing.
    body_bytes = await request.body()

        if os.getenv("DEBUG") == "1":
        try:
            preview = body_bytes.decode('utf-8', errors='replace')[:120]
        except Exception:
            preview = '<non-decodable-bytes>'
        # Attempt to extract public_token for redaction in a safe way
        try:
            j = json.loads(body_bytes)
            pt = j.get('public_token') if isinstance(j, dict) else None
            redacted = _redact_token(pt) if pt else None
            # Build preview with redaction if possible
            if redacted:
                # replace the token in preview with redacted form if present
                preview = preview.replace(pt, redacted)
        except Exception:
            redacted = None

        try:
            logger.info(f"[DEBUG] exchange-public-token raw body length={len(body_bytes)} preview='{preview}'")
        except Exception:
            pass

    # Parse into pydantic model (perform validation here)
    try:
        body = PublicTokenRequest.parse_raw(body_bytes)
    except Exception as e:
        logging.getLogger(__name__).warning("Invalid request payload for exchange-public-token", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid request payload")

    try:
        # Received exchange request — perform Plaid exchange and handle errors
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=body.public_token
        )
        try:
            exchange_response = client.item_public_token_exchange(exchange_request)
        except Exception as exc:
            # Log Plaid error info (no tokens)
            try:
                logger.warning(f"Plaid exchange exception: {repr(exc)}")
            except Exception:
                pass
            raise HTTPException(status_code=502, detail="Plaid exchange failed")

        # In DEBUG/test mode, log non-secret Plaid response details for diagnostics
        if os.getenv("DEBUG") == "1":
            try:
                if isinstance(exchange_response, dict):
                    keys = list(exchange_response.keys())
                    try:
                        logger.info(f"[DEBUG] Plaid response keys: {keys}")
                        if exchange_response.get("error_code"):
                            logger.warning(f"[DEBUG] Plaid error_code: {exchange_response.get('error_code')} message: {exchange_response.get('error_message')}")
                    except Exception:
                        pass
                else:
                    # SDK object — try to introspect attributes without printing tokens
                    attrs = [a for a in dir(exchange_response) if not a.startswith('_')][:10]
                    try:
                        logger.info(f"[DEBUG] Plaid SDK response attrs sample: {attrs}")
                    except Exception:
                        pass
            except Exception:
                pass

        # Extract tokens safely (do not log access_token)
        access_token = exchange_response.get('access_token') if isinstance(exchange_response, dict) else getattr(exchange_response, 'access_token', None)
        item_id = exchange_response.get('item_id') if isinstance(exchange_response, dict) else getattr(exchange_response, 'item_id', None)

        if not access_token:
            raise HTTPException(status_code=500, detail="No access token returned from Plaid.")

        # Encrypt before persisting using Secret Manager-aware helper
        try:
            fernet, key_version = get_fernet_and_version()
            encrypted = fernet.encrypt(access_token.encode()).decode()
        except Exception:
            # Do not reveal secrets in errors
            raise HTTPException(status_code=500, detail="Failed to encrypt access token")

        # Persist token into DB (upsert per user)
        # Use the application's Session factory dynamically so tests can
        # monkeypatch `database.SessionLocal` before importing the app.
        # Ensure the user_plaid_tokens table exists on the runtime engine. In
        # some test setups the table may not have been created on the same
        # engine used by the app thread; `checkfirst=True` makes this safe in
        # production as well (no-op if table already exists).
        db: Session = database.SessionLocal()
        try:
            try:
                # Create the table on the same bind used by this session so
                # the DDL is visible to the session's connection immediately.
                bind = db.get_bind()
                models.UserPlaidToken.__table__.create(bind=bind, checkfirst=True)
            except Exception:
                # If creation fails, continue and let the subsequent DB ops
                # surface a clear error which will be logged.
                pass

            existing = db.query(models.UserPlaidToken).filter_by(user_id=body.user_id).first()
            if existing:
                existing.access_token = encrypted
                existing.item_id = item_id
                existing.key_version = key_version
                existing.created_at = datetime.utcnow()
            else:
                new_token = models.UserPlaidToken(user_id=body.user_id, access_token=encrypted, item_id=item_id, key_version=key_version)
                db.add(new_token)
            db.commit()
            except Exception as e:
            db.rollback()
            try:
                logger.warning(f"DB persist error (no secrets): {e}")
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="Failed to persist token to DB")
        finally:
            db.close()

        try:
            logger.info(f"[Plaid] Stored token for User={body.user_id}")
        except Exception:
            pass

        return {"status": "success", "message": "Token stored successfully", "user_id": body.user_id}
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).error(f"Unexpected error in exchange_public_token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/accounts")
def get_accounts(user_id: int = 1):
    # Prefer DB-stored token (decrypt before use); fallback to PLAID_ACCESS_TOKEN env var
    access_token = None
    db: Session = database.SessionLocal()
    try:
        row = db.query(models.UserPlaidToken).filter_by(user_id=user_id).order_by(models.UserPlaidToken.created_at.desc()).first()
        if row and row.access_token:
            try:
                access_token = decrypt_token(row.access_token)
            except Exception:
                access_token = None
    finally:
        db.close()

    if not access_token:
        access_token = os.getenv("PLAID_ACCESS_TOKEN")

    if not access_token:
        raise HTTPException(status_code=400, detail="No access token for user.")

    try:
        request = AccountsGetRequest(access_token=access_token)
        response = client.accounts_get(request)
        return response.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions")
def get_transactions(user_id: int = 1):
    # Similar to get_accounts: decrypt DB token if present
    access_token = None
    db: Session = database.SessionLocal()
    try:
        row = db.query(models.UserPlaidToken).filter_by(user_id=user_id).order_by(models.UserPlaidToken.created_at.desc()).first()
        if row and row.access_token:
            try:
                access_token = decrypt_token(row.access_token)
            except Exception:
                access_token = None
    finally:
        db.close()

    if not access_token:
        access_token = os.getenv("PLAID_ACCESS_TOKEN")

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
        return {"transactions": response_dict.get('transactions', [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-transactions")
def import_transactions(user_id: int = 1):
    # Decrypt DB token if present
    access_token = None
    db: Session = database.SessionLocal()
    try:
        row = db.query(models.UserPlaidToken).filter_by(user_id=user_id).order_by(models.UserPlaidToken.created_at.desc()).first()
        if row and row.access_token:
            try:
                access_token = decrypt_token(row.access_token)
            except Exception:
                access_token = None
    finally:
        db.close()

    if not access_token:
        access_token = os.getenv("PLAID_ACCESS_TOKEN")

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
        db: Session = database.SessionLocal()
        imported = 0
        for txn in transactions:
            # Normalize Plaid txn into our expected payload
            data = normalize_plaid_transaction(txn)

            # Use Plaid transaction_id to avoid duplicates
            txn_id = txn.get("transaction_id")
            exists = db.query(models.SpendingLog).filter_by(comment=txn_id).first()
            if exists:
                continue

            # Run impulsive detection
            try:
                impulsive = is_impulsive_purchase(
                    user_id=user_id,
                    item_type=data.get("item_type"),
                    mood=data.get("mood"),
                    pattern=data.get("pattern"),
                    urgency=data.get("urgency"),
                    last_purchase=data.get("last_purchase"),
                    situation=data.get("situation"),
                    explanation=data.get("explanation"),
                )
            except Exception:
                impulsive = False

            if impulsive:
                spending = models.SpendingLog(
                    user_id=user_id,
                    item_name=txn.get("name"),
                    amount=data.get("amount"),
                    decision="impulsive",
                    category=data.get("item_type"),
                    comment=txn_id,
                )
                db.add(spending)
                db.flush()

                # create a minimal nudge log (map to model fields) and attach internal E.A.R.N. script
                user_row = db.query(models.User).filter(models.User.id == user_id).first()
                plan = user_row.plan if user_row and hasattr(user_row, "plan") else "free"
                user_name = user_row.name if user_row and hasattr(user_row, "name") else getattr(user_row, "email", "user")
                purchase_name = txn.get("name") or data.get("explanation", "this item")
                earn_script = generate_earn_script(user_name=user_name, purchase=purchase_name, plan=plan)

                nudge = models.NudgeLog(
                    user_id=user_id,
                    spending_intent=txn.get("name") or data.get("explanation", ""),
                    nudge_message=f"Impulse detected: {data.get('item_type')} - {data.get('explanation')}",
                    plan=plan,
                    source="plaid_auto",
                )
                # Dialect-aware assignment
                assign_response_script(db, nudge, earn_script)
                db.add(nudge)
            else:
                log = models.SpendingLog(
                    user_id=user_id,
                    item_name=txn.get("name"),
                    amount=data.get("amount"),
                    decision="normal",
                    category=data.get("item_type"),
                    comment=txn_id,
                )
                db.add(log)

            imported += 1

        db.commit()
        db.close()
        try:
            logger.info(f"[Plaid] Imported={imported} for User={user_id}")
        except Exception:
            pass
        return {"imported": imported, "message": f"Imported {imported} transactions."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions/import")
def import_transactions(user_id: int = Body(...), transactions: list = Body(...),
                        db: Session = Depends(get_db),
                        plaid_client = Depends(get_plaid_client)):
    """Import transactions sent in the request payload and run I.M.P.U.L.S.E. checks.

    Expected input: user_id (int) and transactions (list of txn dicts).
    DB session and Plaid client are injected via dependencies.
    """
    impulsive_logs = []

    try:
        for txn in transactions:
            # normalize fields expected by SpendingLog in model.py
            # SpendingLog fields: amount, category, description, timestamp, regret
            log_data = {
                "description": txn.get("item_name") or txn.get("name"),
                "amount": txn.get("amount"),
                # category may be a list from Plaid; prefer first element or the value
                "category": (txn.get("category") or [None])[0] if isinstance(txn.get("category"), list) else txn.get("category"),
                "timestamp": None,
            }
            # normalize timestamp to a Python datetime/date object for SQLAlchemy/SQLite
            ts = txn.get("timestamp") or txn.get("date")
            if isinstance(ts, str):
                try:
                    ts_parsed = datetime.fromisoformat(ts)
                except Exception:
                    try:
                        ts_parsed = datetime.strptime(ts, "%Y-%m-%d")
                    except Exception:
                        ts_parsed = None
                log_data["timestamp"] = ts_parsed
            else:
                log_data["timestamp"] = ts

            # Build kwargs dynamically so we only set columns that exist in the
            # current DB schema. This avoids sqlite "no such column" errors
            # when tests or older schemas omit fields such as 'description'.
            tbl_cols = {c.name for c in models.SpendingLog.__table__.columns}
            txn_kwargs = {"user_id": user_id}
            # Always set amount and category when present on model
            if "amount" in tbl_cols:
                txn_kwargs["amount"] = log_data.get("amount")
            if "category" in tbl_cols:
                txn_kwargs["category"] = log_data.get("category")
            # Prefer description if available, otherwise try item_name
            if "description" in tbl_cols:
                txn_kwargs["description"] = log_data.get("description")
            elif "item_name" in tbl_cols:
                txn_kwargs["item_name"] = log_data.get("description")
            if "timestamp" in tbl_cols and log_data.get("timestamp") is not None:
                txn_kwargs["timestamp"] = log_data.get("timestamp")

            new_txn = models.SpendingLog(**txn_kwargs)
            db.add(new_txn)
            db.commit()
            db.refresh(new_txn)

            # Run I.M.P.U.L.S.E. check — build a normalized dict expected by the detector
            tx_for_eval = {
                "item_name": txn.get("item_name") or txn.get("name"),
                "amount": txn.get("amount"),
                "timestamp": log_data.get("timestamp"),
                "merchant_name": txn.get("merchant_name"),
                "category": (txn.get("category") or [None])[0] if isinstance(txn.get("category"), list) else txn.get("category"),
            }
            result = evaluate_impulse(tx_for_eval, user_id)

            if result.get("is_impulsive"):
                alert = ImpulseAlert(
                    user_id=user_id,
                    transaction_id=new_txn.id,
                    score=result.get("score"),
                    triggers=result.get("triggers"),
                    reasoning=result.get("reasoning"),
                )
                db.add(alert)
                # Also create an internal NudgeLog with the E.A.R.N. script for later delivery (internal only)
                user_row = db.query(models.User).filter(models.User.id == user_id).first()
                plan = user_row.plan if user_row and hasattr(user_row, "plan") else "free"
                user_name = user_row.name if user_row and hasattr(user_row, "name") else getattr(user_row, "email", "user")
                purchase_name = tx_for_eval.get("item_name") or "this item"
                earn_script = generate_earn_script(user_name=user_name, purchase=purchase_name, plan=plan)
                try:
                    logger.info(f"[EARN] Generated persuasion script for User={user_id}")
                except Exception:
                    pass
                nudge = models.NudgeLog(
                    user_id=user_id,
                    spending_intent=purchase_name,
                    nudge_message=f"Impulsive transaction detected via Plaid import: {purchase_name}",
                    plan=plan,
                    source="plaid_auto",
                )
                assign_response_script(db, nudge, earn_script)
                db.add(nudge)
                impulsive_logs.append(result)

        db.commit()
        return {
            "status": "success",
            "total_transactions": len(transactions),
            "impulsive_transactions": len(impulsive_logs),
            "insights": impulsive_logs,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
