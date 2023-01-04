import csv
from datetime import datetime
from netsuitesdk import NetSuiteConnection
from io import BytesIO
import json
import boto3


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

    NSSECRETS = '/winward-invoice-pdf-to-csv-upload-to-ns/key-secrets'


    #Import Secrets
    secrets_parameter = boto3.client('ssm')
    parameter = secrets_parameter.get_parameter(Name=NSSECRETS, WithDecryption=True)
    get_secrets = parameter['Parameter']['Value']
    secrets = json.loads(get_secrets)


    # Production
    NS_CONSUMER_KEY = secrets['NS_CONSUMER_KEY']
    NS_CONSUMER_SECRET = secrets['NS_CONSUMER_SECRET']
    NS_TOKEN_ID = secrets['NS_TOKEN_ID']
    NS_TOKEN_SECRET = secrets['NS_TOKEN_SECRET']
    NETSUITE_ACCOUNT_ID = secrets['NETSUITE_ACCOUNT_ID']

    # Sandbox
    TEST_CONSUMER_KEY = secrets['TEST_CONSUMER_KEY']
    TEST_CONSUMER_SECRET = secrets['TEST_CONSUMER_SECRET']
    TEST_TOKEN_ID = secrets['TEST_TOKEN_ID']
    TEST_TOKEN_SECRET = secrets['TEST_TOKEN_SECRET']
    TEST_ACCOUNT_ID = secrets['TEST_ACCOUNT_ID']

    def connect(modes: str):
        if modes.lower() == 'test':

            nc = NetSuiteConnection(
            account=TEST_ACCOUNT_ID,
            consumer_key=TEST_CONSUMER_KEY,
            consumer_secret=TEST_CONSUMER_SECRET,
            token_key=TEST_TOKEN_ID,
            token_secret=TEST_TOKEN_SECRET,
            caching=False
            )
            try:
                return nc
            except:
                return "Connection Failed :("

        elif modes.lower() == 'production':

            nc = NetSuiteConnection(
                account=NETSUITE_ACCOUNT_ID,
                consumer_key=NS_CONSUMER_KEY,
                consumer_secret=NS_CONSUMER_SECRET,
                token_key=NS_TOKEN_ID,
                token_secret=NS_TOKEN_SECRET,
                caching=False
            )
            
            try:
                return nc

            except:
                return "Connection Failed"

        else:
            return "Invalid modes selection! Choose either 'production' or 'test'."

        return "Something went wrong. Try again."

    def upload(conn, file_name, folder_internal_id:str, name=None):
        # Require Folder Name.
        # Require path the desired files.
        # Check Media types
        # Upload files with proper Media types require by NS.
        # Return Passing Response.

        # Check if folder Exist.
        print('Proper Folder Check!')
        internal_id = folder_internal_id
        search_file = None
        folders = conn.folders.get_all()
        print('Searching...')
        searched_folder = None
        for index, folder in enumerate(folders):
            if folder['internalId'] == internal_id:
                print('Folder located!')
                searched_folder = folder
        if searched_folder == None:
            return 'Folder Missing Error: Incorrect Folder InternalId.'
            
        folder_ref = {'internalId': searched_folder['internalId'], 'type': 'folder'}

        file_type = file_name.split('.')[-1]

        # Dictionary of Avaliable Mediatypes
        media_type_dict = {
            'xlsx':'_EXCEL',
            'csv':'_CSV',
            'pdf':'_PDF',
            'png':'_PNGIMAGE',
            'jpg':'_JPGIMAGE',
            'jpeg':'_JPGIMAGE'
        }
        if name == None:
            name = file_name
        # Checking for supported media types.
        print('Checking for supported media types.')
        if file_type in media_type_dict:

            media_type = media_type_dict[file_type]

            with open(file_name, "rb") as file:
                buf = BytesIO(file.read())

            file_to_be_upload_json = {
                'folder':folder_ref,
                'name':name,
                'externalId':name,
                'textFileEncoding':'_utf8',
                'FileAttachFrom':'_computer',
                'content': buf.getvalue() ,
                'mediaType': media_type,
                'isOnline': 'true'
            }
            print('Attempting to upload.')
            return conn.files.post(file_to_be_upload_json)
            
        elif file_type not in media_type_dict:
            return 'Invalid: Unsupported File types.'

        return "Try Checking Connection. or Reconnect."

    # Get the current time
    now = datetime.now()

    # Convert the datetime object to a string in the 'yyyy-mm-dd_hh_mm_ss' format
    time_stamp = now.strftime('%Y-%m-%d_%H_%M_%S')
    file_name = f"processed_invoice_csv_{time_stamp}.csv"

    headers =  json.loads(event['Records'][0]['body'])['Headers']

    # Open a file in write mode
    with open('/tmp/'+ file_name, 'w', newline='') as file:
        # Create a CSV writer object
        writer = csv.writer(file)

        # Write the column headers
        writer.writerow(headers)
    
    # Write some rows of data
        for csv_line in event['Records']:
            writer.writerow(json.loads(csv_line['body'])['Body'])

    UPLOAD_CSV_FOLDER_INTERNAL_ID = '15684'
    connection = connect('production')
    try:
        upload_response = upload(connection, '/tmp/'+file_name, UPLOAD_CSV_FOLDER_INTERNAL_ID, file_name)
        print(upload_response)
    except:
        "Failure to connect"

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "success!",
            }
        ),
    }
