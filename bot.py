#!/usr/bin/env python3
import os
import sys
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime

# Try to import transformers; if not present, provide a friendly error.
try:
    from transformers import pipeline, set_seed
except Exception as e:
    print("Warning: transformers not installed or failed to import. Install requirements before running locally.")
    # We'll still continue so the script fails gracefully in CI if model isn't available.
    pipeline = None

# Environment / secrets
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
INSTAGRAM_ID = os.getenv("INSTAGRAM_ID")  # optional
CRYPTOPANIC_TOKEN = os.getenv("CRYPTOPANIC_TOKEN")

if not ACCESS_TOKEN or not PAGE_ID or not CRYPTOPANIC_TOKEN:
    print("ERROR: Please set ACCESS_TOKEN, PAGE_ID, and CRYPTOPANIC_TOKEN as repository secrets.")
    sys.exit(1)

def fetch_latest_headline():
    try:
        res = requests.get(f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_TOKEN}&public=true")
        data = res.json()
        if "results" in data and len(data["results"])>0:
            return data["results"][0]["title"]
        else:
            return "Crypto update: no headlines found."
    except Exception as e:
        print("Error fetching news:", e)
        return "Crypto update: couldn't fetch headlines."

def generate_caption(headline):
    # Prefer transformers if available; otherwise fall back to a simple template
    if pipeline is not None:
        try:
            gen = pipeline("text-generation", model="distilgpt2")
            set_seed(42)
            prompt = f"Write a short, catchy Instagram/Facebook caption about: {headline} Add relevant hashtags."
            out = gen(prompt, max_length=60, num_return_sequences=1)
            caption = out[0]["generated_text"].strip()
            # truncate to 5000 chars safe side for Graph API
            return caption[:2000]
        except Exception as e:
            print("Transformer generation failed:", e)
    # fallback
    return f"{headline} #Crypto #Bitcoin #Blockchain"

def make_image(headline, filename="post.jpg"):
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Try to use a truetype font if available, otherwise default
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 36)
    except:
        font = ImageFont.load_default()
    # split headline to multiple lines
    max_chars_per_line = 28
    words = headline.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars_per_line:
            cur += (" " if cur else "") + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    # vertical position
    y = 360
    for line in lines[:10]:
        w, h = draw.textsize(line, font=font)
        draw.text(((W - w) / 2, y), line, fill=(255,255,255), font=font)
        y += h + 8
    # footer
    footer = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    draw.text((30, H-60), footer, fill=(180,180,180), font=font)
    img.save(filename)
    return filename

def post_photo_to_page(image_path, caption):
    url = f"https://graph.facebook.com/{PAGE_ID}/photos"
    files = {"source": open(image_path, "rb")}
    data = {"caption": caption, "access_token": ACCESS_TOKEN}
    r = requests.post(url, files=files, data=data)
    try:
        return r.status_code, r.json()
    except:
        return r.status_code, r.text

def get_photo_images(photo_id):
    url = f"https://graph.facebook.com/{photo_id}?fields=images&access_token={ACCESS_TOKEN}"
    r = requests.get(url)
    try:
        return r.json().get("images", [])
    except:
        return []

def create_ig_media_from_url(image_url, caption):
    # create container
    url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_ID}/media"
    data = {"image_url": image_url, "caption": caption, "access_token": ACCESS_TOKEN}
    r = requests.post(url, data=data)
    return r.json()

def publish_ig_media(creation_id):
    url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_ID}/media_publish"
    data = {"creation_id": creation_id, "access_token": ACCESS_TOKEN}
    r = requests.post(url, data=data)
    return r.json()

def main():
    headline = fetch_latest_headline()
    print("Headline:", headline)
    caption = generate_caption(headline)
    print("Caption:", caption)
    image_file = "post.jpg"
    make_image(headline, image_file)
    print("Image created:", image_file)

    print("Posting image to Facebook Page...")
    status, resp = post_photo_to_page(image_file, caption)
    print("FB post response:", status, resp)

    if INSTAGRAM_ID:
        # try to obtain a public image URL from the uploaded photo
        try:
            photo_id = resp.get("id") if isinstance(resp, dict) else None
            if photo_id:
                images = get_photo_images(photo_id)
                if images:
                    image_url = images[0].get("source")
                    print("Using image URL for IG:", image_url)
                    container = create_ig_media_from_url(image_url, caption)
                    print("IG container response:", container)
                    creation_id = container.get("id")
                    if creation_id:
                        publish_resp = publish_ig_media(creation_id)
                        print("IG publish response:", publish_resp)
                    else:
                        print("IG container creation failed. Response:", container)
                else:
                    print("No images list returned for photo id:", photo_id)
            else:
                print("No photo id returned from FB upload; cannot post to Instagram automatically.")
        except Exception as e:
            print("Instagram posting flow failed:", e)
    else:
        print("INSTAGRAM_ID not set — skipping Instagram post.")

if __name__ == "__main__":
    main()
