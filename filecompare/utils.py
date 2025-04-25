#utils.py
import os
import re
import nltk
import numpy as np
from docx import Document
import pdfplumber
from django.conf import settings
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# Fix for TensorFlow oneDNN warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import tensorflow as tf
tf.get_logger().setLevel('ERROR')
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from .models import File, Comparison

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

lemmatizer = WordNetLemmatizer()

from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L12-v2')

from langdetect import detect
LANGUAGE_MAP = {
    'en': 'english',
    'ru': 'russian',
    # Add more if needed
}

def get_stopwords_for_text(text):
    """Detect language and return appropriate stopwords."""
    try:
        detected_lang = detect(text)
        LANGUAGE_MAP = {
            'en': 'english',
            'ru': 'russian',
            # Add more mappings as needed
        }
        
        language = LANGUAGE_MAP.get(detected_lang)

        if not language:
            print(f"Warning: Detected language '{detected_lang}' is not in our language map. Using empty stopwords set.")
            return set()
            
    except Exception as e:
        print(f"Language detection failed: {str(e)}. Using empty stopwords set.")
        return set()
    
    if language in stopwords.fileids():
        return set(stopwords.words(language))
    else:
        print(f"No stopwords available for language: {language}")
        return set()

def preprocess_text(text):
    stop_words = get_stopwords_for_text(text)
    text = re.sub(r'\d+', '', text) 
    text = re.sub(r'\s+', ' ', text).strip().lower() 
    
    tokens = [
        lemmatizer.lemmatize(token)
        for token in word_tokenize(text)
        if token.isalnum() and token not in stop_words
    ]
    
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
    """Extract text from DOCX, starting from 'ВВЕДЕНИЕ' and stopping at 'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ' only if they are titles."""
    doc = Document(file_path)
    text_parts = []
    start_extracting = False

    for para in doc.paragraphs:
        para_text = para.text.strip()

        # Check if "ВВЕДЕНИЕ" is a heading
        if para_text.lower() == "введение" and para.style.name.startswith("Heading"):
            start_extracting = True
            continue

        # Check if "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ" is a heading
        if para_text.lower() == "список использованных источников" and para.style.name.startswith("Heading"):
            break  # Stop processing further paragraphs

        if start_extracting:
            text_parts.append(para_text)

    return '\n'.join(text_parts)


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

def split_into_sentences(text):
    """Split text into sentences for granular comparison."""
    sentences = sent_tokenize(text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]

def compute_tfidf_similarity(doc1, doc2):
    """Compute TF-IDF similarity between two documents."""
    vectorizer = TfidfVectorizer()
    
    tfidf_matrix = vectorizer.fit_transform([doc1, doc2])
    
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    
    return float(similarity)

def compute_tfidf_sentence_similarity(sentences1, sentences2, threshold=0.5):
    """
    Compute TF-IDF similarity between sentences of two documents with improved accuracy.
    
    Parameters:
    sentences1 (list): List of sentences from first document
    sentences2 (list): List of sentences from second document
    threshold (float): Minimum similarity score to consider sentences as matching
    
    Returns:
    tuple: (matches, overall_similarity)
    """
    if not sentences1 or not sentences2:
        return [], 0.0

    vectorizer = TfidfVectorizer(
        min_df=2,               
        max_df=0.85,            
        ngram_range=(1, 3),     
        sublinear_tf=True,      
        use_idf=True,           
        smooth_idf=True,        
        analyzer='word',        
        token_pattern=r'\w+',   
    )
    
    all_sentences = sentences1 + sentences2
    
    try:
        tfidf_matrix = vectorizer.fit_transform(all_sentences)
    except ValueError:
        return [], 0.0
    
    tfidf1 = tfidf_matrix[:len(sentences1)]
    tfidf2 = tfidf_matrix[len(sentences1):]
    
    if tfidf1.shape[0] == 0 or tfidf2.shape[0] == 0:
        return [], 0.0
    
    similarity_matrix = cosine_similarity(tfidf1, tfidf2)
    
    matches = []
    for i in range(len(sentences1)):
        best_matches = np.argsort(similarity_matrix[i])[::-1]
        for j in best_matches:
            sim_score = similarity_matrix[i, j]
            if sim_score >= threshold:
                matches.append({
                    'sentence1': sentences1[i],
                    'sentence2': sentences2[j],
                    'similarity': float(sim_score),
                    'method': 'tfidf',
                    'i_index': i,
                    'j_index': j
                })
            else:
                break
    
    if not matches:
        return [], 0.0
    covered_sent1 = set(match['sentence1'] for match in matches)
    covered_sent2 = set(match['sentence2'] for match in matches)
    
    coverage1 = len(covered_sent1) / len(sentences1)
    coverage2 = len(covered_sent2) / len(sentences2)
    
    total_sim_weight = 0
    weighted_sim = 0
    
    for match in matches:
        weight = (len(match['sentence1']) + len(match['sentence2'])) / 2
        weighted_sim += match['similarity'] * weight
        total_sim_weight += weight
    
    avg_similarity = weighted_sim / total_sim_weight if total_sim_weight > 0 else 0
    overall_similarity = (0.45 * coverage1 + 0.45 * coverage2 + 0.1 * avg_similarity) * 100
    return matches, overall_similarity

def find_semantic_matches(sentences1, sentences2, threshold=0.85):
    """Find semantically similar sentences between two documents."""
    embeddings1 = model.encode(sentences1)
    embeddings2 = model.encode(sentences2)
    
    similarity_matrix = cosine_similarity(embeddings1, embeddings2)
    
    matches = []
    for i in range(len(sentences1)):
        for j in range(len(sentences2)):
            if similarity_matrix[i, j] >= threshold:
                matches.append({
                    'sentence1': sentences1[i],
                    'sentence2': sentences2[j],
                    'similarity': float(similarity_matrix[i, j]),
                    'method': 'semantic'
                })
    
    return matches

def highlight_similar_parts(text, matches, is_text1=True):
    """Highlight semantically similar sentences in the text with improved efficiency."""
    key_field = 'sentence1' if is_text1 else 'sentence2'
    
    sorted_matches = sorted(matches, key=lambda x: len(x[key_field]), reverse=True)
    
    replaced_sentences = set()
    
    for match in sorted_matches:
        sentence = match[key_field]
        similarity = match['similarity']
        method = match.get('method', 'semantic')
        
        if sentence in replaced_sentences:
            continue
        
        opacity = min(1, max(0.2, (similarity - 0.85) * 2))
        
        if method == 'semantic':
            color = f"rgba(255, 165, 0, {opacity:.2f})"  # Orange for semantic
        else:
            color = f"rgba(255, 255, 0, {opacity:.2f})"  # Yellow for TF-IDF
        
        escaped_sentence = re.escape(sentence)
        
        pattern = rf'(?<!\w){escaped_sentence}(?!\w)'
        
        compiled_pattern = re.compile(pattern)
        
        replacement = (f'<span class="{method}-match" style="background-color: {color}; padding: 2px; '
                      f'border-radius: 3px;" data-similarity="{similarity:.2f}" data-method="{method}">{sentence}</span>')
        
        if compiled_pattern.search(text):
            text = compiled_pattern.sub(replacement, text, count=1)
            replaced_sentences.add(sentence)
    
    return text

def calculate_document_similarity(semantic_matches, tfidf_matches, sentences1, sentences2):
    """
    Calculate improved document similarity using semantic and TF-IDF methods with better weighting.
    
    Parameters:
    semantic_matches (list): List of semantic similarity matches
    tfidf_matches (list): List of TF-IDF similarity matches
    sentences1 (list): List of sentences from first document
    sentences2 (list): List of sentences from second document
    
    Returns:
    float: Overall similarity percentage
    """
    if not sentences1 or not sentences2:
        return 0.0

    semantic_pairs = {(m['sentence1'], m['sentence2']): m['similarity'] for m in semantic_matches}
    tfidf_pairs = {(m['sentence1'], m['sentence2']): m['similarity'] for m in tfidf_matches}
    
    all_matching_pairs = set(semantic_pairs.keys()) | set(tfidf_pairs.keys())
    
    if not all_matching_pairs:
        return 0.0
    
    covered_sent1 = set(s1 for s1, _ in all_matching_pairs)
    covered_sent2 = set(s2 for _, s2 in all_matching_pairs)
    
    total_chars1 = sum(len(s) for s in sentences1)
    total_chars2 = sum(len(s) for s in sentences2)
    
    covered_chars1 = sum(len(s) for s in covered_sent1)
    covered_chars2 = sum(len(s) for s in covered_sent2)
    
    coverage1 = covered_chars1 / total_chars1
    coverage2 = covered_chars2 / total_chars2
    
    total_similarity = 0
    total_weight = 0
    
    for pair in all_matching_pairs:
        s1, s2 = pair
        
        tfidf_sim = tfidf_pairs.get(pair, 0)
        semantic_sim = semantic_pairs.get(pair, 0)
        
        weight = (len(s1) + len(s2)) / 2
        
        if semantic_sim > 0 and tfidf_sim > 0:
            pair_similarity = (0.7 * semantic_sim + 0.3 * tfidf_sim)
        elif semantic_sim > 0:
            pair_similarity = semantic_sim
        else:
            pair_similarity = tfidf_sim
        
        total_similarity += pair_similarity * weight
        total_weight += weight
    
    avg_similarity = total_similarity / total_weight if total_weight > 0 else 0
    
    final_similarity = (0.45 * coverage1 + 0.45 * coverage2 + 0.1 * avg_similarity) * 100
    
    if final_similarity < 1.0 and (covered_chars1 > 0 or covered_chars2 > 0):
        final_similarity = max(final_similarity, 1.0)  
    
    return final_similarity


def compare_files(file_paths, user_id, comparison_name, semantic_threshold=0.85, tfidf_threshold=0.5):
    raw_contents, preprocessed_contents = zip(*[read_file(fp) for fp in file_paths])
    
    file_instances = [
        File.objects.create(filename=os.path.basename(path), content=raw_content, user_id=user_id)
        for path, raw_content in zip(file_paths, raw_contents)
    ]
    
    results = []
    for i in range(len(file_instances)):
        for j in range(i + 1, len(file_instances)):
            sentences1 = split_into_sentences(raw_contents[i])
            sentences2 = split_into_sentences(raw_contents[j])
            
            semantic_matches = find_semantic_matches(sentences1, sentences2, threshold=semantic_threshold)
            tfidf_matches, tfidf_similarity = compute_tfidf_sentence_similarity(sentences1, sentences2, threshold=tfidf_threshold)
            
            # Подсчет строк по категориям
            no_match_lines = 0
            partial_match_lines = 0
            full_match_lines = 0
            
            # Получаем все совпадения
            all_matches = semantic_matches + tfidf_matches
            
            # Создаем множества строк, которые уже обработаны
            processed_sent1 = set()
            processed_sent2 = set()
            
            # Классифицируем каждую пару совпадений
            for match in all_matches:
                sent1 = match['sentence1']
                sent2 = match['sentence2']
                similarity = match['similarity']
                
                # Пропускаем уже обработанные строки
                if sent1 in processed_sent1 or sent2 in processed_sent2:
                    continue
                
                processed_sent1.add(sent1)
                processed_sent2.add(sent2)
                
                # Классификация по уровню сходства
                if similarity >= 0.85:
                    full_match_lines += 1
                elif similarity >= 0.10:
                    partial_match_lines += 1
                else:
                    no_match_lines += 1
            
            # Подсчитываем строки без совпадений
            for sent in sentences1:
                if sent not in processed_sent1:
                    no_match_lines += 1
            
            for sent in sentences2:
                if sent not in processed_sent2:
                    no_match_lines += 1
            
            total_lines = len(sentences1) + len(sentences2)
            
            # Рассчитываем общее сходство
            combined_similarity = calculate_document_similarity(
                semantic_matches, tfidf_matches, sentences1, sentences2
            )
            
            highlighted_file1 = highlight_similar_parts(raw_contents[i], all_matches, is_text1=True)
            highlighted_file2 = highlight_similar_parts(raw_contents[j], all_matches, is_text1=False)
            
            # Создаем запись сравнения с новыми полями
            comparison = Comparison.objects.create(
                file1=file_instances[i],
                file2=file_instances[j],
                similarity=combined_similarity,
                user_id=user_id,
                highlighted_content1=highlighted_file1,
                highlighted_content2=highlighted_file2,
                comparison_name=comparison_name,
                no_match_lines_count=no_match_lines,
                partial_match_lines_count=partial_match_lines,
                full_match_lines_count=full_match_lines,
                total_lines_count=total_lines
            )
            
            # Обновляем results
            results.append({
                'file1': file_instances[i].filename,
                'file2': file_instances[j].filename,
                'similarity': combined_similarity,
                'semantic_similarity': calculate_document_similarity(semantic_matches, [], sentences1, sentences2),
                'tfidf_similarity': tfidf_similarity,
                'semantic_matches': len(semantic_matches),
                'tfidf_matches': len(tfidf_matches),
                'highlighted_file1': highlighted_file1,
                'highlighted_file2': highlighted_file2,
                'no_match_lines': no_match_lines,
                'partial_match_lines': partial_match_lines,
                'full_match_lines': full_match_lines,
                'total_lines': total_lines,
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
