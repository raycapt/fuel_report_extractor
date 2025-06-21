import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
from openai import OpenAI
import io

st.set_page_config(page_title="Fuel Report Extractor", layout="centered")
st.title("🛢️ Marine Fuel Analysis Extractor")

openai_key = st.text_input("🔑 Enter your OpenAI API Key", type="password")

uploaded_files = st.file_uploader("📄 Upload one or more Fuel Analysis PDFs", type="pdf", accept_multiple_files=True)

if openai_key and uploaded_files:
    client = OpenAI(api_key=openai_key)  # ✅ create client correctly
    results = []

    with st.spinner("Extracting data from uploaded PDFs using GPT-4..."):
        for file in uploaded_files:
            # Read PDF text
            doc = fitz.open(stream=file.read(), filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)

            # Prompt GPT
            prompt = f"""
You are a marine fuel report assistant. Extract the following fields from the given report:
- Ship Name
- IMO Number
- Bunker Port
- Bunker Date
- Fuel Grade
- Viscosity at 40°C
- Sulfur %
- Net Specific Energy

Return ONLY a valid JSON like this:
{{
  "Ship Name": "...",
  "IMO Number": "...",
  "Bunker Port": "...",
  "Bunker Date": "...",
  "Fuel Grade": "...",
  "Viscosity @ 40°C": "...",
  "Sulfur %": "...",
  "Net Specific Energy": "..."
}}

Report:
{text}
"""
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                extracted = response.choices[0].message.content.strip()
                json_data = eval(extracted) if extracted.startswith('{') else {}
                json_data["File Name"] = file.name
                results.append(json_data)

            except Exception as e:
                st.error(f"❌ Failed to process {file.name}: {e}")

    if results:
        df = pd.DataFrame(results)
        st.success("✅ Extraction complete!")
        # Strip units from values (if present)
df["Viscosity @ 40°C"] = df["Viscosity @ 40°C"].str.extract(r"([\d.]+)").astype(float)
df["Sulfur %"] = df["Sulfur %"].str.extract(r"([\d.]+)").astype(float)
df["Net Specific Energy"] = df["Net Specific Energy"].str.extract(r"([\d.]+)").astype(float)

# Update column headers to include units
df.rename(columns={
    "Viscosity @ 40°C": "Viscosity @ 40°C (mm²/s)",
    "Sulfur %": "Sulfur % (m/m)",
    "Net Specific Energy": "Net Specific Energy (MJ/kg)"
}, inplace=True)

        st.dataframe(df)

        # Download Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Fuel Analysis")

        st.download_button("📥 Download Excel", data=output.getvalue(), file_name="fuel_analysis_extracted.xlsx")
else:
    st.info("Please enter your OpenAI key and upload PDF(s).")
