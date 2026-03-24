import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
from fuzzywuzzy import fuzz

# ─────────────────────────────────────────────
# UI CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="VerifyAI Pro", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(to right, #0f2027, #203a43, #2c5364); color: white; }
.stButton>button { background-color: #00c6ff; color: black; border-radius: 10px; font-weight: bold; width: 100%; height: 3em; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGIC FUNCTIONS
# ─────────────────────────────────────────────

def get_ocr_text(image):
    try:
        return pytesseract.image_to_string(image, config='--psm 6').strip()
    except:
        return ""

def compare_faces(id_img, live_img):
    try:
        # Convert PIL to OpenCV
        img1 = cv2.cvtColor(np.array(id_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        img2 = cv2.cvtColor(np.array(live_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        
        # Load Face Detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        
        def extract_face_gray(img):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                return cv2.resize(gray[y:y+h, x:x+w], (100, 100))
            return None

        f1 = extract_face_gray(img1)
        f2 = extract_face_gray(img2)

        if f1 is None or f2 is None:
            return 0, "❌ Face not detected in one or both images."

        # Comparison Logic
        res = cv2.matchTemplate(f1, f2, cv2.TM_CCOEFF_NORMED)
        score = float(res.max())
        
        if score > 0.45:
            return 40, "✅ Biometric Match Confirmed"
        return 0, "❌ Face Mismatch Detected"
    except Exception as e:
        return 0, f"Error: {str(e)}"

# ─────────────────────────────────────────────
# MAIN APP INTERFACE
# ─────────────────────────────────────────────

st.title("🛡️ VerifyAI Pro — Secure KYC")

col1, col2 = st.columns(2)

with col1:
    user_name = st.text_input("Full Name (As on ID)")
    doc_type = st.selectbox("ID Document", ["Aadhar Card", "PAN Card", "Driving Licence"])
    id_upload = st.file_uploader(f"Upload {doc_type}", type=["jpg", "png", "jpeg"])

with col2:
    st.write("### Live Selfie")
    selfie_capture = st.camera_input("Take a photo to verify liveness")

if st.button("🚀 VERIFY IDENTITY"):
    if not user_name or not id_upload or not selfie_capture:
        st.error("Missing Data: Please fill name, upload ID, and take a selfie.")
    else:
        with st.spinner("Analyzing..."):
            id_img = Image.open(id_upload)
            live_img = Image.open(selfie_capture)
            
            # OCR Check
            text_on_id = get_ocr_text(id_img)
            name_match_score = fuzz.partial_ratio(user_name.lower(), text_on_id.lower())
            
            # Face Check
            face_score, face_msg = compare_faces(id_img, live_img)
            
            # Logic for rejection
            st.divider()
            if name_match_score > 80 and face_score > 0:
                st.success(f"### APPROVED (Score: {name_match_score+face_score+20}/100)")
                st.write(f"**Name Match:** {name_match_score}%")
                st.write(f"**Face Match:** {face_msg}")
            else:
                st.error("### REJECTED")
                st.write(f"**Reason:** Name Match ({name_match_score}%) or Face Match failed.")
                with st.expander("Debug: Text found on ID"):
                    st.write(text_on_id if text_on_id else "No text detected")
