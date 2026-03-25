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
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
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
    .risk-low {
        background-color: #28a745;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
    }
    .risk-medium {
        background-color: #ffc107;
        color: #333;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
    }
    .risk-high {
        background-color: #dc3545;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
    }
    .info-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'customer_data' not in st.session_state:
    st.session_state.customer_data = {}
if 'document_images' not in st.session_state:
    st.session_state.document_images = {}
if 'selfie_image' not in st.session_state:
    st.session_state.selfie_image = None
if 'risk_score' not in st.session_state:
    st.session_state.risk_score = 0
if 'verification_status' not in st.session_state:
    st.session_state.verification_status = {}
if 'kyc_status' not in st.session_state:
    st.session_state.kyc_status = None
if 'additional_docs' not in st.session_state:
    st.session_state.additional_docs = None
if 'monitoring_active' not in st.session_state:
    st.session_state.monitoring_active = False
if 'last_monitoring_check' not in st.session_state:
    st.session_state.last_monitoring_check = None

# Header
st.markdown('<div class="main-header"><h1>🤖 Autonomous KYC System</h1><p>AI-Powered Know Your Customer - Banking, Insurance, Mortgage</p></div>', unsafe_allow_html=True)

# Sidebar for status
with st.sidebar:
    st.markdown("## 📊 KYC Status")
    if st.session_state.kyc_status:
        if st.session_state.kyc_status == "Auto Approved":
            st.success(f"**Status:** {st.session_state.kyc_status}")
            st.progress(100)
        elif st.session_state.kyc_status == "Additional Checks Required":
            st.warning(f"**Status:** {st.session_state.kyc_status}")
            st.progress(50)
        elif st.session_state.kyc_status == "Manual Review Required":
            st.error(f"**Status:** {st.session_state.kyc_status}")
            st.progress(25)
        else:
            st.info(f"**Status:** {st.session_state.kyc_status}")
    else:
        st.info("**Status:** Not Started")
    
    if st.session_state.risk_score > 0:
        st.markdown(f"### Risk Score: {st.session_state.risk_score}/100")
        if st.session_state.risk_score <= 30:
            st.markdown('<div class="risk-low">Low Risk - Auto Approval Eligible</div>', unsafe_allow_html=True)
        elif st.session_state.risk_score <= 70:
            st.markdown('<div class="risk-medium">Medium Risk - Additional Checks Needed</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="risk-high">High Risk - Manual Review Required</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🔄 Workflow Steps")
    steps_completed = st.session_state.step - 1
    st.progress(steps_completed / 6)
    st.markdown(f"**Step {st.session_state.step} of 6**")

# Function to simulate document authenticity check
def check_document_authenticity(image_file):
    """Simulate AI-powered document authenticity and tampering detection"""
    try:
        img = Image.open(image_file)
        img_array = np.array(img)
        
        # Calculate image hash for authenticity check
        img_hash = hashlib.md5(img_array.tobytes()).hexdigest()
        
        # Check for potential tampering (simulation)
        # Look for inconsistent patterns or artifacts
        if img_array.size > 0:
            # Calculate image statistics
            std_dev = np.std(img_array)
            entropy = -np.sum(np.abs(img_array) * np.log2(np.abs(img_array) + 1e-10))
            
            # Simulate detection of tampering
            is_tampered = False
            tampering_reasons = []
            
            # Check for unrealistic standard deviation (simulated tampering)
            if std_dev < 5:
                is_tampered = True
                tampering_reasons.append("Inconsistent pixel patterns detected")
            
            # Check entropy (simulated)
            if entropy < 1:
                is_tampered = True
                tampering_reasons.append("Suspicious image compression patterns")
            
            # Check for text overlay detection (simulation)
            if "FAKE" in str(img_hash) or "test" in str(img_hash).lower():
                is_tampered = True
                tampering_reasons.append("Potential text overlay detected")
            
            return not is_tampered, img_array, tampering_reasons if is_tampered else []
        
        return False, None, ["Invalid image format"]
    
    except Exception as e:
        return False, None, [f"Document processing error: {str(e)}"]

# Face comparison function
def compare_faces(id_image_array, selfie_image_array):
    """Compare face from ID document with selfie"""
    try:
        # Convert to RGB if needed
        if len(id_image_array.shape) == 2:
            id_image_rgb = cv2.cvtColor(id_image_array, cv2.COLOR_GRAY2RGB)
        else:
            id_image_rgb = cv2.cvtColor(id_image_array, cv2.COLOR_BGR2RGB) if len(id_image_array.shape) == 3 else id_image_array
        
        if len(selfie_image_array.shape) == 2:
            selfie_rgb = cv2.cvtColor(selfie_image_array, cv2.COLOR_GRAY2RGB)
        else:
            selfie_rgb = cv2.cvtColor(selfie_image_array, cv2.COLOR_BGR2RGB) if len(selfie_image_array.shape) == 3 else selfie_image_array
        
        # Get face encodings
        id_face_locations = face_recognition.face_locations(id_image_rgb)
        selfie_face_locations = face_recognition.face_locations(selfie_rgb)
        
        if len(id_face_locations) == 0:
            return False, 0, "No face detected in ID document"
        
        if len(selfie_face_locations) == 0:
            return False, 0, "No face detected in selfie"
        
        # Get face encodings
        id_encoding = face_recognition.face_encodings(id_image_rgb, id_face_locations)[0]
        selfie_encoding = face_recognition.face_encodings(selfie_rgb, selfie_face_locations)[0]
        
        # Compare faces
        distance = face_recognition.face_distance([id_encoding], selfie_encoding)[0]
        match_threshold = 0.6
        
        is_match = distance < match_threshold
        similarity_score = (1 - distance) * 100
        
        return is_match, similarity_score, "Face verification completed"
    
    except Exception as e:
        return False, 0, f"Face comparison error: {str(e)}"

# Liveness detection simulation
def perform_liveness_detection():
    """Simulate liveness detection with movement detection"""
    st.markdown("### 🎥 Liveness Detection")
    st.markdown("Please follow the instructions to prove you're a real person")
    
    instruction = st.empty()
    liveness_passed = st.session_state.get('liveness_passed', False)
    
    if not liveness_passed:
        instruction.info("📸 Look at the camera and perform the following actions:")
        
        actions = ["Blink your eyes", "Turn your head slightly left", "Turn your head slightly right", "Smile"]
        current_action = st.session_state.get('current_action', 0)
        
        if current_action < len(actions):
            st.markdown(f"### 🎯 Action {current_action + 1}: {actions[current_action]}")
            
            # WebRTC streamer for liveness
            class VideoTransformer(VideoTransformerBase):
                def __init__(self):
                    self.frame_count = 0
                    self.motion_detected = False
                
                def transform(self, frame):
                    img = frame.to_ndarray(format="bgr24")
                    self.frame_count += 1
                    
                    # Simple motion detection simulation
                    if self.frame_count % 30 == 0:
                        self.motion_detected = True
                    
                    return img
            
            webrtc_ctx = webrtc_streamer(
                key="liveness",
                mode=WebRtcMode.SENDRECV,
                video_transformer_factory=VideoTransformer,
                async_processing=True,
            )
            
            if st.button(f"✅ Completed Action {current_action + 1}"):
                st.session_state.current_action = current_action + 1
                st.rerun()
        else:
            st.success("✅ All liveness checks passed!")
            st.session_state.liveness_passed = True
            return True
    
    return st.session_state.get('liveness_passed', False)

# Risk scoring function
def calculate_risk_score(customer_data, verification_results):
    """Calculate risk score based on various factors"""
    risk_score = 0
    
    # Factor 1: Document verification (0-40 points)
    if not verification_results.get('document_authentic', True):
        risk_score += 40
    elif verification_results.get('tampering_detected', False):
        risk_score += 30
    
    # Factor 2: Face match (0-30 points)
    face_match_score = verification_results.get('face_match_score', 100)
    if face_match_score < 50:
        risk_score += 30
    elif face_match_score < 70:
        risk_score += 20
    elif face_match_score < 85:
        risk_score += 10
    
    # Factor 3: Document expiry (0-20 points)
    if verification_results.get('document_expired', False):
        risk_score += 20
    
    # Factor 4: Data consistency (0-10 points)
    name_match = verification_results.get('name_match', True)
    dob_match = verification_results.get('dob_match', True)
    if not name_match or not dob_match:
        risk_score += 10
    
    # Cap at 100
    return min(risk_score, 100)

# Document expiry validation
def check_document_expiry(expiry_date_str):
    """Check if document is expired"""
    try:
        if expiry_date_str:
            expiry_date = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            return expiry_date < datetime.date.today()
        return False
    except:
        return False

# Step 1: Customer Data Capture
if st.session_state.step == 1:
    st.header("📝 Step 1: Customer Data Capture")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Personal Information")
        name = st.text_input("Full Name *", key="name")
        dob = st.date_input("Date of Birth *", key="dob")
        address = st.text_area("Address *", key="address")
        phone = st.text_input("Phone Number *", key="phone")
        email = st.text_input("Email Address *", key="email")
    
    with col2:
        st.subheader("Document Upload")
        st.markdown("Please upload your identification documents:")
        
        document_type = st.selectbox(
            "Select Document Type",
            ["Aadhar Card", "PAN Card", "Passport", "Driving License"],
            key="doc_type"
        )
        
        uploaded_doc = st.file_uploader(
            f"Upload {document_type}",
            type=['jpg', 'jpeg', 'png', 'pdf'],
            key="document_upload"
        )
        
        expiry_date = st.date_input(
            f"{document_type} Expiry Date",
            key="expiry_date"
        )
        
        st.subheader("Selfie Capture")
        st.markdown("Take a selfie for face verification")
        
        selfie_camera = st.camera_input("Take a selfie", key="selfie_capture")
    
    if st.button("Next: Proceed to Verification", type="primary"):
        if all([name, address, phone, email, uploaded_doc, selfie_camera]):
            # Save customer data
            st.session_state.customer_data = {
                'name': name,
                'dob': dob,
                'address': address,
                'phone': phone,
                'email': email,
                'document_type': document_type,
                'expiry_date': expiry_date
            }
            
            # Save images
            st.session_state.document_images[document_type] = uploaded_doc
            st.session_state.selfie_image = selfie_camera
            
            st.session_state.step = 2
            st.rerun()
        else:
            st.error("Please fill all required fields and upload documents")

# Step 2: Identity Verification
elif st.session_state.step == 2:
    st.header("🔍 Step 2: Identity Verification")
    st.markdown("AI is analyzing your documents and verifying your identity...")
    
    with st.spinner("Processing verification..."):
        # Create progress bar
        progress_bar = st.progress(0)
        
        # 1. Document authenticity check
        progress_bar.progress(20)
        st.markdown("📄 Checking document authenticity...")
        
        doc_image = st.session_state.document_images[st.session_state.customer_data['document_type']]
        is_authentic, doc_array, tampering_reasons = check_document_authenticity(doc_image)
        
        # 2. Expiry validation
        progress_bar.progress(40)
        st.markdown("📅 Validating document expiry...")
        
        is_expired = check_document_expiry(str(st.session_state.customer_data['expiry_date']))
        
        # 3. Face verification
        progress_bar.progress(60)
        st.markdown("👤 Comparing face with ID document...")
        
        # Load selfie image
        selfie_image = st.session_state.selfie_image
        selfie_array = np.array(Image.open(selfie_image))
        
        if doc_array is not None:
            face_match, face_score, face_message = compare_faces(doc_array, selfie_array)
        else:
            face_match = False
            face_score = 0
            face_message = "Could not process ID document"
        
        # 4. Liveness detection
        progress_bar.progress(80)
        st.markdown("🎥 Performing liveness detection...")
        
        liveness_passed = perform_liveness_detection()
        
        # Store verification results
        st.session_state.verification_status = {
            'document_authentic': is_authentic,
            'tampering_detected': not is_authentic,
            'tampering_reasons': tampering_reasons,
            'document_expired': is_expired,
            'face_match': face_match,
            'face_match_score': face_score,
            'face_message': face_message,
            'liveness_passed': liveness_passed,
            'name_match': True,  # Simulated
            'dob_match': True     # Simulated
        }
        
        progress_bar.progress(100)
        
        # Display verification results
        st.markdown("---")
        st.subheader("Verification Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if is_authentic:
                st.success("✅ Document Authenticity: Verified")
            else:
                st.error("❌ Document Authenticity: Failed")
                for reason in tampering_reasons:
                    st.warning(f"⚠️ {reason}")
            
            if not is_expired:
                st.success("✅ Document Expiry: Valid")
            else:
                st.error("❌ Document Expiry: Expired")
        
        with col2:
            if face_match:
                st.success(f"✅ Face Match: Verified ({face_score:.1f}% match)")
            else:
                st.error(f"❌ Face Match: Failed ({face_score:.1f}% match)")
            
            if liveness_passed:
                st.success("✅ Liveness Detection: Passed")
            else:
                st.error("❌ Liveness Detection: Failed")
        
        # Calculate risk score
        st.session_state.risk_score = calculate_risk_score(
            st.session_state.customer_data,
            st.session_state.verification_status
        )
        
        st.markdown(f"### Risk Score: {st.session_state.risk_score}/100")
    
    if st.button("Next: Decision Automation", type="primary"):
        st.session_state.step = 3
        st.rerun()

# Step 3: Decision Automation
elif st.session_state.step == 3:
    st.header("⚙️ Step 3: Decision Automation")
    
    risk_score = st.session_state.risk_score
    
    st.markdown(f"### Analyzing Risk Score: {risk_score}/100")
    
    if risk_score <= 30:
        st.success("🎉 **LOW RISK - AUTO APPROVAL**")
        st.markdown("""
        **Decision:** Auto Approve Onboarding
        - No additional checks required
        - Customer will be onboarded automatically
        - Account activation in progress
        """)
        st.session_state.kyc_status = "Auto Approved"
        
    elif risk_score <= 70:
        st.warning("⚠️ **MEDIUM RISK - Additional Checks Required**")
        st.markdown("""
        **Decision:** Request Additional Documents
        Please upload the following for verification:
        - Bank Statement (last 3 months)
        - Proof of Income
        - Utility Bill for address verification
        """)
        
        additional_doc = st.file_uploader(
            "Upload Additional Document",
            type=['jpg', 'jpeg', 'png', 'pdf'],
            key="additional_doc"
        )
        
        if additional_doc:
            st.session_state.additional_docs = additional_doc
            st.session_state.kyc_status = "Additional Checks Required"
        
    else:
        st.error("🔴 **HIGH RISK - Manual Review Required**")
        st.markdown("""
        **Decision:** Escalate for Manual Compliance Review
        - Case has been escalated to compliance team
        - A manual review will be conducted by our experts
        - You will be notified within 24-48 hours
        """)
        st.session_state.kyc_status = "Manual Review Required"
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Complete KYC Process", type="primary"):
            st.session_state.step = 4
            st.rerun()

# Step 4: Continuous Monitoring
elif st.session_state.step == 4:
    st.header("🔄 Step 4: Continuous / Perpetual KYC")
    
    st.success(f"✅ KYC Process Completed: {st.session_state.kyc_status}")
    
    st.markdown("---")
    st.markdown("### 📊 Post-Onboarding Monitoring")
    
    if st.session_state.kyc_status == "Auto Approved":
        st.info("🔍 **Continuous Monitoring Active**")
        st.markdown("""
        The system will continuously monitor:
        - Periodic document refresh checks
        - Transaction pattern analysis
        - Risk profile updates
        - PEP and sanctions screening
        """)
        
        # Start monitoring simulation
        if not st.session_state.monitoring_active:
            st.session_state.monitoring_active = True
            st.session_state.last_monitoring_check = datetime.datetime.now()
        
        if st.session_state.monitoring_active:
            time_since_check = (datetime.datetime.now() - st.session_state.last_monitoring_check).seconds
            
            if time_since_check > 30:  # Simulate periodic check every 30 seconds
                st.warning("📢 **Periodic Document Refresh Reminder**")
                st.info(f"Please confirm your address is still: {st.session_state.customer_data['address']}")
                
                if st.button("Confirm Address"):
                    st.session_state.last_monitoring_check = datetime.datetime.now()
                    st.success("Address confirmed! Next check in 30 seconds.")
                    st.rerun()
            else:
                st.info(f"Next periodic check in {30 - time_since_check} seconds...")
    
    elif st.session_state.kyc_status == "Additional Checks Required":
        st.warning("📋 **Additional Documentation Review Pending**")
        st.markdown("Our team is reviewing your additional documents. You'll be notified once complete.")
        
    else:
        st.error("👥 **Manual Review in Progress**")
        st.markdown("A compliance officer has been assigned to review your case. Status updates will be provided.")
    
    st.markdown("---")
    
    # Display summary
    st.subheader("KYC Summary")
    summary_data = {
        "Customer Name": st.session_state.customer_data.get('name', 'N/A'),
        "Document Type": st.session_state.customer_data.get('document_type', 'N/A'),
        "Risk Score": f"{st.session_state.risk_score}/100",
        "Verification Status": "Passed" if st.session_state.verification_status.get('document_authentic', False) else "Failed",
        "Face Match": f"{st.session_state.verification_status.get('face_match_score', 0):.1f}%",
        "KYC Status": st.session_state.kyc_status
    }
    
    df = pd.DataFrame([summary_data])
    st.table(df)
    
    # Risk visualization
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = st.session_state.risk_score,
        title = {'text': "Risk Score"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "salmon"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig)
    
    if st.button("Start New KYC Application"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# Main execution
if __name__ == "__main__":
    pass
