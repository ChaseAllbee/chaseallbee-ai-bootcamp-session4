"""
Comprehensive test suite for Slalom Capabilities Management System.

Tests cover:
  - Database models and seeding
  - Authentication (login endpoint)
  - Authorization (role-based access control)
  - Capability CRUD and registration
  - Edge cases and error handling
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import (
    app,
    Base,
    get_db,
    CapabilityModel,
    RegistrationModel,
    PracticeLeadModel,
    seed_database,
    _verify_password,
    _hash_password,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────────

import tempfile
import os

# Create a new temporary file for each test run
_test_db_fd, _test_db_path = tempfile.mkstemp()
os.close(_test_db_fd)

# Module-level: create test engine once and reuse it
_test_engine = create_engine(f"sqlite:///{_test_db_path}")
Base.metadata.create_all(bind=_test_engine)

_test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

# Seed on module load
_init_db = _test_session_local()
try:
    seed_database(_init_db)
finally:
    _init_db.close()


@pytest.fixture
def test_db():
    """Create a fresh database session for each test, with transaction management."""
    connection = _test_engine.connect()
    transaction = connection.begin()
    
    db = _test_session_local(bind=connection)
    
    yield db
    
    # Rollback the transaction to restore state before this test
    db.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(test_db):
    """Create a test client with the test database."""
    def override_get_db():
        # Use the same test_db session
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Clean up test database file after all tests."""
    yield
    try:
        os.unlink(_test_db_path)
    except:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# Database Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDatabase:
    """Test database models, relationships, and seeding."""

    def test_capability_model_creation(self, test_db):
        """Test that a capability can be created."""
        cap = CapabilityModel(
            name="Test Capability",
            description="A test capability",
            practice_area="Technology",
            capacity=20,
        )
        test_db.add(cap)
        test_db.commit()
        
        result = test_db.query(CapabilityModel).filter_by(name="Test Capability").first()
        assert result is not None
        assert result.description == "A test capability"
        assert result.capacity == 20

    def test_registration_model_relationship(self, test_db):
        """Test that registrations are linked to capabilities."""
        cap = test_db.query(CapabilityModel).filter_by(name="Cloud Architecture").first()
        assert cap is not None
        
        # Create a new registration
        reg = RegistrationModel(capability_id=cap.id, email="test@example.com")
        test_db.add(reg)
        test_db.commit()
        
        # Verify relationship
        result = test_db.query(CapabilityModel).filter_by(name="Cloud Architecture").first()
        assert len(result.registrations) >= 1
        assert any(r.email == "test@example.com" for r in result.registrations)

    def test_unique_constraint_on_registration(self, test_db):
        """Test that duplicate registrations are prevented."""
        cap = test_db.query(CapabilityModel).filter_by(name="Cloud Architecture").first()
        
        reg1 = RegistrationModel(capability_id=cap.id, email="unique@example.com")
        test_db.add(reg1)
        test_db.commit()
        
        # Try to add a duplicate
        reg2 = RegistrationModel(capability_id=cap.id, email="unique@example.com")
        test_db.add(reg2)
        
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()

    def test_seeding_creates_capabilities(self, test_db):
        """Test that the database is seeded with all 10 capabilities."""
        capabilities = test_db.query(CapabilityModel).all()
        assert len(capabilities) == 10
        
        names = {cap.name for cap in capabilities}
        assert "Cloud Architecture" in names
        assert "Data Analytics" in names
        assert "Slalom Build" in names

    def test_seeding_creates_practice_lead(self, test_db):
        """Test that the default practice lead is created."""
        lead = test_db.query(PracticeLeadModel).filter_by(email="admin@slalom.com").first()
        assert lead is not None
        assert _verify_password("slalom2024", lead.hashed_password)

    def test_seeding_populates_registrations(self, test_db):
        """Test that initial consultant registrations are seeded."""
        cloud_arch = test_db.query(CapabilityModel).filter_by(name="Cloud Architecture").first()
        assert len(cloud_arch.registrations) >= 1
        
        # Verify at least one of the seeded consultants is registered
        emails = {r.email for r in cloud_arch.registrations}
        assert "alice.smith@slalom.com" in emails


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthentication:
    """Test login and authentication mechanisms."""

    def test_practice_lead_login_success(self, client):
        """Test that a practice lead can log in with correct password."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@slalom.com", "password": "slalom2024"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "practice_lead"
        assert data["email"] == "admin@slalom.com"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_practice_lead_login_wrong_password(self, client):
        """Test that a practice lead cannot log in with wrong password."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@slalom.com", "password": "wrongpassword"}
        )
        assert response.status_code == 200
        data = response.json()
        # Falls back to consultant role if password is wrong
        assert data["role"] == "consultant"

    def test_consultant_login_no_password(self, client):
        """Test that a consultant can log in with just email (no password)."""
        response = client.post(
            "/auth/login",
            json={"email": "any.consultant@slalom.com", "password": ""}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "consultant"
        assert data["email"] == "any.consultant@slalom.com"

    def test_consultant_login_with_any_password(self, client):
        """Test that a consultant gets consultant role even with any password."""
        response = client.post(
            "/auth/login",
            json={"email": "consultant@example.com", "password": "anything"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "consultant"

    def test_token_returned_is_valid_jwt(self, client):
        """Test that the returned token is a valid JWT."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": ""}
        )
        data = response.json()
        token = data["access_token"]
        
        # Token should have 3 parts separated by dots (JWT format)
        parts = token.split(".")
        assert len(parts) == 3

    def test_me_endpoint_returns_current_user(self, client):
        """Test the /auth/me endpoint returns current user info."""
        # Login first
        login_response = client.post(
            "/auth/login",
            json={"email": "myemail@example.com", "password": ""}
        )
        token = login_response.json()["access_token"]
        
        # Call /auth/me
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "myemail@example.com"
        assert data["role"] == "consultant"

    def test_missing_token_returns_401(self, client):
        """Test that missing auth token returns 401."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """Test that invalid token returns 401."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Capabilities Endpoint Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCapabilitiesEndpoint:
    """Test the /capabilities endpoint."""

    def test_get_capabilities_public(self, client):
        """Test that capabilities can be retrieved without authentication."""
        response = client.get("/capabilities")
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert isinstance(data, dict)
        assert "Cloud Architecture" in data
        assert data["Cloud Architecture"]["practice_area"] == "Technology"
        assert "consultants" in data["Cloud Architecture"]

    def test_capabilities_include_all_fields(self, client):
        """Test that each capability has all required fields."""
        response = client.get("/capabilities")
        data = response.json()
        
        cloud_arch = data["Cloud Architecture"]
        required_fields = {"description", "practice_area", "skill_levels", 
                          "certifications", "industry_verticals", "capacity", "consultants"}
        assert required_fields.issubset(cloud_arch.keys())

    def test_capabilities_count(self, client):
        """Test that all 10 seeded capabilities are returned."""
        response = client.get("/capabilities")
        data = response.json()
        assert len(data) == 10

    def test_slalom_build_capability_exists(self, client):
        """Test that the newly added Slalom Build capability is present."""
        response = client.get("/capabilities")
        data = response.json()
        
        assert "Slalom Build" in data
        assert "product" in data["Slalom Build"]["description"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Registration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistration:
    """Test consultant registration for capabilities."""

    def test_consultant_can_register(self, client):
        """Test that an authenticated consultant can register for a capability."""
        # Login
        login_response = client.post(
            "/auth/login",
            json={"email": "newconsultant@example.com", "password": ""}
        )
        token = login_response.json()["access_token"]
        
        # Register
        response = client.post(
            "/capabilities/Slalom%20Build/register",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "Registered" in response.json()["message"]

    def test_cannot_register_twice(self, client):
        """Test that a consultant cannot register for the same capability twice."""
        # Login
        login_response = client.post(
            "/auth/login",
            json={"email": "double@example.com", "password": ""}
        )
        token = login_response.json()["access_token"]
        
        # Register once
        response1 = client.post(
            "/capabilities/Cloud%20Architecture/register",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response1.status_code == 200
        
        # Try to register again
        response2 = client.post(
            "/capabilities/Cloud%20Architecture/register",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()

    def test_register_nonexistent_capability(self, client):
        """Test that registering for a non-existent capability returns 404."""
        # Login
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": ""}
        )
        token = login_response.json()["access_token"]
        
        # Try to register for non-existent capability
        response = client.post(
            "/capabilities/Fake%20Capability/register",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_register_without_auth_fails(self, client):
        """Test that registering without authentication fails."""
        response = client.post("/capabilities/Cloud%20Architecture/register")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Unregistration & Authorization Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnregistration:
    """Test consultant unregistration and authorization."""

    def test_consultant_can_unregister_self(self, client):
        """Test that a consultant can unregister themselves."""
        email = "selfunreg@example.com"
        
        # Register
        login_response = client.post(
            "/auth/login",
            json={"email": email, "password": ""}
        )
        token = login_response.json()["access_token"]
        
        client.post(
            "/capabilities/Slalom%20Build/register",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Unregister self
        response = client.delete(
            f"/capabilities/Slalom%20Build/unregister?email={email}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]

    def test_consultant_cannot_unregister_others(self, client):
        """Test that a consultant cannot unregister other consultants."""
        # Consultant 1 registers
        login1 = client.post(
            "/auth/login",
            json={"email": "consultant1@example.com", "password": ""}
        )
        token1 = login1.json()["access_token"]
        
        client.post(
            "/capabilities/DevOps%20Engineering/register",
            headers={"Authorization": f"Bearer {token1}"}
        )
        
        # Consultant 2 tries to unregister consultant 1
        login2 = client.post(
            "/auth/login",
            json={"email": "consultant2@example.com", "password": ""}
        )
        token2 = login2.json()["access_token"]
        
        response = client.delete(
            "/capabilities/DevOps%20Engineering/unregister?email=consultant1@example.com",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.status_code == 403
        assert "can only unregister yourself" in response.json()["detail"].lower()

    def test_practice_lead_can_unregister_anyone(self, client):
        """Test that a practice lead can unregister any consultant."""
        # Consultant registers
        cons_login = client.post(
            "/auth/login",
            json={"email": "targetconsultant@example.com", "password": ""}
        )
        cons_token = cons_login.json()["access_token"]
        
        client.post(
            "/capabilities/Digital%20Strategy/register",
            headers={"Authorization": f"Bearer {cons_token}"}
        )
        
        # Practice lead logs in
        lead_login = client.post(
            "/auth/login",
            json={"email": "admin@slalom.com", "password": "slalom2024"}
        )
        lead_token = lead_login.json()["access_token"]
        
        # Practice lead unregisters consultant
        response = client.delete(
            "/capabilities/Digital%20Strategy/unregister?email=targetconsultant@example.com",
            headers={"Authorization": f"Bearer {lead_token}"}
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]

    def test_unregister_nonexistent_capability(self, client):
        """Test that unregistering from a non-existent capability returns 404."""
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": ""}
        )
        token = login_response.json()["access_token"]
        
        response = client.delete(
            "/capabilities/Fake%20Capability/unregister?email=test@example.com",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_unregister_not_registered(self, client):
        """Test that unregistering when not registered returns 400."""
        login_response = client.post(
            "/auth/login",
            json={"email": "notregistered@example.com", "password": ""}
        )
        token = login_response.json()["access_token"]
        
        response = client.delete(
            "/capabilities/Cloud%20Architecture/unregister?email=notregistered@example.com",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases & Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration and end-to-end tests."""

    def test_full_registration_lifecycle(self, client):
        """Test the full lifecycle: login, register, view, unregister."""
        email = "lifecycle@example.com"
        
        # 1. Login
        login = client.post(
            "/auth/login",
            json={"email": email, "password": ""}
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        
        # 2. Check not yet registered in capabilities list
        caps1 = client.get("/capabilities").json()
        assert email not in caps1["Slalom Build"]["consultants"]
        
        # 3. Register
        register = client.post(
            "/capabilities/Slalom%20Build/register",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert register.status_code == 200
        
        # 4. Verify registered in capabilities list
        caps2 = client.get("/capabilities").json()
        assert email in caps2["Slalom Build"]["consultants"]
        
        # 5. Unregister
        unregister = client.delete(
            f"/capabilities/Slalom%20Build/unregister?email={email}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert unregister.status_code == 200
        
        # 6. Verify unregistered
        caps3 = client.get("/capabilities").json()
        assert email not in caps3["Slalom Build"]["consultants"]

    def test_multiple_consultants_same_capability(self, client):
        """Test that multiple consultants can register for the same capability."""
        cap_name = "Business%20Intelligence"
        
        emails = ["consult1@ex.com", "consult2@ex.com", "consult3@ex.com"]
        
        for email in emails:
            login = client.post(
                "/auth/login",
                json={"email": email, "password": ""}
            )
            token = login.json()["access_token"]
            
            response = client.post(
                f"/capabilities/{cap_name}/register",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
        
        # Verify all registered
        caps = client.get("/capabilities").json()
        for email in emails:
            assert email in caps["Business Intelligence"]["consultants"]

    def test_consultant_can_register_multiple_capabilities(self, client):
        """Test that a consultant can register for multiple capabilities."""
        email = "multireg@example.com"
        
        login = client.post(
            "/auth/login",
            json={"email": email, "password": ""}
        )
        token = login.json()["access_token"]
        
        capabilities = ["Cloud%20Architecture", "Data%20Analytics", "Cybersecurity"]
        
        for cap in capabilities:
            response = client.post(
                f"/capabilities/{cap}/register",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
        
        # Verify all registrations
        caps = client.get("/capabilities").json()
        assert email in caps["Cloud Architecture"]["consultants"]
        assert email in caps["Data Analytics"]["consultants"]
        assert email in caps["Cybersecurity"]["consultants"]

    def test_database_consistency_after_operations(self, client, test_db):
        """Test that database remains consistent after multiple operations."""
        # Perform various operations
        for i in range(5):
            email = f"consistency_test_{i}@example.com"
            
            # Login and register
            login = client.post(
                "/auth/login",
                json={"email": email, "password": ""}
            )
            token = login.json()["access_token"]
            
            client.post(
                "/capabilities/Agile%20Coaching/register",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        # Verify database count
        registrations = test_db.query(RegistrationModel).filter(
            RegistrationModel.email.like("consistency_test_%")
        ).all()
        assert len(registrations) == 5

    def test_password_hashing_consistency(self):
        """Test that password hashing is consistent."""
        password = "test_password_123"
        
        hashed1 = _hash_password(password)
        hashed2 = _hash_password(password)
        
        # Hashed passwords should be different (bcrypt salts)
        assert hashed1 != hashed2
        
        # But both should verify
        assert _verify_password(password, hashed1)
        assert _verify_password(password, hashed2)
        
        # Wrong password should not verify
        assert not _verify_password("wrong_password", hashed1)
