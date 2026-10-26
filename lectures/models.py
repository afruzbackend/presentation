from django.db import models
from django.urls import reverse
from django.utils.text import slugify

SCENES = [
    ('chip', 'Protsessor'), ('tower', 'Tizim bloki'), ('monitor', 'Monitor va klaviatura'),
    ('printer', 'Printer'), ('disk', 'Disk va SSD'), ('layers', 'Qatlamlar'), ('os', 'Operatsion tizim'),
    ('shield', 'Qalqon (xavfsizlik)'), ('safety', 'Ogohlantirish belgisi'), ('gear', 'Tishli g‘ildiraklar'),
    ('tools', 'Asboblar'), ('pulse', 'Diagnostika'), ('fan', 'Ventilyator'),
]
SCENE_IDS = [s for s, _ in SCENES]

# koshin ranglari
PALETTE = [
    ('#0E7C7B', 'Firuza'), ('#C2562D', 'Terrakota'), ('#24508F', 'Lojuvard'),
    ('#9E2A3A', 'Anor'), ('#3F7D4E', 'Yashil sir'), ('#B07D1E', 'Oltin'),
]


def uz_slug(text):
    """O'zbekcha nomdan URL uchun qisqa nom: 'Kompyuter tizimlari' -> 'kompyuter-tizimlari'"""
    text = text.replace('‘', '').replace('’', '').replace("'", '').replace('ʻ', '').replace('ʼ', '')
    return slugify(text)[:60] or 'darslik'


class Course(models.Model):
    """Elektron darslik."""
    title = models.CharField('Darslik nomi', max_length=200)
    slug = models.SlugField('Manzil (URL)', max_length=70, unique=True)
    subtitle = models.CharField('Qisqa tavsif', max_length=300, blank=True,
                                default='Interaktiv elektron darslik: qisqa bayon, 3D ko‘rgazmalar, testlar va mustaqil ta’lim.')
    module = models.CharField('Modul / fan', max_length=200, blank=True)
    college = models.CharField('Ta’lim muassasasi', max_length=200, blank=True)
    direction = models.CharField('Ta’lim yo‘nalishi', max_length=200, blank=True)
    author = models.CharField('Muallif', max_length=120)
    author_role = models.CharField('Lavozimi', max_length=120, blank=True, default='Maxsus fan o‘qituvchisi')
    author_photo = models.FileField('Muallif rasmi', upload_to='authors/', blank=True)
    cover_image = models.FileField('Bosh sahifa fon rasmi', upload_to='covers/', blank=True,
                                   help_text='Keng rasm: masalan, ustoz dars o‘tayotgan payt')
    color = models.CharField('Asosiy rang', max_length=7, default='#0E7C7B', choices=PALETTE)
    hours_theory = models.PositiveSmallIntegerField('Nazariy soat', default=0)
    hours_practice = models.PositiveSmallIntegerField('Amaliy soat', default=0)
    hours_self = models.PositiveSmallIntegerField('Mustaqil ta’lim soati', default=0)
    final_size = models.PositiveSmallIntegerField('Yakuniy testdagi savollar soni', default=20)
    self_study_plan = models.JSONField('Mustaqil ta’lim rejasi', default=list, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated']
        verbose_name = 'Darslik'
        verbose_name_plural = 'Darsliklar'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base, n = uz_slug(self.title), 2
            self.slug = base
            while Course.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug, n = f'{base}-{n}', n + 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('lectures:course', args=[self.slug])

    @property
    def hours_total(self):
        return self.hours_theory + self.hours_practice + self.hours_self

    @property
    def title_first(self):
        return self.title.split(' ', 1)[0]

    @property
    def title_rest(self):
        parts = self.title.split(' ', 1)
        return parts[1] if len(parts) > 1 else ''


class Part(models.Model):
    """Darslik bo'limi (mavzular guruhi)."""
    ICONS = [('cpu', 'Protsessor'), ('shield', 'Qalqon'), ('monitor', 'Monitor'), ('windows', 'Oynalar'),
             ('fan', 'Ventilyator'), ('wrench', 'Kalit'), ('book', 'Kitob'), ('layers', 'Qatlamlar'),
             ('target', 'Nishon'), ('graduation', 'Bitiruv')]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='parts')
    order = models.PositiveSmallIntegerField('Tartib', default=1)
    name = models.CharField('Bo‘lim nomi', max_length=200)
    color = models.CharField('Rang', max_length=7, default='#0E7C7B', choices=PALETTE)
    icon = models.CharField('Belgi', max_length=20, default='book', choices=ICONS)

    class Meta:
        ordering = ['course', 'order', 'id']
        verbose_name = 'Bo‘lim'
        verbose_name_plural = 'Bo‘limlar'

    def __str__(self):
        return self.name


class Topic(models.Model):
    TYPES = [('Nazariy', 'Nazariy'), ('Amaliy', 'Amaliy')]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topics')
    part = models.ForeignKey(Part, on_delete=models.SET_NULL, null=True, blank=True, related_name='topics',
                             verbose_name='Bo‘lim')
    number = models.PositiveSmallIntegerField('Raqami')
    kind = models.CharField('Turi', max_length=10, choices=TYPES, default='Nazariy')
    title = models.CharField('Mavzu nomi', max_length=300)
    hours = models.PositiveSmallIntegerField('Soat', default=2)
    scene = models.CharField('3D ko‘rgazma', max_length=20, choices=SCENES, default='chip')
    goal = models.TextField('Mashg‘ulot maqsadi', blank=True)
    result = models.TextField('Kutilayotgan natija', blank=True)
    methods = models.TextField('O‘qitish metodlari', blank=True)
    lesson_model = models.JSONField('Ta’lim texnologiyasi modeli', default=list, blank=True)
    tech_map = models.JSONField('Texnologik xarita', default=list, blank=True)
    prev_questions = models.JSONField('O‘tgan mavzu savollari', default=list, blank=True)
    questions = models.JSONField('Mustahkamlash savollari', default=list, blank=True)
    grading = models.JSONField('Baholash mezoni', default=list, blank=True)
    self_study = models.JSONField('Mustaqil ta’lim topshiriqlari', default=list, blank=True)
    literature = models.JSONField('Adabiyotlar', default=list, blank=True)

    class Meta:
        ordering = ['course', 'number']
        unique_together = [('course', 'number')]
        verbose_name = 'Mavzu'
        verbose_name_plural = 'Mavzular'

    def __str__(self):
        return f'{self.number}. {self.title}'

    @property
    def color(self):
        return self.part.color if self.part_id else self.course.color

    @property
    def icon(self):
        return self.part.icon if self.part_id else 'book'


class Section(models.Model):
    """Mavzuning bitta reja bo'limi. blocks: [{t: h|p|ul|table|image|video|note, ...}]"""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='sections')
    order = models.PositiveSmallIntegerField('Tartib')
    title = models.CharField('Sarlavha', max_length=300)
    blocks = models.JSONField('Tarkib', default=list, blank=True)

    class Meta:
        ordering = ['topic', 'order', 'id']
        verbose_name = 'Reja bo‘limi'
        verbose_name_plural = 'Reja bo‘limlari'

    def __str__(self):
        return f'{self.topic.number}.{self.order} {self.title}'


class TestQuestion(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='tests')
    order = models.PositiveSmallIntegerField('Tartib', default=1)
    text = models.TextField('Savol')
    options = models.JSONField('Variantlar', default=list)
    answer = models.PositiveSmallIntegerField('To‘g‘ri javob (0 = A)', default=0)

    class Meta:
        ordering = ['topic', 'order', 'id']
        verbose_name = 'Test savoli'
        verbose_name_plural = 'Test savollari'

    def __str__(self):
        return f'{self.topic.number}-mavzu, {self.order}-savol'


class Media(models.Model):
    """Darslikka yuklangan rasm yoki video."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='media')
    file = models.FileField('Fayl', upload_to='media/%Y/%m/')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.file.name


class Resource(models.Model):
    """Taqdimot, video darslik, qo'shimcha material yoki ta'lim texnologiyasi hujjati."""
    KINDS = [
        ('slides', 'Taqdimot'),
        ('video', 'Video darslik'),
        ('material', 'Material'),
        ('tech', 'Ta’lim texnologiyasi'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True, blank=True, related_name='resources',
                              verbose_name='Mavzu')
    kind = models.CharField('Turi', max_length=10, choices=KINDS, default='material')
    title = models.CharField('Nomi', max_length=200)
    file = models.FileField('Fayl', upload_to='resources/%Y/%m/', blank=True)
    url = models.URLField('Havola (YouTube yoki sayt)', blank=True)
    note = models.CharField('Izoh', max_length=300, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['kind', 'topic__number', 'created']
        verbose_name = 'Resurs'
        verbose_name_plural = 'Resurslar'

    def __str__(self):
        return self.title

    @property
    def ext(self):
        return self.file.name.rsplit('.', 1)[-1].lower() if self.file else ''

    @property
    def file_size(self):
        """Fayl hajmi (fayl diskda topilmasa — 0, sahifa buzilmaydi)."""
        try:
            return self.file.size if self.file else 0
        except OSError:
            return 0

    @property
    def is_pdf(self):
        return self.ext == 'pdf'

    @property
    def is_video_file(self):
        return self.ext in ('mp4', 'webm', 'ogg')

    @property
    def is_image(self):
        return self.ext in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'svg')


class GlossaryTerm(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='glossary')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='terms',
                              verbose_name='Mavzu')
    term = models.CharField('Atama', max_length=120)
    definition = models.TextField('Ta’rifi')

    class Meta:
        ordering = ['term']
        verbose_name = 'Glossariy atamasi'
        verbose_name_plural = 'Glossariy'

    def __str__(self):
        return self.term

    @property
    def letter(self):
        t = self.term.strip().upper()
        return t[:2] if t[:2] in ('O‘', 'G‘', 'SH', 'CH') else t[:1]


class QuickQA(models.Model):
    """Tezkor savol-javob (kartochka)."""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='qa')
    order = models.PositiveSmallIntegerField('Tartib', default=1)
    question = models.TextField('Savol')
    answer = models.TextField('Javob')

    class Meta:
        ordering = ['topic', 'order', 'id']
        verbose_name = 'Tezkor savol-javob'
        verbose_name_plural = 'Tezkor savol-javoblar'

    def __str__(self):
        return self.question[:60]
