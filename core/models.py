from django.db import models

class Employee(models.Model):
    employee_code = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        db_table = 'employees'  # ← используем существующую таблицу

class Task(models.Model):
    task_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='todo')
    priority = models.CharField(max_length=10, default='medium')
    project_name = models.CharField(max_length=100)
    due_date = models.DateField()
    required_skills = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_code}: {self.title}"

    class Meta:
        db_table = 'tasks'  # ← используем существующую таблицу

class EmployeeSkill(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    skill_name = models.CharField(max_length=100)
    skill_level = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.employee} - {self.skill_name}"

    class Meta:
        db_table = 'employee_skills'  # ← используем существующую таблицу

class EmployeeTask(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    assigned_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} -> {self.task}"

    class Meta:
        db_table = 'employee_tasks'  # ← используем существующую таблицу
