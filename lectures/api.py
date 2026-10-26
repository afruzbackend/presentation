"""REST API (Django REST Framework): /api/"""
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .content import grade_for
from .models import Course, Part, Section, TestQuestion, Topic


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['order', 'title', 'blocks']


class TestQuestionSerializer(serializers.ModelSerializer):
    """To'g'ri javob API orqali ochilmaydi — /check/ orqali tekshiriladi."""
    class Meta:
        model = TestQuestion
        fields = ['id', 'order', 'text', 'options']


class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Part
        fields = ['id', 'order', 'name', 'color', 'icon']


class TopicListSerializer(serializers.ModelSerializer):
    course = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    part = serializers.StringRelatedField()

    class Meta:
        model = Topic
        fields = ['id', 'course', 'number', 'kind', 'title', 'part', 'hours', 'scene']


class TopicDetailSerializer(TopicListSerializer):
    sections = SectionSerializer(many=True, read_only=True)
    tests = TestQuestionSerializer(many=True, read_only=True)

    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + [
            'goal', 'result', 'methods', 'prev_questions', 'questions', 'grading', 'self_study', 'literature',
            'sections', 'tests']


class CourseSerializer(serializers.ModelSerializer):
    parts = PartSerializer(many=True, read_only=True)
    topics = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['slug', 'title', 'subtitle', 'module', 'college', 'direction', 'author', 'author_role',
                  'hours_theory', 'hours_practice', 'hours_self', 'parts', 'topics', 'updated']

    def get_topics(self, obj):
        return TopicListSerializer(obj.topics.select_related('part'), many=True).data


class CheckSerializer(serializers.Serializer):
    answers = serializers.DictField(child=serializers.IntegerField(min_value=0, max_value=3),
                                    help_text='{"savol_id": variant_raqami (0=A ... 3=D)}')


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Darsliklar ro'yxati va tarkibi."""
    queryset = Course.objects.prefetch_related('parts')
    serializer_class = CourseSerializer
    lookup_field = 'slug'


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """Mavzular. ?course=<slug>, ?kind=Nazariy|Amaliy, ?search=..."""

    def get_queryset(self):
        qs = Topic.objects.select_related('course', 'part')
        p = self.request.query_params
        if p.get('course'):
            qs = qs.filter(course__slug=p['course'])
        if p.get('kind'):
            qs = qs.filter(kind=p['kind'])
        if p.get('search'):
            qs = qs.filter(title__icontains=p['search'])
        if self.action == 'retrieve':
            qs = qs.prefetch_related('sections', 'tests')
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TopicDetailSerializer
        if self.action == 'check':
            return CheckSerializer
        return TopicListSerializer

    @action(detail=True, methods=['post'])
    def check(self, request, pk=None):
        """Test javoblarini tekshirish: {"answers": {"12": 1, "13": 0}}"""
        topic = self.get_object()
        ser = CheckSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        answers = {int(k): v for k, v in ser.validated_data['answers'].items()}
        results, score = [], 0
        tests = list(topic.tests.all())
        for q in tests:
            ok = answers.get(q.pk) == q.answer
            score += ok
            results.append({'id': q.pk, 'chosen': answers.get(q.pk), 'correct': q.answer, 'ok': ok})
        return Response({'topic': topic.number, 'results': results, **grade_for(score, len(tests))})
