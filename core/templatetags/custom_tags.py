from django import template
import os

register = template.Library()

@register.filter
def add(value, arg):
    """Cộng hai số."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return ""

@register.filter
def sub(value, arg):
    """Trừ hai số."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return ""

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Cho phép truy cập giá trị của dictionary bằng key trong template.
    Sử dụng: {{ my_dictionary|get_item:my_key }}
    """
    # Chuyển đổi key sang kiểu int nếu có thể, vì ID câu hỏi thường là int
    try:
        key = int(key)
    except (ValueError, TypeError):
        pass # Giữ nguyên key nếu không phải số
        
    # Thử truy cập bằng key đã chuyển đổi hoặc key gốc
    return dictionary.get(key)

@register.filter(name='mul')
def mul(value, arg):
    """Nhân giá trị với một số. Sử dụng: {{ value|mul:5 }}"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter(name='div')
def div(value, arg):
    """Chia giá trị cho một số. Sử dụng: {{ value|div:2 }}"""
    try:
        divisor = float(arg)
        if divisor == 0:
            return '' # Tránh lỗi chia cho 0
        return float(value) / divisor
    except (ValueError, TypeError):
        return ''

@register.filter(name='filename')
def filename(value):
    """Trả về tên file từ đường dẫn đầy đủ."""
    if isinstance(value, str):
        return os.path.basename(value)
    # Nếu value là FieldFile (Django file field)
    elif hasattr(value, 'name') and value.name:
         return os.path.basename(value.name)
    return "" 