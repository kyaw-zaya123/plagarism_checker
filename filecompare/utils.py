import os
import re
import nltk
import numpy as np
import docx
import pdfplumber
from django.conf import settings
from collections import Counter
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from .models import File, Comparison

# Download necessary resources
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Initialize NLP tools
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('russian'))
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

def preprocess_text(text):
    """Normalize, tokenize, remove stop words, and lemmatize."""
    text = re.sub(r'\s+', ' ', text).strip().lower()
    tokens = [lemmatizer.lemmatize(token) for token in word_tokenize(text) if token.isalnum() and token not in stop_words]
    return ' '.join(tokens)

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return its path."""
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, uploaded_file.name)

    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return file_path

def extract_text_from_docx(file_path):
    """Extract text from DOCX, starting from 'ВВЕДЕНИЕ' and removing sources list."""
    doc = docx.Document(file_path)
    text_parts = []
    start_extracting = False

    for para in doc.paragraphs:
        if re.search(r'\bВВЕДЕНИЕ\b', para.text, re.IGNORECASE):
            start_extracting = True
        if start_extracting:
            text_parts.append(para.text)

    text = '\n'.join(text_parts)
    text = re.split(r'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ', text, flags=re.IGNORECASE)[0]

    # Extract tables content
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += f'\n{cell.text}'

    return text

def extract_text_from_pdf(file_path):
    """Extract text from PDF, skipping first two pages if applicable."""
    with pdfplumber.open(file_path) as pdf:
        pages = pdf.pages[2:] if len(pdf.pages) > 2 else pdf.pages
        text = '\n'.join(page.extract_text() for page in pages if page.extract_text())
    return re.split(r'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ', text, flags=re.IGNORECASE)[0]

def extract_text_from_txt(file_path):
    """Extract text from TXT, skipping first two lines if applicable."""
    with open(file_path, 'r', encoding='utf-8') as text_file:
        lines = text_file.readlines()
    text = ''.join(lines[2:] if len(lines) > 2 else lines)
    return re.split(r'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ', text, flags=re.IGNORECASE)[0]

def read_file(file_path):
    """Extract text from supported file types."""
    ext = file_path.rsplit('.', 1)[-1].lower()
    extractors = {'docx': extract_text_from_docx, 'pdf': extract_text_from_pdf, 'txt': extract_text_from_txt}

    if ext not in extractors:
        raise ValueError(f"Unsupported file format: {ext}")

    text = extractors[ext](file_path)
    return text, preprocess_text(text)

def tfidf_lsa_similarity(texts):
    """Compute similarity using TF-IDF + LSA."""
    vectorizer = TfidfVectorizer(ngram_range=(1, 3))
    tfidf_matrix = vectorizer.fit_transform(texts)

    lsa = TruncatedSVD(n_components=min(100, tfidf_matrix.shape[1]))  # Avoid over-reduction
    reduced_matrix = lsa.fit_transform(tfidf_matrix)

    return cosine_similarity(reduced_matrix[:1], reduced_matrix[1:2])[0][0]

def get_document_embedding(text, chunk_size=800, overlap=200):
    """Generate embeddings with chunking."""
    if len(text) <= chunk_size:
        return model.encode([text])[0]

    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
    return np.mean(model.encode(chunks), axis=0)

def calculate_similarity(embedding1, embedding2):
    """Compute cosine similarity between embeddings."""
    return float(cosine_similarity(embedding1.reshape(1, -1), embedding2.reshape(1, -1))[0][0])

def highlight_similar_parts(text1, text2):
    """Highlight matching words with frequency awareness."""
    tokens1 = text1.split()
    tokens2_freq = Counter(text2.split())  # Track occurrences

    return ' '.join(f'<span style="background-color: yellow;">{token}</span>' if tokens2_freq[token] > 0 else token for token in tokens1)

def compare_files(file_paths, user_id, comparison_name):
    """Perform hybrid comparison using TF-IDF + LSA + semantic similarity."""
    weight_tfidf, weight_semantic = 0.8, 0.2
    raw_contents, preprocessed_contents = zip(*[read_file(fp) for fp in file_paths])

    # Batch process embeddings
    semantic_embeddings = model.encode(raw_contents)

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
    """Return FontAwesome icon for file type."""
    return {
        'pdf': 'fas fa-file-pdf',
        'docx': 'fas fa-file-word',
        'doc': 'fas fa-file-word',
        'txt': 'fas fa-file-alt'
    }.get(filename.split('.')[-1].lower(), 'fas fa-file')
