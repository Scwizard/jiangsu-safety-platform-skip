# -*- coding: utf-8 -*-
"""
User ID 校验模块

提供可复用的 User ID 校验逻辑，解决隐藏字符、长度检查等问题。
"""

def validate_userid(uid):
    """
    校验 User ID 格式
    
    Args:
        uid: 待校验的 User ID 字符串
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not uid:
        return False, "User ID 不能为空"
    
    # 清理所有非数字字符（包括零宽字符、空格、换行等隐藏字符）
    cleaned_uid = ''.join(filter(str.isdigit, str(uid)))
    
    # 检查是否为纯数字
    if not cleaned_uid.isdigit():
        return False, "User ID 应为纯数字（19 位左右），请检查输入"
    
    # 检查长度是否合理（16-22位之间，给用户一定容错空间）
    if len(cleaned_uid) < 16 or len(cleaned_uid) > 22:
        return False, f"User ID 长度异常（当前 {len(cleaned_uid)} 位，应为 19 位左右），请检查输入"
    
    return True, cleaned_uid


# ponytail: 别名，gui/batch_processor 用这个名字调用同一逻辑
validate_and_clean_userid = validate_userid