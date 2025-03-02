import logging
import warnings
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Setup logging
LOG_FILE = "rag.log"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[
    logging.FileHandler(LOG_FILE),
    logging.StreamHandler()
])
logger = logging.getLogger(__name__)

# Function to extract text from PDFs
def get_pdf_text(pdf_docs):
    logger.info("Extracting text from uploaded PDFs...")
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    logger.info("PDF text extraction complete.")
    return text

# Function to split text into chunks
def get_text_chunks(text):
    logger.info("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=50000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    logger.info(f"Total chunks created: {len(chunks)}")
    return chunks

# Function to create a FAISS vector store
def get_vector_store(text_chunks):
    logger.info("Creating FAISS vector store...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    logger.info("Vector store saved successfully.")

# Function to create the conversational chain
def get_conversational_chain():
    logger.info("Initializing conversational AI model...")
    prompt_template = """
    Answer the question as detailed as possible from the provided context. If the answer is not in the context, 
    just say, 'Answer is not available in the context'. Do not provide incorrect information.\n\n
    Context:\n {context}?\n
    Question: \n{question}\n
    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    logger.info("Conversational AI model initialized.")
    return chain

# Function to handle user input
def user_input(user_question):
    logger.info(f"Processing user query: {user_question}")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    try:
        new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = new_db.similarity_search(user_question)

        if not docs:
            logger.warning("No relevant documents found in FAISS index.")

        chain = get_conversational_chain()
        response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)

        # Store chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        st.session_state.chat_history.append({"question": user_question, "answer": response["output_text"]})

        logger.info("Response generated successfully.")
        st.write("Reply: ", response["output_text"])

    except Exception as e:
        logger.error(f"Error during query processing: {e}")
        st.error("An error occurred while processing your request.")

# Main function for Streamlit app
def main():
    st.set_page_config("Multi PDF Chatbot", page_icon=":scroll:")
    st.header("Multi-PDF's 🗐 - Chat Agent 🤖 ")

    # Display previous chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.sidebar:
        st.title("📁 PDF File's Section")
        pdf_docs = st.file_uploader("Upload your PDF Files & Click on Submit & Process", accept_multiple_files=True)

        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Processing complete!")
                logger.info("PDF processing and vector storage completed.")

        st.write("---")
        # Display previous chat history in the sidebar
        st.write("### Chat History 📝")
        for chat in st.session_state.chat_history:
            with st.expander(f"Q: {chat['question']}"):
                st.write(f"**A:** {chat['answer']}")

        st.write("___")
        # st.image("img/Robot.jpg")
        st.write("AI App created by @ Jagadeesh Ajjada")

    # Chat input field
    if prompt := st.chat_input("Ask a Question from the Data uploaded .. ⌨"):
        user_input(prompt)

    st.markdown("""
        <div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: #0E1117; padding: 15px; text-align: center;">
            © <a href="https://github.com/JagadeeshAjjada" target="_blank">Jagadeesh Ajjada</a>️
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
