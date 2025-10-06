import frappe
import zipfile
import os

def extract_game_file(doc, method=None):
    if doc.game_file_zip:
        # Get the absolute path to the uploaded zip file
        zip_file_path = frappe.get_site_path(doc.game_file_zip.lstrip('/'))

        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Find the top-level folder in the zip (first part of the first file path)
            first_member = zip_ref.namelist()[0]
            folder_name = first_member.split('/')[0] if '/' in first_member else frappe.utils.cstr(doc.name)

            # Define the target directory using folder_name
            target_dir = os.path.join(frappe.get_site_path('public', 'files', 'games'), folder_name)

            # Ensure the target directory exists
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            # Extract all contents
            zip_ref.extractall(os.path.join(frappe.get_site_path('public', 'files', 'games')))

        # Update the 'location' field with the public URL (avoid recursion!)
        doc.db_set("location", f"/files/games/{folder_name}/index.html")
        