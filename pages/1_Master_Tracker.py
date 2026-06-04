import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import base64
import gspread
import json
import jinja2
import re
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaFileUpload

# --- CONFIG & AUTH ---
st.set_page_config(page_title="Master Tracker", page_icon="📦", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ipB1DaIdX_BS_0iSWRHMwHcP-wEpfu2pZzFT3nJtlho/edit?gid=0#gid=0"

def get_creds():
    return Credentials.from_service_account_info(
        json.loads(st.secrets["google_api"]["credentials"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )

def get_drive_service():
    return build('drive', 'v3', credentials=get_creds())

def get_gspread_client():
    return gspread.authorize(get_creds())

# --- ROUTING ENGINE ---
def upload_to_drive(file_path, file_name, client_name, invoice_no):
    drive = get_drive_service()
    
    # 1. Find or create Client Folder
    folders = drive.files().list(q=f"name='{client_name}' and mimeType='application/vnd.google-apps.folder'", fields="files(id, name)").execute().get('files', [])
    client_folder_id = folders[0]['id'] if folders else drive.files().create(body={"name": client_name, "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
    
    # 2. Find or create Invoice Folder
    inv_folders = drive.files().list(q=f"name='{invoice_no}' and '{client_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'", fields="files(id, name)").execute().get('files', [])
    inv_folder_id = inv_folders[0]['id'] if inv_folders else drive.files().create(body={"name": invoice_no, "parents": [client_folder_id], "mimeType": "application/vnd.google-apps.folder"}).execute()['id']
    
    # 3. Upload File
    file_metadata = {'name': file_name, 'parents': [inv_folder_id]}
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    file = drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- LOGIC UPDATES ---
# The save_log_data function now integrates these links into the 17-column format
def save_log_data(df):
    gc = get_gspread_client()
    ws = gc.open_by_url(SHEET_URL).sheet1
    ws.clear()
    ws.update([df.fillna("").columns.values.tolist()] + df.fillna("").values.tolist())

# --- REMAINING FUNCTIONS (HTML Factory, UI, etc.) ---
# [Keep your existing generate_html_document, etc. as they were, 
# ensuring they call upload_to_drive upon "Compile" clicks]

# --- COMMIT LOGIC ---
# Ensure your "Commit" button maps the full 17-column dictionary as verified