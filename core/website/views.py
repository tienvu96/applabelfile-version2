from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse, FileResponse
from django.http import JsonResponse
from .models import Photo
import os
import json
import pandas as pd
import json
import io
import csv
import re
from openpyxl import load_workbook
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.shared import Pt, Cm
from pathlib import Path
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, FormView, CreateView
from .forms import PhotoForm
from .models import Photo, Document
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from .models import Photo, Document
from .forms import PhotoForm, FileForm
import os
from django.conf import settings
from .scan_module import scan_file, classify_document_with_multiple_rules, define_rules, label_docx_file, label_xlsx_file_footer, edit_label_xlsx_file, edit_label_docx_file


class UploadView(FormView):
    template_name = 'website/upload.html'
    success_url = '/'
    form_class = PhotoForm  # Form mặc định là PhotoForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gallery"] = Photo.objects.all()  # Lấy toàn bộ ảnh
        context["documents"] = Document.objects.all()  # Lấy toàn bộ tệp
        context["photo_form"] = PhotoForm()  # Form cho ảnh
        context["file_form"] = FileForm()  # Form cho tệp
        return context

    def post(self, request, *args, **kwargs):
        # Khởi tạo form cho ảnh và file
        photo_form = PhotoForm(request.POST, request.FILES)
        file_form = FileForm(request.POST, request.FILES)

        # Xử lý upload ảnh
        if 'file' in request.FILES and request.FILES['file'].content_type.startswith('image'):
            if photo_form.is_valid():
                files = request.FILES.getlist('file')
                for file in files:
                    Photo.objects.create(file=file)

        # Xử lý upload tệp nếu là file không phải ảnh
        elif 'file' in request.FILES and not request.FILES['file'].content_type.startswith('image'):
            if file_form.is_valid():
                files = request.FILES.getlist('file')
                for file in files:
                    Document.objects.create(file=file)

        return HttpResponseRedirect(self.success_url)


def delete_photo(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    if photo.file:
        file_path = os.path.join(settings.MEDIA_ROOT, photo.file.name)
        if os.path.exists(file_path):
            os.remove(file_path)
    photo.delete()
    return redirect('website:index')


def delete_file(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if document.file:
        file_path = os.path.join(settings.MEDIA_ROOT, document.file.name)
        if os.path.exists(file_path):
            os.remove(file_path)
    document.delete()
    return redirect('website:index')


def check_file_compliance(request, file_id):

    # Get the file from the database using the file_id
    document = get_object_or_404(Document, id=file_id)

    # Get the file path of the document
    file_path = document.file.path

    # Call the extract_and_iterate_docx_content function with the file path and optional params
    try:
        # scan_result_doc_content = extract_and_iterate_docx_content(file_path, table_id=None, **pandas_kwargs)
        # keyword_dict = load_keywords_from_json()
        # check_keyword_pattern = find_keywords_and_patterns_in_docx(scan_result_doc_content,keyword_dict,patterns)
        # a1 = check_keywords_and_patterns_in_docx(file_path, patterns)
        a2 = scan_file(file_path)
        s4 = define_rules()
        classify, sms = classify_document_with_multiple_rules(a2, s4)

    except Exception as e:
        # Handle any exceptions that might occur
        return JsonResponse({'error': str(e)}, status=500)

    # If no result is found
    if not a2:
        return JsonResponse({'error': 'No content found in the document.'}, status=400)

    # Perform your file scan logic here (for simplicity, we'll just read the file)
    scan_result = f"Scanning file: {document.file.name}"

    # Render the scan result page, passing the scan result to the template
    return render(request, 'website/scan.html', {
        'scan_result': sms,  # Pass the scan result here
        'file_name': document.file.name,  # Optionally pass the file name too
        'file_id': document.id
    })


def label_file_by_rules(request, file_id):
    # Lấy document từ database
    document = get_object_or_404(Document, id=file_id)
    file_path = document.file.path
    file_extension = Path(file_path).suffix.lower()

    try:
        rs_scan_file = scan_file(file_path)
        rs_rule = define_rules()
        category, sms = classify_document_with_multiple_rules(
            rs_scan_file, rs_rule)

        if category:
            # Gán nhãn theo định dạng file
            if file_extension == ".docx":
                label_text = label_docx_file(file_path, category)
            elif file_extension == ".xlsx":
                label_text = label_xlsx_file_footer(file_path, category)
            else:
                sms = "Hiện tại chỉ hỗ trợ docx và xlsx"
                label_text = sms
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Lưu kết quả scan để có thể dùng sau khi chỉnh sửa nhãn
    request.session['label_text'] = label_text
    request.session['file_id'] = file_id

    # Render trang label.html
    return render(request, 'website/label.html', {
        'scan_result': label_text,
        'file_name': document.file.name,
        'file_id': document.id
    })


def edit_label(request, file_id, label_type):
    # Lấy file từ cơ sở dữ liệu
    document = get_object_or_404(Document, id=file_id)
    file_path = document.file.path

    try:
        # Kiểm tra loại nhãn được truyền vào và gán nhãn tương ứng
        if label_type == "internal":
            label_text = "Tài liệu Nội bộ của BIDV. Cấm sao chép, in ấn dưới mọi hình thức!"
        elif label_type == "public":
            label_text = "Tài liệu công khai"
        elif label_type == "confidential":
            label_text = "Tài liệu Mật của BIDV. Cấm sao chép, in ấn dưới mọi hình thức!"
        else:
            return JsonResponse({'error': 'Loại nhãn không hợp lệ'}, status=400)

        # Gán nhãn cho file tùy thuộc vào định dạng file
        file_extension = Path(file_path).suffix.lower()
        if file_extension == ".docx":
            edit_label = edit_label_docx_file(file_path, label_text)
        elif file_extension == ".xlsx":
            edit_label = edit_label_xlsx_file(file_path, label_text)
        else:
            return JsonResponse({'error': 'Hiện tại chỉ hỗ trợ docx và xlsx'}, status=400)

        # Lưu nhãn mới vào session để có thể hiển thị trong trang và tải về
        request.session['label_text'] = label_text

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Render lại trang sau khi gán nhãn thành công
    return render(request, 'website/edit_label.html', {
        'scan_result': "Nhãn của file đã thay đổi thành: " + label_text,
        'file_name': document.file.name,
        'file_id': document.id
    })


def download_file(request, file_id):
    # Get the file from the database using the file_id
    document = get_object_or_404(Document, id=file_id)

    # Get the file path of the document
    file_path = document.file.path
    file_name = document.file.name

    # Open the file for reading
    try:
        with open(file_path, 'rb') as file:
            response = HttpResponse(
                file.read(), content_type='application/octet-stream')
            response[
                'Content-Disposition'] = f'attachment; filename="{os.path.basename(file_name)}"'
            return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def download_file_all(request, file_id):
    # Lấy file từ cơ sở dữ liệu
    document = get_object_or_404(Document, id=file_id)
    file_path = document.file.path

    # Kiểm tra file có tồn tại trên hệ thống không
    if os.path.exists(file_path):
        # Trả về file dưới dạng phản hồi để tải xuống
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=document.file.name)
    else:
        # Nếu file không tồn tại, trả về lỗi
        return JsonResponse({'error': 'File không tồn tại'}, status=404)


def author(request):
    return render(request, 'website/author.html')


def introduce(request):
    return render(request, 'website/introduce.html')


def rule(request):
    return render(request, 'website/rule.html')



from django.views.decorators.cache import never_cache

@never_cache
def list_files(request):
    """
    Hiển thị danh sách các tệp trong thư mục A.
    """
    folder_path = os.path.join(settings.BASE_DIR, 'media', 'gallery')
    try:
        files = os.listdir(folder_path)
        files = [f for f in files if os.path.isfile(os.path.join(folder_path, f))]
    except FileNotFoundError:
        files = []

    return render(request, 'A.html', {'files': files})
