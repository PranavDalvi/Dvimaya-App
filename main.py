import eel
import subprocess
import os
import time
import shutil
import numpy as np
import cv2
import sys
import base64
import tempfile
import sys
import tflite_runtime.interpreter as tflite

from utils.binvis_standalone import visualize_bin


class DevNull:
    def write(self, msg): pass
    def flush(self): pass


if not sys.stdout or sys.stdout is None:
    sys.stdout = DevNull()
if not sys.stderr or sys.stderr is None:
    sys.stderr = DevNull()


# Temporary storage
TMP_DIR = tempfile.mkdtemp(prefix="dvimaya_tmp_")

logfile = open(os.path.join("app.log"), "w")
sys.stderr = logfile
sys.stdout = logfile

dirname = os.path.dirname(__file__)
current_process = None
model = None


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


@eel.expose
def on_close_callback(route, websockets):
    # Clean up on exit
    if os.path.exists(TMP_DIR):
        try:
            shutil.rmtree(TMP_DIR)
        except Exception as e:
            print(f"Error cleaning temp directory: {e}")
    if not websockets:
        sys.exit(0)


@eel.expose
def save_temp_file(filename, file_data):
    """Saves uploaded file to TMP_DIR, returns file path."""
    try:
        header, encoded = file_data.split(",", 1)
        file_bytes = base64.b64decode(encoded)
        temp_path = os.path.join(TMP_DIR, filename)
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
        return temp_path
    except Exception as e:
        return f"Error: {str(e)}"


@eel.expose
def generate_visualization(input_file):
    """Runs binvis, predicts with CNN, deletes temp files."""
    output_file_tmp = os.path.join(
        TMP_DIR, f"output_{time.strftime('%Y%m%d-%H%M%S')}.png")

    with open(input_file, "rb") as f:
        file_bytes = f.read()
    visualize_bin(file_bytes, output_file_tmp, color_mode="hilbert",
                  image_size=256, image_type="unrolled")
    try:
        prediction = predict_binvis(output_file_tmp)
        os.remove(output_file_tmp)
        os.remove(input_file)
        return prediction
    except Exception as e:
        return f"Error: {str(e)}"


def predict_binvis(image_path):
    """Loads BinVis image and predicts using CNN"""
    global model
    if model is None:
        # Load CNN model
        MODEL_PATH = resource_path("ai-model/cnn_malware_detector.tflite")
        model = tflite.Interpreter(model_path=MODEL_PATH)
        model.allocate_tensors()
    try:
        image = cv2.imread(image_path)
        if image is None:
            return "Error: Failed to read image."

        image = cv2.imread(image_path)
        image = cv2.resize(image, (128, 128))
        image = image.astype('float32') / 255.0
        image = np.expand_dims(image, axis=0)

        input_details = model.get_input_details()
        output_details = model.get_output_details()

        input_dtype = input_details[0]['dtype']
        image = image.astype(input_dtype)

        model.set_tensor(input_details[0]['index'], image)
        model.invoke()

        prediction = model.get_tensor(output_details[0]['index'])
        label = "Risky" if prediction > 0.5 else "Safe"
        return f"{label}"
    except Exception as e:
        return f"Error in prediction: {str(e)}"


@eel.expose
def cancel_scan():
    global current_process
    if current_process:
        current_process.terminate()
        try:
            current_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            current_process.kill()
        current_process = None
    return "Scan canceled successfully"


eel.init(dirname)
eel.start('static/index.html', size=(1000, 800),
          close_callback=on_close_callback)
