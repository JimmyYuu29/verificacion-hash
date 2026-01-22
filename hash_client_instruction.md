# 📦 Hash Client 集成指南

本文档介绍如何将你的文档生成应用与 **Hash Verification System** 集成，使生成的文档能够自动注册到验证系统。

---

## 🎯 概述

当用户在你的应用中生成文档（如 PDF）时，你需要：
1. 生成一个唯一的 Hash Code
2. 计算文档的 SHA-256 哈希值
3. 将元数据注册到验证系统

本模块 `hash_client.py` 提供了简单的接口来完成步骤 2 和 3。

---

## 📁 文件位置

```
verificacion-hash/
├── hash_client.py           # ⭐ 客户端模块（导入此文件）
├── hash_client_instruction.md  # 本说明文档
├── main.py                  # 验证服务 API
└── output/                  # 注册数据存储目录
```

---

## 🚀 快速开始

### 步骤 1：将模块添加到你的项目

**方法 A：创建符号链接（推荐）**

```bash
# 在你的 App 目录中创建链接
ln -s /path/to/verificacion-hash/hash_client.py /你的app路径/hash_client.py
```

**方法 B：直接复制**

```bash
cp /path/to/verificacion-hash/hash_client.py /你的app路径/
```

> ⚠️ **注意**：如果复制文件，需要更新 `hash_client.py` 中的 `OUTPUT_DIR` 路径。

### 步骤 2：在代码中导入

```python
from hash_client import register_document, calculate_pdf_hash, generate_hash_code
```

### 步骤 3：集成到文档生成流程

```python
from hash_client import register_document, calculate_pdf_hash, generate_hash_code
from pathlib import Path

def generate_user_document(client_name, form_data):
    """用户点击生成文档时调用的函数"""
    
    # ========== 1. 你原有的 PDF 生成逻辑 ==========
    pdf_path = your_existing_pdf_generation_function(...)
    
    # ========== 2. 生成 Hash Code ==========
    # 使用内置函数生成（推荐）
    hash_code = generate_hash_code("CM")  # CM = Carta de Manifestacion
    # 或使用你自己的逻辑
    
    # ========== 3. 计算 PDF 的 SHA-256 ==========
    content_hash = calculate_pdf_hash(pdf_path)
    
    # ========== 4. 注册到验证系统 ==========
    result = register_document(
        hash_code=hash_code,
        user_id="your_app_name",        # 你的应用标识符
        content_hash=content_hash,
        client_name=client_name,
        document_type="carta_manifestacion",
        document_type_display="Carta de Manifestacion",
        file_name="document.pdf",
        file_size=Path(pdf_path).stat().st_size,
        form_data=form_data
    )
    
    # ========== 5. 处理结果 ==========
    if result["success"]:
        print(f"✅ 文档已注册")
        print(f"   Hash Code: {result['hash_code']}")
        print(f"   Short Code: {result['short_code']}")
        # 将 hash_code 写入 PDF 页脚
        add_hash_to_pdf_footer(pdf_path, hash_code)
    else:
        print(f"❌ 注册失败: {result['message']}")
    
    return pdf_path, hash_code
```

---

## 📚 API 参考

### `register_document()`

注册文档到验证系统。

```python
result = register_document(
    hash_code="CM-A1B2C3D4E5F6",      # 必填：文档 Hash Code
    user_id="your_app_name",           # 必填：应用标识符
    content_hash="sha256...",          # 可选：PDF 的 SHA-256
    client_name="客户名称",             # 可选：客户名称
    document_type="carta_manifestacion", # 可选：文档类型代码
    document_type_display="Carta de Manifestacion", # 可选：显示名称
    file_name="document.pdf",          # 可选：文件名
    file_size=12345,                   # 可选：文件大小（字节）
    form_data={"key": "value"},        # 可选：额外表单数据
    overwrite=False                    # 可选：是否覆盖已存在的记录
)
```

**返回值：**

```python
# 成功
{
    "success": True,
    "message": "Document registered successfully",
    "path": "/path/to/output/user_id/metadata_XX_XXXX.json",
    "hash_code": "CM-A1B2C3D4E5F6",
    "short_code": "ABC123"
}

# 失败
{
    "success": False,
    "message": "错误描述"
}
```

---

### `generate_hash_code()`

生成新的唯一 Hash Code。

```python
hash_code = generate_hash_code("CM")
# 返回: "CM-A1B2C3D4E5F6"（12位随机字符）
```

**文档类型前缀：**

| 前缀 | 文档类型 |
|------|----------|
| `CM` | Carta de Manifestación |
| `IA` | Informe de Auditoría |
| `CE` | Carta de Encargo |
| `IR` | Informe de Revisión |
| `OT` | Otros Documentos |

---

### `calculate_pdf_hash()`

计算 PDF 文件的 SHA-256 哈希值。

```python
content_hash = calculate_pdf_hash("/path/to/document.pdf")
# 返回: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
```

---

## 🔗 HTTP API 方式（可选）

如果你的应用不是 Python，或者需要远程调用，可以使用 HTTP API：

```bash
curl -X POST "http://localhost:8000/api/register" \
  -H "Content-Type: application/json" \
  -d '{
    "hash_info": {
      "hash_code": "CM-A1B2C3D4E5F6",
      "content_hash": "sha256..."
    },
    "user_info": {
      "user_id": "your_app_name",
      "client_name": "客户名称"
    },
    "document_info": {
      "type": "carta_manifestacion",
      "type_display": "Carta de Manifestacion",
      "file_name": "document.pdf"
    },
    "form_data": {}
  }'
```

---

## ⚙️ 配置

### 修改输出目录

编辑 `hash_client.py` 中的 `OUTPUT_DIR`：

```python
# 选项 1：绝对路径（推荐生产环境）
OUTPUT_DIR = Path("/var/www/verificacion-hash/output")

# 选项 2：相对路径
OUTPUT_DIR = Path(__file__).parent / "output"
```

---

## 🧪 测试

运行模块自带的测试：

```bash
python3 hash_client.py
```

预期输出：

```json
{
  "success": true,
  "message": "Document registered successfully",
  "path": "...",
  "hash_code": "CM-EXAMPLE12345",
  "short_code": "EAPE24"
}
```

验证注册成功：

```bash
curl http://localhost:8000/api/verify/CM-EXAMPLE12345
```

---

## ❓ 常见问题

### Q: 注册后文件存储在哪里？

文件存储在 `output/{user_id}/metadata_{hash}_{trace}.json`

### Q: 相同的 hash 可以重复注册吗？

默认不可以。如需覆盖，设置 `overwrite=True`。

### Q: 如何验证注册的文档？

访问 `http://localhost:8000/api/verify/{hash_code}` 或使用 short_code。

---

## 📞 支持

如有问题，请联系系统管理员或查看主文档 `README.md`。
