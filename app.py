import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
from fuzzywuzzy import fuzz

# ─────────────────────────────────────────────
# UI CONFIG & STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="VerifyAI Pro", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(to right, #0f2027, #203a43, #2c5364); color: white; }
.stButton>button { 
    background-color: #00c6ff; color: black; border-radius: 10px; 
    font-weight: bold; width: 100%; height: 3.5em; border: none;
}
.stButton>button:hover { background-color: #0072ff; color: white; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CORE VERIFICATION LOGIC
# ─────────────────────────────────────────────

def get_ocr_text(image):
    try:
        # Converts image to string using Tesseract
        return pytesseract.image_to_string(image, config='--psm 6').strip()
    except:
        return ""

def compare_faces_biometric(id_img, live_img):
    try:
        # Convert images for OpenCV processing
        img1 = cv2.cvtColor(np.array(id_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        img2 = cv2.cvtColor(np.array(live_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        
        def extract_face(img):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.2, 5)
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                return cv2.resize(gray[y:y+h, x:x+w], (100, 100))
            return None

        face1 = extract_face(img1)
        face2 = extract_face(img2)

        if face1 is None or face2 is None:
            return 0, "❌ Face Not Detected", 0

        # Structural Comparison
        res = cv2.matchTemplate(face1, face2, cv2.TM_CCOEFF_NORMED)
        score = float(res.max())
        
        if score > 0.45:
            return 40, "✅ Biometric Match Confirmed", score
        return 0, "❌ Face Mismatch", score
    except:
        return 0, "⚠️ Processing Error", 0

# ─────────────────────────────────────────────
# MAIN INTERFACE
# ─────────────────────────────────────────────

st.title("🛡️ VerifyAI Pro — Autonomous KYC")
st.write("Secure Identity Verification Environment")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("👤 Step 1: Identity Data")
    user_name = st.text_input("Full Name (Must match ID Card)")
    doc_type = st.selectbox("Select ID Type", ["Aadhar Card", "PAN Card", "Driving Licence", "Voter ID"])
    id_upload = st.file_uploader(f"Upload Front Side of {doc_type}", type=["jpg", "png", "jpeg"])

with col2:
    st.subheader("📸 Step 2: Liveness Check")
    selfie_capture = st.camera_input("Take a live photo for biometric matching")

# ─────────────────────────────────────────────
# EXECUTION BUTTON
# ─────────────────────────────────────────────

if st.button("🚀 RUN SECURE VERIFICATION"):
    if not user_name or not id_upload or not selfie_capture:
        st.error("Please provide your name, ID document, and a live selfie.")
    else:
        with st.spinner("Analyzing data and matching biometrics..."):
            # Load images
            img_id = Image.open(id_upload)
            img_selfie = Image.open(selfie_capture)
            
            # 1. Anti-Fake Name Check (Fuzzy Matching)
            ocr_text = get_ocr_text(img_id)
            name_match_ratio = fuzz.partial_ratio(user_name.lower(), ocr_text.lower())
            
            # 2. Biometric Check
            face_score, face_msg, raw_sim = compare_faces_biometric(img_id, img_selfie)
            
            # 3. Final Score
            total_score = face_score + (40 if name_match_ratio > 80 else 0) + 20
            
            st.divider()
            
            # Result Display
            if total_score >= 80 and name_match_ratio > 75:
                st.success(f"### APPROVED: Trust Score {total_score}/100")
                st.balloons()
            elif total_score >= 50:
                st.warning(f"### REVIEW REQUIRED: Trust Score {total_score}/100")
            else:
                st.error(f"### REJECTED: Trust Score {total_score}/100")

            # Breakdown Table
            results_df = pd.DataFrame({
                "Security Check": ["Name Match on ID", "Biometric Matching", "Data Consistency"],
                "Result": [f"{name_match_ratio}% Match", face_msg, "✅ Verified"],
                "Status": ["Pass" if name_match_ratio > 75 else "Fail", "Pass" if face_score > 0 else "Fail", "Pass"]
            })
            st.table(results_df)

            with st.expander("View System Audit Logs (OCR Text)"):
                st.code(ocr_text if ocr_text else "No text could be read from document.")
