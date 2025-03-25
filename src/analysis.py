import tkinter as tk
import numpy as np
import pandas as pd
from tkinter import ttk

def build_adjacency_matrix(simulator):
    internal_connections = simulator.get_internal_connections()

    all_points = set()
    for start, end in internal_connections:
        all_points.add(start)
        all_points.add(end)

    point_labels = sorted(list(all_points))

    simulator.point_labels = point_labels

    size = len(point_labels)

    matrix = np.zeros((size, size))

    for start, end in internal_connections:
        from_idx = point_labels.index(start)
        to_idx = point_labels.index(end)
        matrix[from_idx][to_idx] = 1

    matrix = matrix.T

    simulator.adjacency_matrix = matrix

    return matrix

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

    matrix = build_adjacency_matrix(simulator)

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
    build_adjacency_matrix(simulator)

    point_labels = simulator.point_labels
    size = len(point_labels)

    output_points = []
    for item in simulator.canvas.find_all():
        tags = simulator.canvas.gettags(item)
        for tag in tags:
            if tag.startswith('in_') and not tag.endswith('text'):
                _, point_id = tag.split('_')
                node = simulator.get_node_by_point(point_id)
                if node and node.type == "output":
                    output_points.append(simulator.get_point_text(point_id, 'in'))

    print(output_points)

    output_indices = [point_labels.index(point) for point in output_points if point in point_labels]

    metrics = []
    for i, point in enumerate(point_labels):
        reachable = np.zeros(size, dtype=int)
        current_matrix = simulator.adjacency_matrix.copy()

        for power in range(1, size + 1):
            reachable = reachable | (current_matrix[i] > 0)
            current_matrix = np.matmul(current_matrix, simulator.adjacency_matrix)

        i1_value = sum(1 for j in output_indices if reachable[j])

        i2_value = np.sum(reachable)

        outgoing_connections = np.sum(simulator.adjacency_matrix[i] > 0)

        transposed_matrix = simulator.adjacency_matrix.T
        incoming_connections = np.sum(transposed_matrix[i] > 0)

        centrality = outgoing_connections + incoming_connections

        metrics.append({
            'point': point,
            'I1': i1_value,
            'I2': i2_value,
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