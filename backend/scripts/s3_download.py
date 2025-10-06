import os
import urllib.request

url="http://localhost:9000/annotation-app-bucket/user_1/hi?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=admin%2F20250831%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20250831T035352Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=99e75fd4d41293443b3b2ed743340d60477be440618c0c3a30ab5b5992410132"

with urllib.request.urlopen(url) as r:
    data = r.read()
    FILE_NAME: str = "downloaded_file"
    SCRIPT_DIRECTORY: str = os.path.dirname(os.path.abspath(__file__))

    file_path: str = os.path.join(SCRIPT_DIRECTORY, FILE_NAME)

    with open(file_path, "wb") as output_file:
        output_file.write(data)
