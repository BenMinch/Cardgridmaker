import os
import zipfile
import pandas as pd
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload_files():
    if "csv" not in request.files or "zip" not in request.files:
        return jsonify({"error": "Missing CSV or ZIP file"}), 400

    # Get user settings
    card_width_mm = float(request.form.get("card_width", 63))
    card_height_mm = float(request.form.get("card_height", 88.4))
    dpi = 300  # High-quality print

    # Convert mm to pixels
    card_width_px = int(card_width_mm * dpi / 25.4)
    card_height_px = int(card_height_mm * dpi / 25.4)
    cols, rows = 3, 3
    page_width, page_height = int(8.5 * dpi), int(11 * dpi)
    x_margin = (page_width - (cols * card_width_px)) // 2
    y_margin = (page_height - (rows * card_height_px)) // 2

    # Save uploaded files
    csv_file = request.files["csv"]
    zip_file = request.files["zip"]
    csv_path = os.path.join(UPLOAD_FOLDER, secure_filename(csv_file.filename))
    zip_path = os.path.join(UPLOAD_FOLDER, secure_filename(zip_file.filename))
    csv_file.save(csv_path)
    zip_file.save(zip_path)

    # Extract images
    image_folder = os.path.join(UPLOAD_FOLDER, "images")
    os.makedirs(image_folder, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(image_folder)

    # Read CSV
    df = pd.read_csv(csv_path)
    card_list = []
    for _, row in df.iterrows():
        filename, copies = row["filename"], int(row["copies"])
        card_list.extend([filename] * copies)

    # Generate Sheets
    sheet_images = []
    for i in range(0, len(card_list), 9):
        sheet = Image.new("RGB", (page_width, page_height), "white")
        batch = card_list[i:i+9]

        for j, filename in enumerate(batch):
            card_path = os.path.join(image_folder, filename)
            if os.path.exists(card_path):
                card = Image.open(card_path).resize((card_width_px, card_height_px))
                x_offset = x_margin + (j % cols) * card_width_px
                y_offset = y_margin + (j // cols) * card_height_px
                sheet.paste(card, (x_offset, y_offset))

        sheet_images.append(sheet)

    # Save to PDF
    pdf_path = os.path.join(OUTPUT_FOLDER, "final_cards.pdf")
    sheet_images[0].save(pdf_path, save_all=True, append_images=sheet_images[1:])
    
    return send_file(pdf_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)

