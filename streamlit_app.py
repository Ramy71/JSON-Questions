import streamlit as st
import json
import zipfile
import io
from pathlib import Path
import tempfile
import os
from datetime import datetime

# Import your enhanced processor
from enhanced_question_processor import QuestionProcessor, ProcessingStats

# Streamlit page configuration
st.set_page_config(
    page_title="Question Processor Tool",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("📝 Educational Question Processor")
st.markdown("""
Convert your educational content into structured JSON format with support for:
- Multiple question types (MCQ, FRQ_ai, String, Gap Text, etc.)
- Arabic and English languages
- Math LaTeX formatting
- Bulk processing
""")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page:", ["Question Processor", "Structure Guide", "Sample Questions"])

if page == "Question Processor":
    # Main processing interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Input Questions")
        
        # Input method selection
        input_method = st.radio(
            "Choose input method:",
            ["Paste Text", "Upload File"]
        )
        
        questions_text = ""
        
        if input_method == "Paste Text":
            questions_text = st.text_area(
                "Paste your questions here:",
                height=400,
                placeholder="""id: 1001
language: en
category: exam
type: mcq

[STEM]
What is 2 + 2?

[CHOICES]
*4
3
5
6
---
id: 1002
language: en
category: lesson
type: string

[STEM]
What is `H_2O`?

[ANSWER]
Water"""
            )
        
        else:  # Upload File
            uploaded_file = st.file_uploader(
                "Upload a text file:",
                type=['txt', 'md'],
                help="Upload a .txt or .md file containing your questions"
            )
            
            if uploaded_file is not None:
                questions_text = str(uploaded_file.read(), "utf-8")
                st.success(f"File uploaded: {uploaded_file.name}")
    
    with col2:
        st.header("Settings")
        
        # Processing settings
        output_dir = st.text_input("Output Directory:", value="generated_questions")
        
        # Language preference for preview
        preview_lang = st.selectbox(
            "Preview Language:",
            ["English", "العربية"],
            help="Language for the interface preview"
        )
        
        # Processing button
        process_btn = st.button(
            "🚀 Process Questions",
            type="primary",
            disabled=not questions_text,
            help="Click to convert your questions to JSON format"
        )
    
    # Processing logic
    if process_btn and questions_text:
        with st.spinner("Processing questions..."):
            try:
                # Create temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Initialize processor
                    processor = QuestionProcessor(output_dir=temp_dir)
                    
                    # Process questions
                    stats = processor.process_google_doc(questions_text)
                    
                    # Display results
                    st.success("✅ Processing completed!")
                    
                    # Statistics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Questions", stats.total_questions)
                    with col2:
                        st.metric("Successful", stats.successful)
                    with col3:
                        st.metric("Failed", stats.failed)
                    with col4:
                        success_rate = (stats.successful / stats.total_questions * 100) if stats.total_questions > 0 else 0
                        st.metric("Success Rate", f"{success_rate:.1f}%")
                    
                    # Show generated files
                    if stats.generated_files:
                        st.header("Generated Files")
                        
                        # Create download section
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            for filename in stats.generated_files:
                                with st.expander(f"📄 {filename}"):
                                    file_path = Path(temp_dir) / filename
                                    if file_path.exists():
                                        with open(file_path, 'r', encoding='utf-8') as f:
                                            content = json.load(f)
                                        
                                        # Show preview
                                        st.json(content, expanded=False)
                        
                        with col2:
                            # Create ZIP download
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for filename in stats.generated_files:
                                    file_path = Path(temp_dir) / filename
                                    if file_path.exists():
                                        zip_file.write(file_path, filename)
                            
                            st.download_button(
                                label="📥 Download All JSON Files",
                                data=zip_buffer.getvalue(),
                                file_name=f"questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                mime="application/zip"
                            )
                    
                    # Show any errors
                    if stats.failed > 0:
                        st.warning(f"⚠️ {stats.failed} questions failed to process. Check the logs for details.")
            
            except Exception as e:
                st.error(f"❌ Error during processing: {str(e)}")

elif page == "Structure Guide":
    st.header("📖 Question Structure Guide")
    
    # Tabs for different aspects
    tab1, tab2, tab3, tab4 = st.tabs(["Basic Structure", "Question Types", "Math Formatting", "Examples"])
    
    with tab1:
        st.markdown("""
        ## Basic Question Structure
        
        Every question must follow this format:
        
        ```
        id: [numeric_id]
        language: [en|ar]
        category: [category_name]
        type: [question_type]
        
        [STEM]
        Your question text here
        
        [CHOICES|ANSWER|GAPS|...] (depends on question type)
        Answer content here
        ---
        ```
        
        ### Required Metadata
        - **id**: Unique numeric identifier
        - **language**: `en` for English, `ar` for Arabic
        
        ### Optional Metadata
        - **category**: Question category (default: "exam")
        - **type**: Question type (can be set per part)
        - **country**: Country code (default: "eg")
        - **ai_template_id**: For AI-graded questions
        """)
    
    with tab2:
        st.markdown("""
        ## Supported Question Types
        
        | Type | Description | Required Sections |
        |------|-------------|------------------|
        | `mcq` | Multiple Choice (single answer) | `[STEM]`, `[CHOICES]` with `*` for correct answer |
        | `mrq` | Multiple Response (multiple answers) | `[STEM]`, `[CHOICES]` with `*` for correct answers |
        | `string` | Text input | `[STEM]`, `[ANSWER]` |
        | `oq` | Ordering questions | `[STEM]`, `[CHOICES]` (no `*` needed) |
        | `gapText` | Fill in the blanks | `[STEM]` with `[BLANK]`, `[GAPS]` |
        | `matching` | Match items | `[STEM]`, `[MATCHING_PAIRS]` with `\|` separator |
        | `input_box` | Numeric input | `[STEM]`, `[ANSWER]` (optionally with units) |
        | `frq` | Free response | `[STEM]`, `[ANSWER]` |
        | `frq_ai` | AI-graded free response | `[STEM]`, `[ANSWER]`, requires `ai_template_id` |
        """)
    
    with tab3:
        st.markdown("""
        ## Math Formatting
        
        ### Single Backticks (Language-aware)
        ```
        `x^2 + 2x + 1`  → Converts to Arabic math in Arabic questions
        ```
        
        ### Double Backticks (Force English)
        ```
        ``F = ma``  → Always stays in English
        ```
        
        ### LaTeX Commands
        All LaTeX commands are protected:
        - `\\frac{a}{b}` → Fraction
        - `\\sqrt{x}` → Square root
        - `\\int_0^1` → Integral
        - `\\alpha`, `\\beta` → Greek letters
        """)
    
    with tab4:
        st.markdown("""
        ## Complete Examples
        
        ### Simple MCQ
        ```
        id: 1001
        language: en
        category: exam
        type: mcq
        
        [STEM]
        What is `2^3`?
        
        [CHOICES]
        *8
        -6
        -9
        -4
        ```
        
        ### Multi-part Question
        ```
        id: 2001
        language: en
        category: exam
        
        [STATEMENT]
        A ball is thrown upward with initial velocity 20 m/s.

        [PART]
        type: mcq
        [STEM]
        What is the maximum height?
        [CHOICES]
        *20.4 m
        -15.3 m
        -25.1 m
        
        [PART]
        type: input_box
        [STEM]
        Time to reach maximum height?
        [ANSWER]
        2.04 | s
        ```
        """)

elif page == "Sample Questions":
    st.header("📝 Sample Questions")
    
    # Category selector
    category = st.selectbox(
        "Choose category:",
        ["exam", "lesson"]
    )
    
    samples = {
        "Mathematics": """id: 3001
language: en
category: exam
type: mcq

[STEM]
Solve for x: `x^2 - 5x + 6 = 0`

[CHOICES]
-x = 1, 6
*x = 2, 3
-x = -2, -3
-x = 0, 5
---
id: 3002
language: en
category: exam
type: input_box

[STEM]
Calculate the area of a circle with radius 5 cm. Use `π = 3.14`

[ANSWER]
78.5 | cm²""",
        
        "Physics": """id: 4001
language: en
category: physics
type: mcq

[STEM]
According to Ohm's law ``V = IR``, if voltage is 12V and current is 3A, what is the resistance?

[CHOICES]
36 Ω
9 Ω
*4 Ω
15 Ω
---
id: 4002
language: en
category: physics
type: string

[STEM]
What is the unit of electric power?

[ANSWER]
Watt (W)""",
        
        "Chemistry": """id: 5001
language: en
category: chemistry
type: matching

[STEM]
Match the chemical symbols with their elements:

[MATCHING_PAIRS]
H | Hydrogen
O | Oxygen
C | Carbon
N | Nitrogen""",
        
        "Biology": """id: 6001
language: en
category: biology
type: gapText

[STEM]
Photosynthesis occurs in the [BLANK] of plant cells and produces [BLANK] and oxygen.

[GAPS]
chloroplasts
glucose""",
        
        "Language": """id: 7001
language: ar
category: arabic
type: mcq

[STEM]
ما هو جمع كلمة "كتاب"؟

[CHOICES]
*كتب
كتاب
كتابات
كتابان"""
    }
    
    if category in samples:
        st.code(samples[category], language="text")
        
        # Copy button simulation
        if st.button(f"📋 Copy {category} Sample"):
            st.success("Sample copied! You can paste it in the Question Processor.")
    
    # Custom question builder
    st.header("🔧 Quick Question Builder")
    
    with st.form("question_builder"):
        col1, col2 = st.columns(2)
        
        with col1:
            q_id = st.number_input("Question ID:", min_value=1, value=8001)
            q_lang = st.selectbox("Language:", ["en", "ar"])
            q_category = st.text_input("Category:", value="general")
            q_type = st.selectbox("Question Type:", ["mcq", "string", "input_box", "gapText"])
        
        with col2:
            q_stem = st.text_area("Question Text:", height=100)
            
            if q_type in ["mcq", "mrq"]:
                choices = st.text_area("Choices (one per line, use * for correct answer):", height=100)
            elif q_type == "string":
                answer = st.text_input("Answer:")
            elif q_type == "input_box":
                answer = st.text_input("Answer (use | for units):")
        
        if st.form_submit_button("Generate Question"):
            if q_stem:
                generated = f"""id: {q_id}
language: {q_lang}
category: {q_category}
type: {q_type}

[STEM]
{q_stem}
"""
                
                if q_type in ["mcq", "mrq"] and choices:
                    generated += f"\n[CHOICES]\n{choices}"
                elif q_type in ["string", "input_box"] and 'answer' in locals():
                    generated += f"\n[ANSWER]\n{answer}"
                
                st.code(generated, language="text")
            else:
                st.error("Please provide question text!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Built with ❤️ using Streamlit | Educational Question Processor v2.0
</div>
""", unsafe_allow_html=True)
