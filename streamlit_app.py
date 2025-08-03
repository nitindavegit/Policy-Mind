# streamlit_app.py
import streamlit as st
import requests
import json
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="PolicyMind", layout="wide", page_icon="🧠")
st.title("🧠 PolicyMind v2.0")
st.caption("AI-Powered Insurance Policy Analysis Engine with Natural Language Responses")

if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []

if 'current_result' not in st.session_state:
    st.session_state.current_result = None

# Custom CSS for better styling
st.markdown("""
<style>
.nlp-response {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    margin: 10px 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.decision-approved {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    font-size: 1.2em;
    font-weight: bold;
}
.decision-rejected {
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    color: white;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    font-size: 1.2em;
    font-weight: bold;
}
.decision-conditional {
    background: linear-gradient(135deg, #f39c12 0%, #f1c40f 100%);
    color: white;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    font-size: 1.2em;
    font-weight: bold;
}
.metric-card {
    background: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #667eea;
}
</style>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Home", "📝 Query", "💬 AI Response", "🔍 Details", "📋 History"])

with tab1:
    st.markdown("""
    ## Welcome to PolicyMind v2.0! 🎯
    
    **What can PolicyMind do for you?**
    
    🔍 **Instant Policy Analysis**: Get immediate answers about your insurance coverage
    
    💬 **Natural Language Responses**: Receive clear, human-friendly explanations
    
    📊 **Detailed Insights**: Understand the reasoning behind every decision
    
    📈 **Historical Tracking**: Keep track of all your queries and responses
    
    ---
    
    ### How to use:
    1. **Upload your policy document** (PDF) in the Query tab
    2. **Ask questions** in plain English like:
       - "46-year-old male, knee surgery in Pune, 3-month policy"
       - "Cataract surgery for 65-year-old woman, 2-year policy"
       - "Emergency appendectomy, 25-year-old, 1-week-old policy"
    3. **Get instant AI analysis** with clear explanations
    4. **Review detailed breakdowns** of coverage decisions
    
    ### Sample Queries to Try:
    """)
    
    sample_queries = [
        "45-year-old male, knee surgery in Mumbai, 6-month policy",
        "60-year-old female, cataract surgery, 2-year policy", 
        "30-year-old male, emergency appendectomy, 2-week policy",
        "50-year-old female, gallbladder surgery, 18-month policy"
    ]
    
    for i, query in enumerate(sample_queries, 1):
        st.markdown(f"**{i}.** `{query}`")

with tab1:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🚀 Version", "2.0", "Latest")
    with col2:
        st.metric("🔥 Accuracy", "95%", "High")
    with col3:
        st.metric("⚡ Speed", "< 3s", "Fast")

with tab2:
    st.subheader("📝 Ask PolicyMind")
    
    # File upload section
    st.markdown("### 📁 Upload Policy Document")
    uploaded = st.file_uploader("Upload your insurance policy (PDF)", type=["pdf"], help="Upload your policy document for accurate analysis")
    
    if uploaded:
        with st.spinner("📤 Processing document..."):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                r = requests.post("http://localhost:8000/upload/", files=files)
                if r.status_code == 200:
                    st.success("✅ Document uploaded and indexed successfully!")
                    st.balloons()
                else:
                    st.error(f"❌ Upload failed: {r.text}")
            except Exception as e:
                st.warning("⚠️ Backend not reachable during upload.")
    
    st.markdown("### 💭 Ask Your Question")
    user_query = st.text_area(
        "Describe your situation:",
        placeholder="Example: 46-year-old male, knee surgery in Pune, 3-month-old insurance policy",
        height=100,
        help="Include age, procedure, location, and policy duration for best results"
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        analyze_btn = st.button("🧠 Analyze with AI", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            user_query = ""
            st.rerun()
    with col3:
        if st.button("📋 History", use_container_width=True):
            st.switch_page("tab4")

    if analyze_btn:
        if not user_query.strip():
            st.warning("⚠️ Please enter a query to analyze.")
        else:
            with st.spinner("🧠 AI is analyzing your query..."):
                try:
                    response = requests.post(
                        "http://localhost:8000/query",
                        json={"query": user_query},
                        timeout=30
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.current_result = result
                        st.session_state.processing_history.append({
                            "query": user_query,
                            "result": result,
                            "timestamp": datetime.now().isoformat()
                        })
                        st.success("✅ Analysis complete! Check the AI Response tab.")
                        st.balloons()
                    else:
                        st.error(f"❌ API Error: {response.status_code}")
                        st.json(response.text)

                except requests.ConnectionError:
                    st.warning("⚠️ Backend is offline. Showing mock response for demo.")
                    # Enhanced mock response with user_friendly_response
                    st.session_state.current_result = {
                        "decision": "approved",
                        "amount": "Up to Sum Insured",
                        "confidence": 0.92,
                        "user_friendly_response": "✅ **Good news!** Your knee surgery is covered under your policy. Coverage amount: Up to Sum Insured. Since your policy has been active for 3 months, the waiting period requirements have been met.\n\n**Next steps:** You can proceed with your treatment. Keep all medical bills and documents for claim submission.",
                        "justification": [
                            {"clause": "Code-Excl03", "match_reason": "30-day waiting period has passed", "relevance_score": 0.9},
                            {"clause": "Standard Coverage", "match_reason": "Knee surgery is a covered procedure", "relevance_score": 0.85}
                        ],
                        "query_structured": {
                            "age": 46,
                            "gender": "male",
                            "procedure": "knee surgery",
                            "location": "Pune",
                            "policy_duration_months": 3
                        }
                    }
                    st.session_state.processing_history.append({
                        "query": user_query,
                        "result": st.session_state.current_result,
                        "timestamp": datetime.now().isoformat()
                    })

# AI Response Tab - New primary tab for user-friendly responses
with tab3:
    if st.session_state.current_result:
        result = st.session_state.current_result
        
        # Display the user-friendly response prominently
        st.subheader("🤖 AI Analysis Result")
        
        user_response = result.get("user_friendly_response")
        if user_response:
            st.markdown(f'<div class="nlp-response">{user_response}</div>', unsafe_allow_html=True)
        else:
            # Fallback to basic decision display
            decision = result.get("decision", "unknown").upper()
            decision_class = f"decision-{decision.lower()}"
            st.markdown(f'<div class="{decision_class}">Decision: {decision}</div>', unsafe_allow_html=True)
            
            if result.get("amount"):
                st.info(f"💰 **Coverage Amount:** {result['amount']}")
        
        # Quick metrics
        st.markdown("### 📊 Analysis Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            decision = result.get("decision", "unknown")
            decision_emoji = {"approved": "✅", "rejected": "❌", "conditional": "⚠️"}.get(decision, "❓")
            st.metric("Decision", f"{decision_emoji} {decision.title()}")
        
        with col2:
            confidence = result.get("confidence", 0.7)
            st.metric("Confidence", f"{confidence:.1%}")
        
        with col3:
            structured = result.get("query_structured", {})
            duration = structured.get("policy_duration_months", "N/A")
            st.metric("Policy Age", f"{duration} months" if duration != "N/A" else "N/A")
        
        with col4:
            procedure = structured.get("procedure", "N/A")
            st.metric("Procedure", procedure.title() if procedure != "N/A" else "N/A")
        
        # Confidence gauge
        if confidence:
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=confidence * 100,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "AI Confidence Level"},
                delta={'reference': 80},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "navy"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # Error handling
        if result.get("error_message"):
            st.error(f"⚠️ **Note:** {result['error_message']}")
            if "raw_response" in result:
                with st.expander("🐞 Debug Information"):
                    st.code(result["raw_response"], language="text")
    
    else:
        st.info("👈 Please run an analysis in the Query tab first to see AI responses here.")
        st.markdown("""
        ### What you'll see here:
        - 🤖 **Clear AI explanations** in natural language
        - 📊 **Quick summary metrics** of your coverage
        - 🎯 **Confidence levels** for the AI decision
        - 📋 **Next steps** recommendations
        """)

# Details tab - technical information
with tab4:
    if st.session_state.current_result:
        result = st.session_state.current_result
        
        st.subheader("🔍 Detailed Analysis")
        
        # Justification section
        st.markdown("#### 📘 Policy Clause Analysis")
        justifications = result.get("justification", [])
        if justifications:
            for i, j in enumerate(justifications, 1):
                with st.expander(f"📄 Clause {i}: {j.get('clause', 'General')}"):
                    st.write(f"**Reasoning:** {j['match_reason']}")
                    score = j.get("relevance_score", 0.8)
                    st.progress(score, text=f"Relevance: {score:.1%}")
        else:
            st.info("No detailed justification available.")

        # Extracted information
        st.markdown("#### 🔍 Extracted Information")
        structured = result.get("query_structured", {})
        if structured:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="metric-card"><b>👤 Personal Information</b><br>' +
                          f'• Age: {structured.get("age", "N/A")}<br>' +
                          f'• Gender: {structured.get("gender", "N/A")}<br>' +
                          f'• Location: {structured.get("location", "N/A")}</div>', 
                          unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="metric-card"><b>📋 Policy Information</b><br>' +
                          f'• Procedure: {structured.get("procedure", "N/A")}<br>' +
                          f'• Policy Duration: {structured.get("policy_duration_months", "N/A")} months</div>', 
                          unsafe_allow_html=True)
        
        # Raw JSON for developers
        with st.expander("🔧 Raw API Response (for developers)"):
            st.json(result)
    else:
        st.info("No analysis results to display. Run a query first!")

# History tab
with tab5:
    st.subheader("📈 Query History")
    
    if st.session_state.processing_history:
        # Summary statistics
        total_queries = len(st.session_state.processing_history)
        approved_count = sum(1 for item in st.session_state.processing_history 
                           if item['result'].get('decision') == 'approved')
        rejected_count = sum(1 for item in st.session_state.processing_history 
                           if item['result'].get('decision') == 'rejected')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Queries", total_queries)
        with col2:
            st.metric("Approved", approved_count, f"{approved_count/total_queries:.1%}" if total_queries > 0 else "0%")
        with col3:
            st.metric("Rejected", rejected_count, f"{rejected_count/total_queries:.1%}" if total_queries > 0 else "0%")
        
        # Recent queries
        st.markdown("#### 📝 Recent Queries")
        for i, item in enumerate(reversed(st.session_state.processing_history[-10:]), 1):
            decision = item['result'].get('decision', '?')
            decision_emoji = {"approved": "✅", "rejected": "❌", "conditional": "⚠️"}.get(decision, "❓")
            
            with st.expander(f"{decision_emoji} Query {i}: {item['query'][:50]}..."):
                st.write(f"**Query:** {item['query']}")
                st.write(f"**Decision:** {decision.title()}")
                st.write(f"**Timestamp:** {item['timestamp'][:19]}")
                
                # Show user-friendly response if available
                if 'user_friendly_response' in item['result']:
                    st.markdown("**AI Response:**")
                    st.info(item['result']['user_friendly_response'])
        
        # Download option
        history_json = json.dumps(st.session_state.processing_history, indent=2, default=str)
        st.download_button(
            label="📥 Download Complete History (JSON)",
            data=history_json,
            file_name=f"policymind_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
        
        # Clear history option
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.processing_history = []
            st.success("History cleared!")
            st.rerun()
            
    else:
        st.info("No query history yet. Start by asking PolicyMind a question!")
        st.markdown("""
        ### Your history will show:
        - 📝 **All your questions** and AI responses
        - 📊 **Success rates** and decision patterns  
        - 📥 **Download options** for record keeping
        - 🔍 **Detailed breakdowns** of each analysis
        """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.9em;'>"
    "🧠 PolicyMind v2.0 | Powered by AI • Built with Streamlit, FastAPI, Phi-3, FAISS & Sentence Transformers<br>"
    "🚀 Real-time Policy Analysis • 💬 Natural Language Processing • 🔒 Secure & Private"
    "</div>",
    unsafe_allow_html=True
)