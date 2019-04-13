import collections
import pickle
import os.path
import random
import re
import requests
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import tweepy
import json


#  Make sure you have a twitter_credentials.json file with the following format:
# {
#   "consumer_key": "...",
#   "consumer_secret": "...",
#   "access_token": "...",
#   "access_token_secret": "..."
# }
from saucenao import SauceNao

folder = '1kN9NxJdUDRw8tBvxwBcx-iIt9Re4_zRY'

with open('twitter_credentials.json') as f:
    twitter_credentials = json.load(f)

with open('messages.json') as f:
    messages = json.load(f)

auth = tweepy.OAuthHandler(twitter_credentials['consumer_key'], twitter_credentials['consumer_secret'])
auth.set_access_token(twitter_credentials['access_token'], twitter_credentials['access_token_secret'])
api = tweepy.API(auth)


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el

def main():
    page_token = None
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    items = []
    # Call the Drive v3 API
    while True:
        results = service.files().list(
            pageSize=1000,
            pageToken=page_token,
            fields='nextPageToken, files(id, name, webContentLink, mimeType)',
            q=f"'{folder}' in parents and trashed = false and mimeType contains 'image'").execute()
        items += results.get('files', [])
        page_token = results.get('nextPageToken', None)
        if not page_token:
            break

    print(len(items))


    if not items:
        print('No files found.')
    else:
        while True:
            item = random.choice(items)
            if 'webContentLink' in item.keys():
                url = item['webContentLink'].replace('&export=download', '')
                filename = f'temp.{item["mimeType"].replace("image/","")}'
                request = requests.get(url, stream=True)
                if request.status_code == 200:
                    with open(filename, 'wb') as image:
                        for chunk in request:
                            image.write(chunk)
                    saucenao = SauceNao(directory='', databases=999, minimum_similarity=92,
                                        combine_api_types=False, api_key='',
                                        exclude_categories='', move_to_categories=False, use_author_as_category=False,
                                        output_type=SauceNao.API_HTML_TYPE, start_file='',
                                        title_minimum_similarity=90)
                    filtered_results = saucenao.check_file(file_name=filename)
                    print(filtered_results)
                    sauces = [{'pixiv_id': [c for c in result['data']['content'] if 'Pixiv' in c], 'urls': result['data']['ext_urls']} for result in filtered_results]
                    p = re.compile('(?<=Pixiv ID: )\d+')
                    sauce_urls = list(flatten([f'https://www.pixiv.net/member_illust.php?mode=medium&illust_id={p.search(sauce["pixiv_id"][0]).group(0)}' if sauce['pixiv_id'] else [url for url in sauce['urls']] for sauce in sauces]))
                    if sauce_urls:
                        print(sauce_urls)
                        message = random.choice(messages).format(sauce_urls[0])
                        api.update_with_media(filename, status=message)
                        os.remove(filename)
                        break
                    os.remove(filename)
                else:
                    print("Unable to download image")


if __name__ == '__main__':
    main()
