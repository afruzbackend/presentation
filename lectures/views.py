"""Darslikni ko'rish (o'quvchi/sinf uchun). Tahrirlash — studio.py da."""
import random

from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .content import grade_for, short_content, slide_count, slide_list, split_item
from .models import Course, QuickQA, Section, TestQuestion, Topic


def slide_url(course, n, s):
    return reverse('lectures:slide', args=[course.slug, n, s])


def check_answers(questions, data):
    """POST ma'lumotidan javoblarni tekshirish (server tomonda)."""
    rows, score = [], 0
    for q in questions:
        raw = data.get(f'q{q.pk}')
        chosen = int(raw) if raw is not None and raw.isdigit() else None
        ok = chosen == q.answer
        score += ok
        rows.append({'q': q, 'chosen': chosen, 'ok': ok})
    return rows, grade_for(score, len(questions))


def course_page(request, slug, template, ctx=None):
    """Darslik sahifalari uchun umumiy kontekst."""
    course = ctx.pop('_course') if ctx and '_course' in ctx else get_object_or_404(Course, slug=slug)
    data = {
        'course': course,
        'parts': list(course.parts.all()),
        'all_topics': list(course.topics.only('number', 'title', 'kind', 'part_id', 'course_id').select_related('part')),
    }
    data.update(ctx or {})
    return render(request, template, data)


# ------------------------------------------------------------------ kutubxona
def library(request):
    courses = Course.objects.annotate(n_topics=Count('topics', distinct=True))
    return render(request, 'lectures/library.html', {'courses': courses})


# ------------------------------------------------------------------ darslik sahifalari
def course_home(request, slug):
    course = get_object_or_404(Course, slug=slug)
    topics = course.topics.all()
    if not topics.exists():
        return course_page(request, slug, 'lectures/course_empty.html', {'_course': course})
    first = topics.first()
    tests = TestQuestion.objects.filter(topic__course=course).count()
    last = request.session.get(f'last_{course.pk}')
    last_topic = topics.filter(number=last[0]).first() if last else None
    if last_topic:
        start = (slide_url(course, *last), 'Davom ettirish', f'{last[0]}-mavzu: {last_topic.title}')
    else:
        start = (slide_url(course, first.number, 0), 'Darsni boshlash', f'{first.number}-mavzudan boshlash')
    res = dict(course.resources.values_list('kind').annotate(n=Count('id')))

    def r(name):
        return reverse(f'lectures:{name}', args=[slug])

    n_qa = QuickQA.objects.filter(topic__course=course).count()
    tiles = [
        (r('lecture'), 'book', 'Ma’ruza matni', f'{topics.count()} ta mavzuning to‘liq matni', '#0E7C7B'),
        (r('slides'), 'monitor', 'Taqdimotlar', f"{res.get('slides', 0)} ta taqdimot", '#C2562D'),
        (r('videos'), 'video', 'Video darsliklar', f"{res.get('video', 0)} ta video", '#9E2A3A'),
        (r('materials'), 'file', 'Materiallar', f"{res.get('material', 0)} ta fayl va havola", '#24508F'),
        (r('tech'), 'layers', 'Fanning ta’lim texnologiyasi', 'Texnologik model va xaritalar', '#3F7D4E'),
        (r('glossary'), 'abc', 'Glossariy', f'{course.glossary.count()} ta atama', '#B07D1E'),
        (r('qa'), 'question', 'Tezkor savol-javob', f'{n_qa} ta kartochka', '#0E7C7B'),
        (r('contents'), 'grid', 'Mundarija', f'{topics.count()} ta mavzu', '#C2562D'),
        (r('plan'), 'list', 'O‘quv-tematik reja', 'Mavzular, turlari va soatlar', '#24508F'),
    ]
    if tests:
        tiles.append((r('final'), 'trophy', 'Yakuniy test', f'{tests} ta savol bazasidan {min(course.final_size, tests)} ta', '#9E2A3A'))
    if course.self_study_plan or topics.exclude(self_study=[]).exists():
        tiles.append((r('self_study'), 'pen', 'Mustaqil ta’lim', 'Topshiriqlar va manbalar', '#3F7D4E'))
    tiles.append((r('author'), 'user', 'Muallif haqida', course.author, '#B07D1E'))
    stats = [(topics.count(), 'mavzu'), (topics.filter(kind='Nazariy').count(), 'nazariy'),
             (topics.filter(kind='Amaliy').count(), 'amaliy')]
    if tests:
        stats.append((tests, 'test savoli'))
    if course.hours_total:
        stats.append((course.hours_total, 'akademik soat'))
    ring = ' · '.join(x for x in [course.title.upper(), course.module.split('.')[0] if course.module else '',
                                   f'{topics.count()} MAVZU', course.college.upper()] if x)
    return course_page(request, slug, 'lectures/home.html', {
        '_course': course, 'tiles': tiles, 'start': start, 'stats': stats, 'ring_text': (ring + ' · ')[:96],
    })


def contents(request, slug):
    course = get_object_or_404(Course, slug=slug)
    kind = request.GET.get('f', 'all')
    q = request.GET.get('q', '').strip()
    topics = course.topics.select_related('part').prefetch_related(
        Prefetch('sections', queryset=Section.objects.only('topic_id', 'order', 'title')))
    if kind in ('Nazariy', 'Amaliy'):
        topics = topics.filter(kind=kind)
    if q:
        cond = Q(title__icontains=q) | Q(sections__title__icontains=q)
        if q.isdigit():
            cond |= Q(number=int(q))
        topics = topics.filter(cond).distinct()
    topics = list(topics)
    groups = [{'part': p, 'topics': [t for t in topics if t.part_id == p.pk]} for p in course.parts.all()]
    loose = [t for t in topics if not t.part_id]
    if loose:
        groups.append({'part': None, 'topics': loose})
    return course_page(request, slug, 'lectures/contents.html', {
        '_course': course, 'groups': [g for g in groups if g['topics']], 'kind': kind, 'q': q, 'found': len(topics),
    })


def topic_start(request, slug, n):
    return redirect('lectures:slide', slug=slug, n=n, s=0)


def slide(request, slug, n, s):
    course = get_object_or_404(Course, slug=slug)
    topic = get_object_or_404(course.topics.select_related('part').prefetch_related('sections', 'tests'), number=n)
    sections = list(topic.sections.all())
    slides = slide_list(topic, sections)
    if not 0 <= s < len(slides):
        raise Http404
    sl = slides[s]
    prev_topic = course.topics.filter(number__lt=n).order_by('-number').first()
    next_topic = course.topics.filter(number__gt=n).order_by('number').first()
    if s > 0:
        prev = slide_url(course, n, s - 1)
    else:
        prev = slide_url(course, prev_topic.number, slide_count(prev_topic) - 1) if prev_topic else ''
    nxt = slide_url(course, n, s + 1) if s < len(slides) - 1 else (slide_url(course, next_topic.number, 0) if next_topic else '')
    numbers = list(course.topics.values_list('number', flat=True))
    pos = numbers.index(n)
    request.session[f'last_{course.pk}'] = [n, s]

    ctx = {
        '_course': course, 't': topic, 's': s, 'slide': sl, 'slides': slides, 'sections': sections,
        'prev': prev, 'next': nxt, 'next_topic': next_topic,
        'near': numbers[max(0, pos - 3):pos + 4],
        'progress': round((pos + (s + 1) / len(slides)) / len(numbers) * 100, 2),
    }
    if sl['kind'] == 'sec':
        sec = sl['sec']
        ctx.update(sec=sec, sc=short_content(sec),
                   sec_table=next((b['rows'] for b in sec.blocks if b['t'] == 'table'), None))
    elif sl['kind'] == 'test':
        questions = list(topic.tests.all())
        if request.method == 'POST':
            ctx['rows'], ctx['res'] = check_answers(questions, request.POST)
        else:
            ctx['rows'] = [{'q': q, 'chosen': None, 'ok': None} for q in questions]
    elif sl['kind'] in ('slides', 'video'):
        ctx['res_list'] = list(topic.resources.filter(kind=sl['kind']))
    elif sl['kind'] == 'qa':
        ctx['qa'] = list(topic.qa.all())
    elif sl['kind'] == 'self':
        ctx['materials'] = list(topic.resources.filter(kind__in=['material', 'tech']))
        tasks = []
        for i, m in enumerate(topic.self_study):
            k, v = split_item(m)
            tasks.append({'k': k or 'Topshiriq', 'v': v, 'cap': i == len(topic.self_study) - 1 and len(topic.self_study) > 2})
        ctx['tasks'] = tasks
    return course_page(request, slug, 'lectures/slide.html', ctx)


def plan(request, slug):
    course = get_object_or_404(Course, slug=slug)
    topics = list(course.topics.select_related('part'))
    theory = course.hours_theory or sum(t.hours for t in topics if t.kind == 'Nazariy')
    practice = course.hours_practice or sum(t.hours for t in topics if t.kind == 'Amaliy')
    selfh = course.hours_self
    total = (theory + practice + selfh) or 1
    return course_page(request, slug, 'lectures/plan.html', {
        '_course': course, 'rows': topics, 'theory': theory, 'practice': practice, 'self_hours': selfh,
        'total_hours': theory + practice + selfh, 'class_hours': sum(t.hours for t in topics),
        'a': round(theory / total * 100, 2), 'b': round((theory + practice) / total * 100, 2),
    })


def self_study(request, slug):
    course = get_object_or_404(Course, slug=slug)
    colors = {t.number: t.color for t in course.topics.select_related('part', 'course')}
    items = []
    for r in course.self_study_plan:
        if not (r and str(r[0]).isdigit()):
            continue
        a, _, b = str(r[2]).replace('–', '-').partition('-')
        try:
            a, b = int(a), int(b or a)
        except ValueError:
            continue
        items.append({'n': int(r[0]), 'title': r[1], 'hours': r[3], 'topics': range(a, b + 1), 'color': colors.get(a, course.color)})
    if not items:  # rejasi yo'q darslik: mavzulardagi topshiriqlardan
        for t in course.topics.exclude(self_study=[]).select_related('part', 'course'):
            items.append({'n': t.number, 'title': t.title, 'hours': '', 'topics': [t.number], 'color': t.color})
    return course_page(request, slug, 'lectures/self_study.html', {'_course': course, 'items': items})


def final_test(request, slug):
    course = get_object_or_404(Course, slug=slug)
    bank = TestQuestion.objects.filter(topic__course=course)
    key = f'final_{course.pk}'
    ids = request.session.get(key)
    if request.GET.get('new') or not ids:
        all_ids = list(bank.values_list('id', flat=True))
        ids = random.sample(all_ids, min(course.final_size, len(all_ids)))
        request.session[key] = ids
        if request.GET.get('new'):
            return redirect('lectures:final', slug=slug)
    by_id = bank.select_related('topic').in_bulk(ids)
    questions = [by_id[i] for i in ids if i in by_id]
    ctx = {'_course': course, 'total_bank': bank.count(), 'pick': course.final_size}
    if request.META.get('HTTP_X_DARSLIK_EXPORT') == '1':
        # eksportda butun savollar bazasi beriladi, 20 tasini brauzer o'zi tanlaydi
        questions = list(bank.select_related('topic'))
    if request.method == 'POST':
        rows, res = check_answers(questions, request.POST)
        ctx.update(rows=rows, res=res, review=sorted({r['q'].topic.number for r in rows if not r['ok']}))
    else:
        ctx['rows'] = [{'q': q, 'chosen': None, 'ok': None} for q in questions]
    return course_page(request, slug, 'lectures/final.html', ctx)


def author(request, slug):
    return course_page(request, slug, 'lectures/author.html')


def toggle_theme(request):
    nxt = request.GET.get('next', '/')
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = '/'
    resp = redirect(nxt)
    resp.set_cookie('theme', 'light' if request.COOKIES.get('theme') == 'dark' else 'dark', max_age=365 * 24 * 3600)
    return resp


# ------------------------------------------------------------------ darslik bo'limlari
def lecture_index(request, slug):
    course = get_object_or_404(Course, slug=slug)
    topics = course.topics.select_related('part').prefetch_related(
        Prefetch('sections', queryset=Section.objects.only('topic_id', 'order', 'title')))
    return course_page(request, slug, 'lectures/lecture_index.html', {'_course': course, 'topics': topics})


def lecture_text(request, slug, n):
    """Mavzuning to'liq ma'ruza matni (o'qish va chop etish uchun)."""
    course = get_object_or_404(Course, slug=slug)
    topic = get_object_or_404(course.topics.select_related('part').prefetch_related('sections'), number=n)
    prev_t = course.topics.filter(number__lt=n).order_by('-number').first()
    next_t = course.topics.filter(number__gt=n).order_by('number').first()
    return course_page(request, slug, 'lectures/lecture_text.html', {
        '_course': course, 't': topic, 'sections': topic.sections.all(), 'prev_t': prev_t, 'next_t': next_t})


RES_PAGES = {
    'slides': ('Taqdimotlar', 'monitor', 'Har bir mavzu bo‘yicha taqdimot materiallari (PowerPoint, PDF).'),
    'video': ('Video darsliklar', 'video', 'Mavzular bo‘yicha video darslar.'),
    'material': ('Materiallar', 'file', 'Qo‘shimcha o‘quv materiallari: hujjatlar, rasmlar, havolalar.'),
}


def resources_page(request, slug, kind):
    course = get_object_or_404(Course, slug=slug)
    items = list(course.resources.filter(kind=kind).select_related('topic'))
    title, icon, lead = RES_PAGES[kind]
    by_topic = {}
    for x in items:
        if x.topic_id:
            by_topic.setdefault(x.topic, []).append(x)
    return course_page(request, slug, 'lectures/resources.html', {
        '_course': course, 'kind': kind, 'page_title': title, 'page_icon': icon, 'lead': lead,
        'general': [x for x in items if not x.topic_id],
        'by_topic': sorted(by_topic.items(), key=lambda kv: kv[0].number), 'count': len(items)})


TECH_COLS = [('Mashg‘ulot shakli', 'Shakli'), ('O‘qitish metodlari', 'Metodlar'),
             ('O‘qitish vositalari', 'Vositalar'), ('Qaytar aloqa', 'Nazorat')]


def technologies(request, slug):
    """Fanning ta'lim texnologiyasi: umumiy hujjatlar + har bir mavzuning texnologik modeli."""
    course = get_object_or_404(Course, slug=slug)
    topics = list(course.topics.select_related('part'))
    rows = [{'t': t, 'vals': [next((r[1] for r in t.lesson_model if len(r) > 1 and r[0].startswith(key)), '')
                              for key, _ in TECH_COLS]} for t in topics]
    return course_page(request, slug, 'lectures/tech.html', {
        '_course': course, 'rows': rows, 'cols': [c for _, c in TECH_COLS],
        'docs': course.resources.filter(kind='tech').select_related('topic'),
        'has_models': any(t.lesson_model for t in topics)})


def glossary(request, slug):
    course = get_object_or_404(Course, slug=slug)
    terms = list(course.glossary.select_related('topic'))
    harf = request.GET.get('harf', '')
    q = request.GET.get('q', '').strip().lower()
    shown = [g for g in terms if (not harf or g.letter == harf)
             and (not q or q in g.term.lower() or q in g.definition.lower())]
    return course_page(request, slug, 'lectures/glossary.html', {
        '_course': course, 'terms': shown, 'letters': sorted({g.letter for g in terms}), 'harf': harf,
        'q': request.GET.get('q', ''), 'total': len(terms)})


def qa_page(request, slug):
    course = get_object_or_404(Course, slug=slug)
    topics = [t for t in course.topics.select_related('part').prefetch_related('qa') if t.qa.all()]
    return course_page(request, slug, 'lectures/qa.html', {
        '_course': course, 'qa_topics': topics, 'total': sum(len(t.qa.all()) for t in topics)})
