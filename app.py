import streamlit as st
import pandas as pd
import numpy as np
import cv2
import face_recognition
import tempfile
import os
import time
from PIL import Image
import hashlib
import datetime
import re
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
import threading
import queue
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Autonomous KYC System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .risk-low { background-color: #28a745; color: white; padding: 0.5rem; border-radius: 5px; text-align: center; }
    .risk-medium { background-color: #ffc107; color: #333; padding: 0.5rem; border-radius: 5px; text-align: center; }
    .risk-high { background-color: #dc3545; color: white; padding: 0.5rem; border-radius: 5px; text-align: center; }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
state_defaults = {
    'step': 1, 'customer_data': {}, 'document_images': {}, 'selfie_image': None,
    'risk_score': 0, 'verification_status': {}, 'kyc_status': None,
    'additional_docs': None, 'monitoring_active': False, 
    'last_monitoring_check': None, 'liveness_passed': False, 'current_action': 0
}
for key, value in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Header
st.markdown('<div class="main-header"><h1>🤖 Autonomous KYC System</h1><p>AI-Powered Know Your Customer</p></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 📊 KYC Status")
    if st.session_state.kyc_status:
        st.info(f"**Status:** {st.session_state.kyc_status}")
    else:
        st.info("**Status:** Not Started")
    
    if st.session_state.risk_score > 0:
        st.markdown(f"### Risk Score: {st.session_state.risk_score}/100")

# Logic Functions
def check_document_authenticity(image_file):
    try:
        img = Image.open(image_file)
        img_array = np.array(img.convert('RGB'))
        return True, img_array, []
    except Exception as e:
        return False, None, [str(e)]

def compare_faces(id_image_array, selfie_image_array):
    try:
        id_encodings = face_recognition.face_encodings(id_image_array)
        selfie_encodings = face_recognition.face_encodings(selfie_image_array)
        
        if not id_encodings or not selfie_encodings:
            return False, 0, "Face not detected"
            
        distance = face_recognition.face_distance([id_encodings[0]], selfie_encodings[0])[0]
        similarity = (1 - distance) * 100
        return distance < 0.6, similarity, "Success"
    except Exception as e:
        return False, 0, f"Error: {str(e)}"

def video_frame_callback(frame):
    img = frame.to_ndarray(format="bgr24")
    return av.VideoFrame.from_ndarray(img, format="bgr24")

def perform_liveness_detection():
    st.markdown("### 🎥 Liveness Detection")
    if not st.session_state.liveness_passed:
        actions = ["Blink your eyes", "Turn head left", "Smile"]
        curr = st.session_state.current_action
        
        if curr < len(actions):
            st.info(f"Action {curr+1}: {actions[curr]}")
            webrtc_streamer(
                key="liveness",
                mode=WebRtcMode.SENDRECV,
                video_frame_callback=video_frame_callback,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={"video": True, "audio": False},
            )
            if st.button(f"Confirm {actions[curr]}"):
                st.session_state.current_action += 1
                st.rerun()
        else:
            st.session_state.liveness_passed = True
            st.rerun()
    return st.session_state.liveness_passed

# Steps Logic
if st.session_state.step == 1:
    st.header("📝 Step 1: Data Capture")
    name = st.text_input("Full Name")
    uploaded_doc = st.file_uploader("Upload ID", type=['jpg', 'jpeg', 'png'])
    selfie_camera = st.camera_input("Take a selfie")
    
    if st.button("Verify Identity"):
        if name and uploaded_doc and selfie_camera:
            st.session_state.customer_data['name'] = name
            st.session_state.document_images['ID'] = uploaded_doc
            st.session_state.selfie_image = selfie_camera
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    st.header("🔍 Step 2: Verification")
    liveness = perform_liveness_detection()
    
    if liveness:
        doc_img = st.session_state.document_images['ID']
        selfie_img = st.session_state.selfie_image
        
        _, doc_arr, _ = check_document_authenticity(doc_img)
        selfie_arr = np.array(Image.open(selfie_img).convert('RGB'))
        
        match, score, msg = compare_faces(doc_arr, selfie_arr)
        
        st.write(f"Face Match: {'✅' if match else '❌'} ({score:.1f}%)")
        st.session_state.risk_score = 15 if match else 85
        
        if st.button("Generate Decision"):
            st.session_state.step = 3
            st.rerun()

elif st.session_state.step == 3:
    st.header("⚙️ Step 3: Decision")
    if st.session_state.risk_score < 30:
        st.success("Auto Approved")
        st.session_state.kyc_status = "Approved"
    else:
        st.error("Manual Review Required")
        st.session_state.kyc_status = "Pending Review"
    
    if st.button("Reset"):
        for key in state_defaults: del st.session_state[key]
        st.rerun()
