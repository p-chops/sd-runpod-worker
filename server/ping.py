import sys
import os
import urllib.request
import urllib.error
import json

def ping_endpoint(endpoint_id, api_key):
    """Constructs the URL, adds auth, and pings the /ping endpoint."""
    
    # Construct the URL from the endpoint ID
    url = f"https://{endpoint_id}.api.runpod.ai/ping"
    
    print(f"Attempting to ping: {url}\n")
    
    # Create the headers
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        # Create a Request object that includes the URL and headers
        request = urllib.request.Request(url, headers=headers, method="GET")
        
        # Make the request with a 10-second timeout
        with urllib.request.urlopen(request, timeout=600) as response:
            
            # Read and decode the response body
            body = response.read().decode('utf-8')
            
            print(f"Status Code: {response.status}")
            print(f"Response: {body}")
            
            # Try to parse the JSON for a clear "healthy" message
            try:
                data = json.loads(body)
                if response.status == 200 and data.get("status") == "healthy":
                    print("\nResult: Endpoint is healthy! ✅")
                else:
                    print("\nResult: Endpoint responded, but not as expected.")
            except json.JSONDecodeError:
                print("\nResult: Received a non-JSON response.")

    except urllib.error.HTTPError as e:
        # Handle HTTP errors (e.g., 401 Unauthorized, 404, 503)
        print(f"Error: Server returned status code {e.code}")
        print(f"Reason: {e.reason}")
    except urllib.error.URLError as e:
        # Handle network/connection errors
        print(f"Error: Failed to reach the server.")
        print(f"Reason: {e.reason}")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # 1. Check for the API key in environment variables
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        print("Error: RUNPOD_API_KEY environment variable not set.")
        sys.exit(1)
        
    # 2. Check for the endpoint ID as a command-line argument
    if len(sys.argv) != 2:
        print("Usage: python ping_runpod.py <your-endpoint-id>")
        sys.exit(1)
        
    endpoint_id = sys.argv[1]
    
    # 3. Run the ping
    ping_endpoint(endpoint_id, api_key)