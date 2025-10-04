import frappe
import zipfile
import os

def extract_game_file(doc, method=None):
    if doc.game_file_zip:
        # Get the absolute path to the uploaded zip file
        zip_file_path = frappe.get_site_path(doc.game_file_zip.lstrip('/'))
        
        # Define the target directory for extraction
        # We'll use the document name to create a unique folder for each game
        game_folder_name = frappe.utils.cstr(doc.name)
        target_dir = os.path.join(frappe.get_site_path('public', 'files', 'games'), game_folder_name)
        
        # Ensure the target directory exists
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Extract the contents of the zip file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)

        # Update the 'location' field with the public URL
        # We assume the main game file is named 'index.html'
        doc.location = f"/files/games/{game_folder_name}/index.html"
        doc.save()