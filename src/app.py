"""
Slalom Capabilities Management System API

A FastAPI application that enables Slalom consultants to register their
capabilities and manage consulting expertise across the organization.

Features:
  - SQLite-backed persistence via SQLAlchemy (replaces in-memory dict)
  - JWT authentication: Practice Leads (email+password) and Consultants (email only)
  - Role-based access: consultants can only unregister themselves; practice leads can manage all
"""

from datetime import datetime, timedelta
from typing import Optional
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

# ─── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY", "slalom-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

DATABASE_URL = f"sqlite:///{Path(__file__).parent}/capabilities.db"

# ─── Database Setup ───────────────────────────────────────────────────────────

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─── Database Models ──────────────────────────────────────────────────────────

class CapabilityModel(Base):
    __tablename__ = "capabilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, default="")
    practice_area = Column(String(100), default="")
    skill_levels = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    industry_verticals = Column(JSON, default=list)
    capacity = Column(Integer, default=0)
    registrations = relationship(
        "RegistrationModel", back_populates="capability", cascade="all, delete-orphan"
    )


class RegistrationModel(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    capability_id = Column(Integer, ForeignKey("capabilities.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    capability = relationship("CapabilityModel", back_populates="registrations")

    __table_args__ = (
        UniqueConstraint("capability_id", "email", name="uq_capability_email"),
    )


class PracticeLeadModel(Base):
    """Authenticated practice lead users who can manage all registrations."""
    __tablename__ = "practice_leads"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

# ─── Auth Utilities ───────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(email: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "role": role, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role", "consultant")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"email": email, "role": role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str

# ─── Seed Data ────────────────────────────────────────────────────────────────

SEED_CAPABILITIES = [
    {
        "name": "Cloud Architecture",
        "description": "Design and implement scalable cloud solutions using AWS, Azure, and GCP",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["AWS Solutions Architect", "Azure Architect Expert"],
        "industry_verticals": ["Healthcare", "Financial Services", "Retail"],
        "capacity": 40,
        "consultants": ["alice.smith@slalom.com", "bob.johnson@slalom.com"],
    },
    {
        "name": "Data Analytics",
        "description": "Advanced data analysis, visualization, and machine learning solutions",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Tableau Desktop Specialist", "Power BI Expert", "Google Analytics"],
        "industry_verticals": ["Retail", "Healthcare", "Manufacturing"],
        "capacity": 35,
        "consultants": ["emma.davis@slalom.com", "sophia.wilson@slalom.com"],
    },
    {
        "name": "DevOps Engineering",
        "description": "CI/CD pipeline design, infrastructure automation, and containerization",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Docker Certified Associate", "Kubernetes Admin", "Jenkins Certified"],
        "industry_verticals": ["Technology", "Financial Services"],
        "capacity": 30,
        "consultants": ["john.brown@slalom.com", "olivia.taylor@slalom.com"],
    },
    {
        "name": "Digital Strategy",
        "description": "Digital transformation planning and strategic technology roadmaps",
        "practice_area": "Strategy",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Digital Transformation Certificate", "Agile Certified Practitioner"],
        "industry_verticals": ["Healthcare", "Financial Services", "Government"],
        "capacity": 25,
        "consultants": ["liam.anderson@slalom.com", "noah.martinez@slalom.com"],
    },
    {
        "name": "Change Management",
        "description": "Organizational change leadership and adoption strategies",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Prosci Certified", "Lean Six Sigma Black Belt"],
        "industry_verticals": ["Healthcare", "Manufacturing", "Government"],
        "capacity": 20,
        "consultants": ["ava.garcia@slalom.com", "mia.rodriguez@slalom.com"],
    },
    {
        "name": "UX/UI Design",
        "description": "User experience design and digital product innovation",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Adobe Certified Expert", "Google UX Design Certificate"],
        "industry_verticals": ["Retail", "Healthcare", "Technology"],
        "capacity": 30,
        "consultants": ["amelia.lee@slalom.com", "harper.white@slalom.com"],
    },
    {
        "name": "Cybersecurity",
        "description": "Information security strategy, risk assessment, and compliance",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["CISSP", "CISM", "CompTIA Security+"],
        "industry_verticals": ["Financial Services", "Healthcare", "Government"],
        "capacity": 25,
        "consultants": ["ella.clark@slalom.com", "scarlett.lewis@slalom.com"],
    },
    {
        "name": "Business Intelligence",
        "description": "Enterprise reporting, data warehousing, and business analytics",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Microsoft BI Certification", "Qlik Sense Certified"],
        "industry_verticals": ["Retail", "Manufacturing", "Financial Services"],
        "capacity": 35,
        "consultants": ["james.walker@slalom.com", "benjamin.hall@slalom.com"],
    },
    {
        "name": "Agile Coaching",
        "description": "Agile transformation and team coaching for scaled delivery",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Certified Scrum Master", "SAFe Agilist", "ICAgile Certified"],
        "industry_verticals": ["Technology", "Financial Services", "Healthcare"],
        "capacity": 20,
        "consultants": ["charlotte.young@slalom.com", "henry.king@slalom.com"],
    },
    {
        "name": "Slalom Build",
        "description": "Product strategy, digital product development, design thinking, and full-stack engineering",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": [
            "Product Management Certificate",
            "Agile Certified Practitioner",
            "Design Thinking Practitioner",
        ],
        "industry_verticals": ["Consumer Products", "Financial Services", "Healthcare", "Technology"],
        "capacity": 35,
        "consultants": [],
    },
]


def seed_database(db: Session) -> None:
    if db.query(CapabilityModel).count() > 0:
        return

    for cap_data in SEED_CAPABILITIES:
        consultants = cap_data.pop("consultants", [])
        cap = CapabilityModel(**cap_data)
        db.add(cap)
        db.flush()
        for email in consultants:
            db.add(RegistrationModel(capability_id=cap.id, email=email))

    if db.query(PracticeLeadModel).count() == 0:
        db.add(PracticeLeadModel(
            email="admin@slalom.com",
            hashed_password=_hash_password("slalom2024"),
        ))

    db.commit()

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Slalom Capabilities Management API",
    description="API for managing consulting capabilities and consultant expertise",
)

current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(current_dir / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")

# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user.
    - Practice Leads: supply email + correct password → receive practice_lead token.
    - Consultants: supply email only (password ignored) → receive consultant token.
    """
    email = request.email.strip().lower()
    role = "consultant"

    if request.password:
        lead = db.query(PracticeLeadModel).filter(PracticeLeadModel.email == email).first()
        if lead and _verify_password(request.password, lead.hashed_password):
            role = "practice_lead"

    token = create_access_token(email=email, role=role)
    return TokenResponse(access_token=token, email=email, role=role)


@app.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ─── Capability Endpoints ─────────────────────────────────────────────────────

def _capability_to_dict(cap: CapabilityModel) -> dict:
    return {
        "description": cap.description,
        "practice_area": cap.practice_area,
        "skill_levels": cap.skill_levels or [],
        "certifications": cap.certifications or [],
        "industry_verticals": cap.industry_verticals or [],
        "capacity": cap.capacity,
        "consultants": [r.email for r in cap.registrations],
    }


@app.get("/capabilities")
def get_capabilities(db: Session = Depends(get_db)):
    """Return all capabilities. Public endpoint — no auth required."""
    caps = db.query(CapabilityModel).all()
    return {cap.name: _capability_to_dict(cap) for cap in caps}


@app.post("/capabilities/{capability_name}/register")
def register_for_capability(
    capability_name: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register the authenticated user for a capability."""
    cap = db.query(CapabilityModel).filter(CapabilityModel.name == capability_name).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")

    existing = db.query(RegistrationModel).filter(
        RegistrationModel.capability_id == cap.id,
        RegistrationModel.email == current_user["email"],
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this capability")

    db.add(RegistrationModel(capability_id=cap.id, email=current_user["email"]))
    db.commit()
    return {"message": f"Registered {current_user['email']} for {capability_name}"}


@app.delete("/capabilities/{capability_name}/unregister")
def unregister_from_capability(
    capability_name: str,
    email: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unregister a consultant from a capability.
    - Practice Leads can remove any consultant.
    - Consultants can only remove themselves.
    """
    if current_user["role"] != "practice_lead" and current_user["email"] != email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only unregister yourself",
        )

    cap = db.query(CapabilityModel).filter(CapabilityModel.name == capability_name).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")

    reg = db.query(RegistrationModel).filter(
        RegistrationModel.capability_id == cap.id,
        RegistrationModel.email == email,
    ).first()
    if not reg:
        raise HTTPException(status_code=400, detail="Consultant is not registered for this capability")

    db.delete(reg)
    db.commit()
    return {"message": f"Unregistered {email} from {capability_name}"}
