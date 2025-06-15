#views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import File, Comparison
from .forms import FileUploadForm, CustomUserCreationForm
from .utils import compare_files, get_file_icon, save_uploaded_file, highlight_similar_parts
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count, Case, When, Value, CharField, Q, Sum, Avg, Min, Max
from django.core.serializers.json import DjangoJSONEncoder
import os
import json


def home(request):
    return render(request, 'filecompare/home.html')


from django.views.decorators.csrf import ensure_csrf_cookie
from django.urls import reverse

@login_required
@ensure_csrf_cookie  
def upload_files(request):
    """Handle file upload for comparison with progress tracking."""
    if request.method == 'POST' and request.FILES.getlist('files'):
        files = request.FILES.getlist('files')
        file_paths = []
        content_type = request.META.get('HTTP_CONTENT_TYPE', '')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        for f in files:
            file_path = save_uploaded_file(f)  
            file_paths.append(file_path)
        
        name_of_comparison = request.POST.get('comparison_name')  
        results = compare_files(file_paths, request.user.id, name_of_comparison)

        if results:
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f"Files uploaded and compared successfully: {name_of_comparison}",
                    'redirect': reverse('filecompare:results') 
                })
            else:
                messages.success(request, f"Files uploaded and compared successfully: {name_of_comparison}")
                return render(request, 'filecompare/results.html', {'results': results, 'comparison_name': name_of_comparison})
        else:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': "No comparison results found. Please try again."
                })
            else:
                messages.error(request, "No comparison results found. Please try again.")
                return render(request, 'filecompare/upload.html')

    return render(request, 'filecompare/upload.html')


@login_required
def comparison_history(request):
    """View for showing the plagiarism comparison history."""
    comparisons = Comparison.objects.filter(user_id=request.user.id).order_by('-compared_at')
    
    # Pagination
    paginator = Paginator(comparisons, 10)  
    page_number = request.GET.get('page')
    comparisons_page = paginator.get_page(page_number)
    
    return render(request, 'filecompare/history.html', {'comparisons': comparisons_page})


from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, PageBreak, Flowable
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
import re
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics 
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from bs4 import BeautifulSoup

pdfmetrics.registerFont(TTFont('FreeSans', 'fonts/FreeSans.ttf'))
pdfmetrics.registerFont(TTFont('FreeSansBold', 'fonts/FreeSansBold.ttf'))
        
class SimilarityChart(Flowable):
    """Custom flowable to create a similarity gauge chart."""
    def __init__(self, similarity_percentage, width=400, height=40):
        Flowable.__init__(self)
        self.similarity_percentage = similarity_percentage
        self.width = width
        self.height = height
        
    def draw(self):
        self.canv.setFillColor(colors.lightgrey)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        
        if self.similarity_percentage >= 70:
            fill_color = colors.red
        elif self.similarity_percentage >= 30:
            fill_color = colors.orange
        else:
            fill_color = colors.green
            
        self.canv.setFillColor(fill_color)
        filled_width = (self.similarity_percentage / 100) * self.width
        self.canv.rect(0, 0, filled_width, self.height, fill=1, stroke=0)
        
        self.canv.setFillColor(colors.black)
        self.canv.setFont("FreeSansBold", 12)
        self.canv.drawCentredString(self.width / 2, self.height / 3, f"{self.similarity_percentage:.1f}%")

def header_footer(canvas, doc):
    """Add the page header and footer to each page."""
    canvas.saveState()
    
    # Header
    canvas.setFont('FreeSansBold', 10)
    canvas.drawString(72, 780, f"File Comparison Report")
    canvas.drawRightString(540, 780, f"Page {doc.page}")
    canvas.line(72, 770, 540, 770)
    
    # Footer
    canvas.setFont('FreeSans', 8)
    canvas.drawCentredString(306, 30, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    canvas.line(72, 40, 540, 40)
    
    canvas.restoreState()

def clean_html_with_highlighting(html_content):
    """Clean HTML content and preserve text highlighting for ReportLab."""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup.find_all(['html', 'body', 'script', 'style', 'meta', 'head']):
        tag.decompose()
        
    semantic_color = "orange"  # OrangeYellow for semantic matches
    tfidf_color = "gold"     # Gold for TF-IDF matches
    
    for span in soup.find_all('span'):
        span_class = span.get('class', [])
        style = span.get('style', '')
        
        if 'semantic-match' in span_class or ('data-method' in span.attrs and span['data-method'] == 'semantic'):
            span['color'] = semantic_color
            if 'style' in span.attrs:
                del span['style']
        elif 'tfidf-match' in span_class or ('data-method' in span.attrs and span['data-method'] == 'tfidf'):
            span['color'] = tfidf_color
            if 'style' in span.attrs:
                del span['style']
        elif 'background-color' in style:
            if 'rgba(255, 255, 0' in style:  # Yellow (semantic)
                span['color'] = semantic_color
            elif 'rgba(255, 165, 0' in style:  # Orange (TF-IDF)
                span['color'] = tfidf_color
            # Remove HTML styling
            if 'style' in span.attrs:
                del span['style']
    
    allowed_tags = {'b', 'i', 'u', 'br', 'strong', 'em', 'p', 'span'}
    allowed_attrs = {'span': ['color'], 'p': ['align']}

    for tag in soup.find_all():
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            for attr in list(tag.attrs):
                if attr not in allowed_attrs.get(tag.name, []):
                    del tag[attr]

    return str(soup)

@login_required
def generate_pdf(request, comparison_id):
    """Generate an enhanced PDF report for file comparison with Russian text support and proper highlighting."""
    comparison = get_object_or_404(Comparison, id=comparison_id)

    buffer = BytesIO()
    
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
        title=f"Comparison Report: {comparison.comparison_name or f'ID-{comparison.id}'}"
    )
    
    # Create page templates
    frame = Frame(doc.leftMargin, doc.bottomMargin, 
                 doc.width, doc.height - 40,  
                 id='normal')
    
    template = PageTemplate(id='normal', frames=frame, onPage=header_footer)
    doc.addPageTemplates([template])
    
    elements = []
    
    # Define styles with Russian font
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName='FreeSansBold', fontSize=18, alignment=1, spaceAfter=20)
    subtitle_style = ParagraphStyle('Subtitle', fontName='FreeSansBold', fontSize=14, leading=16, spaceBefore=12, spaceAfter=6)
    normal_style = ParagraphStyle('Normal', fontName='FreeSans', fontSize=10, leading=12)
    
    # Logo
    logo_path = "static/image/logo1.jpg"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5 * inch, height=1.5 * inch)  
        elements.append(logo)
        elements.append(Spacer(1, 0.2 * inch)) 
    
    # Title
    elements.append(Paragraph("Отчёт о сравнении файлов", title_style))
    
    # Comparison name
    if comparison.comparison_name:
        elements.append(Paragraph(f"<b>Название:</b> {comparison.comparison_name}", normal_style))
    
    elements.append(Spacer(1, 0.2 * inch))
    
    # Metadata Table
    data = [
        ["Файл 1:", comparison.file1.filename],
        ["Файл 2:", comparison.file2.filename],
        ["Процент совпадения:", f"{comparison.similarity:.2f}%"],
        ["Дата сравнения:", comparison.compared_at.strftime('%Y-%m-%d %H:%M')],
        ["Пользователь:", request.user.username],
    ]
    
    metadata_table = Table(data, colWidths=[2.5 * inch, 3.5 * inch])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'FreeSans'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(metadata_table)
    elements.append(Spacer(1, 0.3 * inch))

    similarity = comparison.similarity
    similarity_text = "Высокое совпадение" if similarity >= 70 else ("Среднее совпадение" if similarity >= 30 else "Низкое совпадение")

    elements.append(Paragraph("Уровень схожести:", subtitle_style))
    elements.append(Spacer(1, 0.1 * inch))
    
    elements.append(SimilarityChart(similarity))
    elements.append(Paragraph(f"{similarity_text}", normal_style))
    
    try:
        file1_content = comparison.highlighted_content1 if hasattr(comparison, 'highlighted_content1') else comparison.file1.content
        file2_content = comparison.highlighted_content2 if hasattr(comparison, 'highlighted_content2') else comparison.file2.content
    except Exception as e:
        file1_content = f"Ошибка при загрузке содержимого файла 1: {str(e)}"
        file2_content = f"Ошибка при загрузке содержимого файла 2: {str(e)}"
        elements.append(Paragraph(f"⚠ Ошибка: {str(e)}", normal_style))

    # Add File 1 content with page break to ensure it starts on a new page
    elements.append(PageBreak())
    elements.append(Paragraph("Содержимое файла 1 (с выделением сходств):", subtitle_style))
    elements.append(Spacer(1, 0.1 * inch))
    
    # Add file info
    elements.append(Paragraph(f"<b>Имя файла:</b> {comparison.file1.filename}", normal_style))
    elements.append(Paragraph(f"<b>Тип файла:</b> {os.path.splitext(comparison.file1.filename)[1]}", normal_style))
    normal_style = ParagraphStyle('Normal', fontName='FreeSans', fontSize=10, leading=12, alignment=4)  
    elements.append(Spacer(1, 0.1 * inch))
    
    # Add content with highlighting - using the BeautifulSoup method from the second code
    file1_clean_content = clean_html_with_highlighting(file1_content)
    elements.append(Paragraph(file1_clean_content, normal_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Add File 2 content with page break
    elements.append(PageBreak())
    elements.append(Paragraph("Содержимое файла 2 (с выделением сходств):", subtitle_style))
    elements.append(Spacer(1, 0.1 * inch))
    
    # Add file info
    elements.append(Paragraph(f"<b>Имя файла:</b> {comparison.file2.filename}", normal_style))
    elements.append(Paragraph(f"<b>Тип файла:</b> {os.path.splitext(comparison.file2.filename)[1]}", normal_style))
    normal_style = ParagraphStyle('Normal', fontName='FreeSans', fontSize=10, leading=12, alignment=4)  
    elements.append(Spacer(1, 0.1 * inch))
    
    # Add content with highlighting - using the BeautifulSoup method from the second code
    file2_clean_content = clean_html_with_highlighting(file2_content)
    elements.append(Paragraph(file2_clean_content, normal_style))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("Благодарим вас за использование нашей системы для проверки уникальности!", subtitle_style))

    # Build and save PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    
    filename = f"comparison_report_{comparison.id}.pdf"
    if comparison.comparison_name:
        clean_name = re.sub(r'[^\w\s-]', '', comparison.comparison_name).strip().replace(' ', '_')
        filename = f"{clean_name}_report.pdf"
    
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def view_comparison(request, comparison_id):
    """View to display the detailed comparison results."""
    comparison = get_object_or_404(Comparison, id=comparison_id)
    return render(request, 'filecompare/comparison_detail.html', {'comparison': comparison})


@login_required
def download_file(request, file_id):
    """Download a file from the database."""
    file_instance = get_object_or_404(File, id=file_id)
    file_path = file_instance.file_path
    try:
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type="application/octet-stream")
            response['Content-Disposition'] = f'attachment; filename={file_instance.filename}'
            return response
    except FileNotFoundError:
        messages.error(request, "File not found.")
        return redirect('comparison_history')


def save_uploaded_file(file):
    """Utility function to save uploaded file temporarily."""
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    file_path = os.path.join(upload_dir, file.name)
    with open(file_path, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)  
    return file_path


@login_required
def delete_comparison(request, comparison_id):
    comparison = get_object_or_404(Comparison, id=comparison_id)
    comparison.delete()
    messages.success(request, "Comparison deleted successfully.")
    return redirect('comparison_history')


@login_required
def search_comparisons(request):
    query = request.GET.get('query', '')
    comparisons = Comparison.objects.filter(user_id=request.user.id)

    if query:
        comparisons = comparisons.filter(
            Q(file1__filename__icontains=query) |
            Q(file2__filename__icontains=query) |
            Q(comparison_name__icontains=query)
        )

    comparisons = comparisons.order_by('-compared_at')

    paginator = Paginator(comparisons, 10)  
    page_number = request.GET.get('page')
    comparisons_page = paginator.get_page(page_number)

    return render(request, 'filecompare/history.html', {'comparisons': comparisons_page, 'query': query})


def get_file_icon_view(request, filename):
    """Return file icon based on file extension."""
    icon = get_file_icon(filename)
    return JsonResponse({'icon': icon})


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  
    else:
        form = CustomUserCreationForm()
    return render(request, 'filecompare/register.html', {'form': form})


def user_login(request):
   if request.method == 'POST':
       username = request.POST['username']
       password = request.POST['password']
       user = authenticate(request, username=username, password=password)
       
       if user is not None:
           login(request, user)
           messages.success(request, 'Login successful!')
           return redirect('home')
       else:
           messages.error(request, 'Invalid username or password.')
   return render(request, 'filecompare/login.html')


def custom_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def dashboard(request):
    search_query = request.GET.get('q', '')

    comparisons_queryset = Comparison.objects.filter(user=request.user)

    if search_query:
        comparisons_queryset = comparisons_queryset.filter(comparison_name__icontains=search_query)

    total_comparisons = comparisons_queryset.count()
    
    # Суммируем количество строк в каждой категории
    lines_summary = comparisons_queryset.aggregate(
        no_match_lines=Sum('no_match_lines_count'),
        partial_match_lines=Sum('partial_match_lines_count'),
        full_match_lines=Sum('full_match_lines_count'),
        total_lines=Sum('total_lines_count')
    )
    
    # Проверяем на None и заменяем на 0
    lines_summary = {k: v or 0 for k, v in lines_summary.items()}

    # Calculate duration statistics
    duration_stats = {
        'avg_duration': comparisons_queryset.aggregate(Avg('duration'))['duration__avg'] or 0,
        'max_duration': comparisons_queryset.aggregate(Max('duration'))['duration__max'] or 0,
        'min_duration': comparisons_queryset.aggregate(Min('duration'))['duration__min'] or 0,
        'total_duration': comparisons_queryset.aggregate(Sum('duration'))['duration__sum'] or 0,
    }

    # Get duration data for chart
    duration_data = (
        comparisons_queryset
        .values('file1__filename', 'file2__filename', 'duration', 'compared_at')
        .order_by('-compared_at')[:10]  # Get the 10 most recent comparisons for the chart
    )
    
    duration_data_json = json.dumps(list(duration_data), cls=DjangoJSONEncoder)
    
    # Оригинальное распределение по категориям документов 
    similarity_distribution = (
        comparisons_queryset
        .annotate(
            category=Case(
                When(similarity__lt=30, then=Value('Low')),
                When(Q(similarity__gte=30) & Q(similarity__lt=70), then=Value('Medium')), 
                When(similarity__gte=70, then=Value('High')),
                output_field=CharField()
            )
        )
        .values('category')
        .annotate(count=Count('category'))
        .order_by('category')
    )

    similarity_distribution_dict = {
        'Low': 0,
        'Medium': 0, 
        'High': 0
    }

    for item in similarity_distribution:
        similarity_distribution_dict[item['category']] = item['count']
    
    # JSON для графиков
    similarity_distribution_json = json.dumps(similarity_distribution_dict)
    lines_summary_json = json.dumps({
        'NoMatch': lines_summary['no_match_lines'],
        'PartialMatch': lines_summary['partial_match_lines'],
        'FullMatch': lines_summary['full_match_lines']
    })

    paginator = Paginator(comparisons_queryset, 10)
    page_number = request.GET.get('page', 1)
    comparisons_page = paginator.get_page(page_number)

    context = {
        'total_comparisons': total_comparisons,
        'similarity_distribution_json': similarity_distribution_json,  
        'similarity_distribution': similarity_distribution_dict,
        'lines_summary': lines_summary,
        'lines_summary_json': lines_summary_json,
        'comparisons': comparisons_page,
        'duration_stats': duration_stats,
        'duration_data_json': duration_data_json,
        'search_query': search_query
    }
    
    return render(request, 'filecompare/dashboard.html', context)

# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from .models import File, Comparison
from .serializers import FileSerializer, ComparisonSerializer

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    
    def get_queryset(self):
        """Filter files by current user"""
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            return File.objects.filter(user_id=user_id)
        return File.objects.none()
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID required'}, status=status.HTTP_400_BAD_REQUEST)
            
        uploaded_file = request.FILES['file']
        file_path = save_uploaded_file(uploaded_file)
        
        try:
            from .utils import read_file
            raw_content, _ = read_file(file_path)
            
            file_instance = File.objects.create(
                filename=uploaded_file.name,
                content=raw_content,
                user_id=user_id
            )
            
            return Response(FileSerializer(file_instance).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ComparisonViewSet(viewsets.ModelViewSet):
    queryset = Comparison.objects.all()
    serializer_class = ComparisonSerializer
    
    def get_queryset(self):
        """Filter comparisons by current user"""
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            return Comparison.objects.filter(user_id=user_id)
        return Comparison.objects.none()
    
    @action(detail=False, methods=['post'])
    def compare_files(self, request):
        file_ids = request.data.get('file_ids', [])
        user_id = request.data.get('user_id')
        comparison_name = request.data.get('comparison_name', 'Comparison')
        semantic_threshold = float(request.data.get('semantic_threshold', 0.9))
        tfidf_threshold = float(request.data.get('tfidf_threshold', 0.8))
        
        if not file_ids or len(file_ids) < 2:
            return Response({'error': 'Please select at least two files to compare'}, 
                           status=status.HTTP_400_BAD_REQUEST)
                           
        if not user_id:
            return Response({'error': 'User ID required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            file_paths = []
            for file_id in file_ids:
                file_obj = File.objects.get(id=file_id)
                file_path = os.path.join(settings.MEDIA_ROOT, 'uploads', file_obj.filename)
                
                if not os.path.exists(file_path):
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_obj.content)
                
                file_paths.append(file_path)
            
            results = compare_files(
                file_paths, 
                user_id, 
                comparison_name,
                semantic_threshold,
                tfidf_threshold
            )
            response_data = []
            for result in results:
                comparison = result['comparison']
                response_data.append({
                    'comparison_id': comparison.id,
                    'file1': result['file1'],
                    'file2': result['file2'],
                    'similarity': result['similarity'],
                    'semantic_similarity': result['semantic_similarity'],
                    'tfidf_similarity': result['tfidf_similarity']
                })
                
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        