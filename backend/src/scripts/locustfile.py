from __future__ import annotations

import random
from locust import HttpUser, task, between

class CareerPilotUser(HttpUser):
    """
    Locust User class to simulate concurrent user paths (F6.4).
    Simulates logging in, calling dashboard stats, matching opportunities, and reading health metrics.
    """
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """
        Runs on user startup: registers and logs in a unique load test user.
        """
        email = f"load_test_{random.randint(100000, 999999)}@example.com"
        password = "TestPassword123!"
        
        try:
            # 1. Register
            reg_resp = self.client.post("/api/v2/auth/register", json={"email": email, "password": password})
            if reg_resp.status_code in [200, 201]:
                # 2. Login
                login_resp = self.client.post("/api/v2/auth/login", json={"email": email, "password": password})
                if login_resp.status_code == 200:
                    self.token = login_resp.json().get("access_token")
        except Exception:
            pass

    @task(3)
    def view_dashboard(self):
        """Simulates viewing the career dashboard."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.client.get("/api/v2/dashboard", headers=headers)

    @task(2)
    def match_opportunities(self):
        """Simulates retrieving opportunity ranking calculations."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.client.get("/api/v2/market/opportunities", headers=headers)

    @task(1)
    def check_health(self):
        """Simulates checking system health endpoints."""
        self.client.get("/api/v2/health")
