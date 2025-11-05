from django import forms
from .models import Program, Character, Template

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