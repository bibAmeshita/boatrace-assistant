# ui/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Program, Character, Template, MediaItem, ResultItem
from .forms import ProgramForm, CharacterForm, TemplateForm, MediaForm, ResultForm
from ui.models import Character
from report.core.fetch_payouts import fetch_payouts

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

def prediction_2(request):
    characters = Character.objects.all()
    return render(request, "prediction-2.html", {"characters": characters})

def media(request):
    if request.method == 'POST':
        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('media')
    else:
        form = MediaForm()

    items = MediaItem.objects.all().order_by('-uploaded_at')
    return render(request, 'media.html', {'form': form, 'items': items})


def delete_media(request, pk):
    item = get_object_or_404(MediaItem, pk=pk)
    item.image.delete()
    item.delete()
    return redirect('media')


def result(request):
    if request.method == 'POST':
        # 編集処理
        if 'result_update' in request.POST:
            item = get_object_or_404(ResultItem, pk=request.POST.get('id'))
            form = ResultForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                return redirect('result')

        # 新規登録処理
        else:
            form = ResultForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('result')

    # ← GETのとき、またはPOSTでバリデーション失敗時
    form = ResultForm()
    items = ResultItem.objects.all().order_by('-created_at')
    return render(request, 'result.html', {'form': form, 'items': items})


def delete_result(request, pk):
    item = get_object_or_404(ResultItem, pk=pk)
    item.delete()
    return redirect('result')


def report(request):
    error = None
    venues = None

    try:
        venues = fetch_payouts()  # boatrace.jp から払戻データ取得
    except Exception as e:
        error = str(e)

    characters = Character.objects.all().values('name', 'tone', 'prediction', 'index')

    context = {
        "venues": venues,
        "error": error,
        "characters": list(characters),
        "range_list": range(1, 13),
    }
    return render(request, "report.html", context)