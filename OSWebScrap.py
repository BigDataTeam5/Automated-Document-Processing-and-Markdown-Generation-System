import os
import requests
import boto3
from bs4 import BeautifulSoup
from io import BytesIO
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

# AWS Configuration
session = boto3.Session(
    aws_access_key_id=os.getenv('AWS_SERVER_PUBLIC_KEY'),
    aws_secret_access_key=os.getenv('AWS_SERVER_SECRET_KEY'),
)
s3 = session.client('s3')
bucket_name = os.getenv('AWS_BUCKET_NAME')
aws_region = os.getenv('AWS_REGION')  # e.g., 'us-east-1'

# List of disallowed file extensions
DISALLOWED_EXTENSIONS = [".pdf", ".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".rar"]

# S3 Upload Function
def upload_file_to_s3(file_content, s3_path, content_type="text/plain"):
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_path,
            Body=file_content,
            ContentType=content_type,
        )
        s3_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_path}"
        print(f"Uploaded to S3: {s3_url}")
        return s3_url
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return None

# URL Validation
def is_valid_url(url):
    if not url.startswith(("http://", "https://")):
        print("Invalid URL. Please include http:// or https://.")
        return False

    if any(url.lower().endswith(ext) for ext in DISALLOWED_EXTENSIONS):
        print(f"URL points to a disallowed file type ({url.split('.')[-1]}).")
        return False

    return True

# Comprehensive scraping function
def scrape_visual_data(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Scrape & Embed Images
    img_tags = soup.find_all("img")
    images = []
    for idx, img_tag in enumerate(img_tags):
        img_url = img_tag.get("src")
        if not img_url:
            continue
        img_url = requests.compat.urljoin(url, img_url)

        try:
            img_data = requests.get(img_url).content
            
            # Get content type (default to jpeg if can't determine)
            img_format = "jpeg"
            if img_url.lower().endswith(".png"):
                img_format = "png"
            elif img_url.lower().endswith(".gif"):
                img_format = "gif"
            
            # Convert to base64 for direct embedding
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            embedded_img = f"data:image/{img_format};base64,{img_base64}"
            
            images.append({
                "embedded": embedded_img,
                "alt": img_tag.get("alt", f"Image {idx + 1}")
            })
        except Exception as e:
            print(f"Failed to download image {img_url}: {e}")

    # Scrape & Format Tables
    tables = []
    for table_idx, table in enumerate(soup.find_all("table"), start=1):
        table_data = []
        
        # Get header row first if exists
        header_row = []
        headers = table.find_all("th")
        if headers:
            header_row = [header.get_text(strip=True) for header in headers]
            
        # If no explicit headers found but has rows, use first row as header
        if not header_row:
            first_row = table.find("tr")
            if first_row:
                cells = first_row.find_all(["td", "th"])
                if cells:
                    header_row = [cell.get_text(strip=True) for cell in cells]
        
        # Get all rows (including header if not already extracted)
        rows = table.find_all("tr")
        for row in rows:
            # Skip if this is the header we already processed
            if rows[0] == row and header_row and all(cell.name == "th" for cell in row.find_all(["td", "th"])):
                continue
                
            row_data = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
            if row_data:  # Only add non-empty rows
                table_data.append(row_data)
        
        # Store the complete table with header info
        tables.append({
            "headers": header_row,
            "rows": table_data
        })

    # Extract text content
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()

    # Get visible text
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned_text = "\n".join(chunk for chunk in chunks if chunk)

    # Combine everything into a comprehensive markdown file
    markdown_content = "# Extracted Web Content\n\n"
    markdown_content += "## Content\n\n" + cleaned_text + "\n\n"
    
    # Add Tables with proper markdown formatting
    if tables:
        markdown_content += "## Tables\n\n"
        for idx, table in enumerate(tables, start=1):
            markdown_content += f"### Table {idx}\n\n"
            
            # Add header row with separator
            headers = table["headers"]
            if headers:
                markdown_content += "| " + " | ".join(headers) + " |\n"
                markdown_content += "| " + " | ".join(["---" for _ in headers]) + " |\n"
            
            # Add data rows
            for row in table["rows"]:
                # Ensure row has same number of columns as header by padding if necessary
                if headers and len(row) < len(headers):
                    row.extend(["" for _ in range(len(headers) - len(row))])
                # Ensure cell data doesn't break markdown formatting
                sanitized_row = [cell.replace("|", "\\|") for cell in row]
                markdown_content += "| " + " | ".join(sanitized_row) + " |\n"
            
            markdown_content += "\n"
    
    # Add Images with base64 embedding
    if images:
        markdown_content += "## Images\n\n"
        for idx, image in enumerate(images, start=1):
            alt_text = image.get("alt", f"Image {idx}")
            markdown_content += f"![{alt_text}]({image['embedded']})\n\n"

    # Upload to S3
    markdown_s3_path = "scraped_data/scraped_os_data/scraped_content.md"
    upload_file_to_s3(markdown_content.encode("utf-8"), markdown_s3_path, "text/markdown")
    
    return markdown_s3_path

# Alias function for backward compatibility
def scrape_text_data_with_images(url):
    """Scrape text and images from URL and return the path to the markdown file."""
    return scrape_visual_data(url)

# Modified to just return the path to the single markdown file
def convert_to_markdown(data):
    """
    For backward compatibility - returns the path to the markdown file.
    No longer creates a separate file.
    """
    return "scraped_data/scraped_os_data/scraped_content.md"

if __name__ == "__main__":
    # Prompt user for a URL
    user_url = input("Enter the URL to scrape (must include http:// or https://): ").strip()

    if not is_valid_url(user_url):
        print("Exiting due to invalid URL.")
        exit(1)

    # Scrape text data
    markdown_s3_path = scrape_text_data_with_images(user_url)

    # Print the path to the markdown file
    print(f"Markdown file created at: {markdown_s3_path}")