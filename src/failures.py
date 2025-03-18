def mark_failed_elements(simulator, point_id):
    """
    Помечает элементы тегом failed, обозначающим отказ данного элемента системы.
    После выбора изначальной отказавшей точки проверяет распространение отказов.
    :param point_id: ID изначальной отказавшей точки
    """
    if point_id in simulator.visited_points:
        return
    simulator.visited_points.add(point_id)

    node = simulator.get_node_by_point(point_id)
    if node:
        node_items = simulator.canvas.find_withtag(f'node_{node.id}')
        for item in node_items:
            simulator.canvas.addtag_withtag('failed', item)

    current_point_type = 'in' if simulator.canvas.find_withtag(f'in_{point_id}') else 'out'

    node = simulator.get_node_by_point(point_id)

    if current_point_type == 'in':
        for conn in simulator.connections:
            start, end = conn
            if end == point_id:
                internal_items = simulator.canvas.find_withtag(f'internal_conn_in_{node.id}_{start}_{end}')
                if internal_items:
                    for item in internal_items:
                        simulator.canvas.addtag_withtag('failed', item)
                    out_items = simulator.canvas.find_withtag(f'out_{start}')
                    for item in out_items:
                        simulator.canvas.addtag_withtag('failed', item)
                    simulator.mark_failed_elements(start)
                else:
                    conn_items = simulator.canvas.find_withtag(f'conn_{start}_{end}')
                    if conn_items:
                        for item in conn_items:
                            simulator.canvas.addtag_withtag('failed', item)
                        out_items = simulator.canvas.find_withtag(f'out_{start}')
                        for item in out_items:
                            simulator.canvas.addtag_withtag('failed', item)
                        simulator.mark_failed_elements(start)

    else:
        if node.type == 'aggregate':
            for conn in simulator.connections:
                if conn[0] == point_id:
                    conn_items = simulator.canvas.find_withtag(f'conn_{conn[0]}_{conn[1]}')
                    if conn_items:
                        for item in conn_items:
                            simulator.canvas.addtag_withtag('failed', item)
                        connected_point = conn[1]
                        point_items = simulator.canvas.find_withtag(f'in_{connected_point}')
                        for item in point_items:
                            simulator.canvas.addtag_withtag('failed', item)
                        simulator.mark_failed_elements(connected_point)
        else:
            node_items = simulator.canvas.find_withtag(f'node_{node.id}')
            for item in node_items:
                simulator.canvas.addtag_withtag('failed', item)

            for conn in simulator.connections:
                if conn[0] == point_id:
                    conn_items = simulator.canvas.find_withtag(f'conn_{conn[0]}_{conn[1]}')
                    for item in conn_items:
                        simulator.canvas.addtag_withtag('failed', item)
                    connected_point = conn[1]
                    point_items = simulator.canvas.find_withtag(f'in_{connected_point}')
                    for item in point_items:
                        simulator.canvas.addtag_withtag('failed', item)
                    simulator.mark_failed_elements(connected_point)


def color_failed_elements(simulator):
    """
    Данный метод вызывается после разметки отказавших элементов для окраски вершин и соединений в красный цвет.
    Вершины также увеличиваются в размерах.
    """
    all_items = simulator.canvas.find_all()
    for item in all_items:
        if 'failed' in simulator.canvas.gettags(item):
            item_type = simulator.canvas.type(item)
            if item_type == 'oval':
                coords = simulator.canvas.coords(item)
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
                simulator.canvas.coords(item, *new_coords)
                simulator.canvas.itemconfig(item, fill='red')
            elif item_type == 'polygon':
                simulator.canvas.itemconfig(item, outline='red', width=2)
            elif item_type == 'line':
                simulator.canvas.itemconfig(item, fill='red', width=2)


def set_failure(simulator):
    """
    Обработчик клика мыши в состоянии установки отказа.
    """
    simulator.previous_click_handler = simulator.canvas.bind('<Button-1>')
    simulator.canvas.unbind('<Button-1>')
    simulator.failure_mode = True
    simulator.root.config(cursor="crosshair")
    simulator.visited_points = set()

    def handle_failure_click(event):
        if not simulator.failure_mode:
            return

        clicked_items = simulator.canvas.find_closest(event.x, event.y)
        if not clicked_items:
            return

        tags = simulator.canvas.gettags(clicked_items[0])
        for tag in tags:
            if tag.startswith('out_') and not tag.endswith('text'):
                point_id = tag[4:]
                simulator.visited_points.clear()
                simulator.mark_failed_elements(point_id)
                simulator.color_failed_elements()

                simulator.failure_mode = False
                simulator.root.config(cursor="")
                simulator.canvas.bind('<Button-1>', simulator.canvas_click)
                return

    simulator.canvas.bind('<Button-1>', handle_failure_click)


def reset_failures(simulator):
    """
    Сбрасывает все отказавшие элементы.
    """
    failed_items = simulator.canvas.find_withtag('failed')
    for item in failed_items:
        tags = list(simulator.canvas.gettags(item))
        tags.remove('failed')
        simulator.canvas.dtag(item, 'failed')
        simulator.canvas.itemconfig(item, tags=tags)

        item_type = simulator.canvas.type(item)

        if item_type == 'oval':
            tags = simulator.canvas.gettags(item)
            for tag in tags:
                if tag.startswith('out_'):
                    simulator.canvas.itemconfig(item, fill='red')
                elif tag.startswith('in_'):
                    simulator.canvas.itemconfig(item, fill='green')

            coords = simulator.canvas.coords(item)
            center_x = (coords[0] + coords[2]) / 2
            center_y = (coords[1] + coords[3]) / 2
            new_coords = [
                center_x - 5,
                center_y - 5,
                center_x + 5,
                center_y + 5
            ]
            simulator.canvas.coords(item, *new_coords)

        elif item_type == 'polygon':
            simulator.canvas.itemconfig(item, outline='#999999', width=2)

        elif item_type == 'line':
            simulator.canvas.itemconfig(item, fill='orange', width=3)