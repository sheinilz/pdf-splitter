import streamlit as st
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
import pandas as pd
import io
import zipfile
import re
import pytesseract
from PIL import Image
import sys
import os

if sys.platform.startswith('win'):
    path1 = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    path2 = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    
    if os.path.exists(path1):
        pytesseract.pytesseract.tesseract_cmd = path1
    elif os.path.exists(path2):
        pytesseract.pytesseract.tesseract_cmd = path2
    else:
        st.warning("Warning: Tesseract-OCR engine not found in default directories. Please ensure it is installed.")

st.set_page_config(page_title="Smart PDF Splitter", layout="wide")

# עיצוב מינימליסטי ומתקדם - כיווניות וצבעים
st.markdown("""
    <style>
    .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, div {
        direction: rtl !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    h1, h2, h3 {
        text-align: center !important;
    }
    .stMarkdown p {
        text-align: center !important;
        color: #4b5563; /* אפור עדין לטקסט תיאור */
    }

    [data-testid="stRadio"] {
        width: fit-content !important; 
        position: relative !important;
        right: 90% !important; /* מזיז למרכז */
        transform: translateX(50%) !important; /* מאזן את הקופסה בול לאמצע */
        padding: 25px 35px !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 16px !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05) !important;
    }
    
    [role="radiogroup"] {
        align-items: flex-start !important;
        gap: 12px;
    }

    [data-testid="stWidgetLabel"] {
        display: block;
        text-align: center !important;
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 10px;
    }

    [data-testid="stFileUploader"] {
        padding: 15px;
        background-color: #f8fafc;
        border-radius: 12px;
    }
    [data-testid="stFileUploader"] > section {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
    }

    @media (prefers-color-scheme: dark) {
        [data-testid="stRadio"] {
            border-color: #374151 !important;
            background-color: #1f2937 !important;
        }
        .stMarkdown p { color: #9ca3af; }
        [data-testid="stFileUploader"] { background-color: #111827; }
    }

    .stButton > button, [data-testid="stDownloadButton"] > button {
        display: block !important;
        margin: 20px auto !important;
        border-radius: 40px !important;
        font-weight: bold !important;
    }
    
    input { text-align: center !important; }
    th, td { text-align: center !important; }
    </style>
""", unsafe_allow_html=True)

st.title("מפצל PDF חכם ✂️")
st.write("מערכת אוטומטית לחלוקת קובצי PDF ומתן שמות - מבוסס OCR.")
st.write("---") 

col_spacer1, col_center, col_spacer2 = st.columns([1, 2.5, 1])

with col_center:
    method = st.radio(
        "בחר שיטת פיצול:",
        ["חלוקה קבועה לעמודים + שמות מקובץ אקסל", "זיהוי וחלוקה חכמה (סריקה מהירה לפי מילת מפתח)"]
    )
    st.write("") # מרווח נשימה
    uploaded_file = st.file_uploader("העלה קובץ PDF לפיצול", type="pdf")

st.write("---")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    
    _, info_col, _ = st.columns([1, 2, 1])
    with info_col:
        st.info(f"📄 הקובץ נטען בהצלחה! סה״כ: {total_pages} עמודים.")

    if st.button("🔄 רענן נתונים ונקה טבלה"):
        for key in ['pdf_data', 'current_file']:
            if key in st.session_state:
                del st.session_state[key]

    # ---------------- Option 1: Fixed Page Splitting + Excel ----------------
    if method == "חלוקה קבועה לעמודים + שמות מקובץ אקסל":
        
        _, opt1_col, _ = st.columns([1, 3, 1])
        with opt1_col:
            col1, col2 = st.columns([1, 2])
            with col1:
                pages_per_split = st.number_input("כל כמה עמודים לפצל?", min_value=1, max_value=total_pages, value=1)
            with col2:
                excel_file = st.file_uploader("העלה קובץ שמות (.xlsx / .csv)", type=["xlsx", "csv"])
                
        if excel_file:
            try:
                df_names = pd.read_csv(excel_file) if excel_file.name.endswith('.csv') else pd.read_excel(excel_file)
                _, select_col, _ = st.columns([1, 2, 1])
                with select_col:
                    name_column = st.selectbox("בחר עמודת שמות:", df_names.columns)
                
                if st.button("בצע חלוקה והחל שמות"):
                    st.session_state.current_file = uploaded_file.name
                    names_list = df_names[name_column].dropna().astype(str).tolist()
                    
                    extracted_data = []
                    name_index = 0
                    
                    for start_page in range(1, total_pages + 1, pages_per_split):
                        end_page = min(start_page + pages_per_split - 1, total_pages)
                        file_name = names_list[name_index].strip() if name_index < len(names_list) else f"קובץ_{name_index+1}"
                        
                        extracted_data.append({
                            "עמוד_התחלה": start_page,
                            "עמוד_סיום": end_page,
                            "שם_הקובץ": file_name
                        })
                        name_index += 1
                        
                    st.session_state.pdf_data = extracted_data
                    st.success("הנתונים הוכנו בהצלחה! סקור אותם בטבלה למטה.")
            except Exception as e:
                st.error(f"שגיאה בקריאת הקובץ: {e}")

    # ---------------- Option 2: Smart OCR Splitting (Tesseract) ----------------
    elif method == "זיהוי וחלוקה חכמה (סריקה מהירה לפי מילת מפתח)":
        
        _, opt2_col, _ = st.columns([1, 2, 1])
        with opt2_col:
            anchor_word = st.text_input("מילת החיפוש (המילה שמופיעה מיד לפני השם):", value="שם העובד")
        
        if st.button("🔍 פצל בעזרת OCR"):
            st.session_state.current_file = uploaded_file.name
            
            try:
                pdf_bytes = uploaded_file.getvalue()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                
                extracted_data = []
                current_id = None
                start_page = 1
                
                _, prog_col, _ = st.columns([1, 2, 1])
                with prog_col:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                safe_anchor = re.escape(anchor_word.strip()).replace(r'\ ', r'\s*')
                blacklist = ["תיק ניכויים", "מספר זהות", "תעודת זהות", "תלוש שכר", "שם משפחה", "קוד אישי", "שם עובד"]
                
                for i in range(total_pages):
                    status_text.text(f"סורק עמוד {i+1} מתוך {total_pages}...")
                    
                    page = doc[i]
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    
                    extracted_text = pytesseract.image_to_string(img, lang='heb')
                    clean_text = " ".join(extracted_text.split())
                    
                    page_id = f"לא_מזוהה_עמוד_{i+1}"
                    pattern = rf'{safe_anchor}\s*[:\-]?\s*([א-ת]+\s+[א-ת]+)'
                    
                    matches = re.finditer(pattern, clean_text)
                    for match in matches:
                        potential_name = match.group(1).strip()
                        if not any(bad_word in potential_name for bad_word in blacklist):
                            page_id = potential_name
                            break
                    
                    if page_id == f"לא_מזוהה_עמוד_{i+1}":
                        id_match = re.search(r'(?<!\d)(\d{8,9})(?!\d)', clean_text)
                        if id_match:
                            page_id = f"עובד_{id_match.group(1)}"
                    
                    if current_id is None:
                        current_id = page_id
                        start_page = i + 1
                    elif page_id != current_id and "לא_מזוהה" not in page_id:
                        extracted_data.append({
                            "עמוד_התחלה": start_page,
                            "עמוד_סיום": i,
                            "שם_הקובץ": current_id
                        })
                        current_id = page_id
                        start_page = i + 1
                        
                    progress_bar.progress((i + 1) / total_pages)
                
                if current_id is not None or start_page <= total_pages:
                    extracted_data.append({
                        "עמוד_התחלה": start_page,
                        "עמוד_סיום": total_pages,
                        "שם_הקובץ": current_id
                    })
                    
                st.session_state.pdf_data = extracted_data
                status_text.text("✅ הסריקה הסתיימה בהצלחה!")
                
            except Exception as e:
                st.error(f"שגיאת עיבוד ב-OCR. פרטי השגיאה: {e}")

    # ---------------- Data Editor and Export Module ----------------
    if 'pdf_data' in st.session_state:
        st.write("---")
        st.write("### 📝 עריכה סופית לפני ייצוא")
        
        _, table_col, _ = st.columns([1, 4, 1])
        with table_col:
            st.write("אנא ודא שהשמות נשלפו נכון ותקן ידנית במידת הצורך:")
            df = pd.DataFrame(st.session_state.pdf_data)
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)


        if st.button("✂️ פצל והורד קבצים (ZIP)"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for index, row in edited_df.iterrows():
                    try:
                        start_page = int(row["עמוד_התחלה"]) - 1
                        end_page = int(row["עמוד_סיום"]) - 1
                    except:
                        continue
                        
                    if start_page > end_page or start_page < 0 or end_page >= total_pages:
                        continue 
                    
                    safe_name = re.sub(r'[\\/*?:"<>|]', "", str(row['שם_הקובץ']))
                    if not safe_name.strip():
                        safe_name = f"קובץ_{index+1}"
                    file_name = f"{safe_name}.pdf"
                    
                    writer = PdfWriter()
                    for p in range(start_page, end_page + 1):
                        writer.add_page(reader.pages[p])
                    
                    pdf_buffer = io.BytesIO()
                    writer.write(pdf_buffer)
                    zip_file.writestr(file_name, pdf_buffer.getvalue())

            st.download_button(
                label="⬇️ לחץ כאן להורדת הקבצים (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="split_documents.zip",
                mime="application/zip"
            )
