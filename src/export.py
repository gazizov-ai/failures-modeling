import os
import shutil
import sys

def export_py_to_txt(source_dir, output_dir):
    """
    Утилита для экспорта исходников в txt
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    py_files = [f for f in os.listdir(source_dir) if (f.endswith('.py') and not(f.startswith('export')))]
    
    if not py_files:
        print(f"No .py files found in {source_dir}")
        return

    for py_file in py_files:
        source_path = os.path.join(source_dir, py_file)
        txt_file = os.path.splitext(py_file)[0] + '.txt'
        output_path = os.path.join(output_dir, txt_file)
        
        shutil.copy2(source_path, output_path)
        print(f"Exported: {py_file} -> {txt_file}")

if __name__ == "__main__":
    source_dir = "src"
    output_dir = "src"

    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    export_py_to_txt(source_dir, output_dir)
    print("Экспорт завершен")
