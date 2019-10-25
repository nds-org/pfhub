import os
import sys
import zipfile
from os import listdir

import requests
import yaml
import pprint
import re
from urllib.parse import urlparse, urlunparse
from pytube import YouTube

from box_adaptor import BoxAdaptor
from mdf_connect_client import MDFConnectClient



def zipdir(path, ziph):
    """
    Create a zipfile from a nested directory. Make the paths in the zip file
    relative to the root directory
    :param path: Path to the root directory
    :param ziph: zipfile handler
    :return:
    """
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       arcname=os.path.join(os.path.relpath(root, path),
                                            file))


def download_request(request, file_name, download_folder):
    f = open(os.path.join(download_folder, file_name), 'wb')
    for chunk in request.iter_content(chunk_size=512 * 1024):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
    f.close()


def download_google_drive(file_id, download_folder):
    url = "https://drive.google.com/uc?export=download&id={}".format(file_id)
    r = requests.get(url, allow_redirects=True)
    contents = r.headers['Content-Disposition'].split(';')

    # Extract the filename from the Content-Disposition header
    # It looks like this
    # ['attachment', 'filename="spi_b_ini.png"', "filename*=UTF-8''spi_b_ini.png"]
    f = [re.search('filename="(.*)"', d) for d in contents]
    f1 = list([x.group(1) for x in f if x])[0]

    download_request(r, f1, download_folder)


def download_raw_file(parsed_url, download_folder):
    file_name = parsed_url.path.split("/")[-1]
    ext = os.path.splitext(file_name)[-1]
    if ext not in ['.csv', '.png', '.txt', '.jpg', '']:
        print("ERROR: "+file_name, ext, len(ext))
        print(parsed_url)
        print(urlunparse(parsed_url))
    r = requests.get(urlunparse(parsed_url), allow_redirects=True)
    download_request(r, file_name, download_folder)


def download_youtube_video(parsed_url, download_folder):
    yt = YouTube(urlunparse(parsed_url))
    yt.streams.filter(progressive=True, file_extension='mp4').\
        order_by('resolution').desc().first().download(output_path=download_folder)


def download_figshare(parsed_url, download_folder):
    r = requests.get(urlunparse(parsed_url), allow_redirects=True)
    parsed_redirected_url = urlparse(r.url)
    file_name = parsed_redirected_url.path.split("/")[-1]
    print(file_name)
    download_request(r, file_name, download_folder)


pp = pprint.PrettyPrinter()
# box = BoxAdaptor(None)
# upload_folder = box.get_folder(91012140276)
mdfcc = MDFConnectClient(test=True, service_instance="prod")

for sim in listdir("../_data/simulations"):
    sim_folder = "../_data/simulations/{}".format(sim)
    if not os.path.isdir(sim_folder):
        continue
    print(sim)
    with open(os.path.join(sim_folder, 'meta.yaml')) as stream:
        try:
            meta = yaml.safe_load(stream)

            mdfcc.create_dc_block(

            )

            for data in meta['data']:
                if 'url' in data:
                    url = data['url']
                    foo = urlparse(url)

                    if foo.netloc == 'drive.google.com':
                        file_id = foo.query.split('=')[1]
                        download_google_drive(file_id, sim_folder)
                    elif foo.netloc == 'www.youtube.com':
                        download_youtube_video(foo, sim_folder)
                    elif foo.netloc == 'ndownloader.figshare.com':
                        download_figshare(foo, sim_folder)
                    else:
                        download_raw_file(foo, sim_folder)

            # zip_path = sim_folder + ".zip"
            # zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
            # zipdir(sim_folder, zipf)
            # zipf.close()
            # print("Uploading ", zip_path, " to box")
            #
            # box_file = box.upload_file(upload_folder, zip_path,
            #                                    sim + '.zip')

        except yaml.YAMLError as exc:
            print(exc)
