"""
Load Testing Script for VA Matching Platform using Locust.

This script simulates realistic user behavior for the VA Matching Platform,
including client intake, VA search, matching, and billing operations.

Run with:
    locust -f locustfile.py --host=https://your-domain.com

Or for headless CI:
    locust -f locustfile.py --host=https://your-domain.com --headless -u 100 -r 10 --run-time 5m
"""

from __future__ import annotations

import random
import json
import uuid
from typing import Optional

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


# ========================================
# CONFIGURATION
# ========================================

# Test user credentials (set via environment or use defaults)
TEST_EMAIL = "loadtest@va-matching.dev"
TEST_PASSWORD = "LoadTest123!"

# Common skills for VA search
SKILLS_POOL = [
    "Email Management", "Calendar Management", "Lead Generation", "Customer Support",
    "Social Media Management", "Content Creation", "Project Management", "SOP Creation",
    "Data Entry", "Research", "Appointment Setting", "CRM Management",
    "Travel Coordination", "Expense Tracking", "Canva Design", "Shopify Management",
    "Email Marketing", "Cold Outreach", "Notion/Asana Setup"
]

# Industries for client intake
INDUSTRIES = [
    "technology", "healthcare", "finance", "real_estate", "ecommerce",
    "marketing", "consulting", "other"
]

# Timezones
TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "Europe/London", "Europe/Paris", "Asia/Tokyo", "Asia/Singapore", "Australia/Sydney"
]


# ========================================
# EVENT HOOKS
# ========================================

@events.test_start.add_listener
def on_test_start_handler(environment, **kwargs):
    """Called when test starts."""
    print(f"🚀 Load test started with {environment.runner.target_user_count} users")
    environment.custom_metrics = _custom_metrics.copy()


@events.test_stop.add_listener
def on_test_stop_handler(environment, **kwargs):
    """Called when test stops."""
    print(f"🛑 Load test stopped")
    print(f"📊 Custom metrics: {environment.custom_metrics}")


@events.request.add_listener
def on_request_handler(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests."""
    if response_time > 5000:  # 5 seconds
        print(f"⚠️ Slow request: {request_type} {name} took {response_time}ms")


# ========================================
# BASE USER CLASS
# ========================================

class VAPlatformUser(HttpUser):
    """Base user class with common functionality."""
    
    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks
    
    # Auth state
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.login()
    
    def login(self):
        """Authenticate and store tokens."""
        with self.client.post("/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.user_id = data.get("user", {}).get("user_id")
                
                # Create client profile
                self.create_client()
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    def create_client(self):
        """Create a client profile for this user."""
        intake_data = {
            "email": TEST_EMAIL,
            "company_name": f"LoadTest Corp {uuid.uuid4().hex[:8]}",
            "contact_name": "Load Test User",
            "timezone": random.choice(TIMEZONES),
            "industry": random.choice(INDUSTRIES),
            "company_size": random.randint(5, 100),
            "monthly_budget": random.randint(2000, 10000),
            "needed_hours_per_week": random.randint(10, 40),
            "required_skills": random.sample(SKILLS_POOL, random.randint(3, 6)),
            "tasks_to_delegate": "Email management, calendar scheduling, lead research",
            "current_tools": "Slack, Notion, HubSpot",
            "preferred_timezone_overlap_hours": 4,
            "max_hourly_rate": random.randint(20, 50),
            "source": "load_test"
        }
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        with self.client.post("/api/clients", json=intake_data, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                self.client_id = response.json().get("client_id")
            else:
                response.failure(f"Client creation failed: {response.status_code}")
    
    def auth_headers(self):
        """Return headers with auth token."""
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}


# ========================================
# USER BEHAVIOR CLASSES
# ========================================

class NewClientUser(VAPlatformUser):
    """Simulates a new client going through the full intake and matching flow."""
    
    weight = 30
    
    @task(3)
    def search_vas(self):
        """Search for VAs with random criteria."""
        skills = random.sample(SKILLS_POOL, random.randint(2, 4))
        
        with self.client.post("/api/vas/search", json={
            "skills": skills,
            "limit": 10
        }, headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"VA search failed: {response.status_code}")
    
    @task(2)
    def view_matches(self):
        """View matches for the client."""
        if not self.client_id:
            return
            
        with self.client.get(f"/api/matches/client/{self.client_id}", 
                            headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"View matches failed: {response.status_code}")
    
    @task(1)
    def view_dashboard(self):
        """View dashboard stats."""
        with self.client.get("/api/reports/payments", 
                            headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Dashboard failed: {response.status_code}")
    
    @task(1)
    def search_and_match(self):
        """Full flow: search VAs then create match."""
        if not self.client_id:
            return
            
        # Search for VAs
        skills = random.sample(SKILLS_POOL, random.randint(2, 3))
        
        with self.client.post("/api/vas/search", json={
            "skills": skills,
            "limit": 5
        }, headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"VA search failed: {response.status_code}")
                return
            
            vas = response.json()
            if not vas:
                return
            
            # Create match with first VA
            va = vas[0]
            
            with self.client.post("/api/matches", json={
                "client_id": self.client_id,
                "va_id": va["id"],
                "limit": 1,
                "min_score": 0.0
            }, headers=self.auth_headers(), catch_response=True) as response:
                if response.status_code == 200:
                    matches = response.json()
                    if matches:
                        match_id = matches[0]["match_id"]
                        # Accept the match
                        self.client.post(f"/api/matches/{match_id}/accept",
                                       headers=self.auth_headers())


class ReturningClientUser(VAPlatformUser):
    """Simulates a returning client checking matches and billing."""
    
    weight = 40
    
    @task(4)
    def check_matches(self):
        """Check existing matches."""
        if not self.client_id:
            return
            
        self.client.get(f"/api/matches/client/{self.client_id}", 
                       headers=self.auth_headers())
    
    @task(3)
    def check_notifications(self):
        """Check notifications."""
        self.client.get("/api/notifications", headers=self.auth_headers())
    
    @task(2)
    def view_reports(self):
        """View reports."""
        self.client.get("/api/reports/ledger", headers=self.auth_headers())
        self.client.get("/api/reports/payments", headers=self.auth_headers())
    
    @task(1)
    def check_billing(self):
        """Check billing status."""
        if not self.client_id:
            return
            
        self.client.get(f"/api/billing/placement-fee/{self.client_id}",
                       headers=self.auth_headers())


class VAOnboardingUser(VAPlatformUser):
    """Simulates a VA going through onboarding."""
    
    weight = 20
    
    @task(3)
    def start_onboarding(self):
        """Start onboarding for a match."""
        if not self.client_id:
            return
            
        # Find an accepted match
        with self.client.get(f"/api/matches/client/{self.client_id}",
                            headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                return
            
            matches = response.json()
            accepted = [m for m in matches if m.get("status") == "accepted"]
            if not accepted:
                return
            
            match_id = accepted[0]["match_id"]
            
            self.client.post(f"/api/onboarding/start", json={
                "match_id": match_id
            }, headers=self.auth_headers())
    
    @task(2)
    def check_onboarding_progress(self):
        """Check onboarding progress."""
        if not self.client_id:
            return
            
        with self.client.get(f"/api/matches/client/{self.client_id}",
                            headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                return
            
            matches = response.json()
            onboarding = [m for m in matches if m.get("status") == "onboarding"]
            for match in onboarding:
                self.client.get(f"/api/onboarding/progress/{match['id']}",
                              headers=self.auth_headers())
    
    @task(2)
    def submit_delivery(self):
        """Submit a delivery."""
        if not self.client_id:
            return
            
        with self.client.get(f"/api/matches/client/{self.client_id}",
                            headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                return
            
            matches = response.json()
            for match in matches:
                if match.get("status") in ["onboarding", "active"]:
                    self.client.post("/api/deliveries", json={
                        "match_id": match["id"],
                        "task_id": f"task_{uuid.uuid4().hex[:8]}",
                        "va_id": match.get("va_id", ""),
                        "client_id": self.client_id,
                        "title": f"Task {uuid.uuid4().hex[:6]}",
                        "description": "Load test delivery"
                    }, headers=self.auth_headers())
                    break
    
    @task(1)
    def view_onboarding_progress(self):
        """View onboarding progress page."""
        if not self.client_id:
            return
            
        with self.client.get(f"/api/matches/client/{self.client_id}",
                            headers=self.auth_headers(), catch_response=True) as response:
            if response.status_code != 200:
                return
            
            matches = response.json()
            onboarding = [m for m in matches if m.get("status") == "onboarding"]
            for match in onboarding:
                self.client.get(f"/api/onboarding/progress/{match['id']}",
                              headers=self.auth_headers())


class AdminUser(VAPlatformUser):
    """Simulates admin user checking reports and stats."""
    
    weight = 10
    
    def on_start(self):
        """Admin login."""
        super().on_start()
        # In real scenario, would login as admin
    
    @task(3)
    def view_admin_stats(self):
        """View admin statistics."""
        self.client.get("/admin/stats", headers=self.auth_headers())
    
    @task(2)
    def view_ledger(self):
        """View ledger report."""
        self.client.get("/api/reports/ledger", headers=self.auth_headers())
    
    @task(2)
    def view_payment_stats(self):
        """View payment statistics."""
        self.client.get("/api/reports/payments", headers=self.auth_headers())
    
    @task(1)
    def check_health(self):
        """Health check."""
        self.client.get("/health")


class AnonymousUser(HttpUser):
    """Simulates anonymous visitors browsing public pages."""
    
    weight = 5
    wait_time = between(5, 15)
    
    @task(5)
    def view_homepage(self):
        """View homepage."""
        self.client.get("/")
    
    @task(3)
    def view_intake_form(self):
        """View intake form page."""
        self.client.get("/intake")
    
    @task(2)
    def view_dashboard_page(self):
        """View dashboard page (will redirect to login)."""
        self.client.get("/dashboard")
    
    @task(1)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/health")


# ========================================
# CUSTOM SHAPES FOR LOAD TESTING
# ========================================

class StepLoadShape:
    """Gradually increase load in steps."""
    
    def __init__(self):
        self.step_time = 60  # seconds per step
        self.step_users = 10  # users per step
        self.max_users = 100
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > self.step_time * 10:  # 10 steps
            return None
        
        current_step = int(run_time // self.step_time) + 1
        user_count = min(current_step * self.step_users, self.max_users)
        
        return (user_count, self.step_users)

    def get_run_time(self):
        """Get current run time in seconds."""
        import time
        return time.time() - getattr(self, '_start_time', time.time())


class SpikeLoadShape:
    """Sudden spike in traffic."""
    
    def __init__(self):
        self.spike_duration = 30  # seconds
        self.normal_users = 20
        self.spike_users = 100
    
    def tick(self):
        run_time = self.get_run_time()
        
        # Normal load for first 2 minutes
        if run_time < 120:
            return (self.normal_users, self.normal_users)
        
        # Spike for 30 seconds
        if run_time < 150:
            return (self.spike_users, self.spike_users)
        
        # Back to normal
        if run_time < 270:
            return (self.normal_users, self.normal_users)
        
        # End test
        return None

    def get_run_time(self):
        """Get current run time in seconds."""
        import time
        return time.time() - getattr(self, '_start_time', time.time())


# Custom metrics storage
_custom_metrics = {
    "login_success": 0,
    "login_failure": 0,
    "client_created": 0,
    "va_searches": 0,
    "matches_created": 0,
    "payments_processed": 0,
    "onboarding_started": 0,
    "deliveries_submitted": 0
}

@events.test_start.add_listener
def on_test_start_handler(environment, **kwargs):
    """Initialize custom metrics."""
    environment.custom_metrics = _custom_metrics.copy()


# Request-specific metric tracking
@events.request.add_listener
def track_custom_metrics(request_type, name, response_time, response_length, exception, **kwargs):
    """Track business-relevant metrics."""
    global _custom_metrics
    
    if exception:
        return
    
    # Track specific endpoints
    if name == "/api/auth/login" and request_type == "POST":
        _custom_metrics["login_success"] = _custom_metrics.get("login_success", 0) + 1
    elif name == "/api/clients" and request_type == "POST":
        _custom_metrics["client_created"] = _custom_metrics.get("client_created", 0) + 1
    elif name == "/api/vas/search" and request_type == "POST":
        _custom_metrics["va_searches"] = _custom_metrics.get("va_searches", 0) + 1
    elif name == "/api/matches" and request_type == "POST":
        _custom_metrics["matches_created"] = _custom_metrics.get("matches_created", 0) + 1
    elif "placement-fee" in name and request_type == "POST":
        _custom_metrics["payments_processed"] = _custom_metrics.get("payments_processed", 0) + 1
    elif "/onboarding/start" in name and request_type == "POST":
        _custom_metrics["onboarding_started"] = _custom_metrics.get("onboarding_started", 0) + 1
    elif "/deliveries" in name and request_type == "POST":
        _custom_metrics["deliveries_submitted"] = _custom_metrics.get("deliveries_submitted", 0) + 1


# ========================================
# RUNNER CONFIGURATION
# ========================================

if __name__ == "__main__":
    # This allows running the file directly for debugging
    import sys
    import os
    
    os.environ.setdefault("LOCUST_MODE", "standalone")
    
    # Run with: python -m locust -f locustfile.py
    pass