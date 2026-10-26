"""Avtomatik testlar:  python manage.py test lectures"""
import io
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .content import slide_list
from .docx_parser import parse
from .editing import html_to_text, text_to_html, text_to_table
from .importer import seed_kompyuter_tizimlari
from .models import Course, QuickQA, Section, TestQuestion, Topic

TMP_MEDIA = tempfile.mkdtemp()

# 1x1 PNG
PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
       b'\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')


def make_docx(paragraphs):
    """Kichik docx: [(uslub, matn)] — uslub 'Heading1', 'Heading2' yoki ''."""
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    body = ''.join(
        f'<w:p><w:pPr><w:pStyle w:val="{st}"/></w:pPr><w:r><w:t>{tx}</w:t></w:r></w:p>' if st
        else f'<w:p><w:r><w:t>{tx}</w:t></w:r></w:p>' for st, tx in paragraphs)
    styles = (f'<w:styles xmlns:w="{W}"><w:style w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
              f'<w:style w:styleId="Heading2"><w:name w:val="heading 2"/></w:style></w:styles>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('word/document.xml', f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
        z.writestr('word/styles.xml', styles)
    buf.seek(0)
    return buf


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class BaseCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course, _ = seed_kompyuter_tizimlari()
        cls.user = User.objects.create_superuser('ustoz', password='sinov-parol')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def login(self):
        self.client.force_login(self.user)


class ParserTests(BaseCase):
    def test_majmua(self):
        d = parse(settings.LECTURE_DOCX)
        self.assertEqual(d['format'], 'majmua')
        self.assertEqual(len(d['topics']), 35)
        self.assertEqual(d['course']['hours_theory'], 28)
        self.assertEqual(d['problems'], [])

    def test_generic_headings(self):
        d = parse(make_docx([('', 'Fizika'), ('Heading1', 'Mexanika'), ('Heading2', 'Harakat'), ('', 'Tezlik — yo‘l/vaqt.'),
                             ('Heading2', 'Kuch'), ('', 'Nyuton qonunlari.'), ('Heading1', 'Optika'), ('', 'Yorug‘lik.')]))
        self.assertEqual(d['format'], 'umumiy')
        self.assertEqual([t['title'] for t in d['topics']], ['Mexanika', 'Optika'])
        self.assertEqual([s['title'] for s in d['topics'][0]['sections']], ['Harakat', 'Kuch'])

    def test_editing_roundtrip(self):
        self.assertEqual(text_to_html('**A** < b'), '<b>A</b> &lt; b')
        self.assertEqual(html_to_text('<b>A</b> &lt; b'), '**A** < b')
        self.assertEqual(text_to_table('a | b\nc'), [['a', 'b'], ['c', '']])


class ViewerTests(BaseCase):
    def test_pages(self):
        s = '/d/kompyuter-tizimlari'
        for url in ['/', f'{s}/', f'{s}/mavzular/', f'{s}/reja/', f'{s}/mustaqil/', f'{s}/test/', f'{s}/muallif/',
                    f'{s}/mavzu/1/0/', f'{s}/mavzu/1/2/', f'{s}/mavzu/1/4/', f'{s}/mavzu/35/5/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get(f'{s}/mavzu/1/9/').status_code, 404)

    def test_quiz_is_checked_on_server(self):
        topic = self.course.topics.get(number=3)
        data = {f'q{q.pk}': str(q.answer) for q in topic.tests.all()}
        r = self.client.post('/d/kompyuter-tizimlari/mavzu/3/5/', data)
        self.assertContains(r, '100%')

    def test_api(self):
        r = self.client.get('/api/courses/kompyuter-tizimlari/')
        self.assertEqual(r.json()['title'], 'Kompyuter tizimlari')
        t = self.course.topics.get(number=3)
        r = self.client.get(f'/api/topics/{t.pk}/')
        self.assertNotIn('answer', r.json()['tests'][0])


class StudioTests(BaseCase):
    def test_login_required(self):
        self.assertEqual(self.client.get('/studio/').status_code, 302)

    def test_first_run_setup(self):
        User.objects.all().delete()
        r = self.client.post('/studio/sozlash/', {'name': 'Ustoz', 'username': 'u1', 'password': 'abcd', 'password2': 'abcd'})
        self.assertRedirects(r, '/studio/')
        self.assertTrue(User.objects.get(username='u1').is_superuser)

    def test_create_course_from_docx(self):
        self.login()
        f = SimpleUploadedFile('fizika.docx', make_docx([('Heading1', 'Mexanika'), ('', 'Matn')]).read())
        r = self.client.post('/studio/yangi/', {'import': '1', 'imp-file': f, 'imp-author': 'Ali Valiyev', 'imp-title': 'Fizika'})
        c = Course.objects.get(title='Fizika')
        self.assertRedirects(r, f'/studio/d/{c.slug}/')
        self.assertEqual(c.topics.count(), 1)

    def test_bad_docx(self):
        self.login()
        f = SimpleUploadedFile('x.docx', b'bu docx emas')
        r = self.client.post('/studio/yangi/', {'import': '1', 'imp-file': f, 'imp-author': 'A'})
        self.assertContains(r, 'Faylni o‘qib bo‘lmadi')

    def test_full_editing_flow(self):
        self.login()
        r = self.client.post('/studio/yangi/', {'new-title': 'Biologiya asoslari', 'new-author': 'B. Karimova'})
        c = Course.objects.get(title='Biologiya asoslari')
        base = f'/studio/d/{c.slug}'
        # mavzular
        self.client.post(f'{base}/', {'title': 'Hujayra', 'kind': 'Nazariy'})
        self.client.post(f'{base}/', {'title': 'Genetika', 'kind': 'Amaliy'})
        self.assertEqual(list(c.topics.values_list('title', flat=True)), ['Hujayra', 'Genetika'])
        self.client.post(f'{base}/mavzu/2/surish/up/')
        self.assertEqual(list(c.topics.values_list('title', flat=True)), ['Genetika', 'Hujayra'])
        # bloklar
        sec = Section.objects.get(topic__course=c, topic__title='Hujayra')
        b = f'{base}/mavzu/2/reja/{sec.pk}/blok/'
        self.client.post(b + 'yangi/', {'t': 'p', 'text': '**Hujayra** — tirik organizm birligi.'})
        self.client.post(b + 'yangi/', {'t': 'ul', 'text': 'Yadro: irsiy axborot\nMembrana: himoya'})
        self.client.post(b + 'yangi/', {'t': 'table', 'text': 'Qism | Vazifa\nYadro | Boshqaruv'})
        self.client.post(b + 'yangi/', {'t': 'image', 'caption': 'Hujayra', 'file': SimpleUploadedFile('h.png', PNG)})
        self.client.post(b + 'yangi/', {'t': 'image', 'caption': 'fayl yo‘q'})  # rad etiladi
        sec.refresh_from_db()
        self.assertEqual([x['t'] for x in sec.blocks], ['p', 'ul', 'table', 'image'])
        self.assertEqual(sec.blocks[0]['html'], '<b>Hujayra</b> — tirik organizm birligi.')
        self.client.post(b + '3/up/')
        sec.refresh_from_db()
        self.assertEqual(sec.blocks[2]['t'], 'image')
        # test
        self.client.post(f'{base}/mavzu/2/test/yangi/', {'text': 'Yadro vazifasi?', 'a': 'Boshqaruv', 'b': 'Himoya', 'answer': '0'})
        self.assertEqual(TestQuestion.objects.filter(topic__course=c).count(), 1)
        # ko'rish sahifasi: kirish, reja, test
        for s in range(3):
            self.assertEqual(self.client.get(f'/d/{c.slug}/mavzu/2/{s}/').status_code, 200)
        # o'chirish: raqamlar ketma-ket qoladi
        self.client.post(f'{base}/mavzu/1/ochirish/')
        self.assertEqual(list(c.topics.values_list('number', flat=True)), [1])

    def test_export_zip(self):
        self.login()
        r = self.client.post('/studio/d/kompyuter-tizimlari/eksport/')
        self.assertEqual(r['Content-Type'], 'application/zip')
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = set(z.namelist())
        root = 'kompyuter-tizimlari/'
        for n in ['index.html', 'mavzular.html', 'test.html', 'mavzu-1-0.html', 'mavzu-35-6.html', 'autorun.inf', 'Ochish.bat', 'server.ps1',
                  'maruza.html', 'maruza-7.html', 'glossariy.html', 'savol-javob.html', 'texnologiyalar.html', 'taqdimotlar.html',
                  'static/lectures/css/style.css', 'static/lectures/js/offline.js']:
            self.assertIn(root + n, names)
        self.assertTrue(any(n.startswith(root + 'media/authors/') for n in names))
        html = z.read(root + 'mavzu-1-1.html').decode()
        self.assertIn('href="mavzu-1-2.html"', html)
        self.assertNotIn('href="/', html)  # hamma havola nisbiy
        self.assertNotIn('studio', html)
        quiz = z.read(root + 'mavzu-1-5.html').decode()
        self.assertIn('data-offline', quiz)
        self.assertNotIn('data-a=', quiz)  # to'g'ri javob ochiq yozilmaydi
        self.assertIn('data-h=', quiz)

    def test_static_site_for_netlify(self):
        from .export import write_site
        out = Path(TMP_MEDIA) / 'sayt'
        write_site(self.course, out)
        self.assertTrue((out / 'index.html').exists())
        self.assertTrue((out / 'static/lectures/js/offline.js').exists())
        self.assertNotIn('Ochish.bat', [f.name for f in out.iterdir()])  # faqat ZIP uchun

    def test_export_video_plays_inside(self):
        self.login()
        self.course.topics.get(number=2).resources.create(course=self.course, kind='video', title='Dars', url='https://youtu.be/dQw4w9WgXcQ')
        z = zipfile.ZipFile(io.BytesIO(self.client.post('/studio/d/kompyuter-tizimlari/eksport/').content))
        html = z.read('kompyuter-tizimlari/video.html').decode()
        self.assertIn('srcdoc', html)  # oflayn nusxada ham video ichida
        self.assertNotIn('href="https://www.youtube.com/watch', html)
        self.assertNotIn('allow-popups', html)


class BackupTests(BaseCase):
    def test_download_and_restore(self):
        self.login()
        r = self.client.post('/studio/zaxira/', {'download': '1'})
        self.assertEqual(r['Content-Type'], 'application/zip')
        data = r.content
        n_topics, n_qa = Topic.objects.count(), QuickQA.objects.count()
        # o'zgartiramiz, so'ng zaxiradan tiklaymiz
        self.course.topics.filter(number__gt=30).delete()
        Course.objects.create(title='Ortiqcha', slug='ortiqcha', author='X')
        f = SimpleUploadedFile('z.zip', data, content_type='application/zip')
        r = self.client.post('/studio/zaxira/', {'file': f})  # roziligisiz — tiklanmaydi
        self.assertContains(r, 'roziligingizni')
        f = SimpleUploadedFile('z.zip', data, content_type='application/zip')
        with override_settings(BASE_DIR=Path(TMP_MEDIA)):
            r = self.client.post('/studio/zaxira/', {'file': f, 'agree': '1'})
        self.assertRedirects(r, '/studio/')
        self.assertEqual((Topic.objects.count(), QuickQA.objects.count()), (n_topics, n_qa))
        self.assertFalse(Course.objects.filter(slug='ortiqcha').exists())
        self.assertTrue(User.objects.filter(username='ustoz').exists())  # login saqlanadi

    def test_rejects_foreign_zip(self):
        self.login()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('../yomon.txt', 'x')
        f = SimpleUploadedFile('x.zip', buf.getvalue())
        r = self.client.post('/studio/zaxira/', {'file': f, 'agree': '1'})
        self.assertContains(r, 'zaxira nusxasi emas')
        self.assertEqual(Course.objects.count(), 1)


class SectionsTests(BaseCase):
    """Ma'ruza matni, taqdimot, video, materiallar, texnologiyalar, glossariy, savol-javob."""

    def test_seed_fills_glossary_and_qa(self):
        self.assertGreater(self.course.glossary.count(), 100)
        qa = QuickQA.objects.filter(topic__course=self.course)
        self.assertGreater(qa.count(), 150)
        self.assertEqual(qa.values('topic').distinct().count(), 35)  # har mavzuda bor
        self.assertTrue(self.course.cover_image)

    def test_qa_is_not_a_copy_of_tests(self):
        tests = {t.lower() for t in TestQuestion.objects.filter(topic__course=self.course).values_list('text', flat=True)}
        for q in QuickQA.objects.filter(topic__course=self.course):
            self.assertNotIn(q.question.lower(), tests)
            self.assertTrue(q.answer[:1].isalpha(), q.answer)

    def test_pages(self):
        s = '/d/kompyuter-tizimlari'
        for url in [f'{s}/maruza/', f'{s}/maruza/7/', f'{s}/taqdimotlar/', f'{s}/video/', f'{s}/materiallar/',
                    f'{s}/texnologiyalar/', f'{s}/glossariy/', f'{s}/glossariy/?harf=K', f'{s}/savol-javob/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        r = self.client.get(f'{s}/mavzu/3/4/')
        self.assertContains(r, 'qa-card')  # savol-javob slaydi
        self.assertContains(self.client.get(f'{s}/mavzu/3/0/'), 'Texnologiyalar')

    def test_upload_resources_and_slides(self):
        self.login()
        base = '/studio/d/kompyuter-tizimlari/mavzu/2/?tab=resurslar'
        pdf = SimpleUploadedFile('t.pdf', b'%PDF-1.4 test')
        self.client.post(base, {'kind': 'slides', 'title': 'Taqdimot', 'file': pdf})
        self.client.post(base, {'kind': 'video', 'title': 'Video dars', 'url': 'https://youtu.be/dQw4w9WgXcQ'})
        bad = self.client.post(base, {'kind': 'video', 'title': 'Xato', 'file': SimpleUploadedFile('a.exe', b'x')})
        self.assertEqual(bad.status_code, 200)  # rad etildi, forma qaytdi
        topic = self.course.topics.get(number=2)
        self.assertEqual(sorted(topic.resources.values_list('kind', flat=True)), ['slides', 'video'])
        names = [x['name'] for x in slide_list(topic, list(topic.sections.all()))]
        self.assertIn('Taqdimot', names)
        self.assertIn('Video dars', names)
        r = self.client.get('/d/kompyuter-tizimlari/taqdimotlar/')
        self.assertContains(r, '<iframe')
        # eksportga fayl ham tushadi
        z = zipfile.ZipFile(io.BytesIO(self.client.post('/studio/d/kompyuter-tizimlari/eksport/').content))
        self.assertTrue(any(n.endswith('.pdf') for n in z.namelist()))
        # o'chirish
        res = topic.resources.get(kind='slides')
        self.client.post(f'/studio/d/kompyuter-tizimlari/resurs/{res.pk}/ochirish/')
        self.assertFalse(topic.resources.filter(kind='slides').exists())

    def test_qa_and_glossary_editing(self):
        self.login()
        t = '/studio/d/kompyuter-tizimlari/mavzu/1/'
        self.client.post(t + '?tab=savoljavob', {'question': 'Ergonomika nima?', 'answer': 'Ish joyini moslashtirish.'})
        topic = self.course.topics.get(number=1)
        self.assertTrue(topic.qa.filter(question='Ergonomika nima?').exists())
        g = '/studio/d/kompyuter-tizimlari/glossariy/'
        self.client.post(g, {'term': 'Kiberxavfsizlik', 'definition': 'Tizimlarni himoyalash.'})
        self.assertTrue(self.course.glossary.filter(term='Kiberxavfsizlik').exists())
        self.client.post(g, {'auto': '1'})  # takror ishga tushirish dublikat yaratmaydi
        self.assertEqual(self.course.glossary.filter(term='Ergonomika').count(), 1)


class EditAccessTests(BaseCase):
    def test_edit_button_only_for_teacher(self):
        url = '/d/kompyuter-tizimlari/mavzu/3/1/'
        self.assertNotContains(self.client.get(url), 'edit-btn')
        self.login()
        r = self.client.get(url)
        sec = self.course.topics.get(number=3).sections.first()
        self.assertContains(r, f'href="/studio/d/kompyuter-tizimlari/mavzu/3/reja/{sec.pk}/"')
        self.assertContains(self.client.get('/d/kompyuter-tizimlari/glossariy/'), 'href="/studio/d/kompyuter-tizimlari/glossariy/"')

    def test_export_has_no_edit_button(self):
        self.login()
        z = zipfile.ZipFile(io.BytesIO(self.client.post('/studio/d/kompyuter-tizimlari/eksport/').content))
        self.assertNotIn('edit-btn', z.read('kompyuter-tizimlari/mavzu-3-1.html').decode())

    def test_password_change(self):
        self.login()
        r = self.client.post('/studio/parol/', {'old_password': 'sinov-parol', 'new_password1': 'Yangi-parol-2026',
                                                'new_password2': 'Yangi-parol-2026'})
        self.assertRedirects(r, '/studio/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Yangi-parol-2026'))

    @override_settings(BASE_DIR=Path(TMP_MEDIA))
    def test_ustoz_command(self):
        from django.core.management import call_command
        call_command('ustoz', login='ustoz2', stdout=io.StringIO())
        text = (Path(TMP_MEDIA) / 'KIRISH.txt').read_text(encoding='utf-8')
        password = text.split('Parol:', 1)[1].split()[0]
        self.assertTrue(User.objects.get(username='ustoz2').check_password(password))


class VideoTests(BaseCase):
    YT = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123'

    def test_youtube_id_formats(self):
        from .youtube import youtube_id
        for url in [self.YT, 'https://youtu.be/dQw4w9WgXcQ?si=x', 'https://youtube.com/shorts/dQw4w9WgXcQ',
                    'https://www.youtube.com/live/dQw4w9WgXcQ', 'https://m.youtube.com/watch?feature=share&v=dQw4w9WgXcQ']:
            self.assertEqual(youtube_id(url), 'dQw4w9WgXcQ', url)
        self.assertEqual(youtube_id('https://vimeo.com/1'), '')

    def test_quick_add_youtube_plays_inside_site(self):
        self.login()
        topic = self.course.topics.get(number=4)
        r = self.client.post('/studio/d/kompyuter-tizimlari/video-qoshish/',
                             {'kind': 'video', 'url': self.YT, 'topic': topic.pk, 'title': ''})
        res = self.course.resources.get(kind='video')
        self.assertRedirects(r, f'/d/kompyuter-tizimlari/video/#res{res.pk}')
        self.assertEqual(res.title, 'Video dars')  # nom bo'sh bo'lsa avtomatik
        page = self.client.get('/d/kompyuter-tizimlari/video/').content.decode()
        self.assertIn('youtube-nocookie.com/embed/dQw4w9WgXcQ', page)  # sayt ichidagi pleyer
        self.assertIn('i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg', page)  # muqova rasm
        self.assertNotIn('href="https://www.youtube.com/watch', page)  # YouTube'ga chiqarib yubormaydi
        # mavzuda "Video dars" slaydi paydo bo'ladi
        names = [x['name'] for x in slide_list(topic, list(topic.sections.all()))]
        self.assertIn('Video dars', names)

    def test_quick_add_rejects_non_youtube_link(self):
        self.login()
        self.client.post('/studio/d/kompyuter-tizimlari/video-qoshish/', {'kind': 'video', 'url': 'https://vimeo.com/1'})
        self.assertFalse(self.course.resources.exists())

    def test_quick_add_video_file(self):
        self.login()
        self.client.post('/studio/d/kompyuter-tizimlari/video-qoshish/',
                         {'kind': 'video', 'file': SimpleUploadedFile('dars_1.mp4', b'\x00\x00\x00\x18ftypmp42')})
        res = self.course.resources.get(kind='video')
        self.assertEqual(res.title, 'dars 1')
        self.assertContains(self.client.get('/d/kompyuter-tizimlari/video/'), '<video')

    def test_edit_update_delete_resource(self):
        self.login()
        topic = self.course.topics.get(number=2)
        self.client.post('/studio/d/kompyuter-tizimlari/mavzu/2/?tab=resurslar',
                         {'kind': 'slides', 'title': 'Eski', 'file': SimpleUploadedFile('a.pdf', b'%PDF-1.4 a')})
        res = topic.resources.get()
        old_path = res.file.path
        url = f'/studio/d/kompyuter-tizimlari/resurs/{res.pk}/'
        self.assertEqual(self.client.get(url).status_code, 200)
        # update: nom, mavzu va fayl almashadi, eski fayl diskdan o'chadi
        self.client.post(url, {'kind': 'slides', 'title': 'Yangi', 'topic': self.course.topics.get(number=5).pk,
                               'file': SimpleUploadedFile('b.pdf', b'%PDF-1.4 b')})
        res.refresh_from_db()
        self.assertEqual((res.title, res.topic.number), ('Yangi', 5))
        self.assertFalse(Path(old_path).exists())
        # delete
        new_path = res.file.path
        self.client.post(url, {'delete': '1'})
        self.assertFalse(self.course.resources.exists())
        self.assertFalse(Path(new_path).exists())


class SecurityAndErrorsTests(BaseCase):
    def test_debug_is_off(self):
        self.assertFalse(settings.DEBUG)

    def test_django_admin_removed(self):
        r = self.client.get('/admin/')
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, 'Sahifa topilmadi', status_code=404)

    def test_blank_405_becomes_styled_page(self):
        self.login()
        r = self.client.get('/studio/d/kompyuter-tizimlari/mavzu/1/surish/up/')  # faqat POST
        self.assertEqual(r.status_code, 405)
        self.assertContains(r, 'Bu amal bunday bajarilmaydi', status_code=405)
        self.assertIn('POST', r['Allow'])

    def test_api_errors_stay_json(self):
        r = self.client.get('/api/courses/yoq-darslik/')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r['Content-Type'], 'application/json')

    def test_youtube_referrer_policy(self):
        r = self.client.get('/d/kompyuter-tizimlari/')
        self.assertEqual(r['Referrer-Policy'], 'strict-origin-when-cross-origin')


class OneVideoAtATimeTests(BaseCase):
    def test_player_markup(self):
        from .youtube import player_html
        html = player_html('https://youtu.be/dQw4w9WgXcQ', 'Sinov')
        iframe_tag = html.split('srcdoc=')[0]
        self.assertNotIn(' src=', iframe_tag)  # faqat muqova: YouTube o'zi yuklanib, o'z-o'zidan ijro etilmaydi
        self.assertNotIn('loading="lazy"', iframe_tag)
        self.assertIn('ytStart', html)  # muqova bosilganda sahifaga xabar beradi
        self.assertIn('enablejsapi=1', html)  # sahifa boshqa videolarni to'xtata oladi

    def test_static_links_are_versioned(self):
        html = self.client.get('/d/kompyuter-tizimlari/').content.decode()
        self.assertRegex(html, r'/static/lectures/js/ui\.js\?v=\d+')
        self.assertRegex(html, r'/static/lectures/css/style\.css\?v=\d+')

    def test_ui_js_pauses_other_players(self):
        js = Path(settings.BASE_DIR, 'lectures/static/lectures/js/ui.js').read_text(encoding='utf-8')
        for part in ('pauseVideo', 'ytStart', "addEventListener('play'", 'infoDelivery'):
            self.assertIn(part, js)
