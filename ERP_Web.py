import streamlit as st
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime

# --- SETTINGS ---
st.set_page_config(page_title="Yard ERP Portal", layout="wide")
st.title("🚢 Yard Transshipment ERP Portal")

# --- SIDEBAR: EMAIL SETTINGS ---
with st.sidebar:
    st.header("Mail Server Config")
    smtp_server = st.text_input("SMTP Server", "smtp.office365.com")
    my_email = st.text_input("Your Email")
    my_pass = st.text_input("App Password", type="password")

# --- STEP 1: UPLOAD DATA ---
st.header("Step 1: Upload Files")
col1, col2 = st.columns(2)

with col1:
    uploaded_csvs = st.file_uploader("Upload Yard CSVs", accept_multiple_files=True, type="csv")
with col2:
    settings_file = st.file_uploader("Upload ERP_Master_Settings.xlsx", type="xlsx")

# --- STEP 2: PROCESS DATA ---
if uploaded_csvs and settings_file:
    st.success("Files Uploaded!")
    
    # Consolidate
    df_list = [pd.read_csv(f) for f in uploaded_csvs]
    master_df = pd.concat(df_list, ignore_index=True)
    
    # Filter & Ageing Logic
    ts_df = master_df[master_df['Category'].str.contains('Transshipment', case=False, na=False)].copy()
    ts_df['Ageing'] = ts_df['Days stored'].apply(lambda x: "1 to 14" if x <= 14 else ("15 to 90" if x <= 90 else "91 Above"))
    
    st.header("Step 2: Data Preview")
    st.dataframe(ts_df.head(10)) # Show first 10 rows

    # --- STEP 3: SEND EMAILS ---
    if st.button("🚀 Process & Email All Customers"):
        try:
            contacts = pd.read_excel(settings_file, sheet_name='Contacts')
            email_map = dict(zip(contacts['Customer Name'], contacts['Email Address']))
            
            for customer in ts_df['Customer Name'].unique():
                cust_data = ts_df[ts_df['Customer Name'] == customer]
                
                # Create Email
                recipient = email_map.get(customer)
                if recipient:
                    msg = EmailMessage()
                    msg['Subject'] = f"Inventory Report - {customer}"
                    msg['To'] = recipient
                    msg['From'] = my_email
                    msg.set_content(f"Dear {customer}, your transshipment report is attached.")
                    
                    # Convert dataframe to Excel in memory (No local saving needed!)
                    import io
                    towrite = io.BytesIO()
                    cust_data.to_excel(towrite, index=False, engine='openpyxl')
                    towrite.seek(0)
                    
                    msg.add_attachment(towrite.read(), maintype='application', 
                                       subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                                       filename=f"{customer}_Report.xlsx")
                    
                    # Send
                    with smtplib.SMTP(smtp_server, 587) as s:
                        s.starttls()
                        s.login(my_email, my_pass)
                        s.send_message(msg)
                    st.write(f"✅ Sent to {customer}")
            
            st.balloons()
            st.success("All Emails Sent Successfully!")
        except Exception as e:
            st.error(f"Error: {e}")
