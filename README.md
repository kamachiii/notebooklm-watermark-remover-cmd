# NotebookLM Watermark Remover 🚀

Una herramienta de precisión diseñada para eliminar la marca de agua "NotebookLM" de tus diapositivas PDF de forma quirúrgica, preservando la estética original y minimizando el impacto en el contenido circundante.

## ✨ Características Principales

-   **Detección Multicapa Inteligente:**
    -   **Texto:** Identifica "NotebookLM" como texto nativo.
    -   **Vectores:** Detecta letras trazadas como curvas (útil para PDFs exportados desde otras herramientas).
    -   **Escaneo Visual de Píxeles:** Si falla lo anterior, escanea la esquina para encontrar el área mínima exacta.
-   **Ajuste Adaptativo:** El parche de borrado ya no es fijo; se adapta al tamaño real de la marca de agua encontrada.
-   **Color Dominante (Smart Fill):** Analiza estadísticamente el margen de la página para encontrar el color de fondo exacto, ignorando letras o líneas cercanas.
-   **Procesamiento por Lotes:** Procesa una carpeta entera de PDFs con un solo comando.
-   **Interfaz Moderna:** Incluye barra de progreso visual (`tqdm`).
-   **Modo Preview:** Prueba la configuración en la primera página antes de procesar archivos grandes.

## 🛠 Instalación

1.  **Limpiar entorno previo (si es necesario):**
    ```bash
    rm -rf venv
    ```

2.  **Configurar entorno nuevo:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Uso

### Básico (Un solo archivo)
```bash
python remover.py presentacion.pdf
```
*Genera:* `presentacion_cleaned.pdf`

### Procesar una carpeta completa
```bash
python remover.py ./carpeta_de_pdfs/
```

### Modo Preview (Verificar resultados rápido)
Procesa solo la primera página para que puedas ver cómo queda el parche:
```bash
python remover.py archivo.pdf --preview
```

### Forzar un color específico
Si el fondo es muy complejo y la detección automática no te convence:
```bash
python remover.py archivo.pdf --color "#FFFFFF"
```

## 📂 Estructura del Proyecto

- `remover.py`: El cerebro del proyecto.
- `requirements.txt`: Dependencias (`PyMuPDF`, `tqdm`).
- `LICENSE`: Licencia MIT.

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Si tienes una idea para mejorar la detección en fondos degradados o quieres añadir soporte para otros tipos de marcas de agua, abre un Pull Request.

---
Hecho con ❤️ para mejorar tus presentaciones.
