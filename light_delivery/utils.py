import frappe
from frappe import _
import jwt


def validate_token():
    # Get the Authorization header
    auth_header = frappe.local.request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("token: "):
        frappe.throw(_("Missing or invalid token"), frappe.AuthenticationError)
    
    # Extract the token from the Authorization header
    token = auth_header.split("token ")[-1]
    
    if not token:
        frappe.throw(_("Missing token"), frappe.AuthenticationError)
    
    try:
        # Replace 'your_secret_key' with your actual secret key
        decoded_token = jwt.decode(token, 'your_secret_key', algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        frappe.throw(_("Token has expired"), frappe.AuthenticationError)
    except jwt.InvalidTokenError as e:
        frappe.throw(_("Invalid token: {0}").format(str(e)), frappe.AuthenticationError)
    
    user = decoded_token.get("user")
    
    if not user:
        frappe.throw(_("Invalid token"), frappe.AuthenticationError)
    
    # Ensure user is active
    user_doc = frappe.get_doc("User", user)
    if not user_doc.enabled:
        frappe.throw(_("User is disabled"), frappe.AuthenticationError)
    
    # Set the user for the current request
    frappe.set_user(user)

