"""
Evidence-Bound Drug RAG - Streamlit UI
Production-ready with dark mode and improved UX
"""
import streamlit as st
import requests

# ============================================================================
# PAGE CONFIG (Must be first)
# ============================================================================
st.set_page_config(
    page_title="Evidence-Bound Drug RAG",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# DARK MODE STYLING (IMPROVED)
# ============================================================================
st.markdown("""
<style>
    /* Dark theme */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    section[data-testid="stSidebar"] {
        background-color: #262730;
    }
    
    /* Headers */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #b0b0b0;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* ✅ ISSUE 3 FIX: Answer card that pops */
    .answer-card {
        background-color: #1a1e23;
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 1rem 0;
        border-left: 4px solid #1E88E5;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    /* Cards */
    .metric-card {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .citation {
        background-color: #1a2332;
        padding: 0.5rem;
        border-left: 3px solid #1E88E5;
        margin: 0.5rem 0;
        color: #fafafa;
    }
    .refusal-box {
        background-color: #2d2416;
        padding: 1rem;
        border-left: 3px solid #ff9800;
        margin: 1rem 0;
        color: #fafafa;
    }
    
    /* Text colors */
    h1, h2, h3, h4, h5, h6 {
        color: #fafafa !important;
    }
    p, div, span, label {
        color: #fafafa !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1E88E5;
        color: white;
    }
    .stButton > button:hover {
        background-color: #1565C0;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# API CONFIGURATION
# ============================================================================
try:
    API_URL = st.secrets["API_URL"]
except:
    # Use Docker service name for container-to-container communication
    import os
    API_URL = os.getenv("API_URL", "http://localhost:8000")


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Retriever settings
    st.subheader("🎛️ Retrieval Settings")
    retriever_type = st.selectbox(
        "Method",
        ["hybrid", "vector", "bm25"],
        index=0,
        help="Hybrid = BM25 + Vector (Recommended)"
    )
    
    top_k = st.slider(
        "Top-K chunks",
        min_value=3,
        max_value=15,
        value=8,
        help="More chunks = more context but slower"
    )
    
    st.divider()
    
    # System stats
    st.subheader("📊 System Stats")
    try:
        stats_response = requests.get(f"{API_URL}/stats", timeout=5)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Chunks", stats.get("total_chunks", "N/A"))
            with col2:
                st.metric("Drugs", len(stats.get("drugs_covered", [])))
            
            with st.expander("📋 View all drugs"):
                drugs = stats.get("drugs_covered", [])
                if drugs:
                    st.write(", ".join(sorted(drugs)))
        else:
            st.warning("⚠️ API not responding")
    except:
        st.error("❌ Cannot connect to API")
    
    st.divider()
    
    # About section
    st.subheader("ℹ️ About")
    st.markdown("""
    **Version:** 1.0.0  
    **RAGAS Score:** 0.71/1.0 ✅
    - Faithfulness: 0.80
    - Relevancy: 0.70
    - Context Recall: 0.62
    
    **Features:**
    - 🔍 Hybrid retrieval
    - 📚 853 evidence chunks
    - 🏛️ FDA + NICE + WHO
    - 🚫 Refusal policy
    - 💰 Free (Groq LLM)
    """)

# ============================================================================
# MAIN CONTENT
# ============================================================================
st.markdown('<div class="main-header">💊 Evidence-Bound Drug RAG</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Ask questions about pharmaceutical drugs backed by FDA, NICE & WHO documentation</div>', unsafe_allow_html=True)

st.divider()

# Example queries
with st.expander("💡 Example Queries (Click to view)", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Allowed Questions:**")
        st.code("What are the side effects of warfarin?", language=None)
        st.code("What is the recommended dosage of metformin?", language=None)
        st.code("What are contraindications for amoxicillin?", language=None)
        st.code("What interactions does atorvastatin have?", language=None)
    
    with col2:
        st.markdown("**❌ Refused Questions:**")
        st.code("Should I stop taking my medication?", language=None)
        st.code("Can I take ibuprofen with alcohol?", language=None)
        st.code("What's the best drug for my condition?", language=None)
        st.code("How much should I take?", language=None)

st.divider()

# ✅ ISSUE 2 FIX: Better placeholder text
# Query form (prevents blank screen issues)
with st.form("query_form"):
    query = st.text_area(
        "🔍 Ask your question:",
        height=120,
        placeholder="Try: What are the side effects of warfarin?",  # ✅ More helpful!
        help="Ask about side effects, dosages, contraindications, or interactions"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        submit_button = st.form_submit_button("🚀 Ask", type="primary", use_container_width=True)
    with col2:
        st.caption("💡 Tip: Be specific for better results")

# ============================================================================
# QUERY PROCESSING
# ============================================================================
if submit_button and query.strip():
    with st.spinner("🔎 Retrieving evidence and generating answer..."):
        try:
            response = requests.post(
                f"{API_URL}/ask",
                json={
                    "query": query,
                    "top_k": top_k,
                    "retriever_type": retriever_type
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                st.divider()
                
                # Handle refusal
                if result.get("is_refusal", False):
                    st.markdown(
                        f'<div class="refusal-box">'
                        f'<strong>⚠️ Query Refused</strong><br><br>'
                        f'{result["answer"]}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    st.info("""
                    **Why was this refused?**
                    
                    This system follows strict medical safety policies:
                    - ❌ No personal medical advice
                    - ❌ No diagnostic recommendations  
                    - ❌ No treatment decisions
                    - ❌ No dosing for individuals
                    
                    ✅ **Always consult a healthcare professional for medical decisions.**
                    """)
                else:
                    # Success - show answer
                    st.success("✅ Answer generated from evidence-based sources")
                    
                    # ✅ ISSUE 1 & 3 FIX: Answer in lighter card
                    st.markdown(
                        f'<div class="answer-card">'
                        f'<h3 style="margin-top: 0; color: #1E88E5;">📝 Answer</h3>'
                        f'{result["answer"]}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    
                    # ✅ ISSUE 4 FIX: Better metric labels
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("⏱️ Response Time", f"{result.get('total_latency_ms', 0):.0f}ms")
                    with col2:
                        st.metric("📚 Sources Found", result.get("chunks_retrieved", 0))  # ✅ Clearer!
                    with col3:
                        st.metric("📎 Evidence Used", result.get("chunks_cited", 0))  # ✅ Clearer!
                    
                    # Authorities used
                    if result.get("authorities_used"):
                        authorities = ", ".join(result["authorities_used"])
                        st.info(f"🏛️ **Authoritative Sources:** {authorities}")
                    
                    # Citations
                    cited_chunks = result.get("cited_chunks", [])
                    if cited_chunks:
                        with st.expander(f"📄 View {len(cited_chunks)} Citations", expanded=False):
                            for i, chunk_id in enumerate(cited_chunks, 1):
                                st.markdown(
                                    f'<div class="citation"><strong>[{i}]</strong> {chunk_id}</div>',
                                    unsafe_allow_html=True
                                )
                    
                    # ✅ ISSUE 5 FIX: Cost moved to technical details only
                    # Technical details
                    with st.expander("🔧 Technical Details", expanded=False):
                        st.json({
                            "query": result.get("query"),
                            "retriever_type": retriever_type,
                            "top_k": top_k,
                            "retrieval_time_ms": result.get("retrieval_time_ms", 0),
                            "generation_time_ms": result.get("generation_time_ms", 0),
                            "total_latency_ms": result.get("total_latency_ms", 0),
                            "total_tokens": result.get("total_tokens", 0),
                            "cost_usd": result.get("cost_usd", 0.0),  # ✅ Hidden from main view
                            "is_refusal": result.get("is_refusal", False),
                            "chunks_retrieved": result.get("chunks_retrieved", 0),
                            "chunks_cited": result.get("chunks_cited", 0)
                        })
            
            elif response.status_code == 422:
                st.error("❌ Invalid request format")
                st.code(response.text)
            else:
                st.error(f"❌ API Error: HTTP {response.status_code}")
                st.code(response.text)
        
        except requests.Timeout:
            st.error("⏱️ Request timed out (60s). API might be overloaded.")
        except requests.ConnectionError:
            st.error("❌ Cannot connect to API. Make sure it's running at:")
            st.code(API_URL)
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")

elif submit_button:
    st.warning("⚠️ Please enter a question before submitting")

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9rem; padding: 1rem;">
    <strong>Evidence-Bound Drug RAG</strong> | 
    Built with FastAPI + Groq + ChromaDB + Streamlit | 
    RAGAS Score: 0.71/1.0 ✅ | 
    Zero Hallucinations Policy | 
    <a href="https://github.com/yourusername/evidence-bound-drug-rag" target="_blank" style="color: #1E88E5;">GitHub</a>
</div>
""", unsafe_allow_html=True)

# Disclaimer
with st.expander("⚠️ Important Medical Disclaimer"):
    st.warning("""
    **MEDICAL DISCLAIMER**
    
    This system is for **informational and educational purposes only**. It is **NOT**:
    - A substitute for professional medical advice
    - A diagnostic tool
    - A treatment recommendation system
    - A prescription or dosing guide
    
    **Always:**
    - Consult qualified healthcare professionals for medical decisions
    - Follow your doctor's prescribed treatment plan
    - Report any adverse effects to your healthcare provider
    - Verify all information with official sources
    
    **Emergency:** Call your local emergency number (911 in US) for medical emergencies.
    """)