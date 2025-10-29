# Crypto Auto Poster

This repository contains a simple, free bot that:
- Fetches latest crypto headlines from CryptoPanic
- Generates a short caption (using a small Hugging Face model, if available)
- Creates a black 1080x1080 image with the headline
- Posts to a Facebook Page and (optionally) to Instagram if `INSTAGRAM_ID` is set

## How to use

1. Create a GitHub repository and upload these files.
2. Add repository secrets: `ACCESS_TOKEN`, `PAGE_ID`, `CRYPTOPANIC_TOKEN`. Optionally add `INSTAGRAM_ID`.
3. Enable GitHub Actions for the repo (Actions tab).
4. The workflow runs every 6 hours by default. You can trigger it manually from the Actions tab.

### Notes & Troubleshooting

- The script posts directly to the Facebook Page by uploading the image file. To post to Instagram automatically, the script attempts to reuse the uploaded Facebook photo's public URL as the `image_url` for Instagram's media container — this requires that your Page and Instagram Business account are properly linked and that the access token has `instagram_content_publish` and related permissions.
- If you do not want the transformers model to run in GitHub Actions (it can be heavy), you may remove `transformers` and `torch` from `requirements.txt` and rely on the simple fallback caption in the script.
- If Instagram publishing fails due to permissions or missing public image URL, the script will still post to the Facebook Page.
