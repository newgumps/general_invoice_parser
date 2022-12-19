import boto3
import base64
import json
import email 
import os
import mailparser
import requests
import datetime

ATTACHMENTS_BUCKET = os.environ['ATTACHMENTS_BUCKET']
accessToken = "da2-kdsrvisnq5g63iahdh44elttay"
endpoint = f"https://shu6fh2efbfj3hq4la4addeujm.appsync-api.us-east-1.amazonaws.com/graphql"

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

    # Get the service client
    s3 = boto3.client('s3')

    # Download object at bucket-name with key-name to tmp.txt
    s3.download_file(BUCKET_NAME, EMAIL_OBJ_KEY , "/tmp/temp.txt")
    with open('/tmp/temp.txt') as f:
        data = f.read()

    # Extract the email contents
    mail = mailparser.parse_from_string(data)
    email_from = mail._from[0]
    object_ref = json.dumps({"BUCKET_NAME": BUCKET_NAME, "KEY": EMAIL_OBJ_KEY})
    inbox_date = mail.date.strftime('%Y-%m-%d')

    email_query = f"""  
        mutation MyMutation($Sender: AWSEmail = "{email_from[1]}", $inbox_date: AWSDate = "{inbox_date}", $object_ref: AWSJSON = {json.dumps(object_ref)}, $process_datetime: AWSDateTime = "{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')}") {{
        createEmail(input: {{Sender: $Sender, inbox_date: $inbox_date, object_ref: $object_ref, process_datetime: $process_datetime}}) {{
            id
        }}
        }}

    """
    
    graphql_response = query_graphql_ap_inbox_db(accessToken, endpoint, email_query)

    email_id = graphql_response['id']

    #Save Attachments
    for attachment in mail.mail_partial['attachments']:
        print(attachment.get('filename'))
        print(attachment.get('mail_content_type'))
        file_name = attachment.get('filename')
        file_name = file_name.replace(" ", "_")
        file_bytes = attachment.get('payload')
        content_type = attachment.get('mail_content_type')

        # Save in temp file to be uploaded to S3
        with open("/tmp/"+file_name, "wb") as f:
            f.write(base64.b64decode(file_bytes))
        temp_pdf_filename = "/tmp/"+file_name

        # Upload to S3 attachments bucket
        s3_response = s3.upload_file(temp_pdf_filename, ATTACHMENTS_BUCKET, file_name)

        # Save to DB    

        #Generate Query String
        query_attachments = f"""
        mutation MyMutation2($emailID: ID = "{email_id}", $obj_ref: String = {json.dumps(attachments_ref)}, $type: String = "{content_type}") {{
        createAttachment(input: {{emailID: $emailID, obj_ref: $obj_ref, type: $type}}) {{
                id
            }}
        }}
        """

        graphql_response = query_graphql_ap_inbox_db(accessToken, endpoint, query_attachments)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "hello world",
            }
        ),
    }
