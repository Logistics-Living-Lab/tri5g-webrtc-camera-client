import argparse
import base64
import json
import os

import requests
from requests.auth import HTTPBasicAuth


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode('utf-8')
    return base64_string


def send_image_to_server(image_path, url, username, password):
    base64_image = image_to_base64(image_path)
    headers = {'Content-Type': 'application/json'}
    data = {'image': base64_image}

    response = requests.post(url, json=data, headers=headers, auth=HTTPBasicAuth(username, password))

    if response.status_code == 200:
        response_json = json.loads(response.text)
        if response_json['success'] == 'ok':
            print("Image successfully uploaded.")
    else:
        print(f"Failed to upload image. Status code: {response.status_code}")
        print(f"Response: {response.text}")


if __name__ == '__main__':
    IMAGE_FILE = 'pexels-fabianwiktor-994605.jpg'

    parser = argparse.ArgumentParser(
        description="Test connections Tri5G"
    )
    parser.add_argument("--url", help="URL", type=str)
    parser.add_argument("--username", help="Username", type=str)
    parser.add_argument("--password", help="Password", type=str)

    args = parser.parse_args()

    root_path = os.path.dirname(os.path.abspath(__file__))
    IMAGE_PATH = os.path.join(root_path, "images", IMAGE_FILE)
    send_image_to_server(IMAGE_PATH, args.url, args.username, args.password)
