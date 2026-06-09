import streamlit as st
import requests
import pymupdf
from PIL import Image
import io

st.set_page_config(page_title="Local AI Study Assistant", page_icon="🧠", layout="centered")

st.title("🧠 Local AI Study Assistant")
st.write("Ask questions from pasted notes, PDFs, and images.")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"


def extract_text_from_pdf(uploaded_file):
    pdf_bytes = uploaded_file.read()
    text = ""

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"

    return text.strip()


def try_extract_text_from_image(uploaded_file):
    image_bytes = uploaded_file.read()
    image = Image.open(io.BytesIO(image_bytes))

    st.image(image, caption="Uploaded image", use_container_width=True)

    try:
        import ocrmac

        image_for_ocr = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        annotations = ocrmac.OCR(image_for_ocr).recognize()

        extracted_lines = []
        for item in annotations:
            if isinstance(item, (list, tuple)) and len(item) > 0:
                extracted_lines.append(str(item[0]))
            else:
                extracted_lines.append(str(item))

        return "\n".join(extracted_lines).strip()

    except ImportError:
        return "[Image uploaded successfully, but OCR is not installed yet. Install ocrmac to extract text from images.]"
    except Exception as e:
        return f"[Image uploaded, but OCR failed: {e}]"


def ask_ollama(context_text, question):
    prompt = f"""
You are a helpful study assistant.

Use the context below to answer the question clearly and simply.
If the answer is not in the context, say: "I could not find that in the provided material."

Context:
{context_text}

Question:
{question}

Answer:
"""

    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=data, timeout=120)
    response.raise_for_status()
    result = response.json()
    return result["response"]


notes = st.text_area("Paste your notes here", height=180)

uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

question = st.text_input("Ask a question")

if st.button("Get answer"):
    combined_text = ""

    if notes.strip():
        combined_text += notes.strip() + "\n\n"

    if uploaded_pdf is not None:
        with st.spinner("Reading PDF..."):
            pdf_text = extract_text_from_pdf(uploaded_pdf)
            if pdf_text.strip():
                combined_text += "PDF CONTENT:\n" + pdf_text + "\n\n"
            else:
                st.warning("The PDF was uploaded, but no readable text was found.")

    if uploaded_image is not None:
        with st.spinner("Reading image..."):
            image_text = try_extract_text_from_image(uploaded_image)
            if image_text.strip():
                combined_text += "IMAGE CONTENT:\n" + image_text + "\n\n"

    if not combined_text.strip():
        st.error("Please paste notes or upload a PDF or image first.")
    elif not question.strip():
        st.error("Please enter a question.")
    else:
        try:
            with st.spinner("Thinking..."):
                answer = ask_ollama(combined_text, question)

            st.subheader("Answer")
            st.success(answer)

            with st.expander("See extracted source text"):
                st.text(combined_text[:12000])

        except requests.exceptions.RequestException as e:
            st.error(f"Could not connect to Ollama: {e}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

