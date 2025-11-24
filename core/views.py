from django.shortcuts import render, redirect
from django.db import connection


def index(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM employees")
        total_employees = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != 'done'")
        active_tasks = cursor.fetchone()[0]

    stats = {
        'total_employees': total_employees,
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
    }
    return render(request, 'core/index.html', {'stats': stats})


def task_list(request):
    """Список всех задач"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT t.id, t.task_code, t.title, t.status, t.priority, 
                   t.due_date, t.project_name, t.required_skills,
                   COUNT(et.employee_id) as employee_count
            FROM tasks t
            LEFT JOIN employee_tasks et ON t.id = et.task_id
            GROUP BY t.id, t.task_code, t.title, t.status, t.priority, 
                     t.due_date, t.project_name, t.required_skills
            ORDER BY t.id DESC
        """)
        columns = [col[0] for col in cursor.description]
        tasks = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, 'core/task_list.html', {'tasks': tasks})


def task_detail(request, task_id):
    """Детальная страница задачи"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM tasks WHERE id = %s", [task_id])
        columns = [col[0] for col in cursor.description]
        task = dict(zip(columns, cursor.fetchone()))

        # Получаем назначенных сотрудников
        cursor.execute("""
            SELECT e.id, e.first_name, e.last_name, e.position
            FROM employee_tasks et
            JOIN employees e ON et.employee_id = e.id
            WHERE et.task_id = %s
        """, [task_id])
        assigned_employees = [
            dict(zip(['id', 'first_name', 'last_name', 'position'], row))
            for row in cursor.fetchall()
        ]

        # Получаем рекомендованных сотрудников
        cursor.execute("""
            WITH task_skills AS (
                SELECT TRIM(UNNEST(STRING_TO_ARRAY(required_skills, ','))) as skill
                FROM tasks 
                WHERE id = %s
            ),
            candidate_skills AS (
                SELECT 
                    e.id as emp_id,
                    e.first_name || ' ' || e.last_name as emp_name,
                    COUNT(DISTINCT et.task_id) as task_count,
                    STRING_AGG(
                        es.skill_name || ':' || es.skill_level, 
                        ', '
                    ) as matching_skills_with_levels
                FROM employees e
                INNER JOIN employee_skills es ON e.id = es.employee_id
                LEFT JOIN employee_tasks et ON e.id = et.employee_id
                WHERE e.is_active = true
                  AND es.skill_name IN (SELECT skill FROM task_skills)
                  AND e.id NOT IN (
                      SELECT employee_id 
                      FROM employee_tasks 
                      WHERE task_id = %s
                  )
                GROUP BY e.id, e.first_name, e.last_name
            )
            SELECT 
                emp_id,
                emp_name,
                task_count,
                matching_skills_with_levels
            FROM candidate_skills
            ORDER BY task_count ASC, emp_name
        """, [task_id, task_id])

        suggested_candidates = []
        for row in cursor.fetchall():
            emp_id, emp_name, task_count, skills_with_levels = row

            formatted_skills = []
            if skills_with_levels:
                for skill_pair in skills_with_levels.split(', '):
                    if ':' in skill_pair:
                        skill_name, skill_level = skill_pair.split(':')
                        formatted_skills.append({
                            'name': skill_name,
                            'level': skill_level,
                            'badge_class': 'bg-success' if skill_level == 'expert' else
                            'bg-warning' if skill_level == 'intermediate' else
                            'bg-secondary'
                        })

            suggested_candidates.append({
                'emp_id': emp_id,
                'emp_name': emp_name,
                'task_count': task_count,
                'skills': formatted_skills
            })

    return render(request, 'core/task_detail.html', {
        'task': task,
        'assigned_employees': assigned_employees,
        'suggested_candidates': suggested_candidates,
    })


def employee_list(request):
    """Список всех сотрудников"""
    with connection.cursor() as cursor:
        # Сначала получаем сотрудников
        cursor.execute("""
            SELECT e.id, e.employee_code, e.first_name, e.last_name, 
                   e.position, e.department
            FROM employees e
            WHERE e.is_active = true
            ORDER BY e.last_name, e.first_name
        """)
        employees = []
        for row in cursor.fetchall():
            emp_id, emp_code, first_name, last_name, position, department = row

            # Затем для каждого сотрудника отдельно считаем задачи и навыки
            cursor.execute("""
                SELECT COUNT(DISTINCT task_id) 
                FROM employee_tasks 
                WHERE employee_id = %s
            """, [emp_id])
            task_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT STRING_AGG(skill_name, ', ') 
                FROM employee_skills 
                WHERE employee_id = %s
            """, [emp_id])
            skills = cursor.fetchone()[0] or "Нет навыков"

            employees.append({
                'id': emp_id,
                'employee_code': emp_code,
                'first_name': first_name,
                'last_name': last_name,
                'position': position,
                'department': department,
                'task_count': task_count,
                'skills': skills
            })

    return render(request, 'core/employee_list.html', {'employees': employees})


def employee_detail(request, employee_id):
    """Детальная страница сотрудника"""
    with connection.cursor() as cursor:
        # Получаем основную информацию о сотруднике
        cursor.execute("""
            SELECT id, employee_code, first_name, last_name, 
                   position, department, email
            FROM employees 
            WHERE id = %s AND is_active = true
        """, [employee_id])
        columns = [col[0] for col in cursor.description]
        employee = dict(zip(columns, cursor.fetchone()))

        # Получаем навыки сотрудника
        cursor.execute("""
            SELECT skill_name, skill_level 
            FROM employee_skills 
            WHERE employee_id = %s
            ORDER BY skill_level DESC, skill_name
        """, [employee_id])
        skills = [
            dict(zip(['skill_name', 'skill_level'], row))
            for row in cursor.fetchall()
        ]

        # Получаем задачи сотрудника
        cursor.execute("""
            SELECT t.id, t.task_code, t.title, t.status, t.priority,
                   t.due_date
            FROM employee_tasks et
            JOIN tasks t ON et.task_id = t.id
            WHERE et.employee_id = %s
            ORDER BY t.due_date ASC
        """, [employee_id])
        tasks = [
            dict(zip(['id', 'task_code', 'title', 'status', 'priority', 'due_date'], row))
            for row in cursor.fetchall()
        ]

    return render(request, 'core/employee_detail.html', {
        'employee': employee,
        'skills': skills,
        'tasks': tasks,
    })


def assign_employee(request, task_id, employee_id):
    """Назначить сотрудника на задачу"""
    with connection.cursor() as cursor:
        # Проверяем не назначен ли уже
        cursor.execute("SELECT COUNT(*) FROM employee_tasks WHERE task_id = %s AND employee_id = %s",
                       [task_id, employee_id])
        if cursor.fetchone()[0] == 0:

            cursor.execute("INSERT INTO employee_tasks (employee_id, task_id) VALUES (%s, %s)",
                           [employee_id, task_id])

    return redirect('task_detail', task_id=task_id)


def remove_assignment(request, task_id, employee_id):
    """Убрать сотрудника с задачи"""
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM employee_tasks WHERE task_id = %s AND employee_id = %s",
                       [task_id, employee_id])

    return redirect('task_detail', task_id=task_id)


def update_task_status(request, task_id, new_status):
    """Изменить статус задачи"""
    with connection.cursor() as cursor:
        cursor.execute("UPDATE tasks SET status = %s WHERE id = %s",
                       [new_status, task_id])

    return redirect('task_detail', task_id=task_id)


def task_create(request):
    """Создание новой задачи"""
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO tasks (task_code, title, description, status, priority, 
                                 project_name, due_date, required_skills)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                request.POST['task_code'],
                request.POST['title'],
                request.POST.get('description', ''),
                request.POST.get('status', 'todo'),
                request.POST.get('priority', 'medium'),
                request.POST['project_name'],
                request.POST['due_date'],
                request.POST.get('required_skills', '')
            ])
        return redirect('task_list')

    return render(request, 'core/task_form.html')


def employee_create(request):
    """Добавление нового сотрудника"""
    if request.method == 'POST':
        with connection.cursor() as cursor:
            # Сначала создаем сотрудника
            cursor.execute("""
                INSERT INTO employees (employee_code, first_name, last_name, email,
                                     position, department, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, [
                request.POST['employee_code'],
                request.POST['first_name'],
                request.POST['last_name'],
                request.POST['email'],
                request.POST['position'],
                request.POST['department'],
                request.POST.get('is_active', 'on') == 'on'
            ])

            employee_id = cursor.fetchone()[0]

            skill_names = request.POST.getlist('skill_name')
            skill_levels = request.POST.getlist('skill_level')

            for skill_name, skill_level in zip(skill_names, skill_levels):
                skill_name = skill_name.strip()
                if skill_name:  # только если навык не пустой
                    cursor.execute("""
                        INSERT INTO employee_skills (employee_id, skill_name, skill_level)
                        VALUES (%s, %s, %s)
                    """, [employee_id, skill_name, skill_level])

        return redirect('employee_list')

    return render(request, 'core/employee_form.html')


def task_delete(request, task_id):
    """Удаление задачи"""
    if request.method == 'POST':
        with connection.cursor() as cursor:

            cursor.execute("DELETE FROM employee_tasks WHERE task_id = %s", [task_id])

            cursor.execute("DELETE FROM tasks WHERE id = %s", [task_id])
        return redirect('task_list')

    return redirect('task_list')


def employee_delete(request, employee_id):
    """Удаление сотрудника"""
    if request.method == 'POST':
        with connection.cursor() as cursor:

            cursor.execute("DELETE FROM employee_skills WHERE employee_id = %s", [employee_id])

            cursor.execute("DELETE FROM employee_tasks WHERE employee_id = %s", [employee_id])

            cursor.execute("DELETE FROM employees WHERE id = %s", [employee_id])
        return redirect('employee_list')


def skill_delete(request, employee_id, skill_name):
    """Удаление навыка"""
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM employee_skills WHERE employee_id = %s AND skill_name = %s",
                           [employee_id, skill_name])
        return redirect('employee_detail', employee_id=employee_id)


def skill_add(request):
    """Добавление нового навыка"""
    if request.method == 'POST':
        employee_id = request.POST['employee_id']
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO employee_skills (employee_id, skill_name, skill_level)
                VALUES (%s, %s, %s)
            """, [
                employee_id,
                request.POST['skill_name'],
                request.POST['skill_level']
            ])
        return redirect('employee_detail', employee_id=employee_id)

    return redirect('employee_list')