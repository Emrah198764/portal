import uuid
from datetime import datetime, timedelta

# -----------------------------
# MOCK DATABASE (In-Memory)
# -----------------------------
mock_db = {}

# -----------------------------
# UTILITIES
# -----------------------------
def now():
    return datetime.now()

def generate_token():
    return str(uuid.uuid4())

def print_divider():
    print("\n" + "=" * 50)

# -----------------------------
# MOCK EMAIL SENDER (NO NETWORK)
# -----------------------------
def mock_sendmail(email, subject, message):
    print_divider()
    print("📧 MOCK EMAIL SENT")
    print(f"To      : {email}")
    print(f"Subject : {subject}")
    print(f"Message : {message}")
    print_divider()
    return True

# -----------------------------
# SIGNUP FUNCTION
# -----------------------------
def start_signup(full_name, email):
    print_divider()
    print("🚀 START SIGNUP")

    if not full_name or not email:
        print("❌ Validation Failed")
        return {"success": False, "message": "Full name & email required"}

    email = email.strip().lower()
    full_name = full_name.strip()

    existing = mock_db.get(email)

    # -------------------------
    # Already Verified
    # -------------------------
    if existing and existing["status"] == "Verified":
        print("⚠ Email Already Verified")
        return {"success": False, "message": "Email already verified"}

    # -------------------------
    # Token Still Valid → Reuse
    # -------------------------
    if existing and existing["token_expiry"] > now():
        print("♻ Reusing Existing Token")

        verify_url = f"http://mock.local/verify?token={existing['token']}"

        mock_sendmail(
            email=email,
            subject="Email Verification",
            message=f"Reuse Link → {verify_url}"
        )

        return {
            "success": True,
            "message": "Verification email already sent"
        }

    # -------------------------
    # New Token
    # -------------------------
    token = generate_token()
    expiry = now() + timedelta(hours=1)

    mock_db[email] = {
        "full_name": full_name,
        "token": token,
        "token_expiry": expiry,
        "status": "Email Sent"
    }

    verify_url = f"http://mock.local/verify?token={token}"

    print("✅ New Token Generated")
    print(f"Token  : {token}")
    print(f"Expiry : {expiry}")

    mock_sendmail(
        email=email,
        subject="Email Verification",
        message=f"New Link → {verify_url}"
    )

    return {
        "success": True,
        "message": "Verification email sent"
    }

# -----------------------------
# VERIFY FUNCTION
# -----------------------------
def verify_token(token):
    print_divider()
    print("🔍 VERIFY TOKEN")

    if not token:
        print("❌ Token Missing")
        return {"success": False, "message": "Token missing"}

    for email, record in mock_db.items():

        if record["token"] == token:

            # ---------------------
            # Expired
            # ---------------------
            if record["token_expiry"] < now():
                print("⏰ Token Expired")
                record["status"] = "Expired"
                return {"success": False, "message": "Token expired"}

            # ---------------------
            # Already Verified
            # ---------------------
            if record["status"] == "Verified":
                print("⚠ Already Verified")
                return {"success": True, "message": "Already verified"}

            # ---------------------
            # Verify Success
            # ---------------------
            record["status"] = "Verified"
            record["token"] = None
            record["token_expiry"] = None

            print("✅ Verification Successful")
            print(f"User : {record['full_name']}")
            print(f"Mail : {email}")

            return {"success": True, "message": "Email verified"}

    print("❌ Invalid Token")
    return {"success": False, "message": "Invalid token"}

# -----------------------------
# TEST FLOW (AUTO RUN)
# -----------------------------
if __name__ == "__main__":

    print("\n🎯 MOCK SIGNUP SYSTEM TEST")

    # 1️⃣ First Signup
    response = start_signup("Emrah Turk", "test@mail.com")
    print(response)

    # 2️⃣ Try Signup Again (Reuse Token)
    response = start_signup("Emrah Turk", "test@mail.com")
    print(response)

    # 3️⃣ Grab Token
    token = mock_db["test@mail.com"]["token"]

    # 4️⃣ Verify Token
    response = verify_token(token)
    print(response)

    # 5️⃣ Verify Again (Already Verified)
    response = verify_token(token)
    print(response)

    print_divider()
    print("✅ TEST COMPLETED")