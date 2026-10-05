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

# התאמה חכמה: המחשב יחפש את Tesseract בשתי התיקיות הנפוצות בווינדוס
if sys.platform.startswith('win'):
    path1 = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    path2 = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    
    if os.path.exists(path1):
        pytesseract.pytesseract.tesseract_cmd = path1
    elif os.path.exists(path2):
        pytesseract.pytesseract.tesseract_cmd = path2
    else:
        st.warning("שים לב: מנוע ה-OCR לא נמצא בתיקיות הרגילות. ודא שהתקנת את Tesseract.")

st.set_page_config(page_title="מפצל PDF חכם", layout="wide")
st.title("מפצל PDF חכם ✂")
st.write("כלי לחלוקת קובצי PDF ומתן שמות אוטומטי - פרויקט קוד פתוח מבוסס Tesseract OCR.")

method = st.radio(
    "בחר שיטת פיצול:",
    ["חלוקה קבועה לעמודים + שמות מקובץ אקסל", "זיהוי וחלוקה חכמה (סריקה מהירה לפי מילת מפתח)"]
)

uploaded_file = st.file_uploader("העלה קובץ PDF", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    st.info(f"הקובץ מכיל {total_pages} עמודים.")

    if st.button("🔄 רענן נתונים ונקה טבלה"):
        for key in ['pdf_data', 'current_file']:
            if key in st.session_state:
                del st.session_state[key]

    # ---------------- אופציה 1: חלוקה קבועה + אקסל ----------------
    if method == "חלוקה קבועה לעמודים + שמות מקובץ אקסל":
        
        col1, col2 = st.columns([1, 2])
        with col1:
            pages_per_split = st.number_input("כל כמה עמודים לפצל?", min_value=1, max_value=total_pages, value=1)
        
        with col2:
            excel_file = st.file_uploader("העלה קובץ אקסל (.xlsx) או CSV עם רשימת השמות", type=["xlsx", "csv"])
            
        if excel_file:
            try:
                df_names = pd.read_csv(excel_file) if excel_file.name.endswith('.csv') else pd.read_excel(excel_file)
                name_column = st.selectbox("בחר את העמודה שמכילה את שמות הקבצים:", df_names.columns)
                
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

    # ---------------- אופציה 2: סריקה (Tesseract) ----------------
    elif method == "זיהוי וחלוקה חכמה (סריקה מהירה לפי מילת מפתח)":
        
        # שדה חדש שהמשתמש יכול לערוך
        anchor_word = st.text_input("לפי איזו מילה תרצה לחלץ את השם? (המילה שמופיעה מיד לפני השם)", value="שם העובד")
        
        if st.button("סרוק ופצל בעזרת OCR"):
            st.session_state.current_file = uploaded_file.name
            
            try:
                pdf_bytes = uploaded_file.getvalue()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                
                extracted_data = []
                current_id = None
                start_page = 1
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # התאמה של מילת החיפוש שהוזנה כך שתתעלם מרווחים לא מדויקים במסמך
                safe_anchor = re.escape(anchor_word.strip()).replace(r'\ ', r'\s*')
                
                for i in range(total_pages):
                    status_text.text(f"סורק עמוד {i+1} מתוך {total_pages}...")
                    
                    page = doc[i]
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    
                    extracted_text = pytesseract.image_to_string(img, lang='heb')
                    clean_text = " ".join(extracted_text.split())
                    
                    page_id = f"לא_מזוהה_עמוד_{i+1}"
                    
                    # חיפוש חכם שמבוסס על מה שהקלדת בתיבת הטקסט
                    pattern = rf'{safe_anchor}\s*[:\-]?\s*([א-ת]+\s+[א-ת]+)'
                    name_match = re.search(pattern, clean_text)
                    
                    if name_match:
                        page_id = name_match.group(1).strip()
                    else:
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
                status_text.text("הסריקה הסתיימה בהצלחה!")
                
            except Exception as e:
                st.error(f"שגיאת עיבוד ב-OCR. פרטי השגיאה: {e}")

    # ---------------- טבלת עריכה וייצוא (משותף) ----------------
    if 'pdf_data' in st.session_state:
        st.write("### 📝 עריכה סופית לפני ייצוא")
        st.write("כאן ניתן לוודא שהשמות נשלפו נכון ולתקן ידנית במידת הצורך.")
        
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
                label="⬇️ לחץ כאן להורדת ה-ZIP",
                data=zip_buffer.getvalue(),
                file_name="split_documents.zip",
                mime="application/zip"
            )