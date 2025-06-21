import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
from openai import OpenAI
import io
import re

st.set_page_config(page_title="Fuel Report Extractor", layout="centered")
st.title("🛢️ Marine Fuel Analysis Extractor")

openai_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")
uploaded_files = st.file_uploader("📄 Upload one or more Fuel Analysis PDFs", type="pdf", accept_multiple_files=True)

if openai_key and uploaded_files:
    client = OpenAI(api_key=openai_key)
    results = []

    with st.spinner("Extracting data from uploaded PDFs using GPT-4..."):
        for file in uploaded_files:
            try:
                # Read PDF text
                doc = fitz.open(stream=file.read(), filetype="pdf")
                text = "\n".join(page.get_text() for page in doc)

                # Prompt for GPT
                prompt = f"""
You are a marine fuel report assistant. Extract the following fields from the given report:
- Ship Name
- IMO Number
- Bunker Port
- Bunker Date
- Fuel Grade
- Viscosity at 40°C (numeric only)
- Sulfur % (numeric only)
- Net Specific Energy (numeric only)

Return ONLY a valid JSON like this:
{{
  "Ship Name": "...",
  "IMO Number": "...",
  "Bunker Port": "...",
  "Bunker Date": "...",
  "Fuel Grade": "...",
  "Viscosity": "...",
  "Sulfur": "...",
  "Net Specific Energy": "..."
}}

Report:
{text}
                """

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                extracted = response.choices[0].message.content.strip()
                json_data = eval(extracted) if extracted.startswith('{') else {}

                # Clean numeric fields
                for key in ["Viscosity", "Sulfur", "Net Specific Energy"]:
                    if key in json_data:
                        json_data[key] = re.sub(r"[^\d\.]", "", json_data[key])

                json_data["File Name"] = file.name
                results.append(json_data)

            except Exception as e:
                st.error(f"❌ Failed to process {file.name}: {e}")

    if results:
        # Rename columns with units
        df = pd.DataFrame(results)
        df.rename(columns={
            "Viscosity": "Viscosity @ 40°C (mm²/s)",
            "Sulfur": "Sulfur % (m/m)",
            "Net Specific Energy": "Net Specific Energy (MJ/kg)"
        }, inplace=True)

        st.success("✅ Extraction complete!")
        st.dataframe(df)

        # Excel export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Fuel Data')
        st.download_button(
            label="📥 Download as Excel",
            data=output.getvalue(),
            file_name="fuel_report_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
