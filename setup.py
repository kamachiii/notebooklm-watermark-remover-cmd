from setuptools import setup

setup(
    name="notebook-remover",
    version="0.1.0",
    py_modules=["remover"],
    install_requires=[
        "pymupdf>=1.20.0",
        "tqdm>=4.65.0",
        "Pillow>=10.0.0",
        "opencv-python-headless>=4.8.0",
        "numpy>=1.24.0",
        "python-pptx>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "notebook-remover=remover:main",
        ],
    },
)
