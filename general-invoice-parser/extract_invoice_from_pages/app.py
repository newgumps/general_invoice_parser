import json
import os
import boto3
from dateutil.parser import parse
import datetime
import requests
accessToken = "da2-kar2jm52tja5tcggis7sapyu7a"
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
    return date.strftime('%Y%m%d')


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
    # Extract Invoice Information from pages
    document_dict_textract_extract = event['ProcessWTextract']['ProcessWTextract']['TextractOutput']['process_with_textract']['textract_response']
    pagesID = event['ProcessWTextract']['ProcessWTextract']['TextractOutput']['process_with_textract']['PAGE_ID']
    s3_bucket_name = event['extract_pdf_attachments']['attachments']['BUCKET_NAME']
    s3_bucket_key = event['extract_pdf_attachments']['attachments']['KEY']
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
    if INVOICE_RECEIPT_DATE is None:
        now = datetime.datetime.now()
        INVOICE_RECEIPT_DATE = now.strftime("%Y-%m-%d")
    INVOICE_RECEIPT_DATE = INVOICE_RECEIPT_DATE.replace('/','-')
    INVOICE_RECEIPT_DATE = parse_date(INVOICE_RECEIPT_DATE)
    INVOICE_RECEIPT_DATE = convert_to_aws_date(INVOICE_RECEIPT_DATE)

    # String representation of a date
    date_str = INVOICE_RECEIPT_DATE

    # Parse the string into a datetime object
    date = parse(date_str, fuzzy=True)

    aws_date = date.strftime('%Y-%m-%d')

    # Save invoice information to dynamodb
    graphql_query = f"""
    mutation MyMutation($invoice_date: AWSDate = "{aws_date}",
                        $invoice_number: String = "{INVOICE_RECEIPT_ID}",  
                        $purchase_order: String = "{PO_NUMBER}",
                        $vendor_name: String = "{VENDOR_NAME}",
                        ) {{
    createInvoice(input: {{invoice_date: $invoice_date,
                           invoice_number: $invoice_number, 
                           object_ref: $object_ref,
                           vendor_name: $vendor_name, 
                           purchase_order: $purchase_order}})
    {{
                id,
                invoice_number,
                vendor_name
            }}
    }}

    """

    response = query_graphql_ap_inbox_db(accessToken, endpoint, graphql_query)

    print(response)

    return {
        "ExtractInvoiceFromPages": {
            "InvoiceNumber": INVOICE_RECEIPT_ID,
            "InvoiceDate": aws_date,
            "PurchaseOrder": PO_NUMBER,
            "VendorName": VENDOR_NAME,
        }
    }
