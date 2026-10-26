"""Studiya — elektron darslik yaratish va tahrirlash (ustoz uchun)."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.db import transaction
from django.db.models import Count, Max
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import backup as bk
from . import editing as ed
from .docx_parser import parse
from .export import build_zip
from .forms import (BlockForm, CourseForm, DocxImportForm, LoginForm, NewCourseForm, NewTopicForm, PartForm, QAForm, ResourceForm,
                    SectionForm, SetupForm, TermForm, TestForm, TopicExtrasForm, TopicForm)
from .importer import auto_glossary, create_course, guess_scene, qa_from_content
from .models import PALETTE, SCENES, Course, GlossaryTerm, Media, Part, QuickQA, Resource, Section, TestQuestion, Topic


# ------------------------------------------------------------------ kirish
class StudioLogin(LoginView):
    template_name = 'lectures/studio/login.html'
    authentication_form = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if not User.objects.exists():
            return redirect('studio:setup')
        return super().dispatch(request, *args, **kwargs)


class StudioPasswordChange(PasswordChangeView):
    """Ustoz o'z parolini o'zgartiradi."""
    template_name = 'lectures/studio/password.html'

    def get_success_url(self):
        messages.success(self.request, 'Parol o‘zgartirildi. Keyingi safar yangi parol bilan kiring.')
        return reverse('studio:dashboard')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        labels = {'old_password': 'Hozirgi parol', 'new_password1': 'Yangi parol', 'new_password2': 'Yangi parolni takrorlang'}
        for name, label in labels.items():
            form.fields[name].label = label
            form.fields[name].help_text = ''
        return form


def setup(request):
    """Birinchi ishga tushirish: ustoz o'ziga login va parol yaratadi."""
    if User.objects.exists():
        return redirect('studio:login')
    form = SetupForm(request.POST or None)
    if form.is_valid():
        d = form.cleaned_data
        user = User.objects.create_superuser(d['username'], password=d['password'], first_name=d['name'])
        login(request, user)
        messages.success(request, f"Xush kelibsiz, {d['name']}! Endi darslik yaratishingiz mumkin.")
        return redirect('studio:dashboard')
    return render(request, 'lectures/studio/setup.html', {'form': form})


def studio_view(fn):
    """login_required + darslikni slug bo'yicha topish."""
    @login_required
    @wraps(fn)
    def inner(request, slug=None, *args, **kwargs):
        if slug is None:
            return fn(request, *args, **kwargs)
        course = get_object_or_404(Course, slug=slug)
        return fn(request, course, *args, **kwargs)
    return inner


def get_topic(course, n):
    return get_object_or_404(course.topics.select_related('part'), number=n)


def topic_url(topic, tab=''):
    url = reverse('studio:topic', args=[topic.course.slug, topic.number])
    return f'{url}?tab={tab}' if tab else url


def touch(course):
    course.save(update_fields=['updated'])


# ------------------------------------------------------------------ bosh panel
@studio_view
def dashboard(request):
    courses = Course.objects.annotate(n_topics=Count('topics', distinct=True))
    return render(request, 'lectures/studio/dashboard.html', {'courses': courses})


@studio_view
def course_new(request):
    imp = DocxImportForm(prefix='imp')
    new = NewCourseForm(prefix='new')
    if request.method == 'POST' and 'import' in request.POST:
        imp = DocxImportForm(request.POST, request.FILES, prefix='imp')
        if imp.is_valid():
            d = imp.cleaned_data
            try:
                data = parse(d['file'])
            except Exception:  # noqa: BLE001 — buzilgan yoki docx bo'lmagan fayl
                imp.add_error('file', 'Faylni o‘qib bo‘lmadi. U haqiqiy Word (.docx) faylimi?')
            else:
                course = create_course(data, title=d['title'] or None, author=d['author'], author_photo=d['author_photo'])
                n = course.topics.count()
                tests = TestQuestion.objects.filter(topic__course=course).count()
                fmt = 'o‘quv-uslubiy majmua' if data['format'] == 'majmua' else 'sarlavhalar bo‘yicha'
                messages.success(request, f'Darslik yaratildi ({fmt}): {n} ta mavzu, {tests} ta test savoli.')
                for p in data['problems'][:5]:
                    messages.warning(request, p)
                return redirect('studio:course', slug=course.slug)
    elif request.method == 'POST':
        new = NewCourseForm(request.POST, prefix='new')
        if new.is_valid():
            course = new.save()
            messages.success(request, 'Bo‘sh darslik yaratildi. Endi birinchi mavzuni qo‘shing.')
            return redirect('studio:course', slug=course.slug)
    return render(request, 'lectures/studio/course_new.html', {'imp': imp, 'new': new})


# ------------------------------------------------------------------ darslik
@studio_view
def course_edit(request, course):
    """Mavzular ro'yxati + yangi mavzu qo'shish."""
    form = NewTopicForm(request.POST or None, course=course)
    if request.method == 'POST' and form.is_valid():
        topic = form.save(commit=False)
        topic.course = course
        topic.number = (course.topics.aggregate(m=Max('number'))['m'] or 0) + 1
        topic.scene = guess_scene(topic.title, topic.number)
        topic.save()
        Section.objects.create(topic=topic, order=1, title='Asosiy tushunchalar')
        touch(course)
        messages.success(request, f'{topic.number}-mavzu qo‘shildi.')
        return redirect(topic_url(topic))
    topics = course.topics.select_related('part').annotate(n_sec=Count('sections', distinct=True), n_test=Count('tests', distinct=True))
    return render(request, 'lectures/studio/course.html', {'course': course, 'topics': topics, 'form': form, 'tab': 'mavzular'})


@studio_view
def course_settings(request, course):
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Darslik ma’lumotlari saqlandi.')
        return redirect('studio:settings', slug=course.slug)
    return render(request, 'lectures/studio/settings.html', {'course': course, 'form': form, 'tab': 'sozlamalar', 'palette': PALETTE})


@studio_view
def parts(request, course):
    form = PartForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        part = form.save(commit=False)
        part.course = course
        part.order = (course.parts.aggregate(m=Max('order'))['m'] or 0) + 1
        part.save()
        messages.success(request, f'«{part.name}» bo‘limi qo‘shildi.')
        return redirect('studio:parts', slug=course.slug)
    items = [(p, PartForm(instance=p, prefix=f'p{p.pk}')) for p in course.parts.annotate(n=Count('topics'))]
    return render(request, 'lectures/studio/parts.html', {'course': course, 'form': form, 'items': items, 'tab': 'bolimlar',
                                                          'palette': PALETTE})


@studio_view
@require_POST
def part_save(request, course, pk):
    part = get_object_or_404(course.parts, pk=pk)
    if request.POST.get('delete'):
        part.delete()
        messages.success(request, 'Bo‘lim o‘chirildi (mavzulari saqlanib qoldi).')
    else:
        form = PartForm(request.POST, instance=part, prefix=f'p{pk}')
        if form.is_valid():
            form.save()
            messages.success(request, 'Bo‘lim saqlandi.')
    return redirect('studio:parts', slug=course.slug)


@studio_view
def course_delete(request, course):
    if request.method == 'POST':
        title = course.title
        course.delete()
        messages.success(request, f'«{title}» darsligi o‘chirildi.')
        return redirect('studio:dashboard')
    return render(request, 'lectures/studio/confirm.html', {
        'course': course, 'what': f'«{course.title}» darsligini', 'detail': 'Barcha mavzular, testlar va rasmlar ham o‘chadi.',
        'cancel': reverse('studio:course', args=[course.slug])})


@studio_view
def export(request, course):
    if request.method == 'POST':
        data, filename = build_zip(course)
        resp = HttpResponse(data, content_type='application/zip')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp
    return render(request, 'lectures/studio/export.html', {'course': course, 'tab': 'eksport'})


# ------------------------------------------------------------------ zaxira nusxa
@studio_view
def backup(request):
    if request.method == 'POST' and 'download' in request.POST:
        resp = HttpResponse(bk.make_backup(), content_type='application/zip')
        resp['Content-Disposition'] = f'attachment; filename="{bk.backup_name()}"'
        return resp
    error = ''
    if request.method == 'POST':
        f = request.FILES.get('file')
        if not f:
            error = 'Zaxira faylini tanlang.'
        elif not request.POST.get('agree'):
            error = 'Tiklash joriy darsliklarni almashtiradi — roziligingizni belgilang.'
        else:
            try:
                bk.read_manifest(f)
                bk.auto_backup()  # tiklashdan oldin joriy holat ham saqlab qo'yiladi
                info = bk.restore(f)
            except bk.BackupError as e:
                error = str(e)
            else:
                messages.success(request, f'Zaxira nusxa tiklandi ({info.get("sana", "")}): {Course.objects.count()} ta darslik.')
                return redirect('studio:dashboard')
    autos = sorted(bk.backup_dir().glob('darslik-zaxira-*.zip'), reverse=True) if bk.backup_dir().is_dir() else []
    return render(request, 'lectures/studio/backup.html', {
        'error': error, 'autos': [{'name': a.name, 'size': a.stat().st_size} for a in autos],
        'folder': bk.backup_dir()})


# ------------------------------------------------------------------ mavzu
@studio_view
def topic_edit(request, course, n):
    topic = get_topic(course, n)
    tab = request.GET.get('tab', 'asosiy')
    post = request.method == 'POST'
    form = TopicForm(request.POST if tab == 'asosiy' and post else None, instance=topic)
    extras = TopicExtrasForm(request.POST if tab == 'qoshimcha' and post else None, instance=topic)
    sec_form = SectionForm(request.POST if tab == 'reja' and post else None)
    res_form = ResourceForm(request.POST if tab == 'resurslar' and post else None,
                            request.FILES if tab == 'resurslar' and post else None,
                            initial={'kind': request.GET.get('kind', 'slides')}, fixed_topic=True)
    qa_form = QAForm(request.POST if tab == 'savoljavob' and post else None)
    if post:
        target = {'asosiy': form, 'qoshimcha': extras, 'reja': sec_form, 'resurslar': res_form, 'savoljavob': qa_form}.get(tab)
        if target is not None and target.is_valid():
            if tab == 'reja':
                order = (topic.sections.aggregate(m=Max('order'))['m'] or 0) + 1
                sec = Section.objects.create(topic=topic, order=order, title=sec_form.cleaned_data['title'])
                touch(course)
                return redirect('studio:section', slug=course.slug, n=n, sid=sec.pk)
            if tab == 'resurslar':
                r = res_form.save(commit=False)
                r.course, r.topic = course, topic
                r.save()
                messages.success(request, f'«{r.title}» yuklandi ({r.get_kind_display()}).')
            elif tab == 'savoljavob':
                order = (topic.qa.aggregate(m=Max('order'))['m'] or 0) + 1
                QuickQA.objects.create(topic=topic, order=order, **qa_form.cleaned_data)
                messages.success(request, 'Savol-javob qo‘shildi.')
            else:
                target.save()
                messages.success(request, 'Saqlandi.')
            touch(course)
            return redirect(topic_url(topic, tab))
    return render(request, 'lectures/studio/topic.html', {
        'course': course, 't': topic, 'tab': tab, 'form': form, 'extras': extras, 'sec_form': sec_form,
        'res_form': res_form, 'qa_form': qa_form, 'resources': topic.resources.all(), 'qa': topic.qa.all(),
        'sections': topic.sections.all(), 'tests': topic.tests.all(), 'scenes': SCENES,
    })


@studio_view
@require_POST
def topic_move(request, course, n, direction):
    topic = get_topic(course, n)
    other = (course.topics.filter(number__lt=n).order_by('-number') if direction == 'up'
             else course.topics.filter(number__gt=n).order_by('number')).first()
    if other:
        with transaction.atomic():
            a, b = topic.number, other.number
            topic.number = 0
            topic.save(update_fields=['number'])
            other.number = a
            other.save(update_fields=['number'])
            topic.number = b
            topic.save(update_fields=['number'])
        touch(course)
    return redirect(reverse('studio:course', args=[course.slug]) + f'#t{topic.pk}')


@studio_view
def topic_delete(request, course, n):
    topic = get_topic(course, n)
    if request.method == 'POST':
        with transaction.atomic():
            topic.delete()
            for t in course.topics.filter(number__gt=n).order_by('number'):  # raqamlar ketma-ket qolsin
                t.number -= 1
                t.save(update_fields=['number'])
        touch(course)
        messages.success(request, f'{n}-mavzu o‘chirildi.')
        return redirect('studio:course', slug=course.slug)
    return render(request, 'lectures/studio/confirm.html', {
        'course': course, 'what': f'{n}-mavzuni («{topic.title}»)', 'detail': 'Reja bo‘limlari va testlari ham o‘chadi.',
        'cancel': topic_url(topic)})


# ------------------------------------------------------------------ reja bo'limi va bloklar
def get_section(topic, sid):
    return get_object_or_404(topic.sections, pk=sid)


@studio_view
def section_edit(request, course, n, sid):
    topic = get_topic(course, n)
    sec = get_section(topic, sid)
    form = SectionForm(request.POST or None, initial={'title': sec.title})
    if request.method == 'POST' and form.is_valid():
        sec.title = form.cleaned_data['title']
        sec.save(update_fields=['title'])
        touch(course)
        messages.success(request, 'Sarlavha saqlandi.')
        return redirect('studio:section', slug=course.slug, n=n, sid=sid)
    secs = list(topic.sections.all())
    slide_no = secs.index(sec) + 1
    blocks = [{'i': i, 'b': b, 'name': ed.BLOCK_NAMES.get(b['t'], b['t']), 'summary': ed.block_summary(b)} for i, b in enumerate(sec.blocks)]
    return render(request, 'lectures/studio/section.html', {
        'course': course, 't': topic, 'sec': sec, 'form': form, 'blocks': blocks, 'types': ed.BLOCK_TYPES,
        'slide_no': slide_no,
    })


@studio_view
@require_POST
def section_action(request, course, n, sid, action):
    """Bo'limni yuqoriga/pastga surish yoki o'chirish."""
    topic = get_topic(course, n)
    sec = get_section(topic, sid)
    secs = list(topic.sections.all())
    i = secs.index(sec)
    if action == 'delete':
        secs.pop(i)
        sec.delete()
        messages.success(request, 'Reja bo‘limi o‘chirildi.')
    elif action in ('up', 'down'):
        j = i - 1 if action == 'up' else i + 1
        if 0 <= j < len(secs):
            secs[i], secs[j] = secs[j], secs[i]
    for k, s in enumerate(secs):  # tartib raqamlarini qayta yozish
        if s.order != k + 1:
            s.order = k + 1
            s.save(update_fields=['order'])
    touch(course)
    return redirect(topic_url(topic, 'reja'))


def save_upload(course, f):
    m = Media.objects.create(course=course, file=f)
    return m.file.name


@studio_view
def block_edit(request, course, n, sid, i=None):
    """Blok qo'shish (i=None) yoki tahrirlash."""
    topic = get_topic(course, n)
    sec = get_section(topic, sid)
    if i is not None and not 0 <= i < len(sec.blocks):
        raise Http404
    old = sec.blocks[i] if i is not None else {'t': request.POST.get('t') or request.GET.get('t', 'p')}
    t = old['t']
    if t not in ed.BLOCK_NAMES:
        raise Http404
    initial = {'t': t, 'caption': old.get('caption', ''), 'url': old.get('url', '')}
    initial['text'] = {
        'h': old.get('text', ''), 'p': ed.html_to_text(old.get('html', '')), 'note': ed.html_to_text(old.get('html', '')),
        'ul': ed.list_to_text(old.get('items', [])), 'table': ed.table_to_text(old.get('rows', [])),
    }.get(t, '')
    form = BlockForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        if t == 'h':
            block = {'t': 'h', 'text': d['text'].strip()}
        elif t in ('p', 'note'):
            block = {'t': t, 'html': ed.text_to_html(d['text'])}
        elif t == 'ul':
            block = {'t': 'ul', 'items': ed.text_to_list(d['text'])}
        elif t == 'table':
            block = {'t': 'table', 'rows': ed.text_to_table(d['text'])}
        else:  # image / video
            src = save_upload(course, d['file']) if d.get('file') else old.get('src', '')
            if t == 'image' and not src:
                form.add_error('file', 'Rasm faylini tanlang.')
            if t == 'video' and not src and not d.get('url'):
                form.add_error('url', 'Video fayl yuklang yoki YouTube havolasini kiriting.')
            block = {'t': t, 'src': src, 'caption': d.get('caption', ''), 'url': d.get('url', '') if t == 'video' else ''}
        if form.is_valid():
            blocks = list(sec.blocks)
            if i is None:
                pos = request.POST.get('pos')
                blocks.insert(int(pos) if pos and pos.isdigit() else len(blocks), block)
            else:
                blocks[i] = block
            sec.blocks = blocks
            sec.save(update_fields=['blocks'])
            touch(course)
            messages.success(request, f'«{ed.BLOCK_NAMES[t]}» bloki saqlandi.')
            return redirect('studio:section', slug=course.slug, n=n, sid=sid)
    return render(request, 'lectures/studio/block.html', {
        'course': course, 't': topic, 'sec': sec, 'form': form, 'btype': t, 'bname': ed.BLOCK_NAMES[t],
        'old': old, 'is_new': i is None, 'pos': request.GET.get('pos', ''),
    })


@studio_view
@require_POST
def block_action(request, course, n, sid, i, action):
    topic = get_topic(course, n)
    sec = get_section(topic, sid)
    blocks = list(sec.blocks)
    if not 0 <= i < len(blocks):
        raise Http404
    if action == 'delete':
        blocks.pop(i)
    elif action == 'up' and i > 0:
        blocks[i - 1], blocks[i] = blocks[i], blocks[i - 1]
    elif action == 'down' and i < len(blocks) - 1:
        blocks[i + 1], blocks[i] = blocks[i], blocks[i + 1]
    sec.blocks = blocks
    sec.save(update_fields=['blocks'])
    touch(course)
    return redirect(reverse('studio:section', args=[course.slug, n, sid]) + f'#b{max(0, min(i, len(blocks) - 1))}')


# ------------------------------------------------------------------ testlar
@studio_view
def test_edit(request, course, n, qid=None):
    topic = get_topic(course, n)
    q = get_object_or_404(topic.tests, pk=qid) if qid else None
    initial = {}
    if q:
        initial = {'text': q.text, 'answer': q.answer, **{k: (q.options[j] if j < len(q.options) else '') for j, k in enumerate('abcd')}}
    form = TestForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        if q is None:
            q = TestQuestion(topic=topic, order=(topic.tests.aggregate(m=Max('order'))['m'] or 0) + 1)
        q.text, q.options, q.answer = d['text'].strip(), form.options(), d['answer']
        q.save()
        touch(course)
        messages.success(request, 'Test savoli saqlandi.')
        if 'again' in request.POST:
            return redirect('studio:test_new', slug=course.slug, n=n)
        return redirect(topic_url(topic, 'test'))
    try:
        answer = int(form['answer'].value() or 0)
    except (TypeError, ValueError):
        answer = 0
    return render(request, 'lectures/studio/test.html', {
        'course': course, 't': topic, 'form': form, 'q': q, 'answer': answer,
        'opt_rows': [(L, i, form[k]) for i, (L, k) in enumerate(zip('ABCD', 'abcd'))],
    })


@studio_view
@require_POST
def test_delete(request, course, n, qid):
    topic = get_topic(course, n)
    get_object_or_404(topic.tests, pk=qid).delete()
    touch(course)
    messages.success(request, 'Test savoli o‘chirildi.')
    return redirect(topic_url(topic, 'test'))


# ------------------------------------------------------------------ resurslar (taqdimot, video, material)
@studio_view
@require_POST
def resource_delete(request, course, pk):
    r = get_object_or_404(course.resources, pk=pk)
    back = topic_url(r.topic, 'resurslar') if r.topic_id else reverse('studio:materials', args=[course.slug])
    if r.file:
        r.file.delete(save=False)
    r.delete()
    touch(course)
    messages.success(request, 'O‘chirildi.')
    return redirect(back)


@studio_view
def course_materials(request, course):
    """Darslik bo'yicha umumiy materiallar va ta'lim texnologiyasi hujjatlari (mavzuga bog'lanmagan)."""
    form = ResourceForm(request.POST or None, request.FILES or None, initial={'kind': request.GET.get('kind', 'tech')},
                        course=course)
    if request.method == 'POST' and form.is_valid():
        r = form.save(commit=False)
        r.course = course
        r.save()
        touch(course)
        messages.success(request, f'«{r.title}» yuklandi.')
        return redirect('studio:materials', slug=course.slug)
    return render(request, 'lectures/studio/materials.html', {
        'course': course, 'form': form, 'tab': 'materiallar',
        'items': course.resources.filter(topic__isnull=True),
        'topic_items': course.resources.filter(topic__isnull=False).select_related('topic'),
    })


# ------------------------------------------------------------------ tezkor savol-javob
@studio_view
def qa_edit(request, course, n, pk):
    topic = get_topic(course, n)
    item = get_object_or_404(topic.qa, pk=pk)
    form = QAForm(request.POST or None, initial={'question': item.question, 'answer': item.answer})
    if request.method == 'POST' and form.is_valid():
        item.question, item.answer = form.cleaned_data['question'], form.cleaned_data['answer']
        item.save()
        touch(course)
        messages.success(request, 'Saqlandi.')
        return redirect(topic_url(topic, 'savoljavob'))
    return render(request, 'lectures/studio/simple_form.html', {
        'course': course, 't': topic, 'form': form, 'heading': 'Savol-javobni tahrirlash',
        'cancel': topic_url(topic, 'savoljavob')})


@studio_view
@require_POST
def qa_action(request, course, n, action, pk=None):
    topic = get_topic(course, n)
    if action == 'delete':
        get_object_or_404(topic.qa, pk=pk).delete()
        messages.success(request, 'O‘chirildi.')
    elif action == 'from-text':
        made = qa_from_content(course, topics=[topic])
        messages.success(request, f'Ma’ruza matnidan {made} ta kartochka yaratildi.' if made
                         else 'Bu mavzuda savol-javob allaqachon bor yoki matndan savol topilmadi.')
    touch(course)
    return redirect(topic_url(topic, 'savoljavob'))


@studio_view
@require_POST
def topic_slides(request, course, n):
    """Mavzu matnidan taqdimot (PDF + PowerPoint) tayyorlash — eski avtomatik nusxa almashtiriladi."""
    from .taqdimot import FontMissing, make_for_topic
    topic = get_topic(course, n)
    try:
        made = make_for_topic(topic)
    except FontMissing as e:
        messages.error(request, f'Taqdimot tayyorlanmadi: {e}')
    else:
        messages.success(request, f'Taqdimot tayyor: {made} ta slayd (PDF va PowerPoint).')
    touch(course)
    return redirect(topic_url(topic, 'resurslar'))


# ------------------------------------------------------------------ glossariy
@studio_view
def glossary(request, course):
    form = TermForm(request.POST or None, course=course)
    if request.method == 'POST' and 'auto' in request.POST:
        made = auto_glossary(course)
        messages.success(request, f'Matndan {made} ta yangi atama topildi.' if made else 'Yangi atama topilmadi.')
        return redirect('studio:glossary', slug=course.slug)
    if request.method == 'POST' and form.is_valid():
        g = form.save(commit=False)
        g.course = course
        g.save()
        touch(course)
        messages.success(request, f'«{g.term}» qo‘shildi.')
        return redirect('studio:glossary', slug=course.slug)
    q = request.GET.get('q', '').strip().lower()
    terms = [g for g in course.glossary.select_related('topic') if not q or q in g.term.lower()]
    return render(request, 'lectures/studio/glossary.html', {
        'course': course, 'form': form, 'terms': terms, 'q': request.GET.get('q', ''), 'tab': 'glossariy'})


@studio_view
def term_edit(request, course, pk):
    g = get_object_or_404(course.glossary, pk=pk)
    if request.method == 'POST' and request.POST.get('delete'):
        g.delete()
        messages.success(request, 'Atama o‘chirildi.')
        return redirect('studio:glossary', slug=course.slug)
    form = TermForm(request.POST or None, instance=g, course=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        touch(course)
        messages.success(request, 'Saqlandi.')
        return redirect('studio:glossary', slug=course.slug)
    return render(request, 'lectures/studio/simple_form.html', {
        'course': course, 'form': form, 'heading': f'«{g.term}» atamasi', 'cancel': reverse('studio:glossary', args=[course.slug]),
        'can_delete': True, 'tab': 'glossariy'})


@studio_view
def resource_edit(request, course, pk):
    """Resursni tahrirlash: nomi, turi, mavzusi, faylini almashtirish yoki o'chirish."""
    r = get_object_or_404(course.resources.select_related('topic'), pk=pk)
    back = request.GET.get('next') or request.POST.get('next') or (
        topic_url(r.topic, 'resurslar') if r.topic_id else reverse('studio:materials', args=[course.slug]))
    if not back.startswith('/'):
        back = '/'
    old_file = r.file.name if r.file else ''
    if request.method == 'POST' and request.POST.get('delete'):
        if r.file:
            r.file.delete(save=False)
        r.delete()
        touch(course)
        messages.success(request, 'O‘chirildi.')
        return redirect(back)
    form = ResourceForm(request.POST or None, request.FILES or None, instance=r, course=course)
    if request.method == 'POST' and form.is_valid():
        r = form.save()
        if old_file and (not r.file or r.file.name != old_file):  # eski fayl diskdan ham o'chadi
            r.file.storage.delete(old_file)
        touch(course)
        messages.success(request, f'«{r.title}» saqlandi.')
        return redirect(back)
    return render(request, 'lectures/studio/resource.html', {'course': course, 'r': r, 'form': form, 'back': back})


@studio_view
@require_POST
def video_add(request, course):
    """Ko'rish sahifasidagi tezkor «Video qo'shish» formasi."""
    form = ResourceForm(request.POST, request.FILES, course=course, kinds=['video'])
    back = reverse('lectures:videos', args=[course.slug])
    if form.is_valid():
        r = form.save(commit=False)
        r.course = course
        r.save()
        touch(course)
        messages.success(request, f'«{r.title}» video qo‘shildi.')
        return redirect(f'{back}#res{r.pk}')
    for field, errs in form.errors.items():
        for e in errs:
            messages.error(request, e)
    return redirect(f'{back}#qoshish')
