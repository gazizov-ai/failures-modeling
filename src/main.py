import tkinter as tk
from tkinter import messagebox
import sys
from analysis import *
from rca_fta import *
from failures import *


class Node:
    """
    Класс, представляющий элемент в схеме сопряжения.
    Input - вход программной системы
    Output - выход программной системы
    Aggregate - информационный сервис
    """
    input_nodes = 0
    output_nodes = 0
    aggregate_nodes = 0
    def __init__(self, node_type, node_id):
        """
        Инициализирует новый узел.
        :param node_type: Тип узла ('input', 'output', 'aggregate')
        :param node_id: Уникальный числовой идентификатор элемента
        """
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
    """
    Основной класс программы.
    Управляет графическим интерфейсом, логикой моделирования отказов и анализом схемы сопряжения.
    """
    def __init__(self):
        """
        Инициализирует основное окно программы и настраивает начальное состояние.
        """
        self.root = tk.Tk()
        self.root.title("Структурные модели отказов")

        self.adjacency_matrix = None
        self.point_labels = None

        self.nodes = []
        self.connections = []
        self.failed_points = set()

        self.connection_mode = False
        self.connection_start = None
        self.selected_node = None
        self.selected_point_type = None
        self.drag_data = {"x": 0, "y": 0, "item": None}

        self.failure_mode = False

        self.delete_mode = False

        self.setup_gui()

    def setup_gui(self):
        """
        Настраивает графический интерфейс пользователя.
        Создает меню, холст и привязывает обработчики событий.
        """
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
        """
        Обработчик закрытия главного окна приложения.
        Запрашивает подтверждение перед выходом.
        """
        if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
            self.root.destroy()
            sys.exit(0)


    def create_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        """
        Создает скругленный прямоугольник на холсте, используя встроенный метод для создания полигонов.
        :param canvas: Холст
        :param x1: Координаты верхнего левого угла
        :param y1: Координаты верхнего левого угла
        :param x2: Координаты нижнего правого угла
        :param y2: Координаты нижнего правого угла
        :param radius: Радиус скругления углов
        :param kwargs: Прочие параметры для создания полигона
        :return: int: Идентификатор созданного объекта на холсте
        """
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
        """
        Отрисовывает узел на холсте.
        :param node: Узел для отрисовки
        """
        last_x = 100
        last_y = 300
        for existing_node in self.nodes[:-1]:
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

            in_id = f"{node.typeid}0"
            self.canvas.create_oval(x - 45, y - 5, x - 35, y + 5,
                                    tags=[f'in_{in_id}', f'point_of_{node.id}'], fill='green')

        else:
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

                self.canvas.create_oval(x - 45, y + y_offset - 5, x - 35, y + y_offset + 5,
                                        tags=[f'in_{in_id}', f'point_of_{node.id}'], fill='green')

                self.canvas.create_oval(x + 35, y + y_offset - 5, x + 45, y + y_offset + 5,
                                        tags=[f'out_{out_id}', f'point_of_{node.id}'], fill='red')
                self.canvas.create_text(x + 50, y + y_offset, text=out_id,
                                        fill='black', font=('Arial', 10), tags=f'out_{out_id}_text')

    def draw_connection(self, start_coords, end_coords, smooth, tags):
        """
        Рисует соединение между двумя точками, используя кубическую кривую Безье.
        :param start_coords: Координаты начальной точки
        :param end_coords: Координаты конечной точки
        :param smooth: True - если требуется кривая Безье, False - если требуется прямая между двумя точками (в агрегатах)
        :param tags: Теги для обращения к данному соединению
        :return:
        """
        ctrl_x1 = start_coords[0] + (end_coords[0] - start_coords[0]) * 0.4
        ctrl_x2 = start_coords[0] + (end_coords[0] - start_coords[0]) * 0.6

        if smooth:
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
        """
        Обработчик клика по холсту.
        Используется для выбора элементов и точек соединения.
        Если выбрана точка, то программа переходит в режим создания соединений.
        Если выбран элемент, то программа переходит в режим перетаскивания элемента.
        :param event: Событие клика мыши
        """
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
        """
        Метод для создания соединения и его записи в глобальный список соединений.
        :param point1: Начальная точка
        :param point2: Конечная точка
        :param swap: Если True, меняет конечную и начальную точку местами (во всех соединениях выходная точка идет первой)
        :param internal: Если True, отрисовывает вместо кривой Безье для внешних соединений простую прямую
        """
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

            input_coords = self.canvas.coords(end_item)
            text_x = input_coords[0] - 10
            text_y = (input_coords[1] + input_coords[3]) / 2
            self.canvas.create_text(text_x, text_y, text=out_point,
                                    fill='black', font=('Arial', 10), tags=f'in_{in_point}_text')

    def get_node_by_point(self, point_id):
        """
        Метод для получения экземпляра класса Node по ID точки, принадлежащей этому экземпляру.
        :param point_id: ID точки, для которой нужно определить принадлежность
        :return: Node: Элемент с искомой точкой
        """
        point_items = self.canvas.find_withtag(f'out_{point_id}') or self.canvas.find_withtag(f'in_{point_id}')
        if point_items:
            point_tags = self.canvas.gettags(point_items[0])
            for tag in point_tags:
                if tag.startswith('point_of_'):
                    node_id = int(tag.split('_')[-1])
                    node = self.nodes[node_id]
                    if not node.deleted:
                        return node
        return None

    def get_point_text(self, point_id, point_type):
        """
        Получить текстовую подпись с холста, принадлежащую данной точке.
        Необходим для динамического обновления ID входных точек, у которых ID изменяется после нового подключения.
        :param point_id: ID точки
        :param point_type: 'in' | 'out' - тип точки
        """
        text_items = self.canvas.find_withtag(f'{point_type}_{point_id}_text')
        if text_items:
            return self.canvas.itemcget(text_items[0], 'text')
        return None

    def parse_connection_tags(self, point_id):
        """
        Парсирует теги всех соединений на предмет наличия ID заданной точки
        :param point_id: ID точки
        :return: True, если точка присутствует хотя бы в одном соединении
        """
        all_items = self.canvas.find_all()
        for item in all_items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith('conn_'):
                    _, start, end = tag.split('_')
                    if point_id == start or point_id == end:
                        return True
        return False

    def set_delete_mode(self):
        """
        Активирует режим удаления элементов.
        Позволяет пользователю удалять элементы и соединения.
        """
        self.delete_mode = True
        self.root.config(cursor="X_cursor")
        self.canvas.bind('<Button-1>', self.handle_delete_click)

    def handle_delete_click(self, event):
        """
        Обрабатывает клик в режиме соединения.
        Удаляет выбранный узел или соединение.
        :param event: Событие клика мыши
        """
        if not self.delete_mode:
            return

        self.reset_failures()

        clicked_items = self.canvas.find_closest(event.x, event.y)
        if not clicked_items:
            return

        tags = self.canvas.gettags(clicked_items[0])

        for tag in tags:
            if tag.startswith('node_'):
                node_id = int(tag.split('_')[1])
                node = self.nodes[node_id]
                node.deleted = True

                connections_to_remove = []
                for conn in self.connections:
                    start, end = conn
                    if (any(start == out for out in node.outputs) or
                            any(end == inp for inp in node.inputs)):
                        self.canvas.delete(f'conn_{start}_{end}')
                        self.canvas.delete(f'internal_conn_in_{node_id}_{start}_{end}')
                        self.canvas.delete(f'text_in_{end}')
                        connections_to_remove.append(conn)

                for conn in connections_to_remove:
                    self.connections.remove(conn)

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

        for tag in tags:
            if tag.startswith('conn_'):
                _, start, end = tag.split('_')
                self.canvas.delete(f'conn_{start}_{end}')
                self.canvas.delete(f'text_in_{end}')
                self.connections.remove((start, end))
                return
            if tag.startswith('internal_conn_in_'):
                _, _, _, node_id, start, end = tag.split('_')
                self.canvas.delete(tag)
                if (start, end) in self.connections:
                    self.connections.remove((start, end))
                return


    def start_connection(self, point):
        """
        Активирует режим соединения.
        :param point: Начальная точка соединения
        """
        self.connection_mode = True
        self.connection_start = point
        self.root.config(cursor="cross")


    def stop_connection(self):
        """
        Отменяет создание нового соединения.
        """
        self.connection_mode = False
        self.connection_start = None
        self.selected_node = None
        self.root.config(cursor="")


    def exit_modes(self, event):
        """
        Выходит из всех специальных режимов (удаление, соединение, отказ).
        """
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
        """
        Начинает перетаскивание узла.
        :param event: Событие нажатие кнопки мыши
        """
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
        """
        Обновляет все соединения, связанные с перемещенным узлом.
        :param node: Перемещенный узел
        """
        for conn in self.connections:
            start_point, end_point = conn

            if node.type == 'input':
                input_point = f'0{node.typeid}'
                should_update = (start_point == input_point or end_point == input_point)
            else:
                should_update = (any(start_point == f"{node.typeid}{i}" for i in range(15)) or
                                 any(end_point == f"{node.typeid}{i}" for i in range(15)))

            if should_update:
                in_agg = self.get_node_by_point(start_point) != self.get_node_by_point(end_point)

                old_conn_tag = f'conn_{start_point}_{end_point}'
                old_internal_tag = f'internal_conn_in_{self.get_node_by_point(start_point).id}_{start_point}_{end_point}'

                was_failed = False
                if in_agg:
                    old_items = self.canvas.find_withtag(old_conn_tag)
                else:
                    old_items = self.canvas.find_withtag(old_internal_tag)

                if old_items:
                    was_failed = 'failed' in self.canvas.gettags(old_items[0])

                if in_agg:
                    self.canvas.delete(old_conn_tag)
                else:
                    self.canvas.delete(old_internal_tag)

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

                if was_failed:
                    self.canvas.addtag_withtag('failed', new_conn)
                    self.canvas.itemconfig(new_conn, fill='red', width=2)

    def drag(self, event):
        """
        Обрабатывает перетаскивание узла.
        :param event: Событие перемещения мыши
        """
        if self.connection_mode or self.drag_data["item"] is None:
            return

        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]

        node = self.nodes[self.drag_data["item"]]

        for item in self.canvas.find_withtag(f'node_{node.id}'):
            self.canvas.move(item, dx, dy)

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

        if node.type == 'input':
            out_id = f"0{node.typeid}"
            for item in self.canvas.find_withtag(f'out_{out_id}'):
                self.canvas.move(item, dx, dy)
            for item in self.canvas.find_withtag(f'out_{out_id}_text'):
                self.canvas.move(item, dx, dy)
        elif node.type == 'aggregate':
            for i in range(6):
                out_id = f"{node.typeid}{i + 1}"
                for item in self.canvas.find_withtag(f'out_{out_id}'):
                    self.canvas.move(item, dx, dy)
                for item in self.canvas.find_withtag(f'out_{out_id}_text'):
                    self.canvas.move(item, dx, dy)

        self.update_connections(node)

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        node.x += dx
        node.y += dy

    def get_internal_connections(self):
        """
        Получает список всех внутренних соединений на схеме сопряжения.
        :return: list: Cписок кортежей (начальная_точка, конечная_точка)
        """
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
        """
        Отображает матрицу смежности для текущей схемы сопряжения.
        Создает новое окно с визуализацией связей между точками.
        """
        show_adjacency_matrix(self)

    def build_analysis_table(self):
        build_analysis_table(self)

    def build_tree_base(self, connections, is_fta=True):
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
        build_tree_base(self, connections=connections, is_fta=is_fta)

    def build_fault_tree(self):
        """
        Строит дерево отказов FTA на основе текущей схемы сопряжения.
        """
        build_fault_tree(self)

    def build_rca_tree(self):
        """
        Строит дерево анализа коренных причин RCA на основе текущей схемы сопряжения.
        """
        build_rca_tree(self)

    def drag_stop(self, event):
        """
        Завершает перетаскивание узла.
        :param event: Событие отпускания кнопки мыши
        """
        self.drag_data["item"] = None

    def add_input_node(self):
        """
        Создает входной элемент и отрисовывает его на схеме сопряжения.
        """
        node = Node('input', len(self.nodes))
        self.nodes.append(node)
        self.draw_node(node)

    def add_output_node(self):
        """
        Создает выходной элемент и отрисовывает его на схеме сопряжения.
        """
        node = Node('output', len(self.nodes))
        self.nodes.append(node)
        self.draw_node(node)

    def add_aggregate(self):
        """
        Создает агрегат и отрисовывает его на схеме сопряжения.
        """
        node = Node('aggregate', len(self.nodes))
        self.nodes.append(node)
        self.draw_node(node)

    def mark_failed_elements(self, point_id):
        """
        Помечает элементы тегом failed, обозначающим отказ данного элемента системы.
        После выбора изначальной отказавшей точки проверяет распространение отказов.
        :param point_id: ID изначальной отказавшей точки
        """
        mark_failed_elements(self, point_id=point_id)

    def color_failed_elements(self):
        """
        Данный метод вызывается после разметки отказавших элементов для окраски вершин и соединений в красный цвет.
        Вершины также увеличиваются в размерах.
        """
        color_failed_elements(self)

    def set_failure(self):
        """
        Обработчик клика мыши в состоянии установки отказа.
        """
        set_failure(self)

    def reset_failures(self):
        """
        Сбрасывает все отказавшие элементы.
        """
        reset_failures(self)

    def reset_canvas(self):
        """
        Сбрасывает холст в изначальное состояние, очищая схему сопряжения.
        """
        self.canvas.delete("all")

        Node.input_nodes = 0
        Node.output_nodes = 0
        Node.aggregate_nodes = 0

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

        self.root.config(cursor="")
        self.canvas.bind("<Button-1>", self.canvas_click)


    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    simulator = FailureSimulator()
    simulator.run()