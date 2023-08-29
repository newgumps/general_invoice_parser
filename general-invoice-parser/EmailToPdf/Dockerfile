FROM public.ecr.aws/lambda/python:3.8

COPY app.py requirements.txt ./

# Explicitly uninstall urllib3 v2.0 and install packages without cache
RUN python3.8 -m pip uninstall urllib3 -y
RUN python3.8 -m pip install --no-cache-dir -r requirements.txt -t .

# Command can be overwritten by providing a different command in the template directly.
CMD ["app.lambda_handler"]
