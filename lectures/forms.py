from pathlib import Path

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .editing import BLOCK_TYPES, html_to_text, lines, text_to_html
from .models import SCENES, Course, GlossaryTerm, Part, Resource, Topic
from .youtube import youtube_id

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg'}
VIDEO_EXT = {'.mp4', '.webm', '.ogg'}


def check_ext(f, allowed, label):
    if f and Path(f.name).suffix.lower() not in allowed:
        raise forms.ValidationError(f'{label} formati mos emas. Ruxsat etilgan: {", ".join(sorted(allowed))}')
    return f


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Login'
        self.fields['password'].label = 'Parol'


class SetupForm(forms.Form):
    """Birinchi ishga tushirish: ustoz uchun akkaunt."""
    name = forms.CharField(label='Ismingiz', max_length=120)
    username = forms.CharField(label='Login', max_length=40, help_text='Lotin harflari va raqamlar, masalan: oydin')
    password = forms.CharField(label='Parol', widget=forms.PasswordInput, min_length=4)
    password2 = forms.CharField(label='Parolni takrorlang', widget=forms.PasswordInput)

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError('Bu login band.')
        return u

    def clean(self):
        d = super().clean()
        if d.get('password') and d.get('password') != d.get('password2'):
            self.add_error('password2', 'Parollar bir xil emas.')
        return d


class DocxImportForm(forms.Form):
    file = forms.FileField(label='Word fayli (.docx)')
    title = forms.CharField(label='Darslik nomi', required=False, help_text='Bo‘sh qoldirsangiz, fayldan olinadi')
    author = forms.CharField(label='Muallif (F.I.Sh.)', max_length=120)
    author_photo = forms.FileField(label='Muallif rasmi', required=False)

    def clean_file(self):
        return check_ext(self.cleaned_data['file'], {'.docx'}, 'Fayl')

    def clean_author_photo(self):
        return check_ext(self.cleaned_data.get('author_photo'), IMAGE_EXT, 'Rasm')


class NewCourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'author', 'module', 'college']


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'subtitle', 'module', 'college', 'direction', 'author', 'author_role', 'author_photo', 'cover_image',
                  'color', 'hours_theory', 'hours_practice', 'hours_self', 'final_size']
        widgets = {'subtitle': forms.Textarea(attrs={'rows': 2})}

    def clean_author_photo(self):
        return check_ext(self.cleaned_data.get('author_photo'), IMAGE_EXT, 'Rasm')

    def clean_cover_image(self):
        return check_ext(self.cleaned_data.get('cover_image'), IMAGE_EXT, 'Rasm')


class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = ['name', 'color', 'icon']


class NewTopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['title', 'kind', 'part']

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['part'].queryset = course.parts.all() if course else Part.objects.none()
        self.fields['part'].empty_label = '— bo‘limsiz —'


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['title', 'kind', 'part', 'hours', 'scene', 'goal', 'result', 'methods']
        widgets = {
            'scene': forms.RadioSelect,
            'goal': forms.Textarea(attrs={'rows': 3}),
            'result': forms.Textarea(attrs={'rows': 3}),
            'methods': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['part'].queryset = self.instance.course.parts.all()
        self.fields['part'].empty_label = '— bo‘limsiz —'
        self.fields['scene'].choices = SCENES


class LinesField(forms.CharField):
    """Har bir qator — ro'yxat elementi."""
    widget = forms.Textarea(attrs={'rows': 5})

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, list):
            return '\n'.join(html_to_text(v) for v in value)
        return value

    def to_python(self, value):
        return lines(super().to_python(value))


class TopicExtrasForm(forms.ModelForm):
    questions = LinesField(label='Mustahkamlash uchun savollar', help_text='Har bir savol — alohida qatorda')
    prev_questions = LinesField(label='O‘tgan mavzu bo‘yicha savollar (takrorlash)')
    self_study = LinesField(label='Mustaqil ta’lim topshiriqlari',
                            help_text='Har bir topshiriq — alohida qatorda. «Topshiriq 1: matn» ko‘rinishida yozsangiz, sarlavha qalin chiqadi')
    literature = LinesField(label='Adabiyotlar va manbalar')

    class Meta:
        model = Topic
        fields = ['questions', 'prev_questions', 'self_study', 'literature']

    def clean_self_study(self):
        out = []
        for ln in self.cleaned_data['self_study']:
            if ':' in ln and ln.index(':') < 60 and not ln.startswith('**'):
                k, v = ln.split(':', 1)
                out.append(f'<b>{text_to_html(k)}:</b> {text_to_html(v.strip())}')
            else:
                out.append(text_to_html(ln))
        return out


class SectionForm(forms.Form):
    title = forms.CharField(label='Reja bo‘limi sarlavhasi', max_length=300)


class TestForm(forms.Form):
    text = forms.CharField(label='Savol', widget=forms.Textarea(attrs={'rows': 2}))
    a = forms.CharField(label='A variant', max_length=500)
    b = forms.CharField(label='B variant', max_length=500)
    c = forms.CharField(label='C variant', max_length=500, required=False)
    d = forms.CharField(label='D variant', max_length=500, required=False)
    answer = forms.TypedChoiceField(label='To‘g‘ri javob', coerce=int, widget=forms.RadioSelect,
                                    choices=[(0, 'A'), (1, 'B'), (2, 'C'), (3, 'D')], initial=0)

    def clean(self):
        d = super().clean()
        opts = [d.get(k, '') for k in 'abcd']
        if d.get('answer') is not None and not opts[d['answer']]:
            self.add_error('answer', 'To‘g‘ri deb belgilangan variant bo‘sh.')
        return d

    def options(self):
        opts = [self.cleaned_data.get(k, '').strip() for k in 'abcd']
        while opts and not opts[-1]:
            opts.pop()
        return opts


class BlockForm(forms.Form):
    """Bitta blok. Qaysi maydonlar kerakligi blok turiga bog'liq."""
    t = forms.ChoiceField(choices=[(k, n) for k, n, _ in BLOCK_TYPES], widget=forms.HiddenInput)
    text = forms.CharField(label='Matn', required=False, widget=forms.Textarea(attrs={'rows': 12}))
    caption = forms.CharField(label='Izoh (rasm/video ostida)', required=False, max_length=300)
    file = forms.FileField(label='Fayl', required=False)
    url = forms.URLField(label='YouTube havolasi', required=False)

    def clean(self):
        d = super().clean()
        t, f = d.get('t'), d.get('file')
        if t == 'image':
            check_ext(f, IMAGE_EXT, 'Rasm')
        if t == 'video' and f:
            check_ext(f, VIDEO_EXT, 'Video')
        if t in ('h', 'p', 'ul', 'table', 'note') and not d.get('text', '').strip():
            self.add_error('text', 'Matnni kiriting.')
        return d


# ------------------------------------------------------------------ resurslar, glossariy, savol-javob
RESOURCE_EXT = {
    'slides': {'.pdf', '.ppt', '.pptx', '.odp'} | IMAGE_EXT,
    'video': VIDEO_EXT,
    'material': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.zip', '.rar', '.odt'} | IMAGE_EXT | VIDEO_EXT,
    'tech': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.odt'},
}


class ResourceForm(forms.ModelForm):
    """Taqdimot / video / material. topic — mavzu sahifasida avtomatik, boshqa joyda tanlanadi."""

    class Meta:
        model = Resource
        fields = ['kind', 'topic', 'title', 'file', 'url', 'note']

    def __init__(self, *args, course=None, kinds=None, fixed_topic=False, **kwargs):
        super().__init__(*args, **kwargs)
        if kinds:
            self.fields['kind'].choices = [c for c in self.fields['kind'].choices if c[0] in kinds]
        if fixed_topic or course is None:
            del self.fields['topic']
        else:
            self.fields['topic'].queryset = course.topics.all()
            self.fields['topic'].empty_label = '— butun darslik uchun —'
        self.fields['title'].widget.attrs['placeholder'] = 'Masalan: 1-mavzu taqdimoti'
        self.fields['url'].widget.attrs['placeholder'] = 'https://youtu.be/...'
        self.fields['url'].help_text = 'YouTube havolasini nusxalab qo‘ying — video sayt ichida ijro etiladi'
        self.fields['file'].help_text = 'Kompyuterdan fayl tanlang (video: MP4)'
        self.fields['title'].required = False

    def clean(self):
        d = super().clean()
        kind, f, url = d.get('kind'), d.get('file'), d.get('url')
        if not f and not url:  # f — yangi fayl yoki tahrirlashda mavjud fayl (o'chirilsa False)
            raise forms.ValidationError('Fayl tanlang yoki havola kiriting.')
        if f and kind in RESOURCE_EXT:
            try:
                check_ext(f, RESOURCE_EXT[kind], 'Fayl')
            except forms.ValidationError as e:
                self.add_error('file', e)
        if kind == 'video' and url and not f and not youtube_id(url):
            self.add_error('url', 'Bu YouTube havolasi emas. Video faylni yuklang yoki YouTube havolasini kiriting.')
        if not d.get('title'):
            # nom kiritilmasa — fayl nomidan yoki "Video dars"
            d['title'] = (Path(f.name).stem.replace('_', ' ')[:200] if f else
                          {'video': 'Video dars', 'slides': 'Taqdimot', 'tech': 'Ta’lim texnologiyasi'}.get(kind, 'Material'))
        return d


class QAForm(forms.Form):
    question = forms.CharField(label='Savol', widget=forms.Textarea(attrs={'rows': 2}))
    answer = forms.CharField(label='Javob', widget=forms.Textarea(attrs={'rows': 3}))


class TermForm(forms.ModelForm):
    class Meta:
        model = GlossaryTerm
        fields = ['term', 'definition', 'topic']
        widgets = {'definition': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['topic'].queryset = course.topics.all() if course else self.fields['topic'].queryset.none()
        self.fields['topic'].empty_label = '— umumiy —'
        self.fields['topic'].required = False
