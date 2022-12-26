import json
import boto3
import botocore
from PyPDF2 import PdfFileReader, PdfFileWriter
import os

def publish_message(topic_arn, message, subject):
    """
    Publishes a message to a topic.
    """
    sns_client = boto3.client('sns')
    try:

        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=subject,
        )['MessageId']

    except ClientError:
        logger.exception(f'Could not publish message to the topic.')
        raise
    else:
        return response

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

        output_filename = f'/tmp/{path.strip("/tmp/").strip(".pdf")}_INV_{str(page)}.pdf'

        with open(output_filename, 'wb') as out:
            pdf_writer.write(out)
        list_of_files_name.append(output_filename)
        
    return list_of_files_name

TOPIC_ARN = os.environ['TOPIC_ARN']

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
    object_ref_str = event['Records'][0]['dynamodb']['NewImage']['obj_ref']['S']
    object_ref = json.loads(object_ref_str)
    BUCKET_NAME = object_ref.get('BUCKET_NAME')
    OBJECT_KEY = object_ref.get('KEY')

    sns_client = boto3.client('sns')
    # Get the service client
    s3 = boto3.resource('s3')

    try:
        s3.Bucket(BUCKET_NAME).download_file(OBJECT_KEY, f'/tmp/{OBJECT_KEY}')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    list_of_file_name = separate_pdf(f'/tmp/{OBJECT_KEY}')

    PDF_PAGES_BUCKET = os.environ['PDF_PAGES_BUCKET']
    for file in list_of_file_name:
        # Naming convention for the file to be uploaded to S3
        OBJECT_KEY = file.lstrip('/tmp/')
        s3 = boto3.client('s3')
        s3.upload_file(file, PDF_PAGES_BUCKET, 
            OBJECT_KEY,
            ExtraArgs={'ContentType': 'application/pdf'}
            
            )
        publish_message(TOPIC_ARN, 
                        subject="SavePdfPages", 
                        message=json.dumps({
                            "ATTACHMENT_ID": event['Records'][0]['dynamodb']['NewImage']['id']['S'],
                            "BUCKET_NAME": PDF_PAGES_BUCKET,
                            "KEY": OBJECT_KEY
                        }))        

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "success",
            }
        ),
    }
