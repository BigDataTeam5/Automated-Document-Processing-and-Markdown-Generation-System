

# AI Application Workflow

This project outlines the architecture and workflow of an AI application that processes and standardizes data from various sources (PDFs, web scraping, and enterprise services) and stores it in an AWS S3 bucket. The application is built using a combination of Python libraries, FastAPI for the backend, and Streamlit for the frontend.

## Workflow Diagram

Below is the workflow diagram for the AI Application:

![AI Application Workflow](https://github.com/khavnekar-y/AI-Information-Extractor/blob/main/ai_application_workflow%20(2).png)

### Diagram Description:
1. **User**: The end-user interacts with the application via the Streamlit frontend.
2. **Streamlit App**: The frontend built using Streamlit.
3. **FastAPI Backend**: The backend server that handles data processing.
4. **Data Extraction**:
   - **PyMuPDF / camelot**: For extracting data from PDF files using Open Source tools.
   - **Azure Document Intelligence and Adobe API Extract API**: For extracting data from PDF files using Enterprise tools.
   - **BeautifulSoup**: For web scraping using Open Source Tools.
   - **APIFY**: For web scraping using Enterprise Tools.
5. **Standardization Tools**:
   - **Docling**: A custom tool for standardizing conversions from pdfs to markdowns.
   - **MarkItDown**: Another custom tool for further data standardization.
6. **AWS S3 Bucket**: Used for storing processed data.
7. **Google Cloud Run**: Used for Deploying FastAPI applications
8. **Streamlit In-builtDeployment**: Used for Deploying Streamlit application for UI/UX. 

---

## Components

1. **User**: The end-user interacts with the application via the Streamlit frontend.
2. **Streamlit Frontend**: A custom frontend built using Streamlit for user interaction.
3. **FastAPI Backend**: A backend server built using FastAPI to handle data processing and communication with other services.
4. **Data Extraction**:
   - **PyPDF2 / pdfplumber**: For extracting data from PDF files.
   - **BeautifulSoup/Scrapy**: For web scraping.
   - **Microsoft Document Intelligence**: For enterprise-level document processing.
5. **Standardization Tools**:
   - **Docling**: A custom tool for standardizing extracted data.
   - **MarkItDown**: Another custom tool for further data standardization.
6. **AWS S3 Bucket**: Used for storing processed data.

---

## Workflow Steps

1. The **User** uploads data via the **Streamlit Frontend**.
2. The **Frontend** sends the data to the **FastAPI Backend**.
3. The **Backend** processes the data using one or more of the following:
   - **PyMuPDF / Camelot** for open source PDF extraction.
   - **BeautifulSoup / Scrapy** for open source webscraping.
   - **Microsoft Document Intelligence** for enterprise document processing.
   - **APIFy** for enterprise webscraping.
4. The extracted data is standardized using **Docling** in the pdf_process_pipeline and **MarkItDown** for webscraping_pipeline opensource.(Note:APIFy parses and generates markdown)
5. The processed data is stored in an **AWS S3 Bucket**.
6. The **Frontend** retrieves the processed data from the **S3 Bucket** and displays it to the **User**.

---

## Prerequisites

- Python 3.7+
- [Diagrams](https://diagrams.mingrammer.com/) library for generating the workflow diagram.
- AWS account with S3 bucket access.
- Streamlit and FastAPI installed for frontend and backend development and also other libraries.

---
## Installation

1.Clone the repository:

   ```bash
   git clone https://github.com/yourusername/ai-application-workflow.git
   cd ai-application-workflow
   ```
2.Create a .env file and add the required credentials:

   ```bash
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=your_aws_region
   AZURE_DOCUMENT_INTELLIGENCE_KEY=your_azure_key
   AZURE_FORM_RECOGNIZER_ENDPOINT=aws_form_recognizer_endpoint
   APIFY_TOKEN=your_apify_token
   ```
   
3. Ensure you have the custom icons (`microsoft.png`, `docling.png`, `markitdown.png`, `streamlit.png`) in the `./icons/` directory.
4. Generate the workflow diagram:
   ```bash
   python generate_diagram.py
   ```

4.Install dependencies:
create venv inside api and frotend folder
```bash
cd api
python -m venv venv
venv/Scripts/activate
pip install -r requirements
```
in new terminal
```bash
cd frontend
python -m venv venv
venv/Scripts/activate
pip install -r requirements
```
## Usage for Testing Locally

1. Run the FastAPI backend:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8080  
   ```

2. Run the Streamlit frontend:
   in another term
   ```bash
   streamlit run frontend.py
   ```

4. Open your browser and navigate to `http://localhost:8501` to interact with the application.

---

## Deployment Strategies to Gcloud:
1.Dockerise
   a.There are 2 DockerFiles in the frontend(Streamlit) and api(FASTAPI) folders.
   b.After installing Docker Desktop,create the docker images using the following commands
   create the fast api docker image
   before that run the following commands to authorize Google Cloud SDK.And make sure you run these command in the root directory of the project.
   
## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

### Notes:
- Replace `yourusername` in the repository URL with your actual GitHub username.
- Ensure the `generate_diagram.py` script is created to generate the workflow diagram.
- Update the `LICENSE` file if you choose a different license.

Let me know if you need further assistance!
