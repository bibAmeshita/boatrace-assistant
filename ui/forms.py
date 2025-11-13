from django import forms
from .models import Program, Character, Template, MediaItem, ResultItem

class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['name']

class CharacterForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = ['name', 'tone', 'prediction', 'index']

class TemplateForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = ['name', 'tag', 'content']

class MediaForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = ['key_name', 'image', 'comment']

class ResultForm(forms.ModelForm):
    class Meta:
        model = ResultItem
        fields = ['key_name', 'title', 'body']
        widgets = {
            'key_name': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
            'title': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
            # 👇ここに richtext クラスを追加！
            'body': forms.Textarea(attrs={'class': 'richtext border rounded p-2 w-full'}),
        }