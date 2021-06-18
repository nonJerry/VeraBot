#External
import logging
from PIL import Image, ImageEnhance, ImageOps
import requests
import pytesseract as Tess
# Comment out this tesserocr import if changing stuff here when testing locally
import tesserocr
#Python
from functools import partial
import asyncio
import gc
#Internal
from utility import Utility

class OCR:
    bot = None
    local = None

    @classmethod
    def setup(cls, bot, local):
        cls.bot = bot
        cls.local = local

    @staticmethod
    async def detect_image_date(img_url, lang):
        logging.info("Using %s OCR", lang)
        text, inverted_text = await asyncio.wait_for(OCR.detect_image_text(img_url, lang), timeout = 90)

        img_date = Utility.date_from_txt(inverted_text, lang) or Utility.date_from_txt(text, lang)
        return img_date

    ### Tesseract text detection
    @classmethod
    async def detect_image_text(cls, img_url, lang, size_factor = 1.6):
        # Uses Tesseract to detect text from url img 
        # return tuple of two possible text: normal and inverted

        # Set partial function for image_to_text
        if(cls.local):
            logging.warn("Using local OCR!!!")
            img_to_txt = partial(Tess.image_to_string, timeout=44)
        else:
            tess_path = r"/app/.apt/usr/share/tesseract-ocr/4.00/tessdata"
            img_to_txt = partial(tesserocr.image_to_text, lang=lang, path = tess_path)

        # Get image from url
        with requests.get(img_url, stream=True) as img_response:
            img_response.raw.decode_content = True


            with Image.open(img_response.raw) as img:
                img.load()

                width, height = img.size
                
                resize = False
                if width > 1920:
                    width = 1920
                    resize = True
                if height > 1080:
                    height = 1080
                    resize = True
                if resize:
                    img = img.resize((width, height))


                img = img.crop((3, 0, img.size[0], img.size[1]))
                resized = img.resize(
                    (int(img.size[0] * size_factor), int(img.size[1] * size_factor)), Image.ANTIALIAS
                )
                enhancer = ImageEnhance.Sharpness(resized)
                factor = 3
                img = enhancer.enhance(factor)


                #remove alpha channel and invert image
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if len(img.split()) >= 4 else None) # 3 is the alpha channel
                    img = background

                # get text (run as coroutine to not block the event loop)
                text = await cls.bot.loop.run_in_executor(None, img_to_txt, img)
                logging.debug("Recognized text on %s:\n%s", img_url, text)

                # use inverted image
                with ImageOps.invert(img) as inverted_img:

                    # get inverted text (run as coroutine to not block the event loop)
                    inverted_text = await cls.bot.loop.run_in_executor(None, img_to_txt, inverted_img)
                    logging.debug("Recognized inverted text on %s:\n%s", img_url, inverted_text)
                    
        gc.collect()
        return (text, inverted_text)