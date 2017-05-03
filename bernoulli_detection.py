##UNUSED CURRENTLY

import face_recognition
import asyncio, aiohttp, os, re, pickle
from PIL import Image
from io import BytesIO
from urllib import parse

fileNameRE = re.compile('\\/(\w+\\.\\w+)')

DICTIONARY_NAME = os.getcwd() + "/bernInfrac.pickle"
ENCODING_NAME = os.getcwd() + "/bern_enc.dat"

bern_enc = []
with open(ENCODING_NAME, "rb") as f:
    bern_enc = pickle.load(f)

def dumpTable():
    with open(ENCODING_NAME,'wb') as f:
        pickle.dump(bern_enc, f)

async def checkImage(attachments):
    for attachment in attachments:
        url = attachment.get("url")
        print("image downloaded")
        return(await checkUrlImage(url))

async def checkUrlImage(url):
    res = False
    path = parse.urlparse(url).path
    path = fileNameRE.search(str(path)).group(1)
    filepath = os.getcwd() + "/" + path
    print(filepath)
    print("filepath determined")
    async with aiohttp.get(url) as r:
        img = await r.read()
        with open(filepath, "wb") as f:
            f.write(img)
            print("image written")
    r.close()
    f.close()
    res = await recognize(filepath)
    print("result returned")
    os.remove(filepath)
    print("filed removed")
    return(res)

async def recognize(filename):
    unknown = face_recognition.load_image_file(filename)
    print("image loaded")
    unk_enc = face_recognition.face_encodings(unknown)
    print("image encoded")
    if(len(unk_enc) > 0):
        results = face_recognition.compare_faces([bern_enc], unk_enc[0])
        print("image compared")
        return(results[0])
    return(False)
