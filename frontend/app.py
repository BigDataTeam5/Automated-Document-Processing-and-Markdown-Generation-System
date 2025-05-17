import streamlit as st
import requests
import time
import toml
# Streamlit UI
st.set_page_config(page_title="📄 PDF Processing & Markdown Viewer", layout="wide")
# Initialize session state variables if they do not exist
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "extraction_complete" not in st.session_state:
    st.session_state.extraction_complete = False
if "markdown_ready" not in st.session_state:
    st.session_state.markdown_ready = False
if "show_pdf_uploader" not in st.session_state:
    st.session_state.show_pdf_uploader = False
if "show_url_input" not in st.session_state:
    st.session_state.show_url_input = False
# Initialize session state for markdown history
if "markdown_history" not in st.session_state:
    st.session_state.markdown_history = []  # To store history of markdown files

with open("config.toml", "r") as f:
    config = toml.load(f)
    FASTAPI_URL = config["fastapi"]["url"] 

# API Endpoints
UPLOAD_PDF_API = f"{FASTAPI_URL}/upload-pdf"
LATEST_FILE_API = f"{FASTAPI_URL}/get-latest-file-url"
PARSE_PDF_API = f"{FASTAPI_URL}/parse-pdf"
PARSE_PDF_AZURE_API = f"{FASTAPI_URL}/parse-pdf-azure"
CONVERT_MARKDOWN_API = f"{FASTAPI_URL}/convert-pdf-markdown"
FETCH_MARKDOWN_API = f"{FASTAPI_URL}/fetch-latest-markdown-urls"
FETCH_DOWNLOADABLE_MARKDOWN_API = f"{FASTAPI_URL}/fetch-latest-markdown-downloads"
SCRAPE_OS_API = f"{FASTAPI_URL}/OpenSourceWebscrape/"
SCRAPE_EN_API = f"{FASTAPI_URL}/enscrape"
FETCH_WEB_MARKDOWN_API = f"{FASTAPI_URL}/fetch-WebScrapMarkdowns"

uploaded_file = None  # Define uploaded_file globally
url_input = None  # Define url_input globally

# Sidebar UI
with st.sidebar:
    st.subheader("Select Options")

    # Dropdown for processing type
    processing_type = st.selectbox("Processing Type:", ["Select an option", "PDF Extraction", "Web URL Scraping"], index=0)
    st.session_state.processing_type = processing_type

    # Dropdown for service type
    service_type = st.selectbox("Service Type:", ["Select Service", "Open Source", "Enterprise"], index=0)
    st.session_state.service_type = service_type

 # Next button
    if st.button("Next"):
        if processing_type == "Select an option" or service_type == "Select Service":
            st.error("Please select both Processing Type and Service Type.")
        else:
            st.session_state.next_clicked = True
            st.success("Processing Type and Service Type selected successfully.")    
    st.subheader("📑 Markdown History")
    for markdown in st.session_state.markdown_history:
        if st.button(markdown["label"]):
            st.session_state.selected_markdown = markdown["content"]  # Set the selected markdown content

# Function to Upload File to S3
def upload_pdf(file):
    try:
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
        with st.spinner("📤 Uploading PDF... Please wait."):
            service_type = st.session_state.get("service_type", None)
            response = requests.post(UPLOAD_PDF_API, files=files, params={"service_type": service_type})

        if response.status_code == 200:
            st.session_state.file_uploaded = True
            return response.json()
        else:
            try:
                error_detail = response.json().get("detail", f"Upload failed: {response.status_code}")
            except ValueError:
                error_detail = f"Upload failed: {response.status_code}"
            st.error(f"Error: {error_detail}")
            return {"error": error_detail}
    except requests.RequestException as e:
        st.error(f"Request Exception: {str(e)}")
        return {"error": str(e)}
            
def process_open_source_pdf():
    with st.spinner("⏳ Processing Open Source PDF... Please wait."):
        progress_bar = st.progress(0)  # Initialize progress bar
        try:
            for i in range(10):  # Simulate progress while waiting
                time.sleep(1)
                progress_bar.progress((i + 1) * 10)  # Update progress

            # Step 1: Get Latest File URL
            response_latest = requests.get(LATEST_FILE_API)
            if response_latest.status_code != 200:
                progress_bar.empty()
                return {"error": f"❌ Failed to fetch latest file URL: {response_latest.text}"}

            # Step 2: Parse the PDF
            response_parse = requests.get(PARSE_PDF_API, timeout=600)  # Increased timeout
            if response_parse.status_code == 200:
                st.session_state.extraction_complete = True
                progress_bar.empty()
                return {"message": f"✅ Open Source PDF Analysis Completed! Click Markdown to view results.\n\n**Response:** {response_parse.text}"}
            else:
                progress_bar.empty()
                return {"error": f"❌ Parsing failed! Response: {response_parse.text}"}

        except requests.exceptions.RequestException as e:
            progress_bar.empty()
            return {"error": f"⚠️ API Request Failed: {str(e)}"}
# Function to Trigger Azure PDF Parsing (Enterprise) with Progress Bar & Debugging
def process_azure_pdf():
    with st.spinner("⏳ Processing PDF using Azure Document Intelligence... Please wait."):
        progress_bar = st.progress(0)

        try:
            for i in range(10):  # Simulate progress while waiting
                time.sleep(1)
                progress_bar.progress((i + 1) * 10)
             # Step 1: Get Latest File URL
            response_latest = requests.get(LATEST_FILE_API)
            if response_latest.status_code != 200:
                progress_bar.empty()
                return {"error": f"❌ Failed to fetch latest file URL: {response_latest.text}"}

            response = requests.get(PARSE_PDF_AZURE_API, timeout=600)  # Increased timeout

            if response.status_code == 200:
                st.session_state.extraction_complete = True
                progress_bar.empty()
                return {"message": f"✅ Azure-based PDF Analysis Completed! Click Markdown to view results.\n\n**Response:** {response.text}"}
            else:
                error_message = response.json().get("detail", "❌ Azure PDF Parsing failed!")
                return {"error": error_message}

        except requests.exceptions.RequestException as e:
            progress_bar.empty()
            return {"error": f"⚠️ API Request Failed: {str(e)}"}

# Function to Convert PDF to Markdown (With Progress Bar)
def convert_to_markdown():
    with st.spinner("⏳ Converting PDF to Markdown... Please wait."):
        progress_bar = st.progress(0)

        try:
            for i in range(10):  # Simulate progress while waiting
                time.sleep(1)
                progress_bar.progress((i + 1) * 10)

            service_type = st.session_state.get("service_type", None)
            # Step 1: Get Latest File URL
            response_latest = requests.get(LATEST_FILE_API,params={"service_type": service_type})
            if response_latest.status_code != 200:
                progress_bar.empty()
                return {"error": f"❌ Failed to fetch latest file URL: {response_latest.text}"}

            # Step 2: Convert PDF to Markdown
            response = requests.get(CONVERT_MARKDOWN_API)
            if response.status_code == 200:
                st.session_state.markdown_ready = True
                progress_bar.empty()
                return {"message": "✅ Markdown Conversion Completed! Click View to see results."}
            else:
                progress_bar.empty()
                return {"error": f"❌ Markdown conversion failed! Response: {response.text}"}

        except requests.exceptions.RequestException as e:
            progress_bar.empty()
            return {"error": f"⚠️ API Request Failed: {str(e)}"}
# Function to Fetch Markdown File from S3
def fetch_markdown():
    with st.spinner("⏳ Fetching Markdown File from S3... Please wait."):
        progress_bar = st.progress(0)  # Initialize progress bar

        try:
            for i in range(10):  # Simulate progress
                time.sleep(0.5)
                progress_bar.progress((i + 1) * 10)

            response = requests.get(FETCH_MARKDOWN_API)
            if response.status_code == 200:
                markdown_files = response.json().get("files", [])
                progress_bar.empty()
                if markdown_files:
                    return {"markdown_file": markdown_files[-1]}  # Show latest markdown file
                else:
                    return {"error": "No markdown file found!"}
            else:
                progress_bar.empty()
                return {"error": "Failed to fetch markdown files!"}

        except requests.RequestException as e:
            progress_bar.empty()
            return {"error": str(e)}
# Function to Fetch Downloadable Markdown Files from S3
def fetch_downloadable_markdown():
    """
    Fetch Markdown file download links from the latest job-specific folder in S3.
    """
    try:
        with st.spinner("⏳ Fetching Markdown download links... Please wait."):
            response = requests.get(FETCH_DOWNLOADABLE_MARKDOWN_API)
        
        if response.status_code == 200:
            markdown_data = response.json()
            return markdown_data.get("markdown_downloads", [])
        else:
            return {"error": f"Failed to fetch markdown downloads! Response: {response.text}"}

    except requests.RequestException as e:
        return {"error": str(e)}
    
# ✅ Function to Fetch Web Markdown
def fetch_web_markdown():
    with st.spinner("⏳ Fetching Web Markdown File from S3... Please wait."):
        progress_bar = st.progress(0)

        try:
            for i in range(10):  
                time.sleep(0.5)
                progress_bar.progress((i + 1) * 10)

            # ✅ Ensure service type is fetched correctly
            service_type = st.session_state.get("service_type", None)
            if not service_type or service_type == "Select Service":
                return {"error": "⚠️ Please select a valid Service Type!"}

            # st.write(f"✅ Fetching markdown for service type: {service_type}")

            # ✅ Call API with service_type
            response = requests.get(FETCH_WEB_MARKDOWN_API, params={"service_type": service_type})

            # # ✅ Debugging Output
            # st.write(f"🛠 API Response Code: {response.status_code}")
            # st.write(f"🛠 API Raw Response: {response.text}")

            if response.status_code == 200:
                markdown_file_url = response.json().get("download_url", None)
                progress_bar.empty()

                if markdown_file_url:
                    return {"file_url": markdown_file_url}  # ✅ Return single file URL
                else:
                    return {"error": "No web markdown file found!"}
            else:
                progress_bar.empty()
                return {"error": f"Failed to fetch web markdown file! Status: {response.status_code}"}

        except requests.RequestException as e:
            progress_bar.empty()
            return {"error": str(e)}
        
# ✅ Function to Scrape Open Source URL
def os_scrape_url(url):
    with st.spinner("⏳ Scraping Webpage using Open Source Tools... Please wait."):
        progress_bar = st.progress(0)

        try:
            for i in range(10):  
                time.sleep(0.5)
                progress_bar.progress((i + 1) * 10)

            service_type = st.session_state.get("service_type", None)  # ✅ Fetch selected service type
            if not service_type or service_type == "Select Service":
                return {"error": "⚠️ Please select 'Open Source' or 'Enterprise' before scraping!"}

            payload = {"url": url}
            response = requests.post(
                SCRAPE_OS_API,
                json=payload,
                params={"service_type": service_type}  # ✅ Send service_type dynamically
            )

            progress_bar.empty()

            if response.status_code == 200:
                st.session_state["last_service_type"] = service_type  # ✅ Store service_type after extraction
                return response.json()
            else:
                return {"error": f"Failed to scrape URL. Status code: {response.status_code}"}

        except requests.RequestException as e:
            progress_bar.empty()
            return {"error": str(e)}


# ✅ Function to Scrape Enterprise URL
def en_scrape_url(url):
    with st.spinner("⏳ Scraping Webpage using APIFY... Please wait."):
        progress_bar = st.progress(0)

        try:
            for i in range(10):  
                time.sleep(0.5)
                progress_bar.progress((i + 1) * 10)

            service_type = st.session_state.get("service_type", None)  # ✅ Fetch selected service type
            if not service_type or service_type == "Select Service":
                return {"error": "⚠️ Please select 'Open Source' or 'Enterprise' before scraping!"}

            payload = {"url": url}
            response = requests.post(
                SCRAPE_EN_API,
                json=payload,
                params={"service_type": service_type}  # ✅ Send service_type dynamically
            )

            progress_bar.empty()

            if response.status_code == 200:
                st.session_state["last_service_type"] = service_type  # ✅ Store service_type after extraction
                return response.json()
            else:
                return {"error": f"Failed to scrape URL. Status code: {response.status_code}"}

        except requests.RequestException as e:
            progress_bar.empty()
            return {"error": str(e)}
# Main Page Logic
st.title("📄 Data Processing App & Markdown Viewer")

if st.session_state.get("next_clicked", False):
    if st.session_state.processing_type == "PDF Extraction":
        # Display tools being used
        if st.session_state.service_type == "Open Source":
            st.subheader("Using Tools: PyMuPDF, Camelot")
        elif st.session_state.service_type == "Enterprise":
            st.subheader("Using Tools: Azure Document Intelligence")
        
        # Display file uploader and buttons
        uploaded_file = st.file_uploader("Upload a PDF File:", type=["pdf"], key="pdf_uploader")
        if uploaded_file:
            st.session_state.file_uploaded = True
            upload_response = upload_pdf(uploaded_file)
            if "error" in upload_response:
                pass
            else:
                st.success("✅ PDF File Uploaded Successfully!")

        # Extract button
        if st.button("🛠 Extract"):
            if not uploaded_file:
                st.warning("⚠️ Please upload a file first!")
            elif st.session_state.service_type == "Open Source":
                extract_response = process_open_source_pdf()
                if "error" in extract_response:
                    st.error(extract_response["error"])
                else:
                    st.success(extract_response["message"])
                    st.session_state.extraction_complete = True
            elif st.session_state.service_type == "Enterprise":
                extract_response = process_azure_pdf()
                if "error" in extract_response:
                    st.error(extract_response["error"])
                else:
                    st.success(extract_response["message"])
                    st.session_state.extraction_complete = True

        # Convert to Markdown Button (Only appears after extraction)
        if st.session_state.get("extraction_complete", False) and not st.session_state.get("markdown_ready", False):
            if st.button("📑 Convert to Markdown"):
                markdown_response = convert_to_markdown()
                if "error" in markdown_response:
                    st.error(markdown_response["error"])
                else:
                    st.success(markdown_response["message"])
                    st.session_state.markdown_ready = True  # ✅ Set markdown state to True

        # Fetch markdown URLs from the latest job-specific folder
        if st.session_state.get("markdown_ready", False):

            st.markdown("## 📄 Available Markdown Files")
            
            # ✅ Fetch markdown files from API
            markdown_files = fetch_downloadable_markdown()
            
            if not markdown_files or "error" in markdown_files:
                st.warning("⚠️ No Markdown files found.")
            else:
                # ✅ Display each markdown file as a selectable option
                markdown_options = {file["file_name"]: file["download_url"] for file in markdown_files}
                selected_markdown_name = st.selectbox("Choose a Markdown File", list(markdown_options.keys()), index=0)

                if selected_markdown_name:
                    selected_markdown_url = markdown_options[selected_markdown_name]

                    # ✅ Add a Download Button for the Selected Markdown
                    st.download_button(
                        label="⬇️ Download Markdown",
                        data=requests.get(selected_markdown_url).text,  # Fetch file content
                        file_name=selected_markdown_name,
                        mime="text/markdown"
                    )

                if st.button("👀 View Selected Markdown"):
                    if not selected_markdown_name:
                        st.warning("⚠️ Please select a Markdown file.")
                    else:
                        # ✅ Fetch actual markdown content
                        markdown_content = requests.get(selected_markdown_url).text

                        # ✅ Store selected markdown in session state
                        st.session_state.selected_markdown_content = markdown_content

        # ✅ Show Markdown Content if a file is selected
        if "selected_markdown_content" in st.session_state:
            st.markdown("### 📄 Markdown Viewer")
            
            # ✅ Use `st.markdown()` to properly render Markdown with headings, lists, etc.
            st.markdown(st.session_state.selected_markdown_content, unsafe_allow_html=True)

    # Web URL Scraping Logic
    elif st.session_state.processing_type == "Web URL Scraping":
        # Display tools being used
        if st.session_state.service_type == "Open Source":
            st.subheader("Using Tools: BeautifulSoup, Scrapy")
        elif st.session_state.service_type == "Enterprise":
            st.subheader("Using Tools: APIFY")
        
        # Display text input for URL
        url_input = st.text_input("Enter a Web URL:", placeholder="https://example.com")
        
        # ✅ Scrape button
        if st.button("🔍 Scrape"):
            if not url_input:
                st.warning("⚠️ Please enter a URL first!")
            else:
                with st.spinner("⏳ Scraping in progress... Please wait."):
                    if st.session_state.service_type == "Open Source":
                        scrape_response = os_scrape_url(url_input)
                    elif st.session_state.service_type == "Enterprise":
                        scrape_response = en_scrape_url(url_input)
                    else:
                        st.error("⚠️ Please select 'Open Source' or 'Enterprise'.")
                        scrape_response = {"error": "Invalid service type!"}

                if "error" in scrape_response:
                    st.error(scrape_response["error"])
                else:
                    st.success("✅ Scraping completed successfully!")
                    st.session_state.web_markdown_ready = True  # ✅ Mark as ready

        # ✅ Fetch markdown URLs after scraping
        # Fetch and View Web Markdown
        if st.session_state.get("web_markdown_ready", False):
            st.markdown("## 🌐 Web Markdown Viewer")

            # ✅ Fetch the single markdown file
            markdown_response = fetch_web_markdown()

            if "error" in markdown_response:
                st.warning(markdown_response["error"])
            else:
                markdown_file_url = markdown_response.get("file_url")
                if markdown_file_url:
                    # ✅ Add a Download Button for the Markdown File
                    st.download_button(
                        label="⬇️ Download Web Markdown",
                        data=requests.get(markdown_file_url).text,  # Fetch file content
                        file_name="web_markdown.md",
                        mime="text/markdown"
                    )

                    # ✅ Fetch and Display Markdown Content
                    markdown_content = requests.get(markdown_file_url).text
                    st.markdown("### 📄 Markdown Content Viewer")
                    st.markdown(markdown_content, unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Markdown file URL is missing!")
