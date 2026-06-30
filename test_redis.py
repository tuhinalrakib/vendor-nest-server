import os
import sys

# Try to import redis
try:
    import redis
except ImportError:
    print("Error: 'redis' package is not installed. Please run: pip install redis")
    sys.exit(1)

# Get REDIS_URL from .env
env_path = ".env"
redis_url = None

if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("REDIS_URL="):
                redis_url = line.split("=", 1)[1].strip()
                # Remove quotes if present
                if redis_url.startswith(('"', "'")) and redis_url.endswith(('"', "'")):
                    redis_url = redis_url[1:-1]
                break

if not redis_url:
    print("Error: REDIS_URL not found in .env file.")
    sys.exit(1)

print(f"Testing connection to: {redis_url}")

try:
    # Set a socket timeout of 5 seconds
    client = redis.from_url(redis_url, socket_timeout=5.0)
    print("Sending PING...")
    response = client.ping()
    print(f"Ping successful! Connection status: OK. Response: {response}")
except redis.exceptions.AuthenticationError as auth_err:
    print("\n[RESULT] Authentication Failed!")
    print("Your Redis URL credentials (username/password) are incorrect.")
    print(f"Details: {auth_err}")
except redis.exceptions.TimeoutError as timeout_err:
    print("\n[RESULT] Connection Timed Out!")
    print("Possible reasons:")
    print("1. Your Redis Labs database is paused/suspended (check your Redis Labs console).")
    print("2. Your ISP, router, or corporate firewall is blocking outbound connections on port 19010.")
    print(f"Details: {timeout_err}")
except redis.exceptions.ConnectionError as conn_err:
    print("\n[RESULT] Connection Error!")
    print("Cannot reach the host. Please check your internet connection or the hostname.")
    print(f"Details: {conn_err}")
except Exception as e:
    print(f"\n[RESULT] Failed with unexpected error: {e}")
