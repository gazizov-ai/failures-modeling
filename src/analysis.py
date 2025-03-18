import tkinter as tk
import numpy as np
import pandas as pd
from tkinter import ttk

def show_adjacency_matrix(simulator):
    """
    Отображает матрицу смежности для текущей схемы сопряжения.
    Создает новое окно с визуализацией связей между точками.
    """

    internal_connections = simulator.get_internal_connections()

    all_points = set()
    for start, end in internal_connections:
        all_points.add(start)
        all_points.add(end)

    point_labels = sorted(list(all_points))
    size = len(point_labels)

    matrix = np.zeros((size, size))

    for start, end in internal_connections:
        from_idx = point_labels.index(start)
        to_idx = point_labels.index(end)
        matrix[from_idx][to_idx] = 1

    matrix = matrix.T

    df = pd.DataFrame(matrix,
                      index=point_labels,
                      columns=point_labels)

    matrix_window = tk.Toplevel(simulator.root)
    matrix_window.title("Матрица смежности")

    frame = ttk.Frame(matrix_window)
    frame.pack(expand=True, fill='both', padx=5, pady=5)

    for j, label in enumerate(point_labels, start=1):
        cell = tk.Label(frame, text=label, borderwidth=1, relief="solid",
                        width=6, height=2, bg='lightgray')
        cell.grid(row=0, column=j, sticky='nsew')

    for i, row_label in enumerate(point_labels, start=1):
        row_header = tk.Label(frame, text=row_label, borderwidth=1, relief="solid",
                              width=6, height=2, bg='lightgray')
        row_header.grid(row=i, column=0, sticky='nsew')

        for j, col_label in enumerate(point_labels, start=1):
            value = df.iloc[i - 1, j - 1]
            bg_color = '#90EE90' if value == 1 else '#FFB6C1'
            cell = tk.Label(frame, borderwidth=1, relief="solid",
                            width=6, height=2, bg=bg_color,
                            highlightbackground='#D3D3D3', highlightthickness=1)
            cell.grid(row=i, column=j, sticky='nsew')

    for i in range(len(point_labels) + 1):
        frame.grid_columnconfigure(i, weight=1)
        frame.grid_rowconfigure(i, weight=1)

    canvas = tk.Canvas(matrix_window)

    canvas.pack(side='left', fill='both', expand=True)
    
def build_analysis_table(simulator):
    """
    Создает таблицу анализа схемы с метриками I1, I2 и степенью центральности для каждой точки.
    TODO: исправить логику поиска вершин, некорректно ищет для i1 i2
    """
    internal_connections = simulator.get_internal_connections()

    all_points = set()
    for start, end in internal_connections:
        all_points.add(start)
        all_points.add(end)

    point_labels = sorted(list(all_points))
    size = len(point_labels)
    print(point_labels)

    adjacency_matrix = np.zeros((size, size), dtype=int)

    output_points = []
    in_points = []

    all_items = simulator.canvas.find_all()
    for item in all_items:
        tags = simulator.canvas.gettags(item)
        for tag in tags:
            if tag.startswith('in_') and not tag.endswith('text'):
                _, id = tag.split('_')
                in_points.append(id)

    for point_id in in_points:
        node = simulator.get_node_by_point(point_id)

        if node and node.type == "output":
            point_text = simulator.get_point_text(point_id, 'in')
            output_points.append(point_text)

    metrics = []

    #TODO: тут все ломается, перепроверить
    for i, point in enumerate(point_labels):
        node = simulator.get_node_by_point(point)

        reachable_outputs = 0

        current_matrix = adjacency_matrix.copy()
        reachable = np.zeros(size, dtype=int)

        for power in range(1, size + 1):
            reachable = reachable | (current_matrix[i] > 0)
            current_matrix = np.matmul(current_matrix, adjacency_matrix)

        for j, point_j in enumerate(point_labels):
            if reachable[j] and point_j in output_points:
                reachable_outputs += 1

        reachable_nodes = set()
        current_node_id = node.id if node else -1

        for j, point_j in enumerate(point_labels):
            if reachable[j]:
                target_node = simulator.get_node_by_point(point_j)
                if target_node and target_node.id > current_node_id:
                    reachable_nodes.add(target_node.id)

        centrality = 0

        metrics.append({
            'point': point,
            'I1': reachable_outputs,
            'I2': len(reachable_nodes),
            'centrality': centrality
        })

    table_window = tk.Toplevel(simulator.root)
    table_window.title("Таблица анализа схемы")
    table_window.geometry("600x800")

    frame = tk.Frame(table_window)
    frame.pack(fill=tk.BOTH, expand=True)

    vsb = tk.Scrollbar(frame, orient="vertical")
    hsb = tk.Scrollbar(frame, orient="horizontal")

    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)

    table = ttk.Treeview(frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    vsb.config(command=table.yview)
    hsb.config(command=table.xview)

    table['columns'] = ('I1', 'I2', 'centrality')

    table.column('#0', width=150, minwidth=100)
    table.column('I1', width=100, minwidth=50, anchor=tk.CENTER)
    table.column('I2', width=100, minwidth=50, anchor=tk.CENTER)
    table.column('centrality', width=150, minwidth=100, anchor=tk.CENTER)

    table.heading('#0', text='Точка', anchor=tk.CENTER)
    table.heading('I1', text='I1', anchor=tk.CENTER)
    table.heading('I2', text='I2', anchor=tk.CENTER)
    table.heading('centrality', text='Степень центральности', anchor=tk.CENTER)

    for metric in metrics:
        table.insert('', tk.END, text=metric['point'],
                     values=(metric['I1'], metric['I2'], metric['centrality']))

    table.pack(fill=tk.BOTH, expand=True)