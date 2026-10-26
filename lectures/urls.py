from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, views

app_name = 'lectures'

router = DefaultRouter()
router.register('courses', api.CourseViewSet, basename='course')
router.register('topics', api.TopicViewSet, basename='topic')

urlpatterns = [
    path('', views.library, name='library'),
    path('d/<slug:slug>/', views.course_home, name='course'),
    path('d/<slug:slug>/mavzular/', views.contents, name='contents'),
    path('d/<slug:slug>/mavzu/<int:n>/', views.topic_start, name='topic'),
    path('d/<slug:slug>/mavzu/<int:n>/<int:s>/', views.slide, name='slide'),
    path('d/<slug:slug>/reja/', views.plan, name='plan'),
    path('d/<slug:slug>/mustaqil/', views.self_study, name='self_study'),
    path('d/<slug:slug>/test/', views.final_test, name='final'),
    path('d/<slug:slug>/muallif/', views.author, name='author'),
    path('d/<slug:slug>/maruza/', views.lecture_index, name='lecture'),
    path('d/<slug:slug>/maruza/<int:n>/', views.lecture_text, name='lecture_text'),
    path('d/<slug:slug>/taqdimotlar/', views.resources_page, {'kind': 'slides'}, name='slides'),
    path('d/<slug:slug>/video/', views.resources_page, {'kind': 'video'}, name='videos'),
    path('d/<slug:slug>/materiallar/', views.resources_page, {'kind': 'material'}, name='materials'),
    path('d/<slug:slug>/texnologiyalar/', views.technologies, name='tech'),
    path('d/<slug:slug>/glossariy/', views.glossary, name='glossary'),
    path('d/<slug:slug>/savol-javob/', views.qa_page, name='qa'),
    path('rejim/', views.toggle_theme, name='theme'),
    path('api/', include(router.urls)),
]
