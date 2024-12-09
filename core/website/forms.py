from django import forms
from .models import Photo, Document


# class PhotoForm(forms.ModelForm):
#     file = forms.FileField(widget=forms.FileInput(attrs={'multiple': True}))

#     class Meta:
#         model = Photo
#         fields = ('file', )

from multiupload.fields import MultiFileField

class PhotoForm(forms.ModelForm):
    files = MultiFileField()

    class Meta:
        model = Photo
        fields = ('files', )


class FileForm(forms.ModelForm):
    class Meta:
        model = Document  # Kết nối với model Document
        fields = ('file',)  # Chỉ hiển thị trường file

    def __init__(self, *args, **kwargs):
        super(FileForm, self).__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({'class': 'form-control'})