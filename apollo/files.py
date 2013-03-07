# Read chunk size.
READ_CHUNK_SIZE = 8192
def check_file(audio_file):
    if not audio_file or not audio_file.filename:
        return "No file selected."
    if not audio_file.filename.endswith(".mp3"):
        return "Please select an mp3."

def handle_upload(_file, _fs):
    # Ask for a new GridIn file.
    gridin = _fs.new_file(filename = _file.filename)

    print("handling")
    # Write to the GridIn file in chunks.
    while(True):
        data = _file.file.read(READ_CHUNK_SIZE)
        if not data:
            break
        gridin.write(data)

    gridin.close()

    return gridin._id
