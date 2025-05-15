from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict
from pydantic import BaseModel
import os
import sys
import boto3
import fitz
import requests
from apify_client import ApifyClient
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from fastapi import Query
MAX_FILE_SIZE_MB = 5  # Max allowed file size in MB
MAX_PAGE_COUNT = 5  # Max allowed pages

import time


# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Azure_Document_Intelligence import extract_and_upload_pdf
from EnterpriseWebScrap import is_valid_url, save_and_upload_images, generate_and_upload_markdown
from OSWebScrap import scrape_text_data_with_images, scrape_visual_data, convert_to_markdown
from open_source_parsing import extract_all_from_pdf
from docklingextraction import main
#  Now import the parsing functions
#  Call the Docling conversion function
# Load environment variables from .env file
import tempfile
load_dotenv(override=True)

# AWS S3 Configuration
S3_BUCKET = os.getenv("AWS_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_SERVER_PUBLIC_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SERVER_SECRET_KEY")
AWS_REGION = "us-east-2"

# Apify Configuration
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Create FastAPI instance
app = FastAPI(
    title="Lab Demo API",
    description="Simple FastAPI application with health check and PDF upload to S3"
)

class ScrapeRequest(BaseModel):
    url: str


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage for file details
latest_file_details = {}
# def generate_presigned_url(bucket, key, expiration=3600):
#     return s3_client.generate_presigned_url(
#         "get_object",
#         Params={"Bucket": bucket, "Key": key},
#         ExpiresIn=expiration
#     )
def cleanup_local_files(keep_most_recent=True):
    """
    Cleans up local temporary files, keeping only the most recent ones if specified.
    """
    import shutil
    try:
        # Directories to clean
        dirs_to_clean = [
            os.path.join(os.getcwd(), "output_data"),
            os.path.join(os.getcwd(), "output")
        ]
        
        for directory in dirs_to_clean:
            if not os.path.exists(directory):
                continue
                
            # List all items in the directory
            items = [os.path.join(directory, item) for item in os.listdir(directory)]
            
            if not items:
                continue
                
            if keep_most_recent:
                # Sort by modification time (newest last)
                items.sort(key=os.path.getmtime)
                # Keep only the most recent item
                keep_item = items[-1]
                items = [item for item in items if item != keep_item]
            
            # Delete the items
            for item in items:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
                print(f"🗑️ Removed: {item}")
                
        return {"status": "success", "message": "Cleanup completed successfully"}
    except Exception as e:
        print(f"❌ Cleanup error: {str(e)}")
        return {"status": "error", "message": f"Cleanup failed: {str(e)}"}

def check_pdf_constraints(pdf_path):
    """
    Check if the PDF meets the file size and page count constraints.
    """
    try:
        # Get file size
        pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)  # Convert bytes to MB

        # Get page count
        with fitz.open(pdf_path) as pdf_doc:
            pdf_page_count = len(pdf_doc)

        if pdf_size_mb > MAX_FILE_SIZE_MB:
            error_message = f"❌ File too large: {pdf_size_mb:.2f}MB (Limit: {MAX_FILE_SIZE_MB}MB). Process stopped."
            print(error_message)
            return {"error": error_message}  # Return error instead of raising

        if pdf_page_count > MAX_PAGE_COUNT:
            error_message = f"❌ Too many pages: {pdf_page_count} pages (Limit: {MAX_PAGE_COUNT} pages). Process stopped."
            print(error_message)
            return {"error": error_message}  # Return error instead of raising

        print(f"✅ PDF meets size ({pdf_size_mb:.2f}MB) and page count ({pdf_page_count} pages) limits. Proceeding with upload...")
        return {"success": True}

    except Exception as e:
        return {"error": f"Failed to check PDF constraints: {str(e)}"}@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint with basic service information
    """
    return {
        "service": "Lab Demo API",
        "version": "1.0.0",
        "documentation": "/docs"
    }


# ✅ Favicon Route
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

# ✅ Example Root Endpoint
@app.get("/")
async def root():
    return {"message": "FastAPI is running on Cloud Run!"}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), service_type: str = Query("")) -> Dict[str, str]:
    """
    Uploads a PDF file to AWS S3 after checking constraints.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no name")

    if not S3_BUCKET:
        raise HTTPException(status_code=500, detail="S3_BUCKET environment variable is missing")
    
    temp_pdf_path = None  # Define temp path for cleanup

    try:
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(file.file.read())
            temp_pdf_path = temp_pdf.name

        # Check PDF constraints for only Enterprise service type
        if service_type == "Enterprise":
            constraint_check = check_pdf_constraints(temp_pdf_path)
            if "error" in constraint_check:
                os.remove(temp_pdf_path)  # Cleanup temp file
                raise HTTPException(status_code=400, detail=constraint_check["error"])

        # Upload file to S3 (only if constraints are met)
        s3_key = f"RawInputs/{file.filename}"
        s3_client.upload_file(temp_pdf_path, S3_BUCKET, s3_key)

        # Generate pre-signed URL
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=3600  # 1 hour validity
        )

        # Cleanup: Delete the temp file after successful upload
        os.remove(temp_pdf_path)

        # Save the file details globally
        global latest_file_details
        latest_file_details = {
            "filename": file.filename,
            "file_url": file_url,
            "s3_key": s3_key,
        }

        return {"filename": file.filename, "message": "✅ PDF uploaded successfully!", "file_url": file_url}

    except NoCredentialsError:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)  # Cleanup on error
        raise HTTPException(status_code=500, detail="AWS credentials not found")
    except HTTPException as e:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)  # Cleanup on error
        raise e
    except Exception as e:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)  # Cleanup on error
        raise HTTPException(status_code=500, detail=f"❌ Upload failed: {str(e)}")
    
@app.get("/get-latest-file-url")
async def get_latest_file_url() -> Dict[str, str]:
    """
    Retrieve the most recently uploaded file's URL, download it locally, and save the details.
    """
    if not latest_file_details:
        raise HTTPException(status_code=404, detail="No files have been uploaded yet")

    # Define local download path
    project_root = os.getcwd()
    downloaded_pdf_path = os.path.join(project_root, latest_file_details["filename"])

    # Download the file
    try:
        response = requests.get(latest_file_details["file_url"])
        response.raise_for_status()
        with open(downloaded_pdf_path, "wb") as pdf_file:
            pdf_file.write(response.content)
        print(f"[INFO] PDF downloaded successfully: {downloaded_pdf_path}")

        # Update the local path in the global file details
        latest_file_details["local_path"] = downloaded_pdf_path

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")

    return latest_file_details


@app.get("/parse-pdf")
async def parse_uploaded_pdf():
    
    try:
        cleanup_local_files()
        # Check if the latest file details are available
        if not latest_file_details:
            raise HTTPException(status_code=404, detail="No file has been downloaded yet. Please fetch the latest file first.")

        # Extract the details from the saved data
        local_path = latest_file_details.get("local_path")
        filename = latest_file_details.get("filename")

        if not local_path or not filename:
            raise HTTPException(status_code=404, detail="Incomplete file details. Please fetch the latest file again.")

        # Define output directory for extraction
        output_dir = os.path.join(os.getcwd(), "output_data")

        # Extract data from the locally downloaded PDF
        extract_all_from_pdf(local_path, output_dir)

        return {
            "filename": filename,
            "message": "PDF parsed successfully and extracted data uploaded to S3",
            "local_path": local_path,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

@app.get("/parse-pdf-azure")
async def parse_uploaded_pdf_azure():
    """
    Uses the saved latest file details to extract content using Azure Document Intelligence.
    """
    try:
        cleanup_local_files()
        if not latest_file_details:
            raise HTTPException(status_code=404, detail="No file has been downloaded yet. Please fetch the latest file first.")

        local_path = latest_file_details.get("local_path")
        filename = latest_file_details.get("filename")

        if not local_path or not filename:
            raise HTTPException(status_code=404, detail="Incomplete file details. Please fetch the latest file again.")

        # Extract data from the locally downloaded PDF using Azure Document Intelligence
        extract_and_upload_pdf(local_path)

        return {
            "filename": filename,
            "message": "PDF parsed successfully using Azure Document Intelligence, data uploaded to S3",
            "local_path": local_path,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure PDF Processing failed: {str(e)}")

@app.get("/list-pdf-contents")
async def list_pdf_contents():
    """
    Lists only the parsed contents (text, images, tables, markdown) from PDF processing and web scraping.
    """
    import datetime
    try:
        if not latest_file_details:
            raise HTTPException(status_code=404, detail="No PDF has been processed yet. Please upload and parse a PDF first.")

        filename = latest_file_details.get("filename")
        if not filename:
            raise HTTPException(status_code=404, detail="Incomplete file details. Please upload a PDF again.")
        

        parsed_content_paths = {
            "pdf_os_parsed": "pdf_processing_pipeline/pdf_os_pipeline/parsed_data/",
            "pdf_azure_parsed": "pdf_processing_pipeline/pdf_enterprise_pipeline/",
            "pdf_markdown": "pdf_processing_pipeline/markdown_outputs/",
            "web_os_scraped": "scraped_data/scraped_os_data/",
            "web_en_scraped": "scraped_data/scraped_en_data/"
        }
        
        # Results dictionary to store all parsed contents
        results = {
            "pdf_processing": {
                "text": [],
                "images": [], 
                "tables": [],
                "markdown": []
            },
            "web_scraping": {
                "text": [],
                "images": [],
                "markdown": []
            }
        }
        
        # Check each path for parsed content
        for content_type, s3_path in parsed_content_paths.items():
            try:
                # List objects with this prefix
                response = s3_client.list_objects_v2(
                    Bucket=S3_BUCKET, 
                    Prefix=s3_path
                )
                
                if "Contents" in response:
                    for item in response["Contents"]:
                        key = item["Key"]
                        
                        # Generate a presigned URL for viewing
                        url = s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': S3_BUCKET, 'Key': key},
                            ExpiresIn=3600 
                        )
                        
                        file_info = {
                            "filename": key.split("/")[-1],
                            "url": url,
                            "last_modified": item["LastModified"].isoformat()
                        }
                        
                       
                        if content_type.startswith("pdf_"):
                            if key.endswith('.txt'):
                                results["pdf_processing"]["text"].append(file_info)
                            elif key.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                results["pdf_processing"]["images"].append(file_info)
                            elif key.endswith(('.csv', '.xlsx')):
                                results["pdf_processing"]["tables"].append(file_info)
                            elif key.endswith('.md'):
                                results["pdf_processing"]["markdown"].append(file_info)
                        elif content_type.startswith("web_"):
                            if key.endswith('.txt'):
                                results["web_scraping"]["text"].append(file_info)
                            elif key.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                results["web_scraping"]["images"].append(file_info)
                            elif key.endswith('.md'):
                                results["web_scraping"]["markdown"].append(file_info)
            
            except Exception as e:
                print(f"Error checking path {s3_path}: {str(e)}")
                continue
        
        # Add timestamp for the response
        results["timestamp"] = datetime.datetime.now().isoformat()
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list parsed contents: {str(e)}")

@app.get("/convert-pdf-markdown")
async def convert_pdf_to_markdown_api(service_type: str = Query("Open Source")):
    """
    Uses the saved latest file details to convert the PDF into markdown using Docling.
    """
    try:
        cleanup_local_files()
        if not latest_file_details:
            raise HTTPException(status_code=404, detail="No file has been downloaded yet. Please fetch the latest file first.")

        local_path = latest_file_details.get("local_path")
        filename = latest_file_details.get("filename")

        if not local_path or not filename:
            raise HTTPException(status_code=404, detail="Incomplete file details. Please fetch the latest file again.")

        
        main(local_path,service_type)


        return {
            "filename": filename,
            "message": "PDF successfully converted to Markdown using Docling and uploaded to S3",
            "local_path": local_path,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docling Markdown conversion failed: {str(e)}")
    
@app.get("/fetch-latest-markdown-downloads")
async def fetch_latest_markdown_downloads():
    """
    Fetch Markdown file download links from the latest job-specific folder in S3.
    """
    try:
        # Base S3 folder where markdowns are stored
        s3_base_folder = "pdf_processing_pipeline/markdown_outputs/"

        # Fetch all job subfolders
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=s3_base_folder, Delimiter='/')

        if "CommonPrefixes" not in response:
            raise HTTPException(status_code=404, detail="No markdown folders found in S3.")

        # Extract all subfolders
        subfolders = [prefix["Prefix"] for prefix in response["CommonPrefixes"]]

        if not subfolders:
            raise HTTPException(status_code=404, detail="No markdown subfolders found in S3.")

        # Find the latest folder based on the most recently modified file
        latest_folder = None
        latest_time = None

        for folder in subfolders:
            folder_response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=folder)

            if "Contents" not in folder_response:
                continue

            # Check the latest file modification time inside each subfolder
            for obj in folder_response["Contents"]:
                if obj["Key"].endswith(".md"):
                    last_modified = obj["LastModified"]

                    if latest_time is None or last_modified > latest_time:
                        latest_folder = folder
                        latest_time = last_modified

        if latest_folder is None:
            raise HTTPException(status_code=404, detail="No markdown files found in subfolders.")

        latest_folder_response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=latest_folder)
        markdown_files = [
            obj["Key"] for obj in latest_folder_response["Contents"] if obj["Key"].endswith(".md")
        ]

        if not markdown_files:
            raise HTTPException(status_code=404, detail="No markdown files available for download.")

        # ✅ Generate public or pre-signed download URLs for the markdown files
        markdown_download_links = []
        for file_key in markdown_files:
            # ✅ Option 1: Use pre-signed URL for private files (recommended for security)
            download_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": file_key},
                ExpiresIn=3600 
            )

            markdown_download_links.append({
                "file_name": file_key.split("/")[-1],
                "download_url": download_url
            })

        return {
            "message": f"Fetched Markdown downloads from the latest subfolder: {latest_folder}",
            "latest_folder": latest_folder,
            "markdown_downloads": markdown_download_links
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch markdown downloads: {str(e)}")
        
@app.post("/enscrape")
def scrape_webpage(request: ScrapeRequest):
    """Scrape a webpage using Apify and upload the results to S3."""
    if not is_valid_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid URL or unsupported file type.")
 
    # Apify actor configuration
    actor_id = "apify/puppeteer-scraper"
    input_data = {
        "startUrls": [{"url": request.url}],
        "maxConcurrency": 10,
        "maxPagesPerCrawl": 5,
        "pageFunction": """async ({ page, request }) => {
            try {
                await page.waitForSelector('img');
                const images = await page.$$eval('img', imgs => imgs.map(img => img.src || img.getAttribute('ng-src')));
                const validImages = [...new Set(images)].filter(url => url && url.startsWith('http'));
                const textContent = await page.evaluate(() => document.body.innerText);
                return { url: request.url, title: await page.title(), images: validImages, text: textContent };
            } catch (error) {
                return { url: request.url, error: error.message };
            }
        }""",
    }
 
    try:
        # Initialize Apify client
        client = ApifyClient(APIFY_TOKEN)
 
        # Run the Apify actor
        run = client.actor(actor_id).call(run_input=input_data)
 
        # Fetch the results
        dataset_id = run["defaultDatasetId"]
        items = client.dataset(dataset_id).list_items().items
 
        # Process the results
        for item in items:
            images = item.get("images", [])
            text = item.get("text", "")
            s3_image_urls = save_and_upload_images(images)
            md_s3_url = generate_and_upload_markdown(text, s3_image_urls)
            return {"markdown_s3_url": md_s3_url}
 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    


@app.post("/OpenSourceWebscrape/")
async def scrape_url(scrape_request: ScrapeRequest):
    url = scrape_request.url
 
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")
 
    # Scrape text data
    markdown_s3_path = scrape_text_data_with_images(url)
 
    # Scrape visual data (images & tables)
    visual_data = scrape_visual_data(url)
 
    # Convert to final Markdown with images and tables
    final_markdown_s3_path = convert_to_markdown(visual_data)
 
    return {
        "message": "Scraping completed successfully",
        "markdown_s3_path": markdown_s3_path,
        "final_markdown_s3_path": final_markdown_s3_path,
    }

@app.get("/fetch-WebScrapMarkdowns")
async def fetch_WebScrapMarkdowns_from_s3(service_type: str = Query(...)):
    """
    Fetch the latest Markdown file from the correct S3 folder based on service type.
    """
    try:
        # ✅ Select the correct folder based on service_type
        if service_type == "Open Source":
            s3_folder = "scraped_data/scraped_os_data/"
        elif service_type == "Enterprise":
            s3_folder = "scraped_data/scraped_en_data/"
        else:
            raise HTTPException(status_code=400, detail="Invalid service type! Choose 'Open Source' or 'Enterprise'.")

        # ✅ Fetch all files in the selected folder
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=s3_folder)

        if "Contents" not in response or len(response["Contents"]) == 0:
            raise HTTPException(status_code=404, detail=f"No markdown files found in S3 for {service_type}.")

        # ✅ Get the latest markdown file
        latest_file = None
        latest_time = None

        for obj in response["Contents"]:
            if obj["Key"].endswith(".md"):  # ✅ Process Markdown files
                last_modified = obj["LastModified"]

                if latest_time is None or last_modified > latest_time:
                    latest_file = obj["Key"]
                    latest_time = last_modified

        if latest_file is None:
            raise HTTPException(status_code=404, detail=f"No markdown files found in {service_type} folder.")

        # ✅ Generate pre-signed URL for download
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": latest_file},
            ExpiresIn=3600  # 1-hour expiration
        )

        return {
            "message": f"Fetched latest markdown file for {service_type}.",
            "file_name": latest_file.split("/")[-1],  # Extract just the filename
            "download_url": download_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch markdown downloads: {str(e)}")
