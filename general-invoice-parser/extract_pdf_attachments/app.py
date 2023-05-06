import boto3
import base64
import json
import os
import mailparser
import requests
import datetime
import re
import uuid

# Get Credentials
WORKDOCS_ACCOUNT_CREDENTIAL = json.loads(os.environ['WORKDOCS_ACCOUNT_CREDENTIAL'])

SECRET_KEY = WORKDOCS_ACCOUNT_CREDENTIAL.get('SECRET_KEY')
ACCESS_KEY = WORKDOCS_ACCOUNT_CREDENTIAL.get('ACCESS_KEY')
accessToken = WORKDOCS_ACCOUNT_CREDENTIAL.get('accessToken')
endpoint = WORKDOCS_ACCOUNT_CREDENTIAL.get('endpoint')

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
    print(event)
    records = event['Records'][0] 
    res = json.loads(records['Sns']['Message'])
    EMAIL_OBJ_KEY = res['receipt']['action']['objectKey']

    BUCKET_NAME = res['receipt']['action']['bucketName']
    ATTACHMENTS_BUCKET = os.environ['ATTACHMENTS_BUCKET']
    # Get the service client
    s3 = boto3.client('s3')

    # Download object at bucket-name with key-name to tmp.txt
    s3.download_file(BUCKET_NAME, EMAIL_OBJ_KEY , "/tmp/temp.txt")
    with open('/tmp/temp.txt') as f:
        data = f.read()

    # Extract the email contents
    mail = mailparser.parse_from_string(data)
    email_body = mail.body

    # Use a regex pattern to match the forwarded sender's email address
    forwarded_sender_pattern = re.compile(r"From: .*<(.+@.+)>")
    match = forwarded_sender_pattern.search(email_body)

    if match:
        original_sender_email = match.group(1)
    else:
        original_sender_email = None

    email_from = mail._from[0]
    object_ref = json.dumps({"BUCKET_NAME": BUCKET_NAME, "KEY": EMAIL_OBJ_KEY})

    inbox_date = mail.date.strftime('%Y-%m-%d')

    cloudwatch_client = boto3.client('cloudwatch')

    cloudwatch_client.put_metric_data(
        Namespace='Gumps AP Inbox',
        MetricData = [
            {
                'MetricName': 'Emails Received',
                'Unit': "None",
                'Value': 1
            }],
        
        )


    email_query = f"""  
        mutation MyMutation($Sender: AWSEmail = "{email_from[1]}",
                            $Extracted_Original_Sender: String = "{original_sender_email}",
                            $inbox_date: AWSDate = "{inbox_date}", 
                            $object_ref: AWSJSON = {json.dumps(object_ref)},
                            $process_datetime: AWSDateTime = "{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')}") {{
        createEmail(input: {{
                            Sender: $Sender,
                            Extracted_Original_Sender: $Extracted_Original_Sender,
                            inbox_date: $inbox_date, 
                            object_ref: $object_ref, 
                            process_datetime: $process_datetime}}) {{
            id
        }}
        }}

    """
    
    graphql_response = query_graphql_ap_inbox_db(accessToken, endpoint, email_query)
    print(graphql_response)

    email_id = graphql_response['data']['createEmail']['id']


    #Save Attachments
    payload = []
    for attachment in mail.mail_partial['attachments']:
        print(attachment.get('filename'))
        print(attachment.get('mail_content_type'))
        original_file_name = attachment.get('filename')
        original_file_name = original_file_name.lower()
        extensions_original = original_file_name.split(".")[-1].lower()
        # Generate a unique filename
        unique_id = str(uuid.uuid4())
        file_name = unique_id + "."+ extensions_original
        file_bytes = attachment.get('payload')
        content_type = attachment.get('mail_content_type')

        # Save in temp file to be uploaded to S3
        with open("/tmp/"+file_name, "wb") as f:
            f.write(base64.b64decode(file_bytes))
        temp_pdf_filename = "/tmp/"+file_name

        # Upload to S3 attachments bucket
        s3_response = s3.upload_file(temp_pdf_filename, ATTACHMENTS_BUCKET, file_name)
        attachments_ref = json.dumps({"BUCKET_NAME": ATTACHMENTS_BUCKET, "KEY": file_name})
        # Put Metric Data for Attachments Stored
        cloudwatch_client.put_metric_data(
            Namespace='Gumps AP Inbox',
            MetricData = [
                {
                    'MetricName': ' Attachments Stored',
                    'Dimensions': [
                        {
                            "Name": 'Content Type',
                            "Value": content_type
                        },
                        ],
                    'Unit': "None",
                    'Value': 1
                }],
            )
        cloudwatch_client.put_metric_data(
            Namespace='Gumps AP Inbox',
            MetricData = [
                {
                    'MetricName': ' Attachments Stored',

                    'Unit': "None",
                    'Value': 1
                }],
            )
        # Save to DB    

        #Generate Query String
        query_attachments = f"""
            mutation MyMutation2(
                $emailID: ID = "{email_id}", 
                $UUID: String = "{unique_id}"
                $obj_ref: String = {json.dumps(attachments_ref)}, 
                $type: String = "{content_type}") {{
            createAttachment(input: 
                    {{
                        emailID: $emailID, 
                        obj_ref: $obj_ref, 
                        UUID: $UUID,
                        type: $type
                        }}) {{
                    id
                }}
            }}
        """

        graphql_response = query_graphql_ap_inbox_db(accessToken, endpoint, query_attachments)
        print(graphql_response)
        ATTACHMENTS_ID = graphql_response['data']['createAttachment']['id']
        payload.append({
        "extract_pdf_attachments": {
            "Attachments": "Saved",
            "EmailId": email_id,
            "EmailFrom": email_from[1],
            "UUID": unique_id,
            "Attachments": extensions_original,
            "OriginalSender": original_sender_email,
            "email": json.loads(object_ref),
            "attachments": {"AttachmentId":ATTACHMENTS_ID,
                            "BUCKET_NAME": ATTACHMENTS_BUCKET, 
                            "KEY": file_name,
                            "OriginalFileName": original_file_name}
            }
            }
        )
    return payload
