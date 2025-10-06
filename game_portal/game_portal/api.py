import frappe
from frappe.utils.password import get_decrypted_password

@frappe.whitelist(allow_guest=True)
def create_user_from_webhook():
    # Retrieve the JSON data from the webhook request
    data = frappe.form_dict
    
    # Extract the necessary user data (e.g., phone_number, password, full_name)
    phone_number = data.get('phone_number')
    password = data.get('password')
    full_name = data.get('phone_number')

    # Frappe requires a unique email, so you'll need to generate one
    # A common pattern is to use the phone number as part of the email
    email = f"{phone_number}@yourdomain.com"
    
    # Check if the user already exists to prevent duplicates
    if frappe.db.exists("User", email):
        frappe.throw(f"User with email {email} already exists.", frappe.DuplicateEntryError)

    try:
        # Create a new User document
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": phone_number, # or use a separate first and last name field
            "send_welcome_email": 0, # Don't send a welcome email to the user
            "new_password": password,
            "user_type": "Website User", # Important for website-only access
            "enabled": 1,
            # Add the phone number to the user's document
            "phone_number": phone_number 
        })
        
        # Save the new document to the database
        user.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"message": "User created successfully"}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Webhook User Creation Error")
        frappe.throw(f"Failed to create user: {str(e)}")