import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage, filedialog
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import sys
import csv


class Node:
    input_nodes = 0
    output_nodes = 0
    aggregate_nodes = 0
    def __init__(self, node_type, node_id):
        self.type = node_type
        self.id = node_id
        self.inputs = []
        self.outputs = []
        self.x = 0
        self.y = 0
        self.deleted = False

        if node_type == 'input':
            Node.input_nodes += 1
            self.typeid = Node.input_nodes
            self.outputs.append(f'0{Node.input_nodes}')
        elif node_type == 'output':
            Node.output_nodes += 1
            self.typeid = Node.output_nodes
            self.inputs.append(f'{Node.output_nodes}')
        elif node_type == 'aggregate':
            Node.aggregate_nodes += 1
            self.typeid = Node.aggregate_nodes
            for i in range(6):
                self.inputs.append(f'{Node.aggregate_nodes}{i + 1}')
                self.outputs.append(f'{Node.aggregate_nodes}{i + 1}')


class FailureSimulator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Структурные модели отказов")

        self.nodes = []
        self.connections = []
        self.failed_points = set()

        self.connection_mode = False
        self.connection_start = None
        self.selected_node = None
        self.selected_point_type = None
        self.drag_data = {"x": 0, "y": 0, "item": None}

        self.failure_mode = False

        self.setup_gui()

    def setup_gui(self):
        # Configure root window to be resizable
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Файл', menu=file_menu)
        file_menu.add_command(label='Новый', command=self.reset_canvas, accelerator="Ctrl+N")

        nodes_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Узлы', menu=nodes_menu)

        add_menu = tk.Menu(nodes_menu, tearoff=0)
        nodes_menu.add_cascade(label='Добавить...', menu=add_menu)
        add_menu.add_command(label='Входной узел', command=self.add_input_node, accelerator="Ctrl+Q")
        add_menu.add_command(label='Агрегат', command=self.add_aggregate, accelerator="Ctrl+W")
        add_menu.add_command(label='Выходной узел', command=self.add_output_node, accelerator="Ctrl+E")
        nodes_menu.add_command(label='Удалить', command=self.set_delete_mode, accelerator="Ctrl+D")

        fail_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Моделирование отказов', menu=fail_menu)
        fail_menu.add_command(label='Добавить отказ на узле', command=self.set_failure, accelerator="Ctrl+F")
        fail_menu.add_command(label='Сбросить отказы', command=self.reset_failures, accelerator="Ctrl+R")

        graph_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Графы', menu=graph_menu)
        graph_menu.add_command(label='Матрица смежности', command=self.show_adjacency_matrix)
        graph_menu.add_command(label='Меры важности узлов', command=self.build_analysis_table)
        graph_menu.add_command(label='Дерево отказов FTA', command=self.build_fault_tree)
        graph_menu.add_command(label='Дерево анализа коренных причин RCA', command=self.build_rca_tree)

        self.canvas = tk.Canvas(self.root, bg='#DDDDDD', bd=1, relief='solid')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.canvas_click)
        # self.canvas.bind("<Button-3>", self.delete_node)
        self.canvas.bind("<Button-3>", self.exit_modes)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.drag_stop)

        # Existing English bindings
        self.root.bind("<Control-q>", lambda e: self.add_input_node())
        self.root.bind("<Control-w>", lambda e: self.add_aggregate())
        self.root.bind("<Control-e>", lambda e: self.add_output_node())
        self.root.bind("<Control-f>", lambda e: self.set_failure())
        self.root.bind("<Control-r>", lambda e: self.reset_failures())
        self.root.bind("<Control-n>", lambda e: self.reset_canvas())
        self.root.bind("<Control-d>", lambda e: self.set_delete_mode())

        self.root.bind("<Control-Q>", lambda e: self.add_input_node())
        self.root.bind("<Control-W>", lambda e: self.add_aggregate())
        self.root.bind("<Control-E>", lambda e: self.add_output_node())
        self.root.bind("<Control-F>", lambda e: self.set_failure())
        self.root.bind("<Control-R>", lambda e: self.reset_failures())
        self.root.bind("<Control-N>", lambda e: self.reset_canvas())
        self.root.bind("<Control-D>", lambda e: self.set_delete_mode())


    def on_closing(self):
        """Обработчик закрытия главного окна приложения"""
        if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
            # Завершаем работу приложения
            self.root.destroy()
            sys.exit(0)


    def create_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]

        return canvas.create_polygon(points, smooth=True, **kwargs)

    def draw_node(self, node):
        last_x = 100
        last_y = 300  # Default y position
        for existing_node in self.nodes[:-1]:  # Exclude current node
            if existing_node.type == node.type and existing_node.typeid < node.typeid:
                last_y = existing_node.y + 150
                last_x = existing_node.x
        if self.nodes[-1].type == 'input' and Node.input_nodes == 1:
            last_x = 100
        if self.nodes[-1].type == 'aggregate' and Node.aggregate_nodes == 1:
            last_x = 350
        if self.nodes[-1].type == 'output' and Node.output_nodes == 1:
            last_x = 600
        x = last_x
        y = last_y
        node.x = x
        node.y = y

        body_color = '#333333'
        header_color = '#555555'
        outline_color = '#999999'

        if node.type == 'input':
            self.create_rounded_rectangle(self.canvas, x - 40, y - 30, x + 40, y + 30,
                                          radius=10, fill=body_color, outline=outline_color,
                                          width=2, tags=f'node_{node.id}')
            self.create_rounded_rectangle(self.canvas, x - 40, y - 30, x + 40, y - 15,
                                          radius=10, fill=header_color, outline=outline_color,
                                          width=2, tags=f'node_{node.id}')
            self.canvas.create_text(x, y - 22, text=f'Вход {Node.input_nodes}',
                                    fill='white', tags=f'node_{node.id}')

            # Output point with black index
            out_id = f"0{node.typeid}"
            self.canvas.create_oval(x + 35, y - 5, x + 45, y + 5,
                                    tags=[f'out_{out_id}', f'point_of_{node.id}'], fill='red')
            self.canvas.create_text(x + 48, y - 10, text=out_id,
                                    fill='black', font=('Arial', 10), tags=f'out_{out_id}_text')

        elif node.type == 'output':
            self.create_rounded_rectangle(self.canvas, x - 40, y - 30, x + 40, y + 30,
                                          radius=10, fill=body_color, outline=outline_color,
                                          width=2, tags=f'node_{node.id}')
            self.create_rounded_rectangle(self.canvas, x - 40, y - 30, x + 40, y - 15,
                                          radius=10, fill=header_color, outline=outline_color,
                                          width=2, tags=f'node_{node.id}')
            self.canvas.create_text(x, y - 22, text=f'Выход {Node.output_nodes}',
                                    fill='white', tags=f'node_{node.id}')

            # Input point
            in_id = f"{node.typeid}0"
            self.canvas.create_oval(x - 45, y - 5, x - 35, y + 5,
                                    tags=[f'in_{in_id}', f'point_of_{node.id}'], fill='green')

        else:  # Aggregate
            self.create_rounded_rectangle(self.canvas, x - 40, y - 60, x + 40, y + 60,
                                          radius=10, fill=body_color, outline=outline_color,
                                          width=2, tags=f'node_{node.id}')
            self.create_rounded_rectangle(self.canvas, x - 40, y - 60, x + 40, y - 45,
                                          radius=10, fill=header_color, outline=outline_color,
                                          width=2, tags=f'node_{node.id}')
            self.canvas.create_text(x, y - 52, text=f'Агрегат {Node.aggregate_nodes}',
                                    fill='white', tags=f'node_{node.id}')

            for i in range(6):
                y_offset = -40 + i * 15
                in_id = f"{node.typeid}{i + 7}"
                out_id = f"{node.typeid}{i + 1}"

                # Input point
                self.canvas.create_oval(x - 45, y + y_offset - 5, x - 35, y + y_offset + 5,
                                        tags=[f'in_{in_id}', f'point_of_{node.id}'], fill='green')

                self.canvas.create_oval(x + 35, y + y_offset - 5, x + 45, y + y_offset + 5,
                                        tags=[f'out_{out_id}', f'point_of_{node.id}'], fill='red')
                self.canvas.create_text(x + 50, y + y_offset, text=out_id,
                                        fill='black', font=('Arial', 10), tags=f'out_{out_id}_text')

    def draw_connection(self, start_coords, end_coords, smooth, tags):
        # Calculate control points for the curve
        ctrl_x1 = start_coords[0] + (end_coords[0] - start_coords[0]) * 0.4
        ctrl_x2 = start_coords[0] + (end_coords[0] - start_coords[0]) * 0.6

        if smooth:
            # Create curved line using cubic Bezier curve
            curve_points = [
                start_coords[0], start_coords[1],
                ctrl_x1, start_coords[1],
                ctrl_x2, end_coords[1],
                end_coords[0], end_coords[1]
            ]
            return self.canvas.create_line(curve_points, smooth=True, splinesteps=32,
                                           width=3, fill='orange', tags=tags)
        else:
            return self.canvas.create_line(start_coords[0], start_coords[1],
                                           end_coords[0], end_coords[1],
                                           width=3, fill='orange', tags=tags)

    def canvas_click(self, event):
        clicked_items = self.canvas.find_closest(event.x, event.y)
        if not clicked_items:
            return

        tags = self.canvas.gettags(clicked_items[0])
        print(tags)
        if not tags:
            return

        for tag in tags:
            if (tag.startswith('out_') or tag.startswith('in_')) and not tag.endswith('_text'):
                point_id = tag[4:] if tag.startswith('out_') else tag[3:]
                point_type = 'out' if tag.startswith('out_') else 'in'
                clicked_node = self.get_node_by_point(point_id)

                # Handle clicks inside aggregate
                if clicked_node and clicked_node.type == 'aggregate':
                    if not self.connection_mode:
                        self.selected_node = clicked_node
                        self.selected_point_type = point_type
                        self.start_connection(point_id)
                    else:
                        if not (point_type == self.selected_point_type):
                            if self.selected_node == clicked_node:
                                self.create_new_connection(point_id, self.connection_start,
                                                           swap=False if point_type=='in' else True,
                                                           internal=True)
                            else:
                                self.create_new_connection(point_id, self.connection_start,
                                                           swap=False if point_type == 'in' else True)
                        self.stop_connection()
                    return

                if not self.connection_mode:
                    self.selected_point_type = point_type
                    self.start_connection(point_id)
                else:
                    if not (point_type==self.selected_point_type):
                        self.create_new_connection(point_id, self.connection_start,
                                                   swap=False if point_type=='in' else True)
                    self.stop_connection()
                return

        self.drag_start(event)

    def create_new_connection(self, point1, point2, swap=False, internal=False):
        in_point = point2 if swap else point1
        out_point = point1 if swap else point2
        if internal:
            self.connections.append((out_point, in_point))
            start_item = self.canvas.find_withtag(f'out_{out_point}')[0]
            end_item = self.canvas.find_withtag(f'in_{in_point}')[0]

            start_coords = self.canvas.coords(start_item)
            end_coords = self.canvas.coords(end_item)

            start_x = (start_coords[0] + start_coords[2]) / 2
            start_y = (start_coords[1] + start_coords[3]) / 2
            end_x = (end_coords[0] + end_coords[2]) / 2
            end_y = (end_coords[1] + end_coords[3]) / 2

            # Create line using the center points
            line_coords = [start_x, start_y, end_x, end_y]
            self.canvas.create_line(line_coords, fill='orange', width=2,
                                    tags=f'internal_conn_in_{self.get_node_by_point(point1).id}_{out_point}_{in_point}')
            return

        if not self.parse_connection_tags(in_point):
            self.connections.append((out_point, in_point))
            print(self.connections)

            start_item = self.canvas.find_withtag(f'out_{out_point}')[0]
            end_item = self.canvas.find_withtag(f'in_{in_point}')[0]
            start_coords = self.canvas.coords(start_item)
            end_coords = self.canvas.coords(end_item)

            start_x = (start_coords[0] + start_coords[2]) / 2
            start_y = (start_coords[1] + start_coords[3]) / 2
            end_x = (end_coords[0] + end_coords[2]) / 2
            end_y = (end_coords[1] + end_coords[3]) / 2

            self.draw_connection([start_x, start_y], [end_x, end_y], True,
                                 f'conn_{out_point}_{in_point}')

            # Create text for input point with output point's index
            input_coords = self.canvas.coords(end_item)
            text_x = input_coords[0] - 10
            text_y = (input_coords[1] + input_coords[3]) / 2
            self.canvas.create_text(text_x, text_y, text=out_point,
                                    fill='black', font=('Arial', 10), tags=f'in_{in_point}_text')

    def get_node_by_point(self, point_id):
        point_items = self.canvas.find_withtag(f'out_{point_id}') or self.canvas.find_withtag(f'in_{point_id}')
        if point_items:
            point_tags = self.canvas.gettags(point_items[0])
            for tag in point_tags:
                if tag.startswith('point_of_'):
                    node_id = int(tag.split('_')[-1])
                    node = self.nodes[node_id]
                    if not node.deleted:  # Skip deleted nodes
                        return node
        return None


    def get_point_text(self, point_id, point_type):
        """
        Get text of any point (input or output)
        point_id: ID of the point
        point_type: 'in' or 'out'
        """
        text_items = self.canvas.find_withtag(f'{point_type}_{point_id}_text')
        if text_items:
            return self.canvas.itemcget(text_items[0], 'text')
        return None

    def parse_connection_tags(self, point_id):
        """
        Parses connection tags to check if point is connected
        Returns True if point is found in any connection tag
        """
        all_items = self.canvas.find_all()
        for item in all_items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith('conn_'):
                    # Parse both points from connection tag (format: 'conn_out_in')
                    _, start, end = tag.split('_')
                    if point_id == start or point_id == end:
                        return True
        return False

    def set_delete_mode(self):
        self.delete_mode = True
        self.root.config(cursor="X_cursor")
        self.canvas.bind('<Button-1>', self.handle_delete_click)

    def handle_delete_click(self, event):
        if not self.delete_mode:
            return

        # Reset all failures first
        self.reset_failures()

        clicked_items = self.canvas.find_closest(event.x, event.y)
        if not clicked_items:
            return

        tags = self.canvas.gettags(clicked_items[0])

        # Handle node deletion
        for tag in tags:
            if tag.startswith('node_'):
                node_id = int(tag.split('_')[1])
                node = self.nodes[node_id]
                node.deleted = True

                # Remove all connections related to this node
                connections_to_remove = []
                for conn in self.connections:
                    start, end = conn
                    if (any(start == out for out in node.outputs) or
                            any(end == inp for inp in node.inputs)):
                        self.canvas.delete(f'conn_{start}_{end}')
                        self.canvas.delete(f'internal_conn_in_{node_id}_{start}_{end}')
                        self.canvas.delete(f'text_in_{end}')
                        connections_to_remove.append(conn)

                # Remove connections from list
                for conn in connections_to_remove:
                    self.connections.remove(conn)

                # Delete node visuals
                self.canvas.delete(f'node_{node.id}')

                if node.type == 'input':
                    out_id = f"0{node.typeid}"
                    self.canvas.delete(f'out_{out_id}')
                    self.canvas.delete(f'out_{out_id}_text')
                    Node.input_nodes -= 1

                elif node.type == 'output':
                    in_id = f"{node.typeid}0"
                    self.canvas.delete(f'in_{in_id}')
                    self.canvas.delete(f'in_{in_id}_text')
                    Node.output_nodes -= 1

                elif node.type == 'aggregate':
                    for i in range(6):
                        out_id = f"{node.typeid}{i + 1}"
                        self.canvas.delete(f'out_{out_id}')
                        self.canvas.delete(f'out_{out_id}_text')

                    for i in range(6):
                        in_id = f"{node.typeid}{i + 7}"
                        self.canvas.delete(f'in_{in_id}')
                        self.canvas.delete(f'in_{in_id}_text')
                        for conn in self.connections[:]:
                            if conn[1] == in_id:
                                self.canvas.delete(f'conn_{conn[0]}_{in_id}')
                                self.connections.remove(conn)
                    Node.aggregate_nodes -= 1
                return

        # Handle connection deletion
        for tag in tags:
            if tag.startswith('conn_'):
                _, start, end = tag.split('_')
                self.canvas.delete(f'conn_{start}_{end}')
                self.canvas.delete(f'text_in_{end}')
                self.connections.remove((start, end))
                return
            if tag.startswith('internal_conn_in_'):
                # Parse connection info from tag
                _, _, _, node_id, start, end = tag.split('_')
                # Delete the connection line
                self.canvas.delete(tag)
                # Remove from connections list
                if (start, end) in self.connections:
                    self.connections.remove((start, end))
                return


    def start_connection(self, point):
        self.connection_mode = True
        self.connection_start = point
        self.root.config(cursor="cross")


    def stop_connection(self):
        self.connection_mode = False
        self.connection_start = None
        self.selected_node = None
        self.root.config(cursor="")


    def exit_modes(self, event):
        if self.failure_mode:
            self.failure_mode = False
            self.canvas.bind('<Button-1>', self.canvas_click)
            self.root.config(cursor="")

        if self.connection_mode:
            self.stop_connection()

        if self.delete_mode:
            self.delete_mode = False
            self.canvas.bind('<Button-1>', self.canvas_click)
            self.root.config(cursor="")


    def drag_start(self, event):
        clicked_items = self.canvas.find_closest(event.x, event.y)
        if not clicked_items:
            return

        tags = self.canvas.gettags(clicked_items[0])
        for tag in tags:
            if tag.startswith('node_'):
                self.drag_data["item"] = int(tag.split('_')[1])
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
                return

    def update_connections(self, node):
        for conn in self.connections:
            start_point, end_point = conn

            if node.type == 'input':
                input_point = f'0{node.typeid}'
                should_update = (start_point == input_point or end_point == input_point)
            else:
                should_update = (any(start_point == f"{node.typeid}{i}" for i in range(15)) or
                                 any(end_point == f"{node.typeid}{i}" for i in range(15)))

            # Check if this connection involves the moved node
            if should_update:
                in_agg = self.get_node_by_point(start_point) != self.get_node_by_point(end_point)

                # Store if connection was failed before deletion
                old_conn_tag = f'conn_{start_point}_{end_point}'
                old_internal_tag = f'internal_conn_in_{self.get_node_by_point(start_point).id}_{start_point}_{end_point}'

                was_failed = False
                if in_agg:
                    old_items = self.canvas.find_withtag(old_conn_tag)
                else:
                    old_items = self.canvas.find_withtag(old_internal_tag)

                if old_items:
                    was_failed = 'failed' in self.canvas.gettags(old_items[0])

                # Delete old connection
                if in_agg:
                    self.canvas.delete(old_conn_tag)
                else:
                    self.canvas.delete(old_internal_tag)

                # Create new connection line at updated position
                start_item = self.canvas.find_withtag(f'out_{start_point}')[0]
                end_item = self.canvas.find_withtag(f'in_{end_point}')[0]

                start_coords = self.canvas.coords(start_item)
                end_coords = self.canvas.coords(end_item)

                start_x = (start_coords[0] + start_coords[2]) / 2
                start_y = (start_coords[1] + start_coords[3]) / 2
                end_x = (end_coords[0] + end_coords[2]) / 2
                end_y = (end_coords[1] + end_coords[3]) / 2

                new_conn = self.draw_connection(
                    [start_x, start_y],
                    [end_x, end_y],
                    in_agg,
                    tags=f'conn_{start_point}_{end_point}' if in_agg else
                    f'internal_conn_in_{self.get_node_by_point(start_point).id}_{start_point}_{end_point}'
                )

                # Restore failed state if it was failed before
                if was_failed:
                    self.canvas.addtag_withtag('failed', new_conn)
                    self.canvas.itemconfig(new_conn, fill='red', width=2)

    def drag(self, event):
        if self.connection_mode or self.drag_data["item"] is None:
            return

        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]

        node = self.nodes[self.drag_data["item"]]

        # Move the node body
        for item in self.canvas.find_withtag(f'node_{node.id}'):
            self.canvas.move(item, dx, dy)

        # Move input points based on node type
        if node.type == 'output':
            in_id = f"{node.typeid}0"
            for item in self.canvas.find_withtag(f'in_{in_id}'):
                self.canvas.move(item, dx, dy)
            for item in self.canvas.find_withtag(f'in_{in_id}_text'):
                self.canvas.move(item, dx, dy)
        elif node.type == 'aggregate':
            for i in range(6):
                in_id = f"{node.typeid}{i + 7}"
                for item in self.canvas.find_withtag(f'in_{in_id}'):
                    self.canvas.move(item, dx, dy)
                for item in self.canvas.find_withtag(f'in_{in_id}_text'):
                    self.canvas.move(item, dx, dy)

        # Move output points based on node type
        if node.type == 'input':
            out_id = f"0{node.typeid}"  # Correct format for input node output point
            for item in self.canvas.find_withtag(f'out_{out_id}'):
                self.canvas.move(item, dx, dy)
            for item in self.canvas.find_withtag(f'out_{out_id}_text'):
                self.canvas.move(item, dx, dy)
        elif node.type == 'aggregate':
            for i in range(6):
                out_id = f"{node.typeid}{i + 1}"  # Correct format for aggregate output points
                for item in self.canvas.find_withtag(f'out_{out_id}'):
                    self.canvas.move(item, dx, dy)
                for item in self.canvas.find_withtag(f'out_{out_id}_text'):
                    self.canvas.move(item, dx, dy)

        # Update connections
        self.update_connections(node)

        # Update drag data
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        node.x += dx
        node.y += dy

    def get_internal_connections(self):
        internal_connections = []
        for item in self.canvas.find_all():
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith('internal_conn_in_'):
                    _, _, _, node_id, start_point, end_point = tag.split('_')
                    start_text = self.get_point_text(start_point, 'out')
                    end_text = self.get_point_text(end_point, 'in')
                    internal_connections.append((start_text, end_text))
        return internal_connections

    def show_adjacency_matrix(self):
        import pandas as pd
        from tkinter import ttk
        import tkinter as tk

        # Find all internal connections
        internal_connections = self.get_internal_connections()

        # Get unique point labels
        all_points = set()
        for start, end in internal_connections:
            all_points.add(start)
            all_points.add(end)

        point_labels = sorted(list(all_points))
        size = len(point_labels)

        # Create matrix using numpy
        matrix = np.zeros((size, size))

        # Fill matrix
        for start, end in internal_connections:
            from_idx = point_labels.index(start)
            to_idx = point_labels.index(end)
            matrix[from_idx][to_idx] = 1

        # Transpose matrix
        matrix = matrix.T

        # Create DataFrame
        df = pd.DataFrame(matrix,
                          index=point_labels,
                          columns=point_labels)

        # Create window
        matrix_window = tk.Toplevel(self.root)
        matrix_window.title("Матрица смежности")

        # Create frame for the matrix
        frame = ttk.Frame(matrix_window)
        frame.pack(expand=True, fill='both', padx=5, pady=5)

        # Create labels for columns
        for j, label in enumerate(point_labels, start=1):
            cell = tk.Label(frame, text=label, borderwidth=1, relief="solid",
                            width=6, height=2, bg='lightgray')
            cell.grid(row=0, column=j, sticky='nsew')

        # Create labels for rows and colored cells
        for i, row_label in enumerate(point_labels, start=1):
            # Row label
            row_header = tk.Label(frame, text=row_label, borderwidth=1, relief="solid",
                                  width=6, height=2, bg='lightgray')
            row_header.grid(row=i, column=0, sticky='nsew')

            # Matrix cells
            for j, col_label in enumerate(point_labels, start=1):
                value = df.iloc[i - 1, j - 1]
                bg_color = '#90EE90' if value == 1 else '#FFB6C1'  # Light green for 1, light red for 0
                cell = tk.Label(frame, borderwidth=1, relief="solid",
                                width=6, height=2, bg=bg_color,
                                highlightbackground='#D3D3D3', highlightthickness=1)
                cell.grid(row=i, column=j, sticky='nsew')

        # Configure grid weights
        for i in range(len(point_labels) + 1):
            frame.grid_columnconfigure(i, weight=1)
            frame.grid_rowconfigure(i, weight=1)

        canvas = tk.Canvas(matrix_window)

        canvas.pack(side='left', fill='both', expand=True)

    def _build_tree_base(self, connections, is_fta=True):
        """
        Common base function for building both FTA and RCA trees.

        Args:
            connections: List of (start, end) connections
            is_fta: True for FTA tree, False for RCA tree

        Returns:
            G: NetworkX graph
            pos: Node positions
            node_colors: Colors for each node
            node_sizes: Sizes for each node
        """
        # Create a directed graph
        G = nx.DiGraph()

        # Add all connections to the graph
        for start, end in connections:
            G.add_edge(start, end)

        if is_fta:
            # For FTA: Find root nodes (nodes with no incoming edges)
            root_nodes = [node for node in G.nodes() if G.in_degree(node) == 0]

            if not root_nodes:
                messagebox.showinfo("Информация", "Не найдены корневые узлы для построения дерева отказов")
                return None, None, None, None

            # Add a "System" super-root node for FTA
            system_node = "System"
            for root in root_nodes:
                G.add_edge(system_node, root)

            # Start BFS from system node
            start_nodes = [system_node]
            initial_level = 0
        else:
            # For RCA: Find leaf nodes (nodes with no outgoing edges)
            leaf_nodes = [node for node in G.nodes() if G.out_degree(node) == 0]

            # For RCA, we don't add a system node
            system_node = None
            root_nodes = []

            # Add VLK nodes for non-leaf nodes in RCA
            vlk_nodes = {}
            non_leaf_nodes = [node for node in G.nodes() if node not in leaf_nodes]

            for node in non_leaf_nodes:
                # Get the node object by point name
                node_obj = self.get_node_by_point(node)
                if node_obj:
                    # Create VLK node
                    vlk_name = f"ВЛК_{node_obj.typeid}"
                    vlk_nodes[vlk_name] = node

                    # Add VLK node to the graph
                    G.add_node(vlk_name)
                    G.add_edge(node, vlk_name)

            # Start from all nodes for level calculation
            start_nodes = list(G.nodes())
            initial_level = 0

        # Determine node levels
        levels = {}

        if is_fta:
            # For FTA: Use BFS from system node
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
            # For RCA: Calculate levels based on distance to leaf nodes
            for node in G.nodes():
                if node in vlk_nodes.keys():
                    # VLK nodes are one level below their parent
                    parent = vlk_nodes[node]
                    if parent in levels:
                        levels[node] = levels[parent] + 1
                    else:
                        # Default level if parent not yet processed
                        levels[node] = 0
                else:
                    # Regular nodes
                    max_distance = 0
                    for leaf in leaf_nodes:
                        try:
                            path = nx.shortest_path(G, node, leaf)
                            max_distance = max(max_distance, len(path) - 1)
                        except nx.NetworkXNoPath:
                            pass

                    levels[node] = max_distance

        # Ensure proper hierarchy (parent above child for FTA, below for RCA)
        changed = True
        while changed:
            changed = False
            for u, v in G.edges():
                if is_fta:
                    # For FTA: parent should be above child
                    if levels[u] >= levels[v]:
                        levels[v] = levels[u] + 1
                        changed = True
                else:
                    # For RCA: parent should be below child (after we reverse)
                    if levels[u] <= levels[v] and v not in vlk_nodes:
                        levels[u] = levels[v] + 1
                        changed = True

        # For RCA, reverse the levels so root causes are at the bottom
        if not is_fta:
            max_level = max(levels.values()) if levels else 0
            for node in levels:
                levels[node] = max_level - levels[node]

            # Ensure VLK nodes are one level below their parents after reversal
            for vlk_name, parent in vlk_nodes.items():
                levels[vlk_name] = levels[parent] + 1

        # Group nodes by level
        nodes_by_level = {}
        for node, level in levels.items():
            if level not in nodes_by_level:
                nodes_by_level[level] = []
            nodes_by_level[level].append(node)

        # Calculate positions for all nodes
        pos = {}
        max_level = max(levels.values()) if levels else 0

        for level in range(max_level + 1):
            nodes = nodes_by_level.get(level, [])

            if not is_fta and 'vlk_nodes' in locals():
                # Separate VLK nodes and regular nodes for RCA
                vlk_nodes_at_level = [n for n in nodes if n in vlk_nodes.keys()]
                regular_nodes = [n for n in nodes if n not in vlk_nodes.keys()]

                # Position regular nodes
                n_regular = len(regular_nodes)
                for i, node in enumerate(regular_nodes):
                    x_pos = (i - (n_regular - 1) / 2) * 3
                    pos[node] = (x_pos, -level * 2)

                # Position VLK nodes near their parents
                for vlk_name in vlk_nodes_at_level:
                    parent = vlk_nodes[vlk_name]
                    parent_pos = pos.get(parent)
                    if parent_pos:
                        pos[vlk_name] = (parent_pos[0] + 0.8, -level * 2)
            else:
                # Standard positioning for FTA or non-VLK nodes
                n_nodes = len(nodes)

                # Sort nodes at each level for more consistent layout
                if level > 0 and n_nodes > 1:
                    def get_parent_avg_x(node):
                        parents = [p for p in G.predecessors(node) if p in pos]
                        if parents:
                            return sum(pos[p][0] for p in parents) / len(parents)
                        return 0

                    nodes.sort(key=get_parent_avg_x)

                # Distribute nodes evenly at this level
                for i, node in enumerate(nodes):
                    x_pos = (i - (n_nodes - 1) / 2) * 3
                    pos[node] = (x_pos, -level * 2)

        # Color nodes based on their type
        node_colors = []
        node_sizes = []

        for node in G.nodes():
            if is_fta:
                if node == system_node:
                    node_colors.append('lightgreen')  # System node in green
                    node_sizes.append(3000)
                elif node in root_nodes:
                    node_colors.append('lightcoral')  # Root nodes in red
                    node_sizes.append(2000)
                else:
                    node_colors.append('lightblue')  # Other nodes in blue
                    node_sizes.append(2000)
            else:  # RCA
                if 'vlk_nodes' in locals() and node in vlk_nodes.keys():
                    node_colors.append('lightyellow')  # VLK nodes in yellow
                    node_sizes.append(1500)
                elif node in leaf_nodes:
                    node_colors.append('lightgreen')  # Leaf nodes in green
                    node_sizes.append(2000)
                else:
                    node_colors.append('lightblue')  # Other nodes in blue
                    node_sizes.append(2000)

        return G, pos, node_colors, node_sizes

    def build_fault_tree(self):
        """Build and display a Fault Tree Analysis (FTA) diagram."""
        connections = self.get_internal_connections()
        G, pos, node_colors, node_sizes = self._build_tree_base(connections, is_fta=True)

        if G is None:
            return  # Error occurred

        # Create a new figure
        plt.figure(figsize=(16, 12))

        # Draw edges with arrows
        nx.draw_networkx_edges(G, pos=pos,
                               arrows=True,
                               arrowstyle='-|>',
                               arrowsize=10,
                               width=2,
                               edge_color='black')

        # Draw nodes
        nx.draw_networkx_nodes(G, pos=pos,
                               node_color=node_colors,
                               node_size=node_sizes)

        # Draw node labels
        nx.draw_networkx_labels(G, pos=pos,
                                font_size=10,
                                font_weight='bold')

        # Turn off axis
        plt.axis('off')

        # Create a new window to display the graph
        tree_window = tk.Toplevel(self.root)
        tree_window.title("Дерево отказов FTA")
        tree_window.geometry("1200x900")

        # Embed the matplotlib figure in the Tkinter window
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(plt.gcf(), master=tree_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add a toolbar
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, tree_window)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def build_rca_tree(self):
        """Build and display a Root Cause Analysis (RCA) diagram."""
        connections = self.get_internal_connections()
        G, pos, node_colors, node_sizes = self._build_tree_base(connections, is_fta=False)

        if G is None:
            return  # Error occurred

        # Create a new figure
        plt.figure(figsize=(16, 12))

        # Draw edges with arrows
        nx.draw_networkx_edges(G, pos=pos,
                               arrows=True,
                               arrowstyle='-|>',
                               arrowsize=10,
                               width=2,
                               edge_color='black')

        # Draw nodes
        nx.draw_networkx_nodes(G, pos=pos,
                               node_color=node_colors,
                               node_size=node_sizes)

        # Draw node labels
        nx.draw_networkx_labels(G, pos=pos,
                                font_size=10,
                                font_weight='bold')

        # Turn off axis
        plt.axis('off')

        # Create a new window to display the graph
        tree_window = tk.Toplevel(self.root)
        tree_window.title("Дерево анализа коренных причин RCA")
        tree_window.geometry("1200x900")

        # Embed the matplotlib figure in the Tkinter window
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(plt.gcf(), master=tree_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add a toolbar
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, tree_window)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def build_analysis_table(self):
        """
        Создает таблицу анализа схемы с метриками I1, I2 и степенью центральности для каждой точки.
        """
        # Получаем все внутренние соединения
        internal_connections = self.get_internal_connections()

        # Получаем уникальные метки точек
        all_points = set()
        for start, end in internal_connections:
            all_points.add(start)
            all_points.add(end)

        point_labels = sorted(list(all_points))
        size = len(point_labels)
        print(point_labels)

        # Создаем матрицу смежности
        adjacency_matrix = np.zeros((size, size), dtype=int)

        # Находим все выходные точки (in-точки на узлах с типом output)
        output_points = []
        in_points = []

        # Получаем все in-точки с канваса
        all_items = self.canvas.find_all()
        for item in all_items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith('in_') and not tag.endswith('text'):
                    _, id = tag.split('_')
                    in_points.append(id)

        for point_id in in_points:
            # Получаем узел, которому принадлежит точка
            node = self.get_node_by_point(point_id)

            # Проверяем, является ли узел выходным
            if node and node.type == "output":
                # Получаем текст точки
                point_text = self.get_point_text(point_id, 'in')
                output_points.append(point_text)

        # Вычисляем метрики для каждой точки
        metrics = []

        for i, point in enumerate(point_labels):
            # Получаем узел, которому принадлежит точка
            node = self.get_node_by_point(point)

            # I1: количество конечных точек, в которые можно попасть из текущей точки
            reachable_outputs = 0

            # Используем матрицу смежности для поиска достижимых точек
            # Возводим матрицу в степени для поиска путей разной длины
            current_matrix = adjacency_matrix.copy()
            reachable = np.zeros(size, dtype=int)

            # Учитываем прямые пути и пути через промежуточные точки
            for power in range(1, size + 1):
                reachable = reachable | (current_matrix[i] > 0)
                current_matrix = np.matmul(current_matrix, adjacency_matrix)

            # Подсчитываем количество достижимых выходных точек
            for j, point_j in enumerate(point_labels):
                if reachable[j] and point_j in output_points:
                    reachable_outputs += 1

            # I2: количество уникальных узлов, в которые можно попасть, двигаясь только в сторону увеличения id
            reachable_nodes = set()
            current_node_id = node.id if node else -1

            for j, point_j in enumerate(point_labels):
                if reachable[j]:
                    target_node = self.get_node_by_point(point_j)
                    if target_node and target_node.id > current_node_id:
                        reachable_nodes.add(target_node.id)

            # Степень центральности: количество internal и conn-соединений, входящих в данную точку
            centrality = 0

            # Добавляем метрики в список
            metrics.append({
                'point': point,
                'I1': reachable_outputs,
                'I2': len(reachable_nodes),
                'centrality': centrality
            })

        # Создаем новое окно для таблицы
        table_window = tk.Toplevel(self.root)
        table_window.title("Таблица анализа схемы")
        table_window.geometry("600x800")

        # Создаем фрейм с прокруткой
        frame = tk.Frame(table_window)
        frame.pack(fill=tk.BOTH, expand=True)

        # Добавляем полосы прокрутки
        vsb = tk.Scrollbar(frame, orient="vertical")
        hsb = tk.Scrollbar(frame, orient="horizontal")

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Создаем таблицу (Treeview)
        table = ttk.Treeview(frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Настраиваем полосы прокрутки
        vsb.config(command=table.yview)
        hsb.config(command=table.xview)

        # Определяем столбцы
        table['columns'] = ('I1', 'I2', 'centrality')

        # Форматируем столбцы
        table.column('#0', width=150, minwidth=100)
        table.column('I1', width=100, minwidth=50, anchor=tk.CENTER)
        table.column('I2', width=100, minwidth=50, anchor=tk.CENTER)
        table.column('centrality', width=150, minwidth=100, anchor=tk.CENTER)

        # Добавляем заголовки
        table.heading('#0', text='Точка', anchor=tk.CENTER)
        table.heading('I1', text='I1', anchor=tk.CENTER)
        table.heading('I2', text='I2', anchor=tk.CENTER)
        table.heading('centrality', text='Степень центральности', anchor=tk.CENTER)

        # Заполняем таблицу данными
        for metric in metrics:
            table.insert('', tk.END, text=metric['point'],
                         values=(metric['I1'], metric['I2'], metric['centrality']))

        # Отображаем таблицу
        table.pack(fill=tk.BOTH, expand=True)

        # Добавляем кнопку для экспорта в CSV
        export_button = tk.Button(table_window, text="Экспорт в CSV",
                                  command=lambda: self.export_metrics_to_csv(metrics))
        export_button.pack(pady=10)

    def export_metrics_to_csv(self, metrics):
        """
        Экспортирует метрики в CSV-файл.
        """
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Сохранить метрики как CSV"
        )

        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    # Записываем заголовки
                    writer.writerow(['Точка', 'I1', 'I2', 'Степень центральности'])
                    # Записываем данные
                    for metric in metrics:
                        writer.writerow([
                            metric['point'],
                            metric['I1'],
                            metric['I2'],
                            metric['centrality']
                        ])
                messagebox.showinfo("Экспорт успешен", f"Данные успешно экспортированы в {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка экспорта", f"Не удалось экспортировать данные: {str(e)}")


    def drag_stop(self, event):
        self.drag_data["item"] = None

    def add_input_node(self):
        node = Node('input', len(self.nodes))
        self.nodes.append(node)
        self.draw_node(node)

    def add_output_node(self):
        node = Node('output', len(self.nodes))
        self.nodes.append(node)
        self.draw_node(node)

    def add_aggregate(self):
        node = Node('aggregate', len(self.nodes))
        self.nodes.append(node)
        self.draw_node(node)

    def get_point_index(self, point_id):
        index = 0
        for node in self.nodes:
            for inp in node.inputs:
                if inp == point_id:
                    return index
                index += 1
            for out in node.outputs:
                if out == point_id:
                    return index
                index += 1
        return -1

    def mark_failed_elements(self, point_id, is_initial=False):
        if point_id in self.visited_points:
            return
        self.visited_points.add(point_id)

        # Get the node that owns this point
        node = self.get_node_by_point(point_id)
        if node:
            # Mark the node as failed
            node_items = self.canvas.find_withtag(f'node_{node.id}')
            for item in node_items:
                self.canvas.addtag_withtag('failed', item)

        point_items = self.canvas.find_withtag(f'out_{point_id}') or self.canvas.find_withtag(f'in_{point_id}')
        current_point_type = 'in' if self.canvas.find_withtag(f'in_{point_id}') else 'out'

        node = self.get_node_by_point(point_id)

        if current_point_type == 'in':
            # Mark all internal connections and output points connected to this input
            for conn in self.connections:
                start, end = conn
                if end == point_id:
                    # Check if this is an internal connection
                    internal_items = self.canvas.find_withtag(f'internal_conn_in_{node.id}_{start}_{end}')
                    if internal_items:
                        # Mark the internal connection
                        for item in internal_items:
                            self.canvas.addtag_withtag('failed', item)
                        # Mark the connected output point
                        out_items = self.canvas.find_withtag(f'out_{start}')
                        for item in out_items:
                            self.canvas.addtag_withtag('failed', item)
                        # Continue propagation from the output point
                        self.mark_failed_elements(start)
                    else:
                        # Handle regular connections
                        conn_items = self.canvas.find_withtag(f'conn_{start}_{end}')
                        if conn_items:
                            for item in conn_items:
                                self.canvas.addtag_withtag('failed', item)
                            out_items = self.canvas.find_withtag(f'out_{start}')
                            for item in out_items:
                                self.canvas.addtag_withtag('failed', item)
                            self.mark_failed_elements(start)

        else:  # output point
            # For aggregate output points, only look forward through conn connections
            if node.type == 'aggregate':
                # Check only regular outgoing connections
                for conn in self.connections:
                    if conn[0] == point_id:  # If this point is source
                        # Only handle conn_ connections, skip internal
                        conn_items = self.canvas.find_withtag(f'conn_{conn[0]}_{conn[1]}')
                        if conn_items:  # If regular connection exists
                            for item in conn_items:
                                self.canvas.addtag_withtag('failed', item)
                            connected_point = conn[1]
                            point_items = self.canvas.find_withtag(f'in_{connected_point}')
                            for item in point_items:
                                self.canvas.addtag_withtag('failed', item)
                            self.mark_failed_elements(connected_point)
            else:
                # For non-aggregate output points, mark the node and continue
                node_items = self.canvas.find_withtag(f'node_{node.id}')
                for item in node_items:
                    self.canvas.addtag_withtag('failed', item)

                # Check regular connections
                for conn in self.connections:
                    if conn[0] == point_id:  # If this point is source
                        conn_items = self.canvas.find_withtag(f'conn_{conn[0]}_{conn[1]}')
                        for item in conn_items:
                            self.canvas.addtag_withtag('failed', item)
                        connected_point = conn[1]
                        point_items = self.canvas.find_withtag(f'in_{connected_point}')
                        for item in point_items:
                            self.canvas.addtag_withtag('failed', item)
                        self.mark_failed_elements(connected_point)

    def color_failed_elements(self):
        all_items = self.canvas.find_all()
        for item in all_items:
            if 'failed' in self.canvas.gettags(item):
                item_type = self.canvas.type(item)
                if item_type == 'oval':
                    coords = self.canvas.coords(item)
                    center_x = (coords[0] + coords[2]) / 2
                    center_y = (coords[1] + coords[3]) / 2
                    width = coords[2] - coords[0]
                    height = coords[3] - coords[1]
                    new_width = width * 1.5
                    new_height = height * 1.5
                    new_coords = [
                        center_x - new_width / 2,
                        center_y - new_height / 2,
                        center_x + new_width / 2,
                        center_y + new_height / 2
                    ]
                    self.canvas.coords(item, *new_coords)
                    self.canvas.itemconfig(item, fill='red')
                elif item_type == 'polygon':
                    self.canvas.itemconfig(item, outline='red', width=2)
                elif item_type == 'line':
                    self.canvas.itemconfig(item, fill='red', width=2)

    def set_failure(self):
        self.previous_click_handler = self.canvas.bind('<Button-1>')
        self.canvas.unbind('<Button-1>')
        self.failure_mode = True
        self.root.config(cursor="crosshair")
        self.visited_points = set()

        def handle_failure_click(event):
            if not self.failure_mode:
                return

            clicked_items = self.canvas.find_closest(event.x, event.y)
            if not clicked_items:
                return

            tags = self.canvas.gettags(clicked_items[0])
            for tag in tags:
                if tag.startswith('out_'):
                    point_id = tag[4:]
                    self.visited_points.clear()
                    self.mark_failed_elements(point_id, True)
                    self.color_failed_elements()

                    self.failure_mode = False
                    self.root.config(cursor="")
                    self.canvas.bind('<Button-1>', self.canvas_click)
                    return

        self.canvas.bind('<Button-1>', handle_failure_click)

    def reset_failures(self):
        # Reset all items with 'failed' tag
        failed_items = self.canvas.find_withtag('failed')
        for item in failed_items:
            # Remove 'failed' tag
            tags = list(self.canvas.gettags(item))
            tags.remove('failed')
            self.canvas.dtag(item, 'failed')
            self.canvas.itemconfig(item, tags=tags)

            # Reset appearance based on item type
            item_type = self.canvas.type(item)

            if item_type == 'oval':
                # Reset point size and color
                tags = self.canvas.gettags(item)
                for tag in tags:
                    if tag.startswith('out_'):
                        self.canvas.itemconfig(item, fill='red')
                    elif tag.startswith('in_'):
                        self.canvas.itemconfig(item, fill='green')

                # Reset point size
                coords = self.canvas.coords(item)
                center_x = (coords[0] + coords[2]) / 2
                center_y = (coords[1] + coords[3]) / 2
                new_coords = [
                    center_x - 5,  # Original size was 10x10
                    center_y - 5,
                    center_x + 5,
                    center_y + 5
                ]
                self.canvas.coords(item, *new_coords)

            elif item_type == 'polygon':
                # Reset node appearance
                self.canvas.itemconfig(item, outline='#999999', width=2)

            elif item_type == 'line':
                # Reset connection appearance
                self.canvas.itemconfig(item, fill='orange', width=3)


    def reset_canvas(self):
        # Delete all elements from canvas
        self.canvas.delete("all")

        # Reset node counters
        Node.input_nodes = 0
        Node.output_nodes = 0
        Node.aggregate_nodes = 0

        # Reset all instance variables
        self.nodes = []
        for node in self.nodes:
            node.deleted = False
        self.connections = []
        self.failed_points = set()
        self.connection_mode = False
        self.connection_start = None
        self.selected_node = None
        self.selected_point_type = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.failure_mode = False
        self.visited_points = set()

        # Reset cursor and bindings
        self.root.config(cursor="")
        self.canvas.bind("<Button-1>", self.canvas_click)


    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    simulator = FailureSimulator()
    simulator.run()