"""Load testing with Locust."""

from locust import HttpUser, task, between


class TaxiPassengerUser(HttpUser):
    """Simulate passenger API usage."""

    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Setup auth token before tests."""
        # In real usage, get a valid Clerk JWT here
        self.headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}

    @task(3)
    def list_rides(self):
        """List own rides."""
        self.client.get('/api/v1/rides/', headers=self.headers)

    @task(2)
    def get_notifications(self):
        """Get notifications."""
        self.client.get('/api/v1/notifications/', headers=self.headers)

    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get('/api/v1/health/')