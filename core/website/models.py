from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError



# Create your models here.

class Photo(models.Model):
    file = models.ImageField(upload_to="gallery/")


# Hàm để kiểm tra loại file
def validate_file_extension(value):
    valid_extensions = ['.csv', '.txt', '.xlsx', '.pdf', '.docx']
    ext = value.name.split('.')[-1].lower()  # Lấy phần mở rộng file
    if f'.{ext}' not in valid_extensions:
        raise ValidationError('File không hợp lệ! Chỉ hỗ trợ các định dạng: csv, txt, xlsx, pdf, docx.')

class Document(models.Model):
    file = models.FileField(upload_to="gallery/", validators=[validate_file_extension])

    def __str__(self):
        return self.file.name