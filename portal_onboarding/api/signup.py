
import frappe
import uuid
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, get_url, now_datetime, validate_email_address


def _get_verify_base_url():
    portal_base_url = frappe.conf.get("portal_base_url")
    return portal_base_url.rstrip("/") if portal_base_url else get_url()


@frappe.whitelist(allow_guest=True)
@rate_limit(key="email", limit=5, seconds=60)
def start_signup(full_name: str, email: str):
    logger = frappe.logger("portal_signup")
    logger.info("START_SIGNUP | ENTRY")

    # 1️⃣ VALIDATION
    if not full_name or not email:
        frappe.throw("Full name and email are required")

    clean_full_name = full_name.strip()
    email = email.strip().lower()
    if not validate_email_address(email, throw=False):
        frappe.throw("Invalid email address")
    now = now_datetime()

    # 2️⃣ EXISTING CHECK
    existing = frappe.db.get_value(
        "Portal Signup Request",
        {"email": email},
        [
            "name",
            "status",
            "verification_token",
            "token_expiry",
            "full_name",
        ],
        as_dict=True
    )

    if existing:
        logger.info(
            "START_SIGNUP | EXISTING: name=%s status=%s token=*** expiry=%s",
            existing.name,
            existing.status,
            existing.token_expiry,
        )
    else:
        logger.info("START_SIGNUP | EXISTING: None")

    # 3️⃣ ALREADY VERIFIED
    if existing and existing.status == "Verified":
        logger.warning("START_SIGNUP | EMAIL ALREADY VERIFIED")
        frappe.throw(
            "This email address has already been verified. Please sign in."
        )

    # 4️⃣ TOKEN STILL VALID → REUSE
    if (
        existing
        and existing.verification_token
        and existing.token_expiry
        and existing.token_expiry > now
    ):
        logger.info("START_SIGNUP | REUSING EXISTING TOKEN")

        verify_url = f"{_get_verify_base_url()}/verify?token={existing.verification_token}"

        display_name = existing.full_name or clean_full_name
        try:
            frappe.sendmail(
                recipients=[email],
                subject="Email Verification",
                message=f"""
                    Hello {display_name},<br><br>
                    Your previously sent verification link is still valid:<br><br>
                    <a href="{verify_url}">Verify My Email</a><br><br>
                    This link is valid until it expires.
                """
            )
        except Exception:
            doc = frappe.get_doc("Portal Signup Request", existing.name)
            doc.status = "Email Failed"
            doc.save(ignore_permissions=True)
            logger.exception("START_SIGNUP | REUSE TOKEN EMAIL FAILED")
            frappe.throw("Verification email could not be sent. Please try again.")

        return {
            "success": True,
            "message": (
                "A verification email has already been sent. "
                "Please check your inbox (including Spam)."
            )
        }

    # 5️⃣ NEW TOKEN (CREATE OR UPDATE EXISTING)
    token = str(uuid.uuid4())
    expiry = add_to_date(now, hours=1)

    logger.info(f"START_SIGNUP | NEW TOKEN GENERATED | EXPIRY={expiry}")

    if existing:
        doc = frappe.get_doc("Portal Signup Request", existing.name)
        doc.full_name = clean_full_name
        doc.verification_token = token
        doc.token_expiry = expiry
        doc.is_verified = 0
        doc.status = "Email Sent"
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Portal Signup Request",
            "full_name": clean_full_name,
            "email": email,
            "verification_token": token,
            "token_expiry": expiry,
            "is_verified": 0,
            "status": "Email Sent"
        })

        doc.insert(ignore_permissions=True)

    verify_url = f"{_get_verify_base_url()}/verify?token={token}"

    try:
        frappe.sendmail(
            recipients=[email],
            subject="Email Verification",
            message=f"""
                Hello {clean_full_name},<br><br>
                To continue your registration, click the link below:<br><br>
                <a href="{verify_url}">Verify My Email</a><br><br>
                This link is valid for 1 hour.
            """
        )
    except Exception:
        doc.status = "Email Failed"
        doc.save(ignore_permissions=True)
        logger.exception("START_SIGNUP | EMAIL SEND FAILED")
        frappe.throw("Verification email could not be sent. Please try again.")

    logger.info("START_SIGNUP | EMAIL SENT")

    return {
        "success": True,
        "message": "Verification email sent. Please check your email."
    }





@frappe.whitelist(allow_guest=True)
@rate_limit(key="token", limit=10, seconds=60)
def verify_token(token: str):
    logger = frappe.logger("portal_signup")
    logger.info("VERIFY_TOKEN | ENTRY")

    if not token:
        frappe.throw("Token not found")

    signup_name = frappe.db.get_value(
        "Portal Signup Request",
        {"verification_token": token},
        "name"
    )

    if not signup_name:
        logger.warning("VERIFY_TOKEN | INVALID TOKEN")
        frappe.throw("Invalid verification link")

    doc = frappe.get_doc("Portal Signup Request", signup_name)

    # ⏰ EXPIRY CHECK
    if doc.token_expiry and doc.token_expiry < now_datetime():
        logger.warning("VERIFY_TOKEN | TOKEN EXPIRED")
        doc.status = "Expired"
        doc.save(ignore_permissions=True)
        frappe.throw("Verification link has expired")

    # ✅ ALREADY VERIFIED
    if doc.status == "Verified":
        logger.info("VERIFY_TOKEN | ALREADY VERIFIED")
        return {
            "success": True,
            "message": "Email already verified"
        }

    # ✅ VERIFY
    doc.is_verified = 1
    doc.status = "Verified"
    doc.verification_token = None
    doc.token_expiry = None
    doc.save(ignore_permissions=True)

    logger.info("VERIFY_TOKEN | SUCCESS")

    return {
        "success": True,
        "message": "Email verified successfully"
    }