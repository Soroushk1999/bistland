import random
from locust import HttpUser, task, between


class SubmitUser(HttpUser):
    # Wait time between two consecutive requests for each simulated user
    wait_time = between(0.5, 2.0)

    @task
    def submit_phone_number(self):
        # Generate random Iranian phone number in +989XXXXXXXXX format
        random_number = random.randint(100000000, 999999999)
        phone_number = f"+989{random_number}"

        payload = {
            "phone": phone_number
        }

        # Send POST request to your endpoint
        with self.client.post("/api/submit", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code} and body {response.text}")
