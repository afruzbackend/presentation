from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import studio as v

app_name = 'studio'

T = 'd/<slug:slug>/mavzu/<int:n>/'

urlpatterns = [
    path('', v.dashboard, name='dashboard'),
    path('kirish/', v.StudioLogin.as_view(), name='login'),
    path('chiqish/', LogoutView.as_view(next_page='lectures:library'), name='logout'),
    path('sozlash/', v.setup, name='setup'),
    path('parol/', login_required(v.StudioPasswordChange.as_view()), name='password'),
    path('yangi/', v.course_new, name='course_new'),
    path('zaxira/', v.backup, name='backup'),

    path('d/<slug:slug>/', v.course_edit, name='course'),
    path('d/<slug:slug>/sozlamalar/', v.course_settings, name='settings'),
    path('d/<slug:slug>/bolimlar/', v.parts, name='parts'),
    path('d/<slug:slug>/bolimlar/<int:pk>/', v.part_save, name='part_save'),
    path('d/<slug:slug>/eksport/', v.export, name='export'),
    path('d/<slug:slug>/ochirish/', v.course_delete, name='course_delete'),
    path('d/<slug:slug>/materiallar/', v.course_materials, name='materials'),
    path('d/<slug:slug>/resurs/<int:pk>/', v.resource_edit, name='resource'),
    path('d/<slug:slug>/resurs/<int:pk>/ochirish/', v.resource_delete, name='resource_delete'),
    path('d/<slug:slug>/video-qoshish/', v.video_add, name='video_add'),
    path('d/<slug:slug>/glossariy/', v.glossary, name='glossary'),
    path('d/<slug:slug>/glossariy/<int:pk>/', v.term_edit, name='term'),

    path(T, v.topic_edit, name='topic'),
    path(T + 'surish/<str:direction>/', v.topic_move, name='topic_move'),
    path(T + 'ochirish/', v.topic_delete, name='topic_delete'),
    path(T + 'reja/<int:sid>/', v.section_edit, name='section'),
    path(T + 'reja/<int:sid>/<str:action>/', v.section_action, name='section_action'),
    path(T + 'reja/<int:sid>/blok/yangi/', v.block_edit, name='block_new'),
    path(T + 'reja/<int:sid>/blok/<int:i>/', v.block_edit, name='block'),
    path(T + 'reja/<int:sid>/blok/<int:i>/<str:action>/', v.block_action, name='block_action'),
    path(T + 'test/yangi/', v.test_edit, name='test_new'),
    path(T + 'test/<int:qid>/', v.test_edit, name='test'),
    path(T + 'test/<int:qid>/ochirish/', v.test_delete, name='test_delete'),
    path(T + 'savol-javob/<int:pk>/', v.qa_edit, name='qa'),
    path(T + 'savol-javob/<str:action>/', v.qa_action, name='qa_action'),
    path(T + 'taqdimot/', v.topic_slides, name='topic_slides'),
    path(T + 'savol-javob/<int:pk>/<str:action>/', v.qa_action, name='qa_item_action'),
]
