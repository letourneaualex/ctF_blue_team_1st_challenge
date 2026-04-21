from PIL import Image
img = Image.new("RGB", (100, 100), color=(73, 109, 137))
img.save("/judge/assets/legit_image.jpg", "JPEG")
