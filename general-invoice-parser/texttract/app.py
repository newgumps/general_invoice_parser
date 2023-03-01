import json
import boto3
textract_client = boto3.client('textract')

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
    OBJECT_KEY = event['extract_pdf_attachments']['attachments']['KEY']
    BUCKET_NAME = event['extract_pdf_attachments']['attachments']['BUCKET_NAME']
    response = textract_client.analyze_expense(
            Document={
                'S3Object': {
                    'Bucket': BUCKET_NAME,
                    'Name': OBJECT_KEY
                    }})
    #TODO: SAVE TO S3   
    
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "hello world",
            }
        ),
    }
