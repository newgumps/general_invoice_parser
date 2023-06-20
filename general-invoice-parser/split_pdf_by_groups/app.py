import json
import PyPDF2
import boto3
import re

def make_filename_friendly(s):
    # Remove any leading or trailing whitespaces
    s = s.strip()
    
    # Replace characters not allowed in filenames with underscores
    s = re.sub(r'[<>:"/\\|?*]', '_', s)
    
    # Remove consecutive underscores
    s = re.sub(r'[_]+', '_', s)
    
    # Remove any trailing periods
    s = re.sub(r'\.+$', '', s)
    
    # Truncate the filename to a maximum length of 255 characters
    s = s[:255]
    
    return s
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
    BUCKET_NAME = event['extract_pdf_attachments']['attachments']['BUCKET_NAME']
    KEY = event['extract_pdf_attachments']['attachments']['KEY']
    rename_files_parts = event['File_Names']['File_Names']['re_name_file_name']
    s3 = boto3.client('s3')
    s3.download_file(BUCKET_NAME, KEY, "/tmp/temp.pdf")
    groups = event['PageCompile']['PageCompile']['Groups of Commons']
    def split_pdf_by_groups(input_pdf, output_prefix, page_groups):
        list_of_files_upload_to_s3 = []
        with open(input_pdf, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            for group_index, group in enumerate(page_groups):
                pdf_writer = PyPDF2.PdfWriter()

                for page_num in group:
                    print(page_num)
                    pdf_writer.add_page(pdf_reader.pages[(int(page_num) - 1)])
                
                if rename_files_parts[group_index]['INVOICE_RECEIPT_ID'] == None:
                    rename_files_parts[group_index]['INVOICE_RECEIPT_ID'] = ''
                if rename_files_parts[group_index]['PO_NUMBER'] == None:
                    rename_files_parts[group_index]['PO_NUMBER'] = ''
                
                output_filename = (rename_files_parts[group_index]['INVOICE_DATE'] + "_" ) + rename_files_parts[group_index]['INVOICE_RECEIPT_ID'].replace('/','') +  '_' +rename_files_parts[group_index]['PO_NUMBER'] + '.pdf'
                output_filename = output_filename.replace(' ', '')
                output_filename = make_filename_friendly(output_filename)
                with open("/tmp/"+output_filename, 'wb') as output_pdf:
                    pdf_writer.write(output_pdf)
                with open("/tmp/"+output_filename, 'rb') as output_pdf:
                    s3.upload_fileobj(output_pdf, BUCKET_NAME, output_filename)
                list_of_files_upload_to_s3.append({'BUCKET_NAME': BUCKET_NAME, 
                                                    'KEY': output_filename,
                                                    'PO_NUMBER': make_filename_friendly(rename_files_parts[group_index]['PO_NUMBER']),
                                                    'INVOICE_RECEIPT_ID': make_filename_friendly(rename_files_parts[group_index]['INVOICE_RECEIPT_ID']),
                                                    'PAGE_ID': rename_files_parts[group_index]['PAGE_ID'],})
                print(group_index)
                print(f"Created: {output_filename}")

        return list_of_files_upload_to_s3
    list_1 = split_pdf_by_groups("/tmp/temp.pdf", None, groups)
    return {
        "statusCode": 200,
        "body": list_1
    }
