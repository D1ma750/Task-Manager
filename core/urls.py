from django.urls import path
from . import views
from django.http import HttpResponse

def test_view(request):
    return HttpResponse("Тестовая страница работает!")

urlpatterns = [
    path('test/', test_view),
    path('', views.index, name='index'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name = 'task_create'),
    path('tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),
    path('skill/<int:employee_id>/<str:skill_name>/delete/', views.skill_delete, name='skill_delete'),
    path('skill/add/', views.skill_add, name='skill_add'),
    path('assign/<int:task_id>/<int:employee_id>/', views.assign_employee, name='assign_employee'),
    path('remove/<int:task_id>/<int:employee_id>/', views.remove_assignment, name='remove_assignment'),
    path('update-status/<int:task_id>/<str:new_status>/', views.update_task_status, name='update_task_status'),
]