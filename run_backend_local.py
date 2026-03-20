import os
import sys
import subprocess

# Set environment variables for local run without Docker
os.environ['POSTGRES_SERVER'] = 'localhost'
os.environ['REDIS_ENABLED'] = 'false'
# Use SQLite for discovery to bypass Postgres connection issues
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./discovery.db'

if __name__ == "__main__":
    print("Starting backend for local discovery...")
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "5001", "--reload"], check=True)
    except KeyboardInterrupt:
        print("\nStopping backend...")
    except Exception as e:
        print(f"Failed to start backend: {e}")
