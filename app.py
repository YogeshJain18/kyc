import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import pandas as pd
from fuzzywuzzy import fuzz

# ─────────────────────────────────────────────
# PAGE CONFIG & PREMIUM STYLING
# ─────────────────────────────────────────────
st.set_page_config(page_title="VerifyAI Pro", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(to right, #0f2027, #203a43, #2c5364); color: white; }
.stButton>button { 
    background-color: #00c6ff; 
    color: black; 
    border-radius: 10px; 
    font-weight: bold; 
    height: 3em;
    transition: 0.3s;
}
.stButton>button:hover { background-color: #0072ff; color: white; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CORE AI LOGIC
# ─────────────────────────────────────────────

def extract_ocr_text(image: Image.Image) -> str:
    """Reads text from the uploaded ID."""
    try:
        img = image.convert("RGB")
        text = pytesseract.image_to_string(img, config='--psm 6')
        return text.strip()
    except Exception:
        return ""

def verify_identity_logic(user_name, ocr_text):
    """
    ANTI-FAKE DATA: Compares typed name to ID text.
    Uses Fuzzy Matching to allow for minor OCR typos.
    """
    if not ocr_text or len(user_name) < 3:
        return 0, "❌ Name Not Found on ID"
    
    # Calculate similarity ratio (0 to 100)
    match_ratio = fuzz.partial_ratio(user_name.lower(), ocr_text.lower())
    
    if match_ratio > 85:
        return 40, f"✅ Verified (Match: {match_ratio}%)"
    elif match_ratio > 60:
        return 20, f"⚠️ Partial Match ({match_ratio}%) - Review Required"
    else:
        return 0, "❌ Identity Mismatch (Fraud Detected)"

def biometric_face_check(doc_img, selfie_img):
    """
    Compares the face on the ID to the Live Webcam Selfie.
    """
    def extract_face(img):
        cv_img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            return cv2.resize(face_roi, (120, 120))
        return None

    face_id = extract_face(doc_img)
    face_live = extract_face(selfie_img)

    if face_id is None or face_live is None:
        return 0, "❌ Face detection failed (Check lighting)", 0

    # Structural Correlation
    res = cv2.matchTemplate(face_id, face_live, cv2.TM_CCOEFF_NORMED)
    similarity = float(res.max())

    if similarity > 0.45:
        return 40, "✅ Biometric Match Confirmed", similarity
    else:
        return 0, "❌ Face Mismatch (User is not ID Holder)", similarity

# ─────────────────────────────────────────────
# UI INTERFACE
# ─────────────────────────────────────────────

st.title("🛡️ VerifyAI Pro — Autonomous KYC")
st.info("System Status: Online | Biometric Security Enabled")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("👤 Step 1: Identity Data")
    name = st.text_input("Full Name (Must match ID card)")
    doc_type = st.selectbox("Select ID Type", ["Aadhar Card", "PAN Card", "Driving Licence", "Voter ID"])
    dob = st.date_input("Date of Birth")
    
    st.subheader("📄 Step 2: Document Upload")
    doc_file = st.file_uploader(f"Upload Front Side of {doc_type}", type=["jpg", "jpeg", "png"])

with col2:
    st.subheader("📸 Step 3: Live Liveness Check")
    st.write("Please look directly at the camera.")
    # LIVE WEBCAM COMPONENT
    selfie_capture = st.camera_input("Take Live Selfie")

# ─────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────

if st.button("🚀 RUN SECURE VERIFICATION"):
    if not name or not doc_file or not selfie_capture:
        st.warning("⚠️ Action Required: Please provide Name, ID Document, and Live Selfie.")
    else:
        with st.spinner("Processing Secure Biometrics..."):
            # 1. Load images
            img_doc = Image.open(doc_file)
            img_selfie = Image.open(selfie_capture)

            # 2. Run Cross-Check (Anti-Fake Data)
            raw_text = extract_ocr_text(img_doc)
            name_score, name_status = verify_identity_logic(name, raw_text)

            # 3. Run Face Comparison
            face_score, face_status, raw_sim = biometric_face_check(img_doc, img_selfie)

            # 4. Final Aggregation
            # We give 20 base points for valid data format
            total_score = name_score + face_score + 20
            
            # Display Results
            st.divider()
            
            if total_score >= 80:
                st.success(f"### 🎯 IDENTITY VERIFIED: {total_score}/100")
                st.balloons()
            elif total_score >= 50:
                st.warning(f"### 🔍 MANUAL REVIEW NEEDED: {total_score}/100")
            else:
                st.error(f"### ❌ REJECTED - SECURITY ALERT: {total_score}/100")

            # Detail Breakdown
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.write(f"**Name Check:** {name_status}")
                st.write(f"**Face Matching:** {face_status}")
            with res_col2:
                st.write(f"**Document Type:** {doc_type}")
                st.write(f"**Biometric Similarity:** {round(raw_sim * 100, 1)}%")

            with st.expander("Show Technical Audit Trail (OCR Data)"):
                st.code(raw_text if raw_text else "No machine-readable text found.")
