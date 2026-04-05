from prance import ResolvingParser
import sys

url = "https://catfact.ninja/openapi.json"
try:
    parser = ResolvingParser(url)
    print("Success")
except Exception as e:
    print(f"Caught exception: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
