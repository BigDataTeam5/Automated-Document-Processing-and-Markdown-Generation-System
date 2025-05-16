import logging
import time
from pathlib import Path
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import FigureElement, InputFormat, Table
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
import boto3
import os
from PDF_Extraction_and_Markdown_Generation.open_source_parsing import upload_file_to_s3

# AWS S3 Configuration
s3 = boto3.client('s3',
                  aws_access_key_id=os.getenv('AWS_SERVER_PUBLIC_KEY'),
                  aws_secret_access_key=os.getenv('AWS_SERVER_SECRET_KEY'))
bucket_name = os.getenv('AWS_BUCKET_NAME')

# Constants
IMAGE_RESOLUTION_SCALE = 2.0

def main(pdf_path,service_type):
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path(pdf_path)
    output_dir = Path(f"output/{Path(pdf_path).stem}")


    # Configure pipeline options
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    start_time = time.time()
    # Convert the document
    conv_res = doc_converter.convert(input_doc_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    doc_filename = conv_res.input.file.stem
# Define job-specific folder based on PDF filename and service type
    job_folder = f"{doc_filename}-{service_type}"
    s3_folder = f"pdf_processing_pipeline/markdown_outputs/{job_folder}/"

    # Create a local output directory for the job
    output_dir = output_dir / job_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    # ✅ Save page images inside the job-specific folder
    for page_no, page in conv_res.document.pages.items():
        page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
        with page_image_filename.open("wb") as fp:
            page.image.pil_image.save(fp, format="PNG")
        # ✅ Upload to S3 inside the job-specific folder
        upload_file_to_s3(str(page_image_filename), f"{s3_folder}{page_image_filename.name}")

    # ✅ Save images of tables and figures inside the job-specific folder
    table_counter = 0
    picture_counter = 0
    for element, _level in conv_res.document.iterate_items():
        if isinstance(element, TableItem):
            table_counter += 1
            element_image_filename = output_dir / f"{doc_filename}-table-{table_counter}.png"
            with element_image_filename.open("wb") as fp:
                element.get_image(conv_res.document).save(fp, "PNG")
            # ✅ Upload to S3 inside the job-specific folder
            upload_file_to_s3(str(element_image_filename), f"{s3_folder}{element_image_filename.name}")

        if isinstance(element, PictureItem):
            picture_counter += 1
            element_image_filename = output_dir / f"{doc_filename}-picture-{picture_counter}.png"
            with element_image_filename.open("wb") as fp:
                element.get_image(conv_res.document).save(fp, "PNG")
            # ✅ Upload to S3 inside the job-specific folder
            upload_file_to_s3(str(element_image_filename), f"{s3_folder}{element_image_filename.name}")

    # ✅ Save markdown with embedded images inside the job-specific folder
    md_filename_embedded = output_dir / f"{doc_filename}-with-images.md"
    conv_res.document.save_as_markdown(md_filename_embedded, image_mode=ImageRefMode.EMBEDDED)
    # ✅ Upload to S3 inside the job-specific folder
    upload_file_to_s3(str(md_filename_embedded), f"{s3_folder}{md_filename_embedded.name}")

    # ✅ Save markdown with externally referenced images inside the job-specific folder
    md_filename_referenced = output_dir / f"{doc_filename}-with-image-refs.md"
    conv_res.document.save_as_markdown(md_filename_referenced, image_mode=ImageRefMode.REFERENCED)
    # ✅ Upload to S3 inside the job-specific folder
    upload_file_to_s3(str(md_filename_referenced), f"{s3_folder}{md_filename_referenced.name}")

    end_time = time.time() - start_time
    logging.info(f"Document converted and saved in {end_time:.2f} seconds. Files stored in: {s3_folder}")