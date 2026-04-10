import datetime

def send_email(to_address: str, subject: str, body: str):
    """
    Mock Email sending service.
    This logs the email payload to the console, acting as a placeholder
    until real SMTP/SendGrid API keys are configured.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] 📧 MOCK EMAIL NOTIFICATION")
    print(f"To:      {to_address}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print("-" * 50 + "\n")


def send_sms(phone_number: str, message: str):
    """
    Mock SMS sending service.
    This logs the SMS payload to the console, acting as a placeholder
    until real SMS Gateway (e.g., Twilio) API keys are configured.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] 📱 MOCK SMS NOTIFICATION")
    print(f"To:      +91 {phone_number}")
    print(f"Message: {message}")
    print("-" * 50 + "\n")
