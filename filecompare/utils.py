import os
import re
import nltk
import numpy as np
import docx
import pdfplumber
from django.conf import settings
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from .models import File, Comparison

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# Initialize lemmatizer and stop words
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('russian'))

# Используем многоязычную модель, которая хорошо работает с русским языком
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

def preprocess_text(text):
    """Preprocess text by normalizing, tokenizing, removing stop words, and lemmatizing."""
    text = re.sub(r'\s+', ' ', text).strip().lower() 
    tokens = word_tokenize(text)
    tokens = [lemmatizer.lemmatize(token) for token in tokens if token.isalnum() and token not in stop_words]
    return ' '.join(tokens)

def save_uploaded_file(uploaded_file):
    """Save an uploaded file temporarily and return its path."""
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, uploaded_file.name)
    
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    return file_path

def read_file(file_path, skip_first_and_second_pages=True):
    """Convert file to text including text in tables, preprocess the text, and remove sources section."""
    file_extension = file_path.rsplit('.', 1)[-1].lower()
    text = ""

    print(f"Processing file: {file_path} with extension: {file_extension}")

    if file_extension == 'docx':
        doc = docx.Document(file_path)
        
        # Extract text while detecting page breaks
        full_text = []
        page_count = 0
        
        for para in doc.paragraphs:
            if "\f" in para.text:
                page_count += 1
                if page_count < 2 and skip_first_and_second_pages:
                    continue 
            full_text.append(para.text)

        text = '\n'.join(full_text)

        # Remove text after the heading "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"
        text = re.split(r'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ', text, flags=re.IGNORECASE)[0]

        # Extract text from tables
        if not skip_first_and_second_pages or page_count >= 2:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += '\n' + cell.text

    elif file_extension == 'pdf':
        with pdfplumber.open(file_path) as pdf:
            pages = pdf.pages[2:] if skip_first_and_second_pages else pdf.pages
            text = '\n'.join([page.extract_text() for page in pages if page.extract_text()])
            # Remove text after the heading
            text = re.split(r'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ', text, flags=re.IGNORECASE)[0]

    elif file_extension == 'txt':
        with open(file_path, 'r', encoding='utf-8') as text_file:
            lines = text_file.readlines()
            text = ''.join(lines[2:] if skip_first_and_second_pages else lines)
            # Remove text after the heading
            text = re.split(r'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ', text, flags=re.IGNORECASE)[0]

    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

    print(f"Extracted text length (post skipping and truncating sources): {len(text)}")
    return text, preprocess_text(text)

def tfidf_lsa_similarity(texts):
    """Compute TF-IDF with Latent Semantic Analysis (LSA) for similarity scoring."""
    vectorizer = TfidfVectorizer(ngram_range=(1, 3))  # 1-gram, 2-gram, 3-gram
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Apply LSA to reduce dimensions and improve similarity detection
    lsa = TruncatedSVD(n_components=100)
    reduced_matrix = lsa.fit_transform(tfidf_matrix)

    return cosine_similarity(reduced_matrix[0:1], reduced_matrix[1:2])[0][0]

def get_document_embedding(text, chunk_size=1000, overlap=200):
    """Generate document embeddings using chunking to handle long documents."""
    if len(text) <= chunk_size:
        return model.encode([text])[0]

    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
    chunk_embeddings = model.encode(chunks)
    
    return np.mean(chunk_embeddings, axis=0)

def calculate_similarity(embedding1, embedding2):
    """Вычислить косинусное сходство между эмбеддингами."""
    similarity = cosine_similarity(
        embedding1.reshape(1, -1), 
        embedding2.reshape(1, -1)
    )
    return float(similarity[0][0])

def highlight_similar_parts(text1, text2):
    """Highlight similar parts of two texts."""
    tokens1 = text1.split()
    tokens2 = set(text2.split())
    highlighted_tokens = []
    for token in tokens1:
        if token in tokens2:
            highlighted_tokens.append(f'<span style="background-color: yellow;">{token}</span>')
        else:
            highlighted_tokens.append(token)
    return ' '.join(highlighted_tokens)


def compare_files(file_paths, user_id, comparison_name):
    """Compare files using hybrid TF-IDF + LSA + Semantic similarity and store results."""
    weight_tfidf = 0.8
    weight_semantic = 0.2
    
    raw_contents, preprocessed_contents = [], []
    for file_path in file_paths:
        raw, preprocessed = read_file(file_path)
        raw_contents.append(raw)
        preprocessed_contents.append(preprocessed)

    semantic_embeddings = [get_document_embedding(raw_text) for raw_text in raw_contents]
    file_instances = [
        File.objects.create(filename=os.path.basename(path), content=content, user_id=user_id)
        for path, content in zip(file_paths, preprocessed_contents)
    ]

    results = []
    for i in range(len(file_instances)):
        for j in range(i + 1, len(file_instances)):
            tfidf_sim = tfidf_lsa_similarity([preprocessed_contents[i], preprocessed_contents[j]]) * 100
            semantic_sim = calculate_similarity(semantic_embeddings[i], semantic_embeddings[j]) * 100
            hybrid_similarity = (weight_tfidf * tfidf_sim + weight_semantic * semantic_sim)

            highlighted_file1 = highlight_similar_parts(raw_contents[i], raw_contents[j])
            highlighted_file2 = highlight_similar_parts(raw_contents[j], raw_contents[i])

            comparison = Comparison.objects.create(
                file1=file_instances[i],
                file2=file_instances[j],
                similarity=hybrid_similarity,
                user_id=user_id,
                highlighted_content1=highlighted_file1,
                highlighted_content2=highlighted_file2,
                comparison_name=comparison_name
            )

            results.append({
                'file1': file_instances[i].filename,
                'file2': file_instances[j].filename,
                'similarity': hybrid_similarity,
                'tfidf_similarity': tfidf_sim,
                'semantic_similarity': semantic_sim,
                'highlighted_file1': highlighted_file1,
                'highlighted_file2': highlighted_file2,
                'comparison': comparison
            })

    return results

def get_file_icon(filename):
    """Map file extensions to FontAwesome icons."""
    extension = filename.split('.')[-1].lower()
    icon_map = {
        'pdf': 'fas fa-file-pdf',
        'docx': 'fas fa-file-word',
        'doc': 'fas fa-file-word',
        'txt': 'fas fa-file-alt',
    }
    return icon_map.get(extension, 'fas fa-file')