import json
import boto3
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
    # Parse bucketname and key from event
    # feed bucketname and key to textract
    # save textract output to dynamodb
    # write to t
    print(event)
    obj_ref = json.loads(event['Records'][0]['Sns']['Message'])
    BUCKET_NAME = obj_ref['BUCKET_NAME']
    OBJECT_KEY = obj_ref['KEY']
    ATTACHMENT_ID = obj_ref['ATTACHMENT_ID']
    del obj_ref['ATTACHMENT_ID']
    textractmodule = boto3.client('textract')
    textract_response = textractmodule.analyze_expense(
            Document={
                'S3Object': {
                    'Bucket': BUCKET_NAME,
                    'Name': OBJECT_KEY
                    }})

    S3_URL = f"https://{BUCKET_NAME}.s3.amazonaws.com/{OBJECT_KEY}"
    query = f"""
    mutation MyMutation($obj_ref: String = "{S3_URL}", 
                        $textract_result: String = {json.dumps(json.dumps(textract_response))}, 
                        $attachmentID: ID = "{ATTACHMENT_ID}",
                        $s3_bucket_name: String = "{BUCKET_NAME}", 
                        $s3_bucket_key: String = "{OBJECT_KEY}"
                        ) {{
    createPage(input: {{attachmentID: $attachmentID, obj_ref: $obj_ref, s3_bucket_key: $s3_bucket_key, s3_bucket_name: $s3_bucket_name, textract_result: $textract_result}}) {{
                id
            }}
    }}
        """

    response = query_graphql_ap_inbox_db(accessToken, endpoint, query)


    cloudwatch_client = boto3.client('cloudwatch')

    cloudwatch_client.put_metric_data(
        Namespace='Gumps AP Inbox',
        MetricData = [
            {
                'MetricName': 'Pages of Pdf Extracted',
                'Unit': "None",
                'Value': 1
            }],
        
        )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "success!",
            }
        ),
    }
