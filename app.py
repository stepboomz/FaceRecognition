import os
import cv2
from datetime import datetime
from imgurpython import ImgurClient
from flask import Flask, request, abort
from pyzbar.pyzbar import decode
from PIL import Image
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageMessage, ImageSendMessage
)

app = Flask(__name__)

senders, measures = [], {}
line_bot_api = LineBotApi('abTeZHrpH8QDHsF1IGqaNwPSiWRkXGK2ABeaui1CzEd70bh8PAHsvFV+zhNTKyZ3Jk72xe87Y+ebw28ChLCcNiAxh2WxxKqmHaxQDp40p7hdDQGo4eHTEzeppEFZCRJ+rXMux2sKlvmZVa6f1CUJ9wdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1ff98ebae21ae9e8b9e6c1c16ac1c4cf')


def save_image(path, content):
    with open(path, 'wb') as f:
        for c in content.iter_content():
            f.write(c)


def check(uid, senders, measures):
    if uid not in senders:
        now_timestamp = int(datetime.now().timestamp())
        if uid not in measures or now_timestamp > measures[uid] + 20:
            measures[uid] = now_timestamp
            return True
    return False


def upload_imgur(path):
    client_id = os.environ["IMGUR_ID"]
    client_secret = os.environ["IMGUR_SECRET"]
    client = ImgurClient(client_id, client_secret)
    image = client.upload_from_path(path, config=None, anon=True)
    return image["link"]


def face_recognition(path):
    image = cv2.imread(path)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    class_face = cv2.CascadeClassifier(
        'haarcascade_frontalface_alt.xml')
    facerect = class_face.detectMultiScale(
        gray_image, scaleFactor=1.1, minNeighbors=2, minSize=(30, 30))
    if len(facerect) == 0:
        return False
    for rect in facerect:
        cv2.rectangle(image, tuple(rect[0:2]), tuple(
            rect[0:2] + rect[2:4]), (255, 0, 0), thickness=2)
    cv2.imwrite(path, image)
    return True


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def response_message(event):
    if event.message.text == 'reaction:off':
        if event.source.user_id not in senders:
            senders.append(event.source.user_id)
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="画像に反応しないようにしました。"))
        return
    if event.message.text == 'reaction:on':
        if event.source.user_id in senders:
            senders.remove(event.source.user_id)
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="画像に反応するようにしました。"))
        return


@handler.add(MessageEvent, message=ImageMessage)
def response_message(event):
    if check(event.source.user_id, senders, measures) is False:
        return
    path = f'{event.message.id}.jpg'
    save_image(path, line_bot_api.get_message_content(event.message.id))
    if face_recognition(path):
        link = upload_imgur(path)
        image_message = ImageSendMessage(
            original_content_url=link,
            preview_image_url=link
        )
        line_bot_api.reply_message(
            event.reply_token, image_message)
    else:
        datas = decode(Image.open(path))
        if datas:
            text = "นี่คือผลลัพธ์ของการสแกนรหัส QR ในภาพ\n"
            decoded = [data[0].decode('utf-8', 'ignore') for data in datas]
            text += "\n".join(decoded)
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=text))
    os.remove(path)


if __name__ == "__main__":
    app.run()
