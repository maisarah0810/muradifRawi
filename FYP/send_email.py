from mailjet_rest import Client
import os

API_KEY = '2889beeb8413007e0146f4d1a3dee5f7'
API_SECRET = '588088681208fb358b7832e7ec18a8d7'

mailjet = Client(auth=(API_KEY, API_SECRET), version='v3.1')

def send_password_email(to_email, password,fullname):
    # Get the base URL from environment variable or default to localhost
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    reset_link = f"{base_url}/reset-password?email={to_email}"

    data = {
        'Messages': [
            {
                "From": {
                    "Email": "sarahmai856@gmail.com",
                    "Name": "muradifRawi"
                },
                "To": [
                    {
                        "Email": to_email,
                        "Name": fullname
                    }
                ],
                "Subject": "Set Your Password",
                "TextPart": f"Hi {fullname},\n\nYour account has been created.\nTemporary password: {password}",
                "HTMLPart": f"""
                    <h3>Hello {fullname},</h3>
                    <p>Your account has been created. Please use the temporary password below to log in:</p>
                    <p><strong>{password}</strong></p>
                    <p> Link to open muradifRawi : {base_url}</p>
                    <p>Recommended to change password</p>
                
                """
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)
    print(result.json())
