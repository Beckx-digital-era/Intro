import requests
import sys

# URL of the Flask application
base_url = "http://localhost:5000"

# Test the login page
try:
    # Check if login page is accessible
    login_response = requests.get(f"{base_url}/login")
    print(f"Login page status code: {login_response.status_code}")
    
    if login_response.status_code == 200:
        print("Login page is accessible")
        
        # Attempt to login with admin credentials
        login_data = {
            "username": "admin",
            "password": "Meeki"
        }
        
        # Create a session to handle cookies
        session = requests.Session()
        
        # Post login data
        login_post = session.post(f"{base_url}/login", data=login_data)
        print(f"Login attempt status code: {login_post.status_code}")
        
        # Check if we got redirected (successful login)
        if login_post.history:
            print(f"Redirected to: {login_post.url}")
            
            # Try to access the index page (should be accessible after login)
            index_response = session.get(f"{base_url}/")
            print(f"Index page status code: {index_response.status_code}")
            
            if index_response.status_code == 200:
                print("Successfully logged in and accessed the index page!")
                sys.exit(0)
            else:
                print("Failed to access index page after login")
                sys.exit(1)
        else:
            print("Login failed - no redirection occurred")
            sys.exit(1)
    else:
        print("Could not access login page")
        sys.exit(1)
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)