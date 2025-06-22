# frontend_streamlit.py
# A frontend for the Legal Aid AI Agent built with Streamlit.
# To run this:
# 1. Ensure the FastAPI backend (main.py) is running on http://localhost:8000.
# 2. Run this file from your terminal:
#    streamlit run frontend_streamlit.py

import streamlit as st
import requests
from datetime import datetime

# --- Configuration ---
API_BASE_URL = "http://localhost:8000"

# --- Helper Functions to Interact with Backend ---

def get_cases():
    """Fetches all cases from the backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/cases", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {e}")
        return []

def create_new_case(name: str):
    """Sends a request to create a new case."""
    try:
        response = requests.post(f"{API_BASE_URL}/api/cases", json={"name": name})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to create case: {e}")
        return None

def post_chat_message(case_id: int, message: str):
    """Sends a user's chat message to the backend."""
    try:
        response = requests.post(f"{API_BASE_URL}/api/cases/{case_id}/chat", json={"message": message})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to send message: {e}")
        return None

def upload_document_to_case(case_id: int, file):
    """Uploads a document to a specific case."""
    try:
        files = {'file': (file.name, file, file.type)}
        response = requests.post(f"{API_BASE_URL}/api/cases/{case_id}/documents", files=files)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to upload document: {e}")
        return None

# --- Main Application UI ---

st.set_page_config(layout="wide", page_title="Legal Aid Assistant")

# Initialize session state to hold data
if 'cases' not in st.session_state:
    st.session_state.cases = get_cases()

if 'selected_case_id' not in st.session_state:
    st.session_state.selected_case_id = st.session_state.cases[0]['id'] if st.session_state.cases else None

# --- Sidebar for Navigation ---
with st.sidebar:
    st.title("Legal Case Assistant")

    st.header("Create New Case")
    with st.form("new_case_form", clear_on_submit=True):
        new_case_name = st.text_input("New Case Name")
        submitted = st.form_submit_button("Create Case")
        if submitted and new_case_name:
            with st.spinner("Creating case..."):
                new_case = create_new_case(new_case_name)
                if new_case:
                    st.session_state.cases = get_cases() # Refresh case list
                    st.session_state.selected_case_id = new_case['id']
                    st.success(f"Case '{new_case_name}' created!")

    st.header("Your Cases")
    if st.session_state.cases:
        case_names = [case['name'] for case in st.session_state.cases]
        case_ids = [case['id'] for case in st.session_state.cases]
        
        # Find the index of the currently selected case
        try:
            selected_index = case_ids.index(st.session_state.selected_case_id)
        except (ValueError, TypeError):
            selected_index = 0

        selected_case_name = st.radio(
            "Select a case",
            options=case_names,
            index=selected_index,
            label_visibility="collapsed"
        )
        # Update selected_case_id based on the name selected
        st.session_state.selected_case_id = case_ids[case_names.index(selected_case_name)]
    else:
        st.write("No cases found.")


# --- Main Panel for Case Details ---
if not st.session_state.selected_case_id:
    st.header("Select a case from the sidebar or create a new one to get started.")
else:
    # Find the full data for the selected case
    selected_case = next((case for case in st.session_state.cases if case['id'] == st.session_state.selected_case_id), None)
    
    if not selected_case:
        st.error("Selected case not found. Please refresh.")
    else:
        st.title(f"Case Details: {selected_case['name']}")

        # Create two columns for Chat and Documents
        col1, col2 = st.columns([2, 1])

        with col1:
            st.header("Case Chat")
            
            # Display chat history
            chat_container = st.container(height=500, border=True)
            with chat_container:
                for message in selected_case.get('chat_history', []):
                    with st.chat_message(name=message['sender']):
                        st.write(message['content'])

            # Chat input
            if prompt := st.chat_input("Ask a question about your case..."):
                # Display user message
                with chat_container:
                    with st.chat_message("user"):
                        st.write(prompt)

                # Send message to backend and get response
                with st.spinner("Agent is thinking..."):
                    agent_response = post_chat_message(selected_case['id'], prompt)
                    if agent_response:
                        # Refresh cases and rerun to display the new message
                        st.session_state.cases = get_cases()
                        st.rerun()

        with col2:
            st.header("Documents & Info")

            # Document Uploader
            with st.form("upload_form", clear_on_submit=True):
                uploaded_file = st.file_uploader(
                    "Upload a document (PNG, JPG)",
                    type=['png', 'jpg', 'jpeg']
                )
                upload_submitted = st.form_submit_button("Upload and Analyze")

                if upload_submitted and uploaded_file is not None:
                    with st.spinner(f"Uploading and analyzing {uploaded_file.name}..."):
                        upload_result = upload_document_to_case(selected_case['id'], uploaded_file)
                        if upload_result:
                            st.session_state.cases = get_cases() # Refresh case list
                            st.rerun()

            st.divider()

            # Display uploaded documents
            st.subheader("Uploaded Documents")
            if selected_case.get('documents'):
                for doc in selected_case['documents']:
                    with st.expander(f"{doc['name']}"):
                        st.write(f"**Upload Date:** {datetime.fromisoformat(doc['upload_date']).strftime('%Y-%m-%d')}")
                        st.write(f"**AI Summary:** *{doc['summary']}*")
                        if doc.get('extracted_data'):
                            st.write("**Extracted Data:**")
                            st.json(doc['extracted_data'])
            else:
                st.info("No documents have been uploaded for this case yet.")
