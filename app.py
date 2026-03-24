"""
VerifyAI — Autonomous KYC
A realistic KYC verification system using OCR, face matching, and risk scoring.
"""

import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import pandas as pd

# ⚠️ If using Windows, uncomment and set your path
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VerifyAI — Autonomous KYC",
    page_icon="🛡️",
    layout="wide",
)

# ─────────────────────────────────────────────
# PREMIUM UI STYLE
# ─────────────────────────────────────────────
st.markdown("""
<style>
.stApp {
    background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
    color: white;
}
.stTextInput input, .stTextArea textarea {
    background-color: #1e1e1e !important;
    color: white !important;
}
.stButton>button {
    background-color: #00c6ff;
    color: black;
    border-radius: 10px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    digits = re.sub(r'\D', '', phone)
    return len(digits) == 10


def extract_ocr_text(image: Image.Image) -> str:
    try:
        img = image.convert("RGB")
        text = pytesseract.image_to_string(img, config='--psm 6')
        return text.strip()
    except Exception as e:
        return f"OCR Error: {str(e)}"


def score_document(ocr_text: str):
    if not ocr_text or "OCR Error" in ocr_text:
        return 0, "❌ No Text Detected"

    score = 0
    if len(ocr_text) > 10:
        score += 20

    has_numbers = bool(re.search(r'\d{4,}', ocr_text))
    has_words = len([w for w in ocr_text.split() if len(w) >= 3]) >= 3

    if has_numbers or has_words:
        score += 20

    if score >= 40:
        status = "✅ Verified"
    elif score >= 20:
        status = "⚠️ Needs Review"
    else:
        status = "❌ Unverified"

    return score, status


def pil_to_cv2(image: Image.Image):
    img = image.convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def detect_faces(cv2_img):
    try:
        gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )
        return faces
    except:
        return []


def compare_faces(doc_img, selfie_img):
    similarity = 0.0  # Initialize to avoid UnboundLocalError
    
    doc_cv = pil_to_cv2(doc_img)
    selfie_cv = pil_to_cv2(selfie_img)

    # Resize for comparison
    h, w = 200, 200
    doc_resized = cv2.resize(doc_cv, (w, h))
    selfie_resized = cv2.resize(selfie_cv, (w, h))

    doc_hsv = cv2.cvtColor(doc_resized, cv2.COLOR_BGR2HSV)
    selfie_hsv = cv2.cvtColor(selfie_resized, cv2.COLOR_BGR2HSV)

    similarity_scores = []
    for ch in range(3):
        hist1 = cv2.calcHist([doc_hsv], [ch], None, [64], [0, 256])
        hist2 = cv2.calcHist([selfie_hsv], [ch], None, [64], [0, 256])

        cv2.normalize(hist1, hist1)
        cv2.normalize(hist2, hist2)

        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        similarity_scores.append(score)

    similarity = float(np.mean(similarity_scores))

    if similarity >= 0.55:
        return 40, "✅ Face Match — Strong", similarity
    elif similarity >= 0.25:
        return 20, "⚠️ Face Match — Weak", similarity
    else:
        return 0, "❌ Face Mismatch", similarity


def score_data(name, address, dob, phone, email):
    score = 20
    issues = []

    if not name.strip():
        score -= 5
        issues.append("Name missing")
    if not address.strip():
        score -= 5
        issues.append("Address missing")
    if not dob:
        score -= 3
        issues.append("DOB missing")
    if not validate_phone(phone):
        score -= 4
        issues.append("Invalid phone")
    if not validate_email(email):
        score -= 3
        issues.append("Invalid email")

    score = max(0, score)
    status = "✅ Complete" if score == 20 else f"⚠️ Issues: {', '.join(issues)}"
    return score, status


def get_risk_category(total):
    if total >= 71:
        return "🟢 Trusted", "✅ Auto Approve"
    elif total >= 31:
        return "🟡 Suspicious", "⚠️ Need More Verification"
    else:
        return "🔴 High Risk", "🔍 Manual Review Required"


# ─────────────────────────────────────────────
# UI INPUTS
# ─────────────────────────────────────────────

st.title("🛡️ VerifyAI — Autonomous KYC")
st.subheader("👤 Customer Information")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Full Name")
    address = st.text_area("Address")
    dob = st.date_input("Date of Birth")
with col2:
    phone = st.text_input("Phone")
    email = st.text_input("Email")

st.subheader("📄 Upload Documents")
doc_file = st.file_uploader("Upload ID Document", type=["png", "jpg", "jpeg"])
selfie_file = st.file_uploader("Upload Selfie", type=["png", "jpg", "jpeg"])

run_kyc = st.button("🚀 Run KYC Verification")

# ─────────────────────────────────────────────
# MAIN LOGIC
# ─────────────────────────────────────────────

if run_kyc:
    errors = []
    if not name.strip(): errors.append("Name required")
    if not address.strip(): errors.append("Address required")
    if not validate_email(email): errors.append("Invalid email")
    if not validate_phone(phone): errors.append("Invalid phone")
    if not doc_file: errors.append("Upload document")
    if not selfie_file: errors.append("Upload selfie")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    with st.spinner("🔍 Running KYC Verification..."):
        doc_img = Image.open(doc_file).convert("RGB")
        selfie_img = Image.open(selfie_file).convert("RGB")

        data_score, data_status = score_data(name, address, dob, phone, email)
        ocr_text = extract_ocr_text(doc_img)
        doc_score, doc_status = score_document(ocr_text)
        face_score, face_status, similarity = compare_faces(doc_img, selfie_img)

        total_score = min(data_score + doc_score + face_score, 100)
        risk, decision = get_risk_category(total_score)

        # ─────────────────────────────────────────
        # OUTPUT (Inside the button block)
        # ─────────────────────────────────────────
        st.subheader("📊 KYC Results")
        st.markdown(f"## 🎯 Final Score: {total_score}/100")
        st.progress(total_score / 100)

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.write("### Breakdown")
            st.write("📄 Document Score:", doc_score, doc_status)
            st.write("🧑 Face Score:", face_score, face_status)
            st.write("📋 Data Score:", data_score, data_status)
            st.write(f"🔬 Similarity Metric: {round(similarity, 2)}")

        with res_col2:
            st.write("### Decision")
            if "Trusted" in risk:
                st.success(f"{risk} — {decision}")
            elif "Suspicious" in risk:
                st.warning(f"{risk} — {decision}")
            else:
                st.error(f"{risk} — {decision}")

        st.write("### OCR Extracted Text")
        st.info(ocr_text if ocr_text else "No text found")

        st.write("### Summary")
        df = pd.DataFrame({
            "Field": ["Name", "Email", "Phone", "Score", "Risk"],
            "Value": [name, email, phone, total_score, risk]
        })
        st.table(df)