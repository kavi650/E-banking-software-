from datetime import date, datetime
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


# ---------------- Configuration ----------------
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "ebank")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "ebankpass")
MYSQL_DB = os.getenv("MYSQL_DB", "ebank")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- Models ----------------
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=False, unique=True, index=True)
    address = Column(String(255), nullable=False)
    dob = Column(Date, nullable=False)
    aadhar = Column(String(20), nullable=False)
    account_number = Column(String(20), nullable=False, unique=True, index=True)
    pin = Column(String(10), nullable=False)
    balance = Column(Numeric(14, 2), nullable=False, default=0)
    wallet_balance = Column(Numeric(14, 2), nullable=False, default=0)

    outgoing_transactions = relationship(
        "Transaction",
        back_populates="from_account",
        foreign_keys="Transaction.from_account_id",
    )
    incoming_transactions = relationship(
        "Transaction",
        back_populates="to_account",
        foreign_keys="Transaction.to_account_id",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    type = Column(String(50), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    merchant = Column(String(100), nullable=True)

    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])


# ---------------- Schemas ----------------
class AccountCreate(BaseModel):
    name: str
    mobile: str
    address: str
    dob: date
    aadhar: str
    pin: Optional[str] = None


class AccountOut(BaseModel):
    name: str
    mobile: str
    address: str
    dob: date
    aadhar: str
    account_number: str
    balance: float
    wallet_balance: float

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    mobile: str
    pin: str


class AdminLogin(BaseModel):
    admin_id: str
    password: str


class DepositRequest(BaseModel):
    account_number: str
    pin: Optional[str] = None
    amount: float = Field(gt=0)


class WithdrawWalletRequest(BaseModel):
    account_number: str
    pin: str
    amount: float = Field(gt=0)


class TransferRequest(BaseModel):
    from_account_number: str
    to_account_number: str
    pin: str
    amount: float = Field(gt=0)


class WalletPayRequest(BaseModel):
    account_number: str
    amount: float = Field(gt=0)
    merchant: str


class TransactionOut(BaseModel):
    date: str
    type: str
    amount: float
    fromAccount: Optional[str] = None
    toAccount: Optional[str] = None


# ---------------- App ----------------
app = FastAPI(title="e-bank Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Helpers ----------------
def _generate_account_number(db: Session) -> str:
    import secrets

    while True:
        candidate = str(secrets.randbelow(90000000) + 10000000)
        if not db.query(Account).filter(Account.account_number == candidate).first():
            return candidate


def get_account_by_number(db: Session, account_number: str) -> Account:
    acc = db.query(Account).filter(Account.account_number == account_number).one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


def record_tx(
    db: Session,
    tx_type: str,
    amount: float,
    from_account: Optional[Account] = None,
    to_account: Optional[Account] = None,
    merchant: Optional[str] = None,
):
    tx = Transaction(
        type=tx_type,
        amount=amount,
        from_account=from_account,
        to_account=to_account,
        merchant=merchant,
    )
    db.add(tx)
    db.flush()
    return tx


# ---------------- Startup: create tables and seed demo ----------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        exists = db.query(Account.id).first()
        if not exists:
            demo_accounts = [
                {
                    "name": "kavi",
                    "mobile": "1234567890",
                    "address": "123 Main Street, New York, NY 10001",
                    "dob": date(1990, 1, 15),
                    "aadhar": "123456789012",
                    "account_number": "12345678",
                    "pin": "1234",
                    "balance": 5000.0,
                    "wallet_balance": 500.0,
                },
                {
                    "name": "arun",
                    "mobile": "9876543210",
                    "address": "456 Oak Avenue, Los Angeles, CA 90210",
                    "dob": date(1985, 3, 22),
                    "aadhar": "987654321098",
                    "account_number": "87654321",
                    "pin": "5678",
                    "balance": 7500.0,
                    "wallet_balance": 750.0,
                },
                {
                    "name": "gokul",
                    "mobile": "5551234567",
                    "address": "789 Pine Road, Chicago, IL 60601",
                    "dob": date(1992, 7, 8),
                    "aadhar": "456789123456",
                    "account_number": "45678912",
                    "pin": "9876",
                    "balance": 3200.0,
                    "wallet_balance": 320.0,
                },
            ]
            for data in demo_accounts:
                db.add(Account(**data))
            db.commit()
    finally:
        db.close()


# ---------------- Auth ----------------
@app.post("/auth/login-user", response_model=AccountOut)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(Account).filter(Account.mobile == payload.mobile).one_or_none()
    if not user or user.pin != payload.pin:
        raise HTTPException(status_code=401, detail="Invalid mobile or PIN")
    return user


@app.post("/auth/login-admin")
def login_admin(payload: AdminLogin):
    admin_id = os.getenv("ADMIN_ID", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "a123")
    if payload.admin_id == admin_id and payload.password == admin_password:
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Invalid admin credentials")


# ---------------- Accounts ----------------
@app.post("/admin/accounts", response_model=AccountOut)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    # Unique mobile
    if db.query(Account).filter(Account.mobile == account.mobile).first():
        raise HTTPException(status_code=400, detail="Account with this mobile already exists")

    account_number = _generate_account_number(db)
    pin_value = account.pin or "0000"
    acc = Account(
        name=account.name,
        mobile=account.mobile,
        address=account.address,
        dob=account.dob,
        aadhar=account.aadhar,
        account_number=account_number,
        pin=pin_value,
        balance=0,
        wallet_balance=0,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@app.get("/accounts/{account_number}", response_model=AccountOut)
def get_account(account_number: str, db: Session = Depends(get_db)):
    return get_account_by_number(db, account_number)


class AccountUpdate(BaseModel):
    address: Optional[str] = None
    pin: Optional[str] = None


@app.put("/accounts/{account_number}", response_model=AccountOut)
def update_account(account_number: str, payload: AccountUpdate, db: Session = Depends(get_db)):
    acc = get_account_by_number(db, account_number)
    if payload.address is not None:
        acc.address = payload.address
    if payload.pin is not None:
        if len(payload.pin) != 4 or not payload.pin.isdigit():
            raise HTTPException(status_code=400, detail="PIN must be 4 digits")
        acc.pin = payload.pin
    db.commit()
    db.refresh(acc)
    return acc


@app.get("/admin/users", response_model=List[AccountOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(Account).order_by(Account.id.asc()).all()


@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db)):
    total_customers = db.query(func.count(Account.id)).scalar() or 0
    total_bank_balance = float(db.query(func.coalesce(func.sum(Account.balance), 0)).scalar() or 0.0)
    total_wallet_balance = float(db.query(func.coalesce(func.sum(Account.wallet_balance), 0)).scalar() or 0.0)
    return {
        "totalCustomers": int(total_customers),
        "totalBankBalance": total_bank_balance,
        "totalWalletBalance": total_wallet_balance,
    }


# ---------------- Transactions ----------------
def ensure_pin(acc: Account, pin: Optional[str]):
    if pin is None or acc.pin != pin:
        raise HTTPException(status_code=401, detail="Invalid PIN")


@app.post("/transactions/deposit")
def deposit_money(payload: DepositRequest, db: Session = Depends(get_db)):
    acc = get_account_by_number(db, payload.account_number)
    # If pin provided, validate (customer deposit); if not, allow (admin deposit) via /admin/deposit preferred
    if payload.pin is not None:
        ensure_pin(acc, payload.pin)
    acc.balance = float(acc.balance) + payload.amount
    record_tx(db, "deposit", payload.amount, to_account=acc)
    db.commit()
    return {"ok": True}


@app.post("/transactions/withdraw-wallet")
def withdraw_to_wallet(payload: WithdrawWalletRequest, db: Session = Depends(get_db)):
    acc = get_account_by_number(db, payload.account_number)
    ensure_pin(acc, payload.pin)
    if payload.amount <= 0 or float(acc.balance) < payload.amount:
        raise HTTPException(status_code=400, detail="Invalid amount or insufficient balance")
    acc.balance = float(acc.balance) - payload.amount
    acc.wallet_balance = float(acc.wallet_balance) + payload.amount
    record_tx(db, "withdrawal-to-wallet", payload.amount, from_account=acc)
    db.commit()
    return {"ok": True}


@app.post("/transactions/transfer")
def transfer_money(payload: TransferRequest, db: Session = Depends(get_db)):
    if payload.from_account_number == payload.to_account_number:
        raise HTTPException(status_code=400, detail="Cannot transfer to same account")
    from_acc = get_account_by_number(db, payload.from_account_number)
    to_acc = get_account_by_number(db, payload.to_account_number)
    ensure_pin(from_acc, payload.pin)
    if payload.amount <= 0 or float(from_acc.balance) < payload.amount:
        raise HTTPException(status_code=400, detail="Invalid amount or insufficient balance")
    from_acc.balance = float(from_acc.balance) - payload.amount
    to_acc.balance = float(to_acc.balance) + payload.amount
    record_tx(db, "transfer", payload.amount, from_account=from_acc, to_account=to_acc)
    db.commit()
    return {"ok": True}


@app.post("/wallet/pay")
def wallet_pay(payload: WalletPayRequest, db: Session = Depends(get_db)):
    acc = get_account_by_number(db, payload.account_number)
    if float(acc.wallet_balance) < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    acc.wallet_balance = float(acc.wallet_balance) - payload.amount
    record_tx(db, "wallet-payment", payload.amount, from_account=acc, merchant=payload.merchant)
    db.commit()
    return {"ok": True}


@app.get("/transactions", response_model=List[TransactionOut])
def list_transactions(
    account_number: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if account_number:
        acc = get_account_by_number(db, account_number)
        q = q.filter(
            (Transaction.from_account_id == acc.id) | (Transaction.to_account_id == acc.id)
        )
    if start_date:
        q = q.filter(Transaction.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        q = q.filter(Transaction.created_at <= datetime.combine(end_date, datetime.max.time()))
    q = q.order_by(Transaction.created_at.desc())
    rows = q.all()
    out: List[TransactionOut] = []
    for r in rows:
        out.append(
            TransactionOut(
                date=r.created_at.isoformat(),
                type=r.type,
                amount=float(r.amount),
                fromAccount=(r.from_account.account_number if r.from_account else None),
                toAccount=(r.to_account.account_number if r.to_account else r.merchant),
            )
        )
    return out


# ---------------- Admin helpers ----------------
class AdminDepositRequest(BaseModel):
    account_number: str
    amount: float = Field(gt=0)


@app.post("/admin/deposit")
def admin_deposit(payload: AdminDepositRequest, db: Session = Depends(get_db)):
    acc = get_account_by_number(db, payload.account_number)
    acc.balance = float(acc.balance) + payload.amount
    record_tx(db, "admin-deposit", payload.amount, to_account=acc)
    db.commit()
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}

