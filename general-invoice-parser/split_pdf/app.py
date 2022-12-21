import json
import boto3
from PyPDF2 import PdfFileReader, PdfFileWriter

def separate_pdf(path):
    """Helper functions: Split pdf by Page per pages.

    Args:
        path (path): _path to pdf_
        list_po (list): _list of PO #_
        list_inv_date (list): _list of inventory date_
        list_inv_name (list): _list of inventory name_

    Returns:
        _list of file name_: _list type list: of splitted filename_
    """
    pdf = PdfFileReader(path)
    list_of_files_name = []
    for page in range(pdf.getNumPages()):
        pdf_writer = PdfFileWriter()
        pdf_writer.addPage(pdf.getPage(page))

        output_filename = f'/tmp/{fname.strip("/tmp/").strip(".pdf")}_INV_{str(page)}.pdf'

        with open(output_filename, 'wb') as out:
            pdf_writer.write(out)
        list_of_files_name.append(output_filename)
        
    return list_of_files_name

def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """
    print(event)
    # Grab the bucket name and key from the event. 

    # Save the file to /tmp

    # Call the separate_pdf function

    # Upload the file to S3

    # For each split file, invoke a lambda function: process_page_w_texttract
    
    # Return a 200 response

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "hello world",
            }
        ),
    }
