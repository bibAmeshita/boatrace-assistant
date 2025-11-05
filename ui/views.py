from django.shortcuts import render, redirect, get_object_or_404
from .models import Program, Character, Template
from .forms import ProgramForm, CharacterForm, TemplateForm
from ui.models import Character

def home(request):
    return render(request, 'home.html')

def config(request):
    program = Program.objects.first()
    if not program:
        program = Program.objects.create(name="未設定")

    if request.method == 'POST':
        # --- Program ---
        if 'program_save' in request.POST:
            form = ProgramForm(request.POST, instance=program)
            if form.is_valid():
                form.save()
            return redirect('config')

        # --- Character 保存 ---
        if 'character_save' in request.POST:
            id = request.POST.get('id')
            if id:
                instance = get_object_or_404(Character, id=id)
            else:
                instance = None
            form = CharacterForm(request.POST, instance=instance)
            if form.is_valid():
                form.save()
            return redirect('config')

        # --- Character 削除 ---
        if 'character_delete' in request.POST:
            Character.objects.filter(id=request.POST.get('id')).delete()
            return redirect('config')

        # --- Template 保存 ---
        if 'template_save' in request.POST:
            id = request.POST.get('id')
            if id:
                instance = get_object_or_404(Template, id=id)
            else:
                instance = None
            form = TemplateForm(request.POST, instance=instance)
            if form.is_valid():
                form.save()
            return redirect('config')

        # --- Template 削除 ---
        if 'template_delete' in request.POST:
            Template.objects.filter(id=request.POST.get('id')).delete()
            return redirect('config')

    return render(request, 'config.html', {
        'program': program,
        'characters': Character.objects.all(),
        'templates': Template.objects.all(),
    })


def prediction_1(request):
    characters = Character.objects.all()
    return render(request, "prediction-1.html", {"characters": characters})
