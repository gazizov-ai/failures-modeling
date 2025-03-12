import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import networkx as nx
import numpy as np


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

        self.setup_gui()

    def setup_gui(self):
        # Configure root window to be resizable
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Main container with grid
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=9)  # 90% for canvas
        main_frame.grid_columnconfigure(1, weight=1)  # 10% for buttons

        # Canvas setup - 90% width
        self.canvas = tk.Canvas(main_frame, bg='#DDDDDD', bd=1, relief='solid')
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Control frame - 10% width
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        control_frame.grid_rowconfigure(3, weight=1)  # Extra space at bottom

        self.canvas.bind("<Button-1>", self.canvas_click)
        # self.canvas.bind("<Button-3>", self.delete_node)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.drag_stop)


        ttk.Button(control_frame, text="Добавить входной узел",
                   command=self.add_input_node).pack(pady=5)
        ttk.Button(control_frame, text="Добавить выходной узел",
                   command=self.add_output_node).pack(pady=5)
        ttk.Button(control_frame, text="Добавить агрегат",
                   command=self.add_aggregate).pack(pady=5)
        ttk.Button(control_frame, text="Добавить отказ на узле",
                   command=self.set_failure).pack(pady=5)
        ttk.Button(control_frame, text="Матрица смежности",
                   command=self.show_adjacency_matrix).pack(pady=5)

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
            self.canvas.create_text(x + 50, y, text=out_id,
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
        if not tags:
            return

        for tag in tags:
            if (tag.startswith('out_') or tag.startswith('in_')) and not tag.endswith('_text'):
                point_id = tag[4:] if tag.startswith('out_') else tag[3:]
                point_type = 'out' if tag.startswith('out_') else 'in'
                clicked_node = self.get_node_by_point(point_id)

                # Handle clicks inside aggregate
                if clicked_node and clicked_node.type == 'aggregate':
                    print("a")
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
        print(out_point, in_point)
        if internal:
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
        # Find point on canvas by its tag
        point_items = self.canvas.find_withtag(f'out_{point_id}') or self.canvas.find_withtag(f'in_{point_id}')
        if point_items:
            # Get all tags of the found point
            point_tags = self.canvas.gettags(point_items[0])
            for tag in point_tags:
                # Find tag that identifies which node this point belongs to
                if tag.startswith('point_of_'):
                    node_id = int(tag.split('_')[-1])
                    return self.nodes[node_id]
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

    def delete_node(self, event):
        clicked_items = self.canvas.find_closest(event.x, event.y)
        if not clicked_items:
            return

        tags = self.canvas.gettags(clicked_items[0])
        for tag in tags:
            if tag.startswith('node_'):
                node_id = int(tag.split('_')[1])
                node = self.nodes[node_id]

                connections_to_remove = []
                for conn in self.connections:
                    start, end = conn
                    if (any(start == out for out in node.outputs) or
                            any(end == inp for inp in node.inputs)):
                        self.canvas.delete(f'conn_{start}_{end}')
                        # Delete input point text when connection is removed
                        self.canvas.delete(f'text_in_{end}')
                        connections_to_remove.append(conn)

                for conn in connections_to_remove:
                    self.connections.remove(conn)

                self.canvas.delete(f'node_{node.id}')
                for inp in node.inputs:
                    self.canvas.delete(f'in_{inp}')
                for out in node.outputs:
                    self.canvas.delete(f'out_{out}')

                self.nodes.remove(node)
                break


    def start_connection(self, point):
        self.connection_mode = True
        self.connection_start = point
        self.root.config(cursor="cross")


    def stop_connection(self):
        self.connection_mode = False
        self.connection_start = None
        self.selected_node = None
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

            # Check if this connection involves the moved node
            if (any(start_point == f"{node.typeid}{i}" for i in range(15)) or
                    any(end_point == f"{node.typeid}{i}" for i in range(15))):
                in_agg = self.get_node_by_point(start_point) != self.get_node_by_point(end_point)

                if in_agg:
                    self.canvas.delete(f'conn_{start_point}_{end_point}')
                else:
                    self.canvas.delete(f'internal_conn_in_{self.get_node_by_point(start_point).id}_{start_point}_{end_point}')

                # Create new connection line at updated position
                start_item = self.canvas.find_withtag(f'out_{start_point}')[0]
                end_item = self.canvas.find_withtag(f'in_{end_point}')[0]

                start_coords = self.canvas.coords(start_item)
                end_coords = self.canvas.coords(end_item)

                start_x = (start_coords[0] + start_coords[2]) / 2
                start_y = (start_coords[1] + start_coords[3]) / 2
                end_x = (end_coords[0] + end_coords[2]) / 2
                end_y = (end_coords[1] + end_coords[3]) / 2

                self.draw_connection([start_x, start_y], [end_x, end_y], in_agg,
                                     tags=f'conn_{start_point}_{end_point}' if in_agg else
                                     f'internal_conn_in_{self.get_node_by_point(start_point).id}_{start_point}_{end_point}'
                                     )

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
            # all_items = self.canvas.find_all()
            # for item in all_items:
            #     tags = self.canvas.gettags(item)
            #     for tag in tags:
            #         if tag.startswith(f'internal_conn_in_{node.id}'):
            #             self.canvas.move(item, dx, dy)

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

    def show_adjacency_matrix(self):
        # Collect only unique point IDs from nodes
        point_ids = set()

        for node in self.nodes:
            if node.type == 'input':
                point_ids.add(f"{node.id}0")
            elif node.type == 'output':
                point_ids.add(f"i{node.id}0")
            elif node.type == 'aggregate':
                for i in range(6):
                    point_ids.add(f"{node.id}{i}")
                    point_ids.add(f"i{node.id}{i}")

        point_ids = sorted(list(point_ids))
        size = len(point_ids)
        matrix = np.zeros((size, size))

        for conn in self.connections:
            from_idx = point_ids.index(conn[0])
            to_idx = point_ids.index(conn[1])
            matrix[from_idx][to_idx] = 1

        matrix_window = tk.Toplevel(self.root)
        matrix_window.title("Матрица смежности")

        for j, point_id in enumerate(point_ids):
            ttk.Label(matrix_window, text=point_id).grid(row=0, column=j + 1, padx=5, pady=5)

        for i, point_id in enumerate(point_ids):
            ttk.Label(matrix_window, text=point_id).grid(row=i + 1, column=0, padx=5, pady=5)
            for j in range(size):
                ttk.Label(matrix_window, text=f"{int(matrix[i][j])}").grid(row=i + 1, column=j + 1, padx=5, pady=5)

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

    def set_failure(self):
        pass

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

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    simulator = FailureSimulator()
    simulator.run()