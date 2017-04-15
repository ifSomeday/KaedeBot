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
        return(await checkUrlImage(url))

async def checkUrlImage(url):
    res = False
    path = parse.urlparse(url).path
    path = fileNameRE.search(str(path)).group(1)
    filepath = os.getcwd() + "/" + path
    print(filepath)
    async with aiohttp.get(url) as r:
        img = await r.read()
        with open(filepath, "wb") as f:
            f.write(img)
            print("image written")
        res = await recognize(filepath)
        os.remove(filepath)
        return(res)
    return(res)

async def recognize(filename):
    unknown = face_recognition.load_image_file(filename)
    try:
        unk_enc = face_recognition.face_encodings(unknown)[0]
        results = face_recognition.compare_faces([bern_enc], unk_enc)
        return(results[0])
    except:
        return(False)
    return("lol")
