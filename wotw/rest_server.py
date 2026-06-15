# ===========================================================================
# rest_server.py  —  a fully REST-compliant HTTP server with an ORM + database.
# ===========================================================================
# Built to satisfy the assignment spec:
#   * Python HTTP server (FastAPI) talking to a STANDALONE database (SQLite)
#     through an ORM (SQLAlchemy) — requirement 1.
#   * Correct HTTP methods, plural-noun URLs, and status codes — section 2.
#
# Resources
#   users : authentication via POST /sign-up, POST /sign-in, POST /logout
#   saves : protected CRUD; a user may only touch their OWN saves
#
# Run it:   uvicorn rest_server:app --reload
# Explore:  http://127.0.0.1:8000/docs   (interactive API docs)
#
# How auth works: sign-in/sign-up hand back a random token. The client then
# sends it on every protected request as the header:  Authorization: Bearer <token>
#   * no/invalid token  -> 401 UNAUTHORIZED
#   * valid token but someone else's save -> 403 FORBIDDEN
# ===========================================================================
import secrets
from typing import Optional

from fastapi import FastAPI, Depends, Header, HTTPException, status, Response, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import (
    declarative_base, sessionmaker, Session, Mapped, mapped_column,
)

# --------------------------------------------------------------------------
# 1) DATABASE + ORM  (the "standalone database via ORM" requirement)
# --------------------------------------------------------------------------
# A real SQLite database file on disk, accessed only through SQLAlchemy models
# (no raw SQL). `Base` is the parent class every table model inherits from.
DATABASE_URL = "sqlite:///./wotw.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


class User(Base):
    """A registered account (the 'users' resource)."""
    __tablename__ = "users"
    id:       Mapped[int] = mapped_column(primary_key=True)
    email:    Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str] = mapped_column()            # plain text — demo only!
    token:    Mapped[Optional[str]] = mapped_column(nullable=True)


class Save(Base):
    """A saved game, owned by one user (the 'saves' resource)."""
    __tablename__ = "saves"
    id:            Mapped[int]   = mapped_column(primary_key=True)
    owner_id:      Mapped[int]   = mapped_column(ForeignKey("users.id"))
    current_level: Mapped[int]   = mapped_column(default=1)
    score:         Mapped[int]   = mapped_column(default=0)
    position_x:    Mapped[float] = mapped_column(default=0.0)
    position_y:    Mapped[float] = mapped_column(default=0.0)


Base.metadata.create_all(engine)   # create the tables on first run


def get_db():
    """Hand each request its own DB session, and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_to_dict(s: Save) -> dict:
    """Turn a Save ORM object into a plain dict for JSON responses."""
    return {
        "id": s.id,
        "owner_id": s.owner_id,
        "current_level": s.current_level,
        "score": s.score,
        "position_x": s.position_x,
        "position_y": s.position_y,
    }


# --------------------------------------------------------------------------
# 2) REQUEST BODY SHAPES  (validated by Pydantic -> JSON in, JSON out)
# --------------------------------------------------------------------------
class Credentials(BaseModel):       # POST /sign-up and /sign-in
    email: str
    password: str

class SaveCreate(BaseModel):        # POST /saves
    current_level: int
    score: int
    position_x: float
    position_y: float

class SaveUpdate(BaseModel):        # PUT /saves/{id}  (replace all fields)
    current_level: int
    score: int
    position_x: float
    position_y: float

class SavePatch(BaseModel):         # PATCH /saves/{id}  (any subset of fields)
    current_level: Optional[int] = None
    score: Optional[int] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None


# --------------------------------------------------------------------------
# 3) THE APP + GLOBAL ERROR HANDLERS  (status codes from section 2.2)
# --------------------------------------------------------------------------
app = FastAPI(title="Wok of the Warrior - REST API")


@app.exception_handler(RequestValidationError)
async def on_invalid_body(request: Request, exc: RequestValidationError):
    # 2.2.5: a malformed/invalid body must be 400 (FastAPI's default is 422).
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


@app.exception_handler(Exception)
async def on_server_error(request: Request, exc: Exception):
    # 2.2.9: any unexpected crash while handling a valid request -> 500, JSON.
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


def get_current_user(authorization: Optional[str] = Header(default=None),
                     db: Session = Depends(get_db)) -> User:
    """Auth gate for protected endpoints.

    2.2.6: no token / bad token -> 401 UNAUTHORIZED.
    Reads the 'Authorization: Bearer <token>' header and finds the user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    user = db.query(User).filter(User.token == token).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def owned_save(save_id: int, db: Session, user: User) -> Save:
    """Fetch a save and enforce ownership.

    2.2.8: missing save -> 404.   2.2.7: not your save -> 403.
    """
    s = db.get(Save, save_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Save not found")
    if s.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this save")
    return s


# --------------------------------------------------------------------------
# 4) AUTH ENDPOINTS  (2.1.12: always POST, verb-URLs allowed only here)
# --------------------------------------------------------------------------
@app.post("/sign-up", status_code=status.HTTP_201_CREATED)
def sign_up(creds: Credentials, db: Session = Depends(get_db)):
    """Register a new user and return a token. Creates a resource -> 201."""
    if db.query(User).filter(User.email == creds.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=creds.email, password=creds.password, token=secrets.token_hex(16))
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email, "token": user.token}


@app.post("/sign-in", status_code=200)
def sign_in(creds: Credentials, db: Session = Depends(get_db)):
    """Log in: return a fresh token. Returns a body -> 200."""
    user = db.query(User).filter(User.email == creds.email).first()
    if user is None or user.password != creds.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user.token = secrets.token_hex(16)
    db.commit()
    return {"token": user.token}


@app.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invalidate the caller's token. No body in the reply -> 204."""
    user.token = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# 5) SAVES RESOURCE  (CRUD; every endpoint requires a valid token)
# --------------------------------------------------------------------------
@app.get("/saves", status_code=200)
def list_saves(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Read all of the caller's saves. 2.1.8: GET /saves -> 200."""
    saves = db.query(Save).filter(Save.owner_id == user.id).all()
    return [save_to_dict(s) for s in saves]


@app.get("/saves/{save_id}", status_code=200)
def get_save(save_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Read one save. 2.1.7: GET /saves/{id} -> 200 (404/403 as needed)."""
    return save_to_dict(owned_save(save_id, db, user))


@app.post("/saves", status_code=status.HTTP_201_CREATED)
def create_save(data: SaveCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a save. 2.1.9 + 2.2.2: POST /saves -> 201."""
    s = Save(owner_id=user.id, **data.model_dump())
    db.add(s)
    db.commit()
    return save_to_dict(s)


@app.put("/saves/{save_id}", status_code=200)
def update_save(save_id: int, data: SaveUpdate,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Replace every field of a save. 2.1.10: PUT /saves/{id} -> 200."""
    s = owned_save(save_id, db, user)
    for field, value in data.model_dump().items():
        setattr(s, field, value)
    db.commit()
    return save_to_dict(s)


@app.patch("/saves/{save_id}", status_code=200)
def patch_save(save_id: int, data: SavePatch,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update only the fields that were sent. 2.1.5: PATCH /saves/{id} -> 200."""
    s = owned_save(save_id, db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    return save_to_dict(s)


@app.delete("/saves/{save_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_save(save_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a save. 2.1.11 + 2.2.4: DELETE /saves/{id} -> 204 (no body)."""
    s = owned_save(save_id, db, user)
    db.delete(s)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
