import os

# Locate the templates directory relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# Ensure the templates folder exists
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Define the HTML layout for base.html
BASE_HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Generator</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">Lead Generator</a>
        </div>
    </nav>

    <div class="container mb-5">
        {% block content %}{% endblock %}
    </div>

    <!-- Bootstrap 5 JS Bundle -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Write base.html inside templates directory
base_file_path = os.path.join(TEMPLATES_DIR, 'base.html')

with open(base_file_path, 'w', encoding='utf-8') as f:
    f.write(BASE_HTML_CONTENT)

print(f"Successfully generated base.html at: {base_file_path}")