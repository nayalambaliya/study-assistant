import streamlit as st
import requests
import pymupdf
from PIL import Image
import io

st.set_page_config(page_title="Local AI Study Assistant", page_icon="🧠", layout="centered")

st.title("🧠 Local AI Study Assistant")
st.write("Upload your study material, then ask questions about it.")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "context" not in st.session_state:
    st.session_state.context = ""


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
        return "[OCR not installed. Install ocrmac to extract text from images.]"
    except Exception as e:
        return f"[Image uploaded, but OCR failed: {e}]"


def ask_ollama(context_text, chat_history):
    system_prompt = f"""You are a helpful study assistant.
Use the context below to answer questions clearly and simply.
If the answer is not in the context, say: "I could not find that in the provided material."

Context:
{context_text}"""

    messages = [{"role": "system", "content": system_prompt}] + chat_history

    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL_NAME, "messages": messages, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


# --- Material upload section ---
notes = st.text_area("Paste your notes here", height=150)
uploaded_pdfs = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

if st.button("Load material"):
    combined_text = ""

    if notes.strip():
        combined_text += notes.strip() + "\n\n"

    for pdf in uploaded_pdfs:
        with st.spinner(f"Reading {pdf.name}..."):
            pdf_text = extract_text_from_pdf(pdf)
            if pdf_text.strip():
                combined_text += f"[PDF: {pdf.name}]\n{pdf_text}\n\n"
            else:
                st.warning(f"{pdf.name}: no readable text found.")

    if uploaded_image is not None:
        with st.spinner("Reading image..."):
            image_text = try_extract_text_from_image(uploaded_image)
            if image_text.strip():
                combined_text += f"[IMAGE]\n{image_text}\n\n"

    if not combined_text.strip():
        st.error("Please paste notes or upload a file first.")
    else:
        st.session_state.context = combined_text
        st.session_state.messages = []
        st.success("Material loaded! Ask your questions below.")

# --- Chat section ---
if st.session_state.context:
    st.divider()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("Ask a question about your material...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = ask_ollama(st.session_state.context, st.session_state.messages)
                    st.write(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not connect to Ollama: {e}")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

    if st.session_state.messages:
        chat_export = "\n\n".join(
            f"{'You' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in st.session_state.messages
        )
        st.download_button(
            label="Export chat as .txt",
            data=chat_export,
            file_name="chat_history.txt",
            mime="text/plain",
        )

    with st.expander("See extracted source text"):
        st.text(st.session_state.context[:12000])
