import re
import os
import html


MAX_TEXT_LENGTH = 50000
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
ALLOWED_VIDEO_TYPES = {'mp4', 'avi', 'mov', 'mkv'}
ALLOWED_TEXT_TYPES = {'txt', 'csv', 'json', 'md'}
IMAGE_MAGIC_BYTES = {
    b'\x89PNG': 'png',
    b'\xff\xd8\xff': 'jpg',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'BM': 'bmp',
}


def sanitize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = html.escape(text)
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]
    return text


def validate_text_input(text):
    errors = []
    if not text or not text.strip():
        errors.append("Text input cannot be empty.")
        return False, errors

    if len(text) > MAX_TEXT_LENGTH:
        errors.append(f"Text exceeds maximum length of {MAX_TEXT_LENGTH:,} characters.")

    if re.search(r'<script[^>]*>.*?</script>', text, re.IGNORECASE | re.DOTALL):
        errors.append("Input contains potentially unsafe script tags.")

    if re.search(r'(javascript|data|vbscript):', text, re.IGNORECASE):
        errors.append("Input contains potentially unsafe URI schemes.")

    if len(errors) > 0:
        return False, errors
    return True, []


def sanitize_filename(filename):
    if not isinstance(filename, str):
        return "unnamed_file"
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-.]', '_', filename)
    filename = re.sub(r'\.{2,}', '.', filename)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename


def validate_file_upload(uploaded_file, allowed_types):
    errors = []
    if uploaded_file is None:
        errors.append("No file provided.")
        return False, errors

    if uploaded_file.size > MAX_FILE_SIZE_BYTES:
        errors.append(f"File size ({uploaded_file.size / 1024 / 1024:.1f} MB) exceeds the {MAX_FILE_SIZE_MB} MB limit.")

    ext = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    if ext not in allowed_types:
        errors.append(f"File type '.{ext}' is not allowed. Accepted types: {', '.join(allowed_types)}")

    if len(errors) > 0:
        return False, errors
    return True, []


def validate_image_upload(uploaded_file):
    valid, errors = validate_file_upload(uploaded_file, ALLOWED_IMAGE_TYPES)
    if not valid:
        return False, errors

    try:
        header = uploaded_file.read(8)
        uploaded_file.seek(0)
        is_valid_image = False
        for magic, fmt in IMAGE_MAGIC_BYTES.items():
            if header.startswith(magic):
                is_valid_image = True
                break
        if not is_valid_image:
            errors.append("File does not appear to be a valid image based on its contents.")
            return False, errors
    except Exception:
        errors.append("Could not read file contents for validation.")
        return False, errors

    return True, []


def validate_video_upload(uploaded_file):
    return validate_file_upload(uploaded_file, ALLOWED_VIDEO_TYPES)


def validate_batch_text(text):
    errors = []
    if not text or not text.strip():
        errors.append("Batch text input cannot be empty.")
        return False, errors, []

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 500:
        errors.append(f"Too many entries ({len(lines)}). Maximum is 500 entries per batch.")
        return False, errors, []

    sanitized_lines = []
    for i, line in enumerate(lines):
        valid, line_errors = validate_text_input(line)
        if not valid:
            errors.append(f"Line {i+1}: {'; '.join(line_errors)}")
        else:
            sanitized_lines.append(sanitize_text(line))

    if errors:
        return False, errors, sanitized_lines

    return True, [], sanitized_lines


def validate_slider_value(value, min_val, max_val, name="Value"):
    if not isinstance(value, (int, float)):
        return False, f"{name} must be a number."
    if value < min_val or value > max_val:
        return False, f"{name} must be between {min_val} and {max_val}."
    return True, ""
