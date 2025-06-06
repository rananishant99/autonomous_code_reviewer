# authentication/constants.py

class Authentication:
    SIGNUP = {
        'CREATED': "User created successfully."
    }
    
    LOGIN = {
        'LOGIN': "User logged in successfully.",
        'NOT_FOUND': "User not found."
    }

    USER = {
        'EMAIL_EXISTS': "This email is already registered.",
        'NOT_FOUND': "User not found."
    }

    GITHUB = {
        "CREATED": "GitHub token saved successfully.",
        "UPDATED": "GitHub token updated successfully."
    }
