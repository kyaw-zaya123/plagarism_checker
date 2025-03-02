from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import File, Comparison
from .forms import FileUploadForm, CustomUserCreationForm
from .utils import compare_files, get_file_icon, save_uploaded_file
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count, Case, When, Value, CharField, Q

import os
import json


def home(request):
    return render(request, 'filecompare/home.html')


@login_required
def upload_files(request):
    """Handle file upload for comparison."""
    if request.method == 'POST' and request.FILES.getlist('files'):
        files = request.FILES.getlist('files')
        file_paths = []

        for f in files:
            file_path = save_uploaded_file(f)  
            file_paths.append(file_path)
        
        name_of_comparison = request.POST.get('comparison_name')  
        results = compare_files(file_paths, request.user.id, name_of_comparison)

        # Assign a name if needed
        if results:
            messages.success(request, f"Files uploaded and compared successfully: {name_of_comparison}")
            return render(request, 'filecompare/results.html', {'results': results, 'comparison_name': name_of_comparison})
        else:
            messages.error(request, "No comparison results found. Please try again.")
            return render(request, 'filecompare/upload.html')

    return render(request, 'filecompare/upload.html')


@login_required
def comparison_history(request):
    """View for showing the plagiarism comparison history."""
    comparisons = Comparison.objects.filter(user_id=request.user.id).order_by('-compared_at')
    
    # Pagination
    paginator = Paginator(comparisons, 10)  # Show 10 comparisons per page
    page_number = request.GET.get('page')
    comparisons_page = paginator.get_page(page_number)
    
    return render(request, 'filecompare/history.html', {'comparisons': comparisons_page})


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

    # Pagination
    paginator = Paginator(comparisons, 10)  # Show 10 comparisons per page
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

    # Filter comparisons based on user and search query
    comparisons_queryset = Comparison.objects.filter(user=request.user)

    if search_query:
        comparisons_queryset = comparisons_queryset.filter(comparison_name__icontains=search_query)

    # Get total comparisons for the user
    total_comparisons = comparisons_queryset.count()
    
    # Calculate similarity distribution with correct categories
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

    # Create distribution dictionary with default values
    similarity_distribution_dict = {
        'Low': 0,
        'Medium': 0, 
        'High': 0
    }
    
    # Update with actual counts
    for item in similarity_distribution:
        similarity_distribution_dict[item['category']] = item['count']

    # Convert dictionary to JSON
    similarity_distribution_json = json.dumps(similarity_distribution_dict)
    
    # Paginate comparisons
    paginator = Paginator(Comparison.objects.filter(user=request.user), 10)
    page_number = request.GET.get('page', 1)
    comparisons_page = paginator.get_page(page_number)

    context = {
        'total_comparisons': total_comparisons,
        'similarity_distribution_json': similarity_distribution_json,  
        'similarity_distribution': similarity_distribution_dict, 
        'comparisons': comparisons_page,
        'search_query': search_query
    }
    
    return render(request, 'filecompare/dashboard.html', context)
