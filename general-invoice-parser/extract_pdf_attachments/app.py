import json


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
    records = event['Records'][0] 
    res = json.loads(records['Sns']['Message'])
    EMAIL_OBJ_KEY = res['receipt']['action']['objectKey']
    BUCKET_NAME = res['receipt']['action']['bucketName']
    ATTACHMENTS_BUCKET = os.environ['ATTACHMENTS']

    

    # Get the service client
    s3 = boto3.client('s3')

    # Download object at bucket-name with key-name to tmp.txt
    s3.download_file(BUCKET_NAME, EMAIL_OBJ_KEY , "/tmp/temp.txt")
    with open('/tmp/temp.txt') as f:
        data = f.read()
    
    # Extract the email contents
    payloads = email.message_from_string(data)
    # Isolate Content-Type
    list_of_allowed_content_types = ['application/pdf']

    # Iterate through the payloads to find content matching the allowed content types
    for payload in payloads.get_payload():
        if payload.get_content_type() in list_of_allowed_content_types:
            print("Following Content-type found:",payload.get_content_type())
            print('Attachments with the filename:',payload.get_filename(), 'detected!')
            file_name = payload.get_filename()
            file_name = file_name.replace(" ", "_")
            file_bytes = payload.get_payload()
            content_type = payload.get_content_type()

            # Save in temp file to be uploaded to S3
            with open("/tmp/"+file_name, "wb") as f:
                f.write(base64.b64decode(file_bytes))
            temp_pdf_filename = "/tmp/"+file_name

            # Upload to S3 attachments bucket
            s3.upload_file(temp_pdf_filename, ATTACHMENTS_BUCKET, file_name)

            
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "hello world",
            }
        ),
    }
