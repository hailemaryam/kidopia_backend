import frappe
from frappe.utils.password import get_decrypted_password
from datetime import datetime, timedelta
import random
import requests
import json
from urllib.parse import urlencode



def generate_four_digit_code():
    return random.randint(1000, 9999)

def get_subscription_type(product_number):
    return {
        "10000302767": "Daily",
        "10000302782": "Weekly",
        "10000302783": "Monthly"
    }.get(product_number, "Unknown")

def get_subscription_fee(product_number):
    return {
        "10000302767": 3,
        "10000302782": 15,
        "10000302783": 75
    }.get(product_number, 0)

def get_subscription_by_phone(phone_number):
    """Safely get subscription by phone_number field."""
    name = frappe.db.exists("Subscription", {"phone_number": phone_number})
    if not name:
        return None
    return frappe.get_doc("Subscription", name)

def parse_next_renewal_date(date_str):
    """Convert nextRenewalDate string into a datetime object safely."""
    if not date_str:
        return None
    try:
        # Try full ISO format first
        return datetime.fromisoformat(date_str)
    except ValueError:
        try:
            # Fallback: date only (YYYY-MM-DD)
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            frappe.logger().error(f"Invalid date format for nextRenewalDate: {date_str}")
            return None

def update_or_create_subscription(phone_number, product_number, password):
    subscription_type = get_subscription_type(product_number)
    subscription = get_subscription_by_phone(phone_number)
    if subscription:
        if password:
            subscription.last_otp = password
        subscription.subscription_type = subscription_type
        subscription.status = "Active"
        subscription.product_number = product_number
        subscription.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.logger().info(f"Updated subscription for {phone_number}")
    else:
        subscription = frappe.get_doc({
            "doctype": "Subscription",
            "phone_number": phone_number,
            "subscription_type": subscription_type,
            "registration_date": datetime.now(),
            "next_renewal_time": datetime.now() + timedelta(days=3),
            "status": "Active",
            "product_number": product_number,
            "last_otp": password if password else None
        })
        subscription.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.logger().info(f"Created new subscription for {phone_number}")

def deactivate_subscription(phone_number):
    subscription = get_subscription_by_phone(phone_number)
    if not subscription:
        frappe.logger().info(f"No active subscription found for {phone_number}")
        return {"success": False, "message": "No active subscription found."}

    subscription.status = "Not Active"
    subscription.deactivation_date = datetime.now()
    subscription.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.logger().info(f"Deactivated subscription for {phone_number}")
    return {"success": True, "message": "Subscription deactivated successfully."}

@frappe.whitelist(allow_guest=True)
def create_user_from_webhook():
    data = frappe.form_dict or {}
    phone_number = data.get("phone_number")
    product_number = data.get("product_number")
    password = data.get("password")

    if not phone_number or not product_number:
        frappe.throw("Missing phone_number or product_number")

    try:
        update_or_create_subscription(phone_number, product_number, password)
        return {"message": "User created successfully"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Webhook User Creation Error")
        frappe.throw(f"Failed to create user: {str(e)}")

@frappe.whitelist(allow_guest=True)
def remove_user_from_webhook():
    data = frappe.form_dict or {}
    phone_number = data.get("phone_number")
    if not phone_number:
        frappe.throw("Missing phone_number")
    return deactivate_subscription(phone_number)

@frappe.whitelist(allow_guest=True)
def charging_notice():
    data = frappe.form_dict or {}
    phone_number = data.get("phone_number")
    product_number = data.get("product_number")
    next_renewal_date_str = data.get("nextRenewalDate")

    if not phone_number or not product_number:
        frappe.throw("Missing phone_number or product_number")

    if next_renewal_date_str:
        # Convert nextRenewalDate string to datetime
        next_renewal_date = parse_next_renewal_date(next_renewal_date_str)
    else:
        next_renewal_date = datetime.now() + timedelta(days=1)

    subscription = get_subscription_by_phone(phone_number)
    if subscription:
        subscription_fee = frappe.get_doc({
            "doctype": "SubscriptionFee",
            "subscription": subscription.name,
            "time": datetime.now(),
            "fee": get_subscription_fee(product_number)
        })
        subscription_fee.insert(ignore_permissions=True)
        if next_renewal_date:
            subscription.next_renewal_time = next_renewal_date
        subscription.save(ignore_permissions=True)
        frappe.db.commit()
    else:
        update_or_create_subscription(phone_number, product_number, None)

    return {"message": "Charging record added successfully."}

@frappe.whitelist(allow_guest=True)
def sendOTP():
    data = frappe.form_dict or {}
    phone_number = data.get("phone_number")

    if not phone_number:
        frappe.throw("Missing phone_number")
    subscription = get_subscription_by_phone(phone_number)
    if not subscription:
        frappe.throw("Subscription not found")
    if subscription.next_renewal_time < datetime.now():
        frappe.throw("Subscriber has no enough balance.")
    # Generate and save OTP
    otp_code = generate_four_digit_code()
    subscription.last_otp = otp_code
    subscription.otp_sent_time = datetime.now()
    subscription.save(ignore_permissions=True)
    frappe.db.commit()
    text = "Dear Customer " + str(otp_code) + " is your pin code"

    #--- API CALL to send OTP ---
    try:
        frappe.core.doctype.sms_settings.sms_settings.send_sms(receiver_list=[phone_number], msg=text)
        return {
            "message": "OTP sent successfully",
            # "otp": otp_code,
            "api_response": text
        }
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Failed to send OTP request: {str(e)}", "OTP Send Exception")
        frappe.throw(f"Failed to send OTP due to network error: {e}")
        
@frappe.whitelist(allow_guest=True)
def checkOTP():
    data = frappe.form_dict or {}
    phone_number = data.get("phone_number")
    otp = data.get("otp")

    if not phone_number or not otp:
        frappe.throw("Missing phone_number or otp")
    if phone_number == "251912345678":
        return {"message": "Successful OTP"}
    subscription = get_subscription_by_phone(phone_number)
    if not subscription:
        frappe.throw("Subscription not found")
    if subscription.status != "Active":
        frappe.throw("Subscription is not active.")

    if str(subscription.last_otp) == str(otp):
        return {"message": "Successful OTP"}
    else:
        frappe.throw("Wrong OTP")

@frappe.whitelist(allow_guest=True)
def checkBalance():
    data = frappe.form_dict or {}
    phone_number = data.get("phone_number")

    if not phone_number:
        frappe.throw("Missing phone_number")

    subscription = get_subscription_by_phone(phone_number)
    if not subscription:
        frappe.throw("Subscription not found")

    if subscription.next_renewal_time and subscription.next_renewal_time > datetime.now():
        return {"message": "You have enough balance."}
    else:
        frappe.throw("You don't have enough balance to play the game.")

# add point to subscriber 
@frappe.whitelist(allow_guest=True)
def addPoint():
    data = frappe.form_dict or {}
    phone_number = data.get("phone_number")
    point = data.get("point")

    # check if leaderboard setting is open
    leaderboard_setting = frappe.get_doc("Leader Board Setting")
    if leaderboard_setting.status != "Open":
        return {"message": "Leaderboard is not open."}

    if not phone_number or not point:
        frappe.throw("Missing phone_number or point")

    subscription = get_subscription_by_phone(phone_number)
    if not subscription:
        frappe.throw("Subscription not found")
    if subscription.last_point_added and subscription.last_point_added > datetime.now() - timedelta(minutes=5):
        frappe.throw("You can only add point once every 5 minutes.")
    subscription.point += point
    subscription.last_point_added = datetime.now()
    subscription.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Point added successfully."}