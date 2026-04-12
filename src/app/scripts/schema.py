class SchemaProvider:
    # Use a dictionary to store the raw strings
    _SCHEMAS = {
        "employees": """
### Table: Employees
- **EmployeeID**: INT (PK)
- **FirstName**: VARCHAR(100)
- **LastName**: VARCHAR(100)
- **DepartmentID**: INT (FK to Departments.DepartmentID)
""",
        "departments": """
### Table: Departments
- **DepartmentID**: INT (PK)
- **DepartmentName**: VARCHAR(150)
- **ManagerID**: INT (FK to Employees.EmployeeID)
""",
        "vacancies": """
### Table: JobVacancies
- **JobID**: INT (PK)
- **Title**: VARCHAR(200)
- **DepartmentID**: INT (FK to Departments.DepartmentID)
""",
        "applicants": """
### Table: Applicants
- **ApplicantID**: INT (PK)
- **FirstName**: VARCHAR(100)
- **LastName**: VARCHAR(100)
""",
        "applications": """
### Table: JobApplications
- **ApplicationID**: INT (PK)
- **JobID**: INT (FK to JobVacancies.JobID)
- **ApplicantID**: INT (FK to Applicants.ApplicantID)
"""
    }

    @classmethod
    def get_context(cls, keys: list) -> str:
        """Joins requested table schemas into a single string."""
        return "\n".join([cls._SCHEMAS[k] for k in keys if k in cls._SCHEMAS])

