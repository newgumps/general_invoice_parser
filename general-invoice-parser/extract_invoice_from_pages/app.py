import json
import os
import boto3
from dateutil.parser import parse
import datetime
import requests
accessToken = "da2-kdsrvisnq5g63iahdh44elttay"
endpoint = f"https://shu6fh2efbfj3hq4la4addeujm.appsync-api.us-east-1.amazonaws.com/graphql"

def query_graphql_ap_inbox_db(accessToken, endpoint, query):
    # establish a session with requests session
    session = requests.Session()
    # As found in AWS Appsync under Settings for your endpoint.
    APPSYNC_API_ENDPOINT_URL = endpoint
    # Now we can simply post the request...
    response = session.request(
        url=APPSYNC_API_ENDPOINT_URL,
        method='POST',
        headers={'x-api-key': accessToken},
        json={'query': query}
    )
    return response.json()


def parse_date(date_str):
    try:
        return parse(date_str)
    except ValueError:
        return None
def convert_to_aws_date(date):
    return date.strftime('%Y%m%dT%H%M%SZ')


def query_graphql_ap_inbox_db(accessToken, endpoint, query):
    # establish a session with requests session
    session = requests.Session()
    # As found in AWS Appsync under Settings for your endpoint.
    APPSYNC_API_ENDPOINT_URL = endpoint
    # Now we can simply post the request...
    response = session.request(
        url=APPSYNC_API_ENDPOINT_URL,
        method='POST',
        headers={'x-api-key': accessToken},
        json={'query': query}
    )
    return response.json()


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
    # Extract Invoice Information from pages
    document_dict_textract_extract = json.loads(event['Records'][0]['dynamodb']['NewImage']['textract_result']['S'])
    object_ref = json.loads(event['Records'][0]['dynamodb']['NewImage']['obj_ref']['S'])
    pagesID = json.loads(event['Records'][0]['dynamodb']['NewImage']['id']['S'])
    list_of_fields = [
        'INVOICE_RECEIPT_ID',
        'INVOICE_RECEIPT_DATE',
        'PO_NUMBER',
        'VENDOR_NAME'
    ]


    key_fields_value = {}
    for field in list_of_fields:
        key_fields_value[field] = {
            'Text': None,
            'Confidence': 0
        }
    for fields in document_dict_textract_extract['ExpenseDocuments'][0]['SummaryFields']:
        if fields['Type']['Text'] in list_of_fields:
            if fields['Type']['Confidence'] > key_fields_value[fields['Type']['Text']]['Confidence']:
                key_fields_value[fields['Type']['Text']] = {
                    'Text': fields['ValueDetection']['Text'],
                    'Confidence': fields['Type']['Confidence']
                }       
    
    INVOICE_RECEIPT_ID = key_fields_value['INVOICE_RECEIPT_ID']['Text']
    INVOICE_RECEIPT_DATE = key_fields_value['INVOICE_RECEIPT_DATE']['Text']
    PO_NUMBER = key_fields_value['PO_NUMBER']['Text']
    VENDOR_NAME = key_fields_value['VENDOR_NAME']['Text']
    print(type(INVOICE_RECEIPT_DATE))
    if INVOICE_RECEIPT_DATE is None:
        now = datetime.datetime.now()
        INVOICE_RECEIPT_DATE = now.strftime("%Y-%m-%d")

    if INVOICE_RECEIPT_ID is None:
        return "missing invoice receipt id"

    INVOICE_RECEIPT_DATE = INVOICE_RECEIPT_DATE.replace('/','-')
    INVOICE_RECEIPT_DATE = parse_date(INVOICE_RECEIPT_DATE)
    INVOICE_RECEIPT_DATE = convert_to_aws_date(INVOICE_RECEIPT_DATE)
    VENDOR_NAME = VENDOR_NAME.replace('.','')
    rename_pdf_file_name = INVOICE_RECEIPT_DATE + "_" + INVOICE_RECEIPT_ID + "_" + (PO_NUMBER or "POMISSING")+".pdf"

    PDF_BUCKET_NAME = object_ref['BUCKET_NAME']
    PDF_KEY = object_ref['KEY']

    # Save rename file to s3
    # Set the name of the bucket and the old and new keys (file names)
    s3 = boto3.client('s3')
    bucket_name = PDF_BUCKET_NAME
    old_key = PDF_KEY
    new_key = rename_pdf_file_name

    # Create an S3 client

    # Copy the file to the new key and delete the old key
    s3.copy_object(Bucket=bucket_name, CopySource={'Bucket': bucket_name, 'Key': old_key}, Key=new_key)



    # String representation of a date
    date_str = INVOICE_RECEIPT_DATE

    # Parse the string into a datetime object
    date = parse(date_str, fuzzy=True)

    aws_date = date.strftime('%Y-%m-%d')

    # Save invoice information to dynamodb
    graphql_query = f"""
    mutation MyMutation($invoice_date: AWSDate = "{aws_date}", $invoice_number: String = "{INVOICE_RECEIPT_ID}", $purchase_order: String = "{PO_NUMBER}") {{
    createInvoice(input: {{invoice_date: $invoice_date, invoice_number: $invoice_number, purchase_order: $purchase_order}})
    {{
                id
            }}
    }}

    """

    response = query_graphql_ap_inbox_db(accessToken, endpoint, graphql_query)

    # Create an SQS client
    sqs = boto3.client('sqs')

    # Set the queue URL and the message you want to send
    queue_url = os.environ['SQS_QUEUE_URL']
    message_body = {
        "Headers": ['Vendor Name', 
                    'Invoice Number', 
                    'Invoice Date', 
                    'PO Number', 
                    'S3 Links'],
        "Body": [VENDOR_NAME, 
                 INVOICE_RECEIPT_ID, 
                 INVOICE_RECEIPT_DATE, 
                 PO_NUMBER, 
                 "https://gumps-ap-inbox-automation-pdfpagesstorage-ck2ujlxmg3d5.s3.amazonaws.com/"+rename_pdf_file_name]
    }

    # Convert the message body to a JSON string
    message_body = json.dumps(message_body)

    # Publish the message to the specified SQS queue
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body
    )

    # Print the message ID of the published message
    print(response['MessageId'])

    # Vendor Name, Invoice Number, Invoice Date, PO Number, S3 Links
    # Update DynamoDB Invoice Status to "Send to CSV Compiler"

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "success",
            }
        ),
    }
