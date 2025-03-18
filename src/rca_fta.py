import networkx as nx
import tkinter as tk
import matplotlib.pyplot as plt
from tkinter import messagebox

def build_tree_base(simulator, connections, is_fta=True):
    """
    Базовая функция для отрисовки деревьев FTA и RCA.

    :param connections: Кортеж соединений типа (начальная_точка, конечная_точка)
    :param is_fta: True для FTA, False для RCA

    :returns:
        G: Граф NetworkX;
        pos: Координаты расположения для всех узлов графа;
        node_colors: Информация о цвете для каждого узла;
        node_sizes: Информация о размере для каждого узла;
    """
    G = nx.DiGraph()

    for start, end in connections:
        G.add_edge(start, end)

    if is_fta:
        root_nodes = [node for node in G.nodes() if G.in_degree(node) == 0]

        if not root_nodes:
            messagebox.showinfo("Информация", "Не найдены корневые узлы для построения дерева отказов")
            return None, None, None, None

        system_node = "System"
        for root in root_nodes:
            G.add_edge(system_node, root)

        start_nodes = [system_node]
        initial_level = 0
    else:
        leaf_nodes = [node for node in G.nodes() if G.out_degree(node) == 0]

        system_node = None
        root_nodes = []

        vlk_nodes = {}
        non_leaf_nodes = [node for node in G.nodes() if node not in leaf_nodes]

        for node in non_leaf_nodes:
            node_obj = simulator.get_node_by_point(node)
            if node_obj:
                vlk_name = f"ВЛК_{node_obj.typeid}"
                vlk_nodes[vlk_name] = node

                G.add_node(vlk_name)
                G.add_edge(node, vlk_name)

        start_nodes = list(G.nodes())
        initial_level = 0

    levels = {}

    if is_fta:
        queue = [(system_node, initial_level)]
        visited = {system_node}

        while queue:
            node, level = queue.pop(0)
            levels[node] = level

            for successor in G.successors(node):
                if successor not in visited:
                    visited.add(successor)
                    queue.append((successor, level + 1))
    else:
        for node in G.nodes():
            if node in vlk_nodes.keys():
                parent = vlk_nodes[node]
                if parent in levels:
                    levels[node] = levels[parent] + 1
                else:
                    levels[node] = 0
            else:
                max_distance = 0
                for leaf in leaf_nodes:
                    try:
                        path = nx.shortest_path(G, node, leaf)
                        max_distance = max(max_distance, len(path) - 1)
                    except nx.NetworkXNoPath:
                        pass

                levels[node] = max_distance

    changed = True
    while changed:
        changed = False
        for u, v in G.edges():
            if is_fta:
                if levels[u] >= levels[v]:
                    levels[v] = levels[u] + 1
                    changed = True
            else:
                if levels[u] <= levels[v] and v not in vlk_nodes:
                    levels[u] = levels[v] + 1
                    changed = True

    if not is_fta:
        max_level = max(levels.values()) if levels else 0
        for node in levels:
            levels[node] = max_level - levels[node]

        for vlk_name, parent in vlk_nodes.items():
            levels[vlk_name] = levels[parent] + 1

    nodes_by_level = {}
    for node, level in levels.items():
        if level not in nodes_by_level:
            nodes_by_level[level] = []
        nodes_by_level[level].append(node)

    pos = {}
    max_level = max(levels.values()) if levels else 0

    for level in range(max_level + 1):
        nodes = nodes_by_level.get(level, [])

        if not is_fta and 'vlk_nodes' in locals():
            vlk_nodes_at_level = [n for n in nodes if n in vlk_nodes.keys()]
            regular_nodes = [n for n in nodes if n not in vlk_nodes.keys()]

            n_regular = len(regular_nodes)
            for i, node in enumerate(regular_nodes):
                x_pos = (i - (n_regular - 1) / 2) * 3
                pos[node] = (x_pos, -level * 2)

            for vlk_name in vlk_nodes_at_level:
                parent = vlk_nodes[vlk_name]
                parent_pos = pos.get(parent)
                if parent_pos:
                    pos[vlk_name] = (parent_pos[0] + 0.8, -level * 2)
        else:
            n_nodes = len(nodes)

            if level > 0 and n_nodes > 1:
                def get_parent_avg_x(node):
                    parents = [p for p in G.predecessors(node) if p in pos]
                    if parents:
                        return sum(pos[p][0] for p in parents) / len(parents)
                    return 0

                nodes.sort(key=get_parent_avg_x)

            for i, node in enumerate(nodes):
                x_pos = (i - (n_nodes - 1) / 2) * 3
                pos[node] = (x_pos, -level * 2)

    node_colors = []
    node_sizes = []

    for node in G.nodes():
        if is_fta:
            if node == system_node:
                node_colors.append('lightgreen')
                node_sizes.append(3000)
            elif node in root_nodes:
                node_colors.append('lightcoral')
                node_sizes.append(2000)
            else:
                node_colors.append('lightblue')
                node_sizes.append(2000)
        else:  # RCA
            if 'vlk_nodes' in locals() and node in vlk_nodes.keys():
                node_colors.append('lightyellow')
                node_sizes.append(1500)
            elif node in leaf_nodes:
                node_colors.append('lightgreen')
                node_sizes.append(2000)
            else:
                node_colors.append('lightblue')
                node_sizes.append(2000)

    return G, pos, node_colors, node_sizes


def build_fault_tree(simulator):
    """
    Строит дерево отказов FTA на основе текущей схемы сопряжения.
    """
    connections = simulator.get_internal_connections()
    G, pos, node_colors, node_sizes = build_tree_base(simulator=simulator, connections=connections, is_fta=True)

    if G is None:
        return

    plt.figure(figsize=(16, 12))

    nx.draw_networkx_edges(G, pos=pos,
                           arrows=True,
                           arrowstyle='-|>',
                           arrowsize=10,
                           width=2,
                           edge_color='black')

    nx.draw_networkx_nodes(G, pos=pos,
                           node_color=node_colors,
                           node_size=node_sizes)

    nx.draw_networkx_labels(G, pos=pos,
                            font_size=10,
                            font_weight='bold')

    plt.axis('off')

    tree_window = tk.Toplevel(simulator.root)
    tree_window.title("Дерево отказов FTA")
    tree_window.geometry("1200x900")

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    canvas = FigureCanvasTkAgg(plt.gcf(), master=tree_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
    toolbar = NavigationToolbar2Tk(canvas, tree_window)
    toolbar.update()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def build_rca_tree(simulator):
    """
    Строит дерево анализа коренных причин RCA на основе текущей схемы сопряжения.
    """
    connections = simulator.get_internal_connections()
    G, pos, node_colors, node_sizes = build_tree_base(simulator=simulator, connections=connections, is_fta=False)

    if G is None:
        return

    plt.figure(figsize=(16, 12))

    nx.draw_networkx_edges(G, pos=pos,
                           arrows=True,
                           arrowstyle='-|>',
                           arrowsize=10,
                           width=2,
                           edge_color='black')

    nx.draw_networkx_nodes(G, pos=pos,
                           node_color=node_colors,
                           node_size=node_sizes)

    nx.draw_networkx_labels(G, pos=pos,
                            font_size=10,
                            font_weight='bold')

    plt.axis('off')

    tree_window = tk.Toplevel(simulator.root)
    tree_window.title("Дерево анализа коренных причин RCA")
    tree_window.geometry("1200x900")

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    canvas = FigureCanvasTkAgg(plt.gcf(), master=tree_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
    toolbar = NavigationToolbar2Tk(canvas, tree_window)
    toolbar.update()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)