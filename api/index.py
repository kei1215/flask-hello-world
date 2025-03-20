import os
import random
import string
import requests
from flask import Flask, request, jsonify, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_hash():
    """Generate a unique 8-character hash."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

@app.route("/soliup/upload_chunk", methods=["POST"])
def upload_chunk():
    """Handle file chunk upload."""
    if "file" not in request.files:
        return "No file part", 400

    chunk = request.files["file"]
    visibility = request.form.get("visibility")
    
    # Generate a unique file name to store the chunks
    base_filename = secure_filename(chunk.filename)
    chunk_filename = os.path.join(UPLOAD_FOLDER, f"{base_filename}.part{random.randint(1000, 9999)}")
    
    # Save the chunk to disk
    chunk.save(chunk_filename)

    # Logic to reassemble the file after all chunks have been uploaded
    # You can use a unique hash or filename to match chunks
    # Example: Check if all parts are uploaded, then combine them

    return jsonify({"status": "chunk uploaded", "filename": chunk_filename})

@app.route("/soliup/finish_upload", methods=["POST"])
def finish_upload():
    """Reconstruct the file after all chunks are uploaded."""
    file_hash = request.form.get("file_hash")
    
    # Combine all the parts into a single file
    file_parts = [os.path.join(UPLOAD_FOLDER, f"{file_hash}.part{part}") for part in range(1, 5)]  # Adjust this based on your needs

    with open(f"/tmp/uploads/{file_hash}.final", "wb") as final_file:
        for part in file_parts:
            with open(part, "rb") as f:
                final_file.write(f.read())

    # After combining the parts, you can now delete the temporary chunks
    for part in file_parts:
        os.remove(part)

    return jsonify({"status": "file upload complete", "filename": f"{file_hash}.final"})

if __name__ == "__main__":
    app.run(debug=True)
